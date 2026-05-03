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
    # Expired or Blocked → not allowed

    if allowed:
        return False  # not blocked

    # ── Blocked UI ────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style='text-align:center; padding:3rem 1rem;'>
            <h1 style='color:#ef4444; font-size:2rem;'>🔒 Subscription Expired</h1>
            <p style='color:#b8b1d9; font-size:1.1rem; max-width:500px; margin:auto;'>
                Your LayZ subscription has expired or is inactive.
                Please renew to continue managing your PG.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.divider()
        plan = user.get("plan_name", "—")
        exp_display = expiry_str if expiry_str else "Unknown"
        status_color = "#ef4444"

        st.markdown(
            f"""
            <div style='background:#1e1a2e; border:1px solid #3d3558; border-radius:12px; padding:1.5rem;'>
                <p style='color:#b8b1d9; margin:0;'>Status</p>
                <h3 style='color:{status_color}; margin:4px 0 1rem 0;'>{status}</h3>
                <p style='color:#b8b1d9; margin:0;'>Plan</p>
                <p style='color:#f5f3ff; margin:4px 0 1rem 0;'>{plan}</p>
                <p style='color:#b8b1d9; margin:0;'>Expiry Date</p>
                <p style='color:#f5f3ff; margin:4px 0;'>{exp_display}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        try:
            payment_link = st.secrets["razorpay"]["payment_link"]
        except Exception:
            payment_link = "https://rzp.io/your-payment-link"

        plan_name = ""
        monthly_price = "499"
        try:
            plan_name = st.secrets["razorpay"]["plan_name"]
            monthly_price = st.secrets["razorpay"]["monthly_price"]
        except Exception:
            pass

        st.markdown(
            f"""
            <div style='text-align:center;'>
                <a href='{payment_link}' target='_blank'>
                    <button style='background:#8b5cf6; color:#fff; border:none; border-radius:8px;
                        padding:0.75rem 2rem; font-size:1rem; cursor:pointer; font-weight:700;'>
                        💳 Pay ₹{monthly_price}/mo – Renew Now
                    </button>
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🔄 I have paid – Refresh Status", use_container_width=True):
            # Re-fetch user from sheet to pick up webhook updates
            from utils.sheets import read_sheet
            df = read_sheet("Users")
            if not df.empty and "email" in df.columns:
                row = df[df["email"] == user.get("email", "")]
                if not row.empty:
                    st.session_state.user = row.iloc[0].to_dict()
                    st.success("Status refreshed. Reloading…")
                    st.rerun()
            st.info("No change detected. Please contact support if your payment was successful.")

    return True  # blocked


# ── Webhook-ready stub ────────────────────────────────────────────────────────

def handle_razorpay_webhook(payload: dict):
    """
    TODO: Mount this on a separate FastAPI or Flask endpoint to receive Razorpay
    subscription webhook events.

    Events to handle:
    - subscription.activated  → set status=Active, update expiry_date
    - subscription.charged    → set status=Active, update expiry_date
    - subscription.cancelled  → set status=Expired
    - subscription.halted     → set status=Blocked

    Example:
        email = payload["payload"]["subscription"]["entity"]["notes"]["owner_email"]
        sub_id = payload["payload"]["subscription"]["entity"]["id"]
        event = payload["event"]
        # Update Users sheet accordingly
    """
    pass
