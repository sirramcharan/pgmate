"""
utils/auth.py
Authentication: login, register, session management, role-based access.
Passwords hashed with bcrypt (direct, passlib-free — Python 3.14 compatible).
Login persists across reloads via a browser cookie (extra-streamlit-components).
"""

from __future__ import annotations

import bcrypt as _bcrypt
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional

from utils.sheets import (
    read_sheet, append_row, update_row, new_id, now_str, today_str
)

# Cookie name stored in the browser
_COOKIE_NAME = "layz_auth"
_COOKIE_EXPIRY_DAYS = 30


# ─── Cookie manager (lazy singleton) ──────────────────────────────────────────────────────

def _get_cookie_manager():
    """Return a CookieManager instance (cached in session_state to avoid duplicates)."""
    if "_cookie_manager" not in st.session_state:
        try:
            import extra_streamlit_components as stx
            st.session_state["_cookie_manager"] = stx.CookieManager(key="layz_cm")
        except Exception:
            st.session_state["_cookie_manager"] = None
    return st.session_state["_cookie_manager"]


def _read_cookie() -> Optional[str]:
    """Return the saved email from the browser cookie, or None."""
    cm = _get_cookie_manager()
    if cm is None:
        return None
    try:
        return cm.get(_COOKIE_NAME) or None
    except Exception:
        return None


def _write_cookie(email: str):
    """Persist the logged-in email in a browser cookie for 30 days."""
    cm = _get_cookie_manager()
    if cm is None:
        return
    try:
        cm.set(
            _COOKIE_NAME,
            email,
            expires_at=datetime.now() + timedelta(days=_COOKIE_EXPIRY_DAYS),
        )
    except Exception:
        pass


def _delete_cookie():
    """Remove the auth cookie on logout."""
    cm = _get_cookie_manager()
    if cm is None:
        return
    try:
        cm.delete(_COOKIE_NAME)
    except Exception:
        pass


# ─── Password helpers ────────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


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


# ─── Session hydration from cookie ─────────────────────────────────────────────────────────────

def restore_session_from_cookie():
    """
    Called at the top of every page (via require_login).
    If session is empty but a valid cookie exists, silently re-logs the user in.
    """
    if st.session_state.get("logged_in"):
        return  # already active
    email = _read_cookie()
    if not email:
        return
    user = get_user_by_email(email)
    if user and str(user.get("is_active", "TRUE")).upper() in ("TRUE", "1", "YES"):
        st.session_state["logged_in"] = True
        st.session_state["user"] = user


# ─── Auth actions ───────────────────────────────────────────────────────────────────────────

def login_user(email: str, password: str) -> dict:
    """Verify credentials, persist cookie, return user dict on success."""
    user = get_user_by_email(email)
    if user is None:
        return {"success": False, "message": "Email not found."}
    if str(user.get("is_active", "TRUE")).upper() not in ("TRUE", "1", "YES"):
        return {"success": False, "message": "Account is disabled."}
    if not verify_password(password, str(user.get("password_hash", ""))):
        return {"success": False, "message": "Incorrect password."}
    # ✓ Credentials valid — write cookie so reloads stay logged in
    _write_cookie(email.lower())
    return {"success": True, "user": user}


def logout_user():
    _delete_cookie()
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
    # Auto-login after registration
    _write_cookie(email.lower())
    return {"success": True, "user": user}


# ─── Access guards ───────────────────────────────────────────────────────────────────────────

def require_login():
    """Stop page render if user is not logged in.
    Tries to restore session from cookie first before blocking.
    """
    restore_session_from_cookie()
    if not st.session_state.get("logged_in"):
        st.warning("Please log in to access this page.")
        st.stop()


def get_current_user() -> dict:
    return st.session_state.get("user", {})


def require_role(*roles: str):
    """Block page if logged-in user role is not in `roles`."""
    user = get_current_user()
    if user.get("role") not in roles:
        st.error("You do not have permission to view this page.")
        st.stop()


def is_owner() -> bool:
    return get_current_user().get("role") == "Owner"
