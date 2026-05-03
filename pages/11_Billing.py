"""
pages/11_Billing.py
Dedicated billing page — accessible even for blocked users.
Shows subscription status and payment link.
"""

import streamlit as st
from datetime import datetime

from utils.auth import require_login, get_current_user
from utils.styles import inject_css, page_header

inject_css()
require_login()
user = get_current_user()
# Note: NO subscription gate here — billing page must always be visible.

owner_email = user.get("email", "")
page_header("💳 Billing & Subscription", "Manage your LayZ subscription")

sub_status = str(user.get("subscription_status", "Trial"))
plan = str(user.get("plan_name", "—"))
expiry = str(user.get("expiry_date", "—"))
rzp_customer = str(user.get("razorpay_customer_id", "—"))
rzp_sub_id = str(user.get("razorpay_subscription_id", "—"))

status_color = {
    "Active": "#22c55e", "Trial": "#f59e0b",
    "Expired": "#ef4444", "Blocked": "#ef4444",
}.get(sub_status, "#b8b1d9")

try:
    payment_link = st.secrets["razorpay"]["payment_link"]
    plan_name = st.secrets["razorpay"]["plan_name"]
    monthly_price = st.secrets["razorpay"]["monthly_price"]
except Exception:
    payment_link = "https://rzp.io/your-payment-link"
    plan_name = "LayZ Pro"
    monthly_price = "1499"

col1, col2, col3 = st.columns([1, 2, 1])
with col2:

    # ── Status card ──────────────────────────────────────────────────────
    st.html(f"""
    <style>
        .billing-card {{
            background: #1e1a2e;
            border: 1px solid #3d3558;
            border-radius: 14px;
            padding: 2rem;
            text-align: center;
            margin-bottom: 1rem;
        }}
        .billing-card h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.25rem;
            color: #8b5cf6;
        }}
        .billing-card .subtitle {{
            color: #b8b1d9;
            margin-bottom: 1.5rem;
        }}
        .status-pill {{
            display: inline-block;
            background: {status_color}22;
            color: {status_color};
            border: 1px solid {status_color}55;
            border-radius: 999px;
            padding: 4px 20px;
            font-size: 0.9rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
        }}
        .plan-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        .plan-cell {{
            background: #2a2540;
            border-radius: 10px;
            padding: 1rem;
        }}
        .plan-cell .label {{
            color: #b8b1d9;
            font-size: 0.8rem;
            margin: 0;
        }}
        .plan-cell .value {{
            color: #f5f3ff;
            font-weight: 700;
            margin: 4px 0 0 0;
        }}
        .pricing-card {{
            background: #1e1a2e;
            border: 1px solid #8b5cf6;
            border-radius: 14px;
            padding: 1.5rem;
            text-align: center;
            margin-bottom: 1rem;
        }}
        .pricing-card .plan-label {{
            color: #b8b1d9;
            margin: 0;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .pricing-card .price {{
            color: #f5f3ff;
            font-size: 2.2rem;
            margin: 0.25rem 0;
        }}
        .pricing-card .price span {{
            font-size: 1rem;
            color: #b8b1d9;
        }}
        .features {{
            text-align: left;
            color: #b8b1d9;
            font-size: 0.9rem;
            margin: 1rem 0;
            line-height: 2;
        }}
        .pay-btn-wrap {{
            text-align: center;
            margin: 1rem 0;
        }}
        .pay-btn {{
            background: #8b5cf6;
            color: #fff;
            border: none;
            border-radius: 10px;
            padding: 1rem 3rem;
            font-size: 1.1rem;
            cursor: pointer;
            font-weight: 800;
            box-shadow: 0 4px 20px rgba(139,92,246,0.4);
            text-decoration: none;
            display: inline-block;
        }}
        .support-text {{
            color: #b8b1d9;
            font-size: 0.8rem;
            text-align: center;
        }}
        .support-text a {{
            color: #8b5cf6;
        }}
    </style>

    <div class="billing-card">
        <h1>LayZ</h1>
        <p class="subtitle">PG Management Platform</p>
        <div class="status-pill">● {sub_status}</div>
        <div class="plan-grid">
            <div class="plan-cell">
                <p class="label">Current Plan</p>
                <p class="value">{plan}</p>
            </div>
            <div class="plan-cell">
                <p class="label">Expiry Date</p>
                <p class="value">{expiry}</p>
            </div>
        </div>
    </div>

    <div class="pricing-card">
        <p class="plan-label">LayZ Pro</p>
        <p class="price">₹{monthly_price} <span>/month</span></p>
        <div class="features">
            ✅ Unlimited buildings &amp; rooms<br>
            ✅ Unlimited tenants<br>
            ✅ Rent collection &amp; tracking<br>
            ✅ Expense tracker<br>
            ✅ Analytics &amp; reports<br>
            ✅ WhatsApp reminder links<br>
            ✅ Google Sheets backend<br>
        </div>
    </div>

    <div class="pay-btn-wrap">
        <a class="pay-btn" href="{payment_link}" target="_blank">
            💳 Pay Now – ₹{monthly_price}/month
        </a>
    </div>
    """)

    if st.button("🔄 I've Paid – Refresh My Status", use_container_width=True):
        from utils.sheets import read_sheet
        df = read_sheet("Users")
        if not df.empty and "email" in df.columns:
            row = df[df["email"] == owner_email]
            if not row.empty:
                updated = row.iloc[0].to_dict()
                st.session_state.user = updated
                st.success("Status refreshed!")
                st.rerun()
        st.info("No change detected. Contact support if payment was made.")

    st.html(f"""
    <div class="support-text" style="margin-top:1rem;">
        <b>Razorpay Customer ID:</b> {rzp_customer}<br>
        <b>Subscription ID:</b> {rzp_sub_id}<br><br>
        For support: <a href="mailto:support@layz.in">support@layz.in</a>
    </div>
    """)

    st.divider()

    with st.expander("❓ How does billing work?"):
        st.markdown(
            """
            - LayZ uses **Razorpay** for secure payments.
            - You pay ₹1499/month for the Pro plan.
            - After payment, your subscription is activated automatically (or click Refresh).
            - Your data is stored securely in your **own Google Sheets** — we never own your data.
            - Cancel anytime by stopping the Razorpay subscription.
            """
        )

    with st.expander("❓ Is my data safe?"):
        st.markdown(
            """
            Yes. All your data lives in **your Google Sheets spreadsheet** (LayZ_DB).
            LayZ only reads and writes to it via the service account you set up.
            We don't store your tenant or rent data on our servers.
            """
        )
