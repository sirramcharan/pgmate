"""
utils/auth.py
Authentication: login, register, session management, role-based access.

Persistent login strategy:
  - On login: generate UUID token, save to Users sheet (session_token col)
  - Token is written to browser localStorage via a JS component
  - On every page load: JS reads localStorage, posts token back to Streamlit
  - Session is silently restored without any login prompt
"""

from __future__ import annotations

import bcrypt as _bcrypt
import streamlit as st
import streamlit.components.v1 as components
import uuid
from datetime import datetime, timedelta
from typing import Optional

from utils.sheets import (
    read_sheet, append_row, update_row, new_id, now_str, today_str
)

_TOKEN_KEY = "layz_session_token"


# ─── Password helpers ────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ─── localStorage JS bridge ────────────────────────────────────────────

def _write_token_to_storage(token: str):
    """Inject JS that writes the token to localStorage."""
    components.html(
        f"""
        <script>
            localStorage.setItem('{_TOKEN_KEY}', '{token}');
        </script>
        """,
        height=0,
    )


def _clear_token_from_storage():
    """Inject JS that removes the token from localStorage."""
    components.html(
        f"""
        <script>
            localStorage.removeItem('{_TOKEN_KEY}');
        </script>
        """,
        height=0,
    )


def render_token_reader():
    """
    Must be called once at the top of app.py (before any session checks).
    Renders a hidden iframe that reads localStorage and posts the token
    back into st.query_params so Python can read it.
    Only fires when session is not already active.
    """
    if st.session_state.get("logged_in"):
        return
    if st.session_state.get("_token_read_done"):
        return

    token_from_url = st.query_params.get("s")
    if token_from_url:
        # Already have it from a previous cycle, restore session
        _restore_from_token(token_from_url)
        st.session_state["_token_read_done"] = True
        return

    # Inject JS to read localStorage and redirect with ?s=token
    components.html(
        f"""
        <script>
            const token = localStorage.getItem('{_TOKEN_KEY}');
            if (token) {{
                const url = new URL(window.parent.location.href);
                url.searchParams.set('s', token);
                window.parent.location.replace(url.toString());
            }}
        </script>
        """,
        height=0,
    )


# ─── User lookup ──────────────────────────────────────────────────────

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
    df = read_sheet("Users")
    if df.empty or "session_token" not in df.columns:
        return None
    df["session_token"] = df["session_token"].astype(str)
    row = df[df["session_token"] == token]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def _restore_from_token(token: str):
    """Given a token string, look up the user and restore session_state."""
    user = _get_user_by_token(token)
    if user and str(user.get("is_active", "TRUE")).upper() in ("TRUE", "1", "YES"):
        st.session_state["logged_in"] = True
        st.session_state["user"] = user


def restore_session_from_cookie():
    """
    Called at the top of every page via require_login().
    Checks ?s= query param (set by the JS localStorage bridge in render_token_reader).
    """
    if st.session_state.get("logged_in"):
        return
    token = st.query_params.get("s")
    if token:
        _restore_from_token(token)


# ─── Auth actions ──────────────────────────────────────────────────────

def login_user(email: str, password: str) -> dict:
    user = get_user_by_email(email)
    if user is None:
        return {"success": False, "message": "Email not found."}
    if str(user.get("is_active", "TRUE")).upper() not in ("TRUE", "1", "YES"):
        return {"success": False, "message": "Account is disabled."}
    if not verify_password(password, str(user.get("password_hash", ""))):
        return {"success": False, "message": "Incorrect password."}
    token = str(uuid.uuid4())
    update_row("Users", "email", email.lower(), {"session_token": token})
    # Store token in session so app.py can write it to localStorage after rerun
    st.session_state["_pending_token"] = token
    st.query_params["s"] = token
    return {"success": True, "user": user}


def logout_user():
    email = st.session_state.get("user", {}).get("email", "")
    if email:
        update_row("Users", "email", email.lower(), {"session_token": ""})
    try:
        st.query_params.clear()
    except Exception:
        pass
    for key in ["logged_in", "user", "selected_building", "_token_read_done", "_pending_token"]:
        st.session_state.pop(key, None)


def register_user(name: str, email: str, phone: str, pg_name: str, password: str) -> dict:
    existing = get_user_by_email(email)
    if existing:
        return {"success": False, "message": "Email already registered."}

    user_id = new_id()
    token = str(uuid.uuid4())
    expiry = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

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
        "trial_start_date": today_str(),
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

    append_row("Settings", {
        "setting_id": new_id(), "owner_email": email,
        "default_rent_due_day": "5", "grace_period_days": "3",
        "auto_reminder_enabled": "FALSE", "late_fee_enabled": "FALSE",
        "late_fee_amount": "0", "created_at": now_str(), "updated_at": now_str(),
    })
    st.session_state["_pending_token"] = token
    st.query_params["s"] = token
    return {"success": True, "user": user}


# ─── Access guards ──────────────────────────────────────────────────────

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
