"""
pages/10_Settings.py
Owner settings: profile, rent defaults, billing summary, seed data.
"""

import streamlit as st

from utils.auth import require_login, get_current_user
from utils.billing import check_subscription
from utils.styles import inject_css, page_header
from utils.helpers import get_owner_settings, save_owner_settings
from utils.sheets import update_row, now_str, read_sheet

inject_css()
require_login()
user = get_current_user()
if check_subscription(user):
    st.stop()

owner_email = user.get("email", "")
page_header("⚙️ Settings", "Configure your account and PG preferences")

tab1, tab2, tab3, tab4 = st.tabs(["👤 Profile", "🏠 Rent Defaults", "💳 Billing", "🌱 Demo Data"])

# ── Tab 1: Profile ─────────────────────────────────────────────────────────────
with tab1:
    st.markdown("#### Owner Profile")
    with st.form("profile_form"):
        p_name = st.text_input("Your Name", value=str(user.get("name", "")))
        p_pg = st.text_input("PG / Hostel Name", value=str(user.get("pg_name", "")))
        p_phone = st.text_input("Phone", value=str(user.get("phone", "")))
        p_email = st.text_input("Email", value=owner_email, disabled=True,
                                 help="Email cannot be changed.")
        p_role = st.text_input("Role", value=str(user.get("role", "Owner")), disabled=True)
        save_profile = st.form_submit_button("Save Profile", use_container_width=True)

    if save_profile:
        ok = update_row("Users", "email", owner_email, {
            "name": p_name,
            "pg_name": p_pg,
            "phone": p_phone,
        })
        if ok:
            st.session_state.user["name"] = p_name
            st.session_state.user["pg_name"] = p_pg
            st.session_state.user["phone"] = p_phone
            st.success("Profile updated!")
        else:
            st.error("Failed to update profile.")

# ── Tab 2: Rent Defaults ───────────────────────────────────────────────────────
with tab2:
    st.markdown("#### Rent & Late Fee Settings")
    settings = get_owner_settings(owner_email)

    with st.form("rent_settings_form"):
        col1, col2 = st.columns(2)
        with col1:
            due_day = st.number_input(
                "Default Rent Due Day",
                min_value=1, max_value=28,
                value=int(settings.get("default_rent_due_day", 5)),
                help="Day of the month when rent is due (e.g. 5 = 5th of every month).",
            )
            grace = st.number_input(
                "Grace Period (days)",
                min_value=0, max_value=30,
                value=int(settings.get("grace_period_days", 3)),
            )
        with col2:
            late_fee_enabled = st.toggle(
                "Enable Late Fee",
                value=str(settings.get("late_fee_enabled", "FALSE")).upper() == "TRUE",
            )
            late_fee_amount = st.number_input(
                "Late Fee Amount (₹)",
                min_value=0, value=int(settings.get("late_fee_amount", 0)),
            )
            auto_reminder = st.toggle(
                "Auto Reminder (future feature)",
                value=str(settings.get("auto_reminder_enabled", "FALSE")).upper() == "TRUE",
                disabled=True,
                help="WhatsApp auto-reminders (coming soon).",
            )
        save_settings = st.form_submit_button("Save Settings", use_container_width=True)

    if save_settings:
        ok = save_owner_settings(owner_email, {
            "default_rent_due_day": due_day,
            "grace_period_days": grace,
            "late_fee_enabled": "TRUE" if late_fee_enabled else "FALSE",
            "late_fee_amount": late_fee_amount,
            "auto_reminder_enabled": "FALSE",
        })
        st.success("Settings saved!") if ok else st.error("Failed to save settings.")

# ── Tab 3: Billing ─────────────────────────────────────────────────────────────
with tab3:
    st.markdown("#### Subscription & Billing")

    sub_status = str(user.get("subscription_status", "Trial"))
    plan = str(user.get("plan_name", "—"))
    expiry = str(user.get("expiry_date", "—"))

    status_color = {
        "Active": "#22c55e", "Trial": "#f59e0b",
        "Expired": "#ef4444", "Blocked": "#ef4444",
    }.get(sub_status, "#b8b1d9")

    st.markdown(
        f"""
        <div class='layz-card'>
            <div style='display:flex; gap:2rem; flex-wrap:wrap;'>
                <div>
                    <p style='color:#b8b1d9; margin:0; font-size:0.8rem;'>Status</p>
                    <h3 style='color:{status_color}; margin:4px 0;'>{sub_status}</h3>
                </div>
                <div>
                    <p style='color:#b8b1d9; margin:0; font-size:0.8rem;'>Plan</p>
                    <h3 style='color:#f5f3ff; margin:4px 0;'>{plan}</h3>
                </div>
                <div>
                    <p style='color:#b8b1d9; margin:0; font-size:0.8rem;'>Expiry</p>
                    <h3 style='color:#f5f3ff; margin:4px 0;'>{expiry}</h3>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        payment_link = st.secrets["razorpay"]["payment_link"]
        monthly_price = st.secrets["razorpay"]["monthly_price"]
    except Exception:
        payment_link = "https://rzp.io/your-payment-link"
        monthly_price = "499"

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f"<a href='{payment_link}' target='_blank'>"
        f"<button style='background:#8b5cf6; color:#fff; border:none; border-radius:8px; "
        f"padding:0.75rem 2rem; font-size:1rem; cursor:pointer; font-weight:700;'>"
        f"💳 Renew / Upgrade – ₹{monthly_price}/mo</button></a>",
        unsafe_allow_html=True,
    )

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("**Razorpay Customer ID:** " + str(user.get("razorpay_customer_id", "—")))
    st.markdown("**Subscription ID:** " + str(user.get("razorpay_subscription_id", "—")))

# ── Tab 4: Demo Data ──────────────────────────────────────────────────────────
with tab4:
    st.markdown("#### 🌱 Seed Demo Data")
    st.warning(
        "This will add sample buildings, rooms, tenants, and rent records to your account. "
        "Only use this on a fresh / demo setup."
    )
    st.markdown(
        "Demo includes:\n"
        "- 1 owner (demo@layz.in / demo1234)\n"
        "- 2 buildings · 8 rooms · 18 beds · 10 tenants\n"
        "- Current + previous month rent records\n"
        "- 8 expense entries"
    )

    confirm_seed = st.checkbox("I understand this will add demo data")
    if st.button("🌱 Seed Demo Data", disabled=not confirm_seed):
        with st.spinner("Seeding demo data…"):
            from utils.seed import seed_demo_data
            result = seed_demo_data()
        if result.get("success"):
            st.success(result["message"])
            st.balloons()
        else:
            st.error("Seeding failed.")

    st.markdown("---")
    st.markdown(
        "**Demo login credentials:**\n\n"
        "Email: `demo@layz.in`  \nPassword: `demo1234`"
    )
