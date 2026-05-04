"""
utils/auth.py
Authentication helpers for LayZ.

Persistent login:
  - On login  : UUID token saved to sheet (bypassing cache) + set in st.query_params['s']
  - On reload : app.py calls restore_session_from_cookie() which reads ?s= and does a
                DIRECT (no-cache) sheet lookup to validate and restore the session.
  - query_params persist across Streamlit page navigation in multipage apps.
"""

from __future__ import annotations

import bcrypt as _bcrypt
import streamlit as st
import uuid
from datetime import datetime, timedelta
from typing import Optional

import gspread
from utils.sheets import (
    read_sheet, append_row, update_row, new_id, now_str, today_str,
    get_sheet, SHEET_HEADERS, _invalidate_cache
)


# ─── Password helpers ───────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ─── Direct (no-cache) sheet read for auth ────────────────────────────

def _read_users_direct() -> list[dict]:
    """Read Users sheet directly from Google Sheets, skipping st.cache_data."""
    ws = get_sheet("Users")
    if ws is None:
        return []
    try:
        return ws.get_all_records()
    except Exception:
        return []


def _get_user_by_token_direct(token: str) -> Optional[dict]:
    """Lookup user by session_token WITHOUT using the cache."""
    if not token or token == "None":
        return None
    rows = _read_users_direct()
    for row in rows:
        if str(row.get("session_token", "")).strip() == token.strip():
            return row
    return None


def _get_user_by_email_direct(email: str) -> Optional[dict]:
    """Lookup user by email WITHOUT using the cache."""
    rows = _read_users_direct()
    for row in rows:
        if str(row.get("email", "")).strip().lower() == email.strip().lower():
            return row
    return None


# ─── Session restore ─────────────────────────────────────────────────

def restore_session_from_cookie():
    """
    Called at the top of app.py on every run.
    Reads ?s= from query params and restores session if valid.
    Uses a direct sheet read (no cache) so a freshly-written token is always found.
    """
    if st.session_state.get("logged_in"):
        return  # already logged in, nothing to do

    token = st.query_params.get("s")
    if not token:
        return

    user = _get_user_by_token_direct(token)
    if user and str(user.get("is_active", "TRUE")).upper() in ("TRUE", "1", "YES"):
        st.session_state["logged_in"] = True
        st.session_state["user"] = user


# kept for import compatibility
def render_token_reader():
    pass


def _write_token_to_storage(token: str):
    pass


# ─── Auth actions ─────────────────────────────────────────────────

def login_user(email: str, password: str) -> dict:
    user = _get_user_by_email_direct(email)
    if user is None:
        return {"success": False, "message": "Email not found."}
    if str(user.get("is_active", "TRUE")).upper() not in ("TRUE", "1", "YES"):
        return {"success": False, "message": "Account is disabled."}
    if not verify_password(password, str(user.get("password_hash", ""))):
        return {"success": False, "message": "Incorrect password."}

    token = str(uuid.uuid4())
    # Write token directly to sheet (bypass cache)
    ws = get_sheet("Users")
    if ws:
        try:
            rows = ws.get_all_records()
            headers = ws.row_values(1)
            for i, row in enumerate(rows):
                if str(row.get("email", "")).strip().lower() == email.strip().lower():
                    token_col = headers.index("session_token") + 1
                    ws.update_cell(i + 2, token_col, token)
                    _invalidate_cache("Users")
                    break
        except Exception as e:
            st.error(f"Token write error: {e}")

    # Set token in query params — persists across page navigation
    st.query_params["s"] = token
    return {"success": True, "user": user}


def logout_user():
    email = st.session_state.get("user", {}).get("email", "")
    if email:
        ws = get_sheet("Users")
        if ws:
            try:
                rows = ws.get_all_records()
                headers = ws.row_values(1)
                for i, row in enumerate(rows):
                    if str(row.get("email", "")).strip().lower() == email.strip().lower():
                        if "session_token" in headers:
                            token_col = headers.index("session_token") + 1
                            ws.update_cell(i + 2, token_col, "")
                            _invalidate_cache("Users")
                        break
            except Exception:
                pass
    try:
        st.query_params.clear()
    except Exception:
        pass
    for key in ["logged_in", "user", "selected_building"]:
        st.session_state.pop(key, None)


def get_user_by_email(email: str) -> Optional[dict]:
    return _get_user_by_email_direct(email)


def register_user(name: str, email: str, phone: str, pg_name: str, password: str) -> dict:
    existing = _get_user_by_email_direct(email)
    if existing:
        return {"success": False, "message": "Email already registered."}

    user_id = new_id()
    token = str(uuid.uuid4())
    expiry = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    user = {
        "user_id": user_id, "name": name, "email": email, "phone": phone,
        "password_hash": hash_password(password), "role": "Owner",
        "pg_name": pg_name, "subscription_status": "Trial", "plan_name": "Trial",
        "trial_start_date": today_str(), "expiry_date": expiry,
        "razorpay_customer_id": "", "razorpay_subscription_id": "",
        "payment_link": "", "is_active": "TRUE",
        "session_token": token, "created_at": now_str(),
    }
    ok = append_row("Users", user)
    if not ok:
        return {"success": False, "message": "Failed to create account."}

    append_row("Settings", {
        "setting_id": new_id(), "owner_email": email,
        "default_rent_due_day": "5", "grace_period_days": "3",
        "auto_reminder_enabled": "FALSE", "late_fee_enabled": "FALSE",
        "late_fee_amount": "0", "created_at": now_str(), "updated_at": now_str(),
    })
    st.query_params["s"] = token
    return {"success": True, "user": user}


# ─── Access guards ─────────────────────────────────────────────────

def require_login():
    restore_session_from_cookie()
    if not st.session_state.get("logged_in"):
        st.warning("Please log in to access this page.")
        st.stop()


def get_current_user() -> dict:
    return st.session_state.get("user", {})


def require_role(*roles: str):
    user = get_current_user()
    if user.get("role") not in roles:
        st.error("You do not have permission to view this page.")
        st.stop()


def is_owner() -> bool:
    return get_current_user().get("role") == "Owner"
