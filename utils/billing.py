"""
utils/billing.py
Subscription gating for LayZ.
Checks user's subscription_status and expiry_date.
Returns True (blocked) or False (allowed).
"""

from __future__ import annotations

import streamlit as st
from datetime import datetime, date
from typing import Optional


def _parse_date(date_str: str) -> Optional[date]:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(date_str).strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _get_secret(section: str, key: str, default: str = "") -> str:
    """Safely read a secret — never raises KeyError."""
    try:
        return str(st.secrets[section][key])
    except Exception:
        return default


def check_subscription(user: dict) -> bool:
    """
    Check if user has a valid subscription.
    Returns True if BLOCKED (should not see app), False if access allowed.
    Shows billing UI when blocked.
    """
    status = str(user.get("subscription_status", "Trial")).strip()
    expiry_str = str(user.get("expiry_date", "")).strip()
    expiry = _parse_date(expiry_str)
    today = date.today()

    allowed = False
    if status == "Active":
        allowed = expiry is None or expiry >= today
    elif status == "Trial":
        allowed = expiry is None or expiry >= today

    if allowed:
        return False  # not blocked

    # ── Blocked UI ────────────────────────────────────────────────────────────
    payment_link = _get_secret("razorpay", "payment_link", "#")
    monthly_price = _get_secret("razorpay", "monthly_price", "1499")
    plan = user.get("plan_name") or "—"
    exp_display = expiry_str if expiry_str else "Unknown"

    st.html(f"""
    <style>
        .blocked-wrap {{
            text-align: center;
            padding: 3rem 1rem 1rem 1rem;
        }}
        .blocked-wrap h1 {{
            color: #ef4444;
            font-size: 2rem;
        }}
        .blocked-wrap p {{
            color: #b8b1d9;
            font-size: 1.1rem;
            max-width: 500px;
            margin: 0.5rem auto 0 auto;
        }}
        .sub-info-card {{
            background: #1e1a2e;
            border: 1px solid #3d3558;
            border-radius: 12px;
            padding: 1.5rem;
            max-width: 420px;
            margin: 1rem auto;
        }}
        .sub-info-card .si-label {{
            color: #b8b1d9;
            margin: 0;
            font-size: 0.85rem;
        }}
        .sub-info-card .si-value {{
            color: #f5f3ff;
            margin: 2px 0 1rem 0;
            font-weight: 700;
        }}
        .sub-info-card .si-status {{
            color: #ef4444;
            font-size: 1.2rem;
            margin: 2px 0 1rem 0;
            font-weight: 700;
        }}
        .pay-btn-wrap {{
            text-align: center;
            margin: 1.5rem auto;
            max-width: 420px;
        }}
        .pay-btn {{
            background: #8b5cf6;
            color: #fff;
            border: none;
            border-radius: 8px;
            padding: 0.75rem 2rem;
            font-size: 1rem;
            cursor: pointer;
            font-weight: 700;
            text-decoration: none;
            display: inline-block;
        }}
    </style>

    <div class="blocked-wrap">
        <h1>&#128274; Subscription Expired</h1>
        <p>Your LayZ trial has ended. Subscribe to continue managing your PG.</p>
    </div>

    <div class="sub-info-card">
        <p class="si-label">Status</p>
        <p class="si-status">{status}</p>
        <p class="si-label">Plan</p>
        <p class="si-value">{plan}</p>
        <p class="si-label">Expiry Date</p>
        <p class="si-value">{exp_display}</p>
    </div>

    <div class="pay-btn-wrap">
        <a class="pay-btn" href="{payment_link}" target="_blank">
            &#128179; Pay &#8377;{monthly_price}/mo &ndash; Subscribe Now
        </a>
    </div>
    """)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("\U0001f504 I have paid \u2013 Refresh Status", use_container_width=True):
            _refresh_user_status(user)

    return True  # blocked


def _refresh_user_status(user: dict):
    """Re-read the Users sheet and update session state."""
    try:
        from utils.sheets import read_sheet
        df = read_sheet("Users")
        if df.empty or "email" not in df.columns:
            st.info("Could not reach the database. Try again in a moment.")
            return
        email = str(user.get("email", "")).strip().lower()
        df["email"] = df["email"].astype(str).str.strip().str.lower()
        row = df[df["email"] == email]
        if row.empty:
            st.info("User not found. Contact support.")
            return
        updated_user = row.iloc[0].to_dict()
        new_status = str(updated_user.get("subscription_status", "")).strip()
        if new_status == "Active":
            st.session_state.user = updated_user
            st.success("✅ Subscription activated! Reloading…")
            st.rerun()
        else:
            st.warning(
                f"Status is still **{new_status}**. "
                "If you just paid, please wait a minute and try again, "
                "or contact support."
            )
    except Exception as e:
        st.error(f"Refresh failed: {e}")


# ── Webhook-ready stub ────────────────────────────────────────────────────────

def handle_razorpay_webhook(payload: dict):
    """
    TODO: Mount on a FastAPI/Flask endpoint to receive Razorpay webhook events.
    Events: subscription.activated, subscription.charged,
            subscription.cancelled, subscription.halted
    """
    pass
