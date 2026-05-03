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
        # Trial expires AT END of expiry_date (i.e. expiry_date itself is still allowed)
        allowed = expiry is None or expiry >= today
    # Expired or Blocked → not allowed

    if allowed:
        return False  # not blocked

    # ── Blocked UI ────────────────────────────────────────────────────────────
    try:
        payment_link = st.secrets["razorpay"]["payment_link"]
    except Exception:
        payment_link = "https://rzp.io/your-payment-link"

    monthly_price = "499"
    try:
        monthly_price = st.secrets["razorpay"]["monthly_price"]
    except Exception:
        pass

    plan = user.get("plan_name", "—")
    exp_display = expiry_str if expiry_str else "Unknown"
    status_color = "#ef4444"

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
            color: {status_color};
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
        <h1>🔒 Subscription Expired</h1>
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
            💳 Pay ₹{monthly_price}/mo – Subscribe Now
        </a>
    </div>
    """)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 I have paid – Refresh Status", use_container_width=True):
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
    """
    pass
