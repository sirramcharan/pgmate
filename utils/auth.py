"""
utils/auth.py
Authentication: login, register, session management, role-based access.

Persistent login strategy (Instagram-style):
  - On login: generate a UUID session token, save to Users sheet (session_token col)
  - Token is placed in st.query_params["s"] so it survives page reloads
  - On every page load: if session_state is empty, read ?s= token, look up user, restore session
  - On logout: clear token from sheet + query params
"""

from __future__ import annotations

import bcrypt as _bcrypt
import streamlit as st
import uuid
from datetime import datetime, timedelta
from typing import Optional

from utils.sheets import (
    read_sheet, append_row, update_row, new_id, now_str, today_str
)


# ─── Password helpers ───────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ─── Token helpers ─────────────────────────────────────────────────────────────────

def _generate_token() -> str:
    return str(uuid.uuid4())


def _save_token(email: str, token: str):
    """Write session_token column in Users sheet for this email."""
    update_row("Users", "email", email.lower(), {"session_token": token})


def _clear_token(email: str):
    """Wipe the session_token in Users sheet on logout."""
    update_row("Users", "email", email.lower(), {"session_token": ""})


def _set_url_token(token: str):
    """Put token in the browser URL as ?s=<token> so it survives reload."""
    try:
        st.query_params["s"] = token
    except Exception:
        pass


def _clear_url_token():
    try:
        st.query_params.clear()
    except Exception:
        pass


def _get_url_token() -> Optional[str]:
    try:
        return st.query_params.get("s") or None
    except Exception:
        return None


# ─── User lookup ───────────────────────────────────────────────────────────────────────────

def get_user_by_email(email: str) -> Optional[dict]:
    df = read_sheet("Users")
    if df.empty or "email" not in df.columns:
        return None
    df["email"] = df["email"].astype(str).str.lower()
    row = df[df["email"] == email.lower()]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def _get_user_by_token(token: str) -> Optional[dict]:
    """Look up a user by their session_token column."""
    df = read_sheet("Users")
    if df.empty or "session_token" not in df.columns:
        return None
    df["session_token"] = df["session_token"].astype(str)
    row = df[df["session_token"] == token]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


# ─── Session restore on reload ───────────────────────────────────────────────────────────

def restore_session_from_cookie():
    """
    Called at the top of every page.
    If session is empty, reads ?s= token from URL and silently restores the session.
    This is the same pattern used by web apps like Instagram:
      browser stores a token → sent on every request → server validates it.
    Here the URL query param acts as the persistent token carrier.
    """
    if st.session_state.get("logged_in"):
        return
    token = _get_url_token()
    if not token:
        return
    user = _get_user_by_token(token)
    if user and str(user.get("is_active", "TRUE")).upper() in ("TRUE", "1", "YES"):
        st.session_state["logged_in"] = True
        st.session_state["user"] = user


# ─── Auth actions ───────────────────────────────────────────────────────────────────────────

def login_user(email: str, password: str) -> dict:
    """Verify credentials, issue a session token, return user dict on success."""
    user = get_user_by_email(email)
    if user is None:
        return {"success": False, "message": "Email not found."}
    if str(user.get("is_active", "TRUE")).upper() not in ("TRUE", "1", "YES"):
        return {"success": False, "message": "Account is disabled."}
    if not verify_password(password, str(user.get("password_hash", ""))):
        return {"success": False, "message": "Incorrect password."}
    # Issue token
    token = _generate_token()
    _save_token(email, token)
    _set_url_token(token)
    return {"success": True, "user": user}


def logout_user():
    email = st.session_state.get("user", {}).get("email", "")
    if email:
        _clear_token(email)
    _clear_url_token()
    for key in ["logged_in", "user", "selected_building"]:
        st.session_state.pop(key, None)


def register_user(
    name: str, email: str, phone: str, pg_name: str, password: str
) -> dict:
    """Create a new owner account with a 1-day trial."""
    existing = get_user_by_email(email)
    if existing:
        return {"success": False, "message": "Email already registered."}

    user_id = new_id()
    trial_start = today_str()
    expiry = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    token = _generate_token()

    user = {
        "user_id": user_id,
        "name": name,
        "email": email,
        "phone": phone,
        "password_hash": hash_password(password),
        "role": "Owner",
        "pg_name": pg_name,
        "subscription_status": "Trial",
        "plan_name": "Trial",
        "trial_start_date": trial_start,
        "expiry_date": expiry,
        "razorpay_customer_id": "",
        "razorpay_subscription_id": "",
        "payment_link": "",
        "is_active": "TRUE",
        "session_token": token,
        "created_at": now_str(),
    }
    ok = append_row("Users", user)
    if not ok:
        return {"success": False, "message": "Failed to create account."}

    append_row(
        "Settings",
        {
            "setting_id": new_id(),
            "owner_email": email,
            "default_rent_due_day": "5",
            "grace_period_days": "3",
            "auto_reminder_enabled": "FALSE",
            "late_fee_enabled": "FALSE",
            "late_fee_amount": "0",
            "created_at": now_str(),
            "updated_at": now_str(),
        },
    )
    _set_url_token(token)
    return {"success": True, "user": user}


# ─── Access guards ───────────────────────────────────────────────────────────────────────────

def require_login():
    """
    Stop page render if user is not logged in.
    Tries to restore session from URL token first.
    """
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
