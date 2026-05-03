"""
utils/auth.py
Authentication: login, register, session management, role-based access.
Passwords hashed with bcrypt via passlib.
"""

from __future__ import annotations

import streamlit as st
from passlib.hash import bcrypt
from datetime import datetime, timedelta
from typing import Optional

from utils.sheets import (
    read_sheet, append_row, update_row, new_id, now_str, today_str
)


# ─── Password helpers ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.verify(plain, hashed)
    except Exception:
        return False


# ─── User lookup ──────────────────────────────────────────────────────────────

def get_user_by_email(email: str) -> Optional[dict]:
    df = read_sheet("Users")
    if df.empty or "email" not in df.columns:
        return None
    df["email"] = df["email"].astype(str).str.lower()
    row = df[df["email"] == email.lower()]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


# ─── Auth actions ─────────────────────────────────────────────────────────────

def login_user(email: str, password: str) -> dict:
    """Verify credentials and return user dict on success."""
    user = get_user_by_email(email)
    if user is None:
        return {"success": False, "message": "Email not found."}
    if str(user.get("is_active", "TRUE")).upper() not in ("TRUE", "1", "YES"):
        return {"success": False, "message": "Account is disabled."}
    if not verify_password(password, str(user.get("password_hash", ""))):
        return {"success": False, "message": "Incorrect password."}
    return {"success": True, "user": user}


def logout_user():
    for key in ["logged_in", "user", "selected_building"]:
        st.session_state.pop(key, None)


def register_user(
    name: str, email: str, phone: str, pg_name: str, password: str
) -> dict:
    """Create a new owner account with a 30-day trial."""
    existing = get_user_by_email(email)
    if existing:
        return {"success": False, "message": "Email already registered."}

    user_id = new_id()
    trial_start = today_str()
    expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

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

    # Create default settings
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
    return {"success": True, "user": user}


# ─── Access guards ─────────────────────────────────────────────────────────────

def require_login():
    """Stop page render if user is not logged in."""
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
