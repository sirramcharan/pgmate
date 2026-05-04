"""
LayZ - PG/Hostel Management SaaS
Main entry point: handles login, session, and routing.
"""

import streamlit as st
from utils.styles import inject_css
from utils.auth import (
    require_login, logout_user, login_user, register_user,
    restore_session_from_cookie, render_token_reader, _write_token_to_storage
)
from utils.sheets import connect_to_gsheets, read_sheet
from utils.billing import check_subscription

st.set_page_config(
    page_title="LayZ – PG Manager",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# Step 1: Try to restore session from ?s= query param (set by localStorage bridge)
restore_session_from_cookie()

# Step 2: If still not logged in, render the JS reader that checks localStorage
# and redirects with ?s=token if a saved token exists
if not st.session_state.get("logged_in"):
    render_token_reader()

# Step 3: If a pending token was just issued (fresh login), write it to localStorage
if "_pending_token" in st.session_state:
    _write_token_to_storage(st.session_state["_pending_token"])
    del st.session_state["_pending_token"]

# Step 4: Init session defaults
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_building" not in st.session_state:
    st.session_state.selected_building = None


def show_login():
    """Render the login / register screen."""
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown(
            """
            <div style='text-align:center; padding: 2rem 0 1rem 0;'>
                <h1 style='font-size:2.8rem; font-weight:800; color:#8b5cf6; letter-spacing:-1px;'>LayZ</h1>
                <p style='color:#b8b1d9; font-size:1rem; margin-top:-0.5rem;'>Smart PG & Hostel Management</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["🔐 Login", "✍️ Register"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="owner@example.com")
                password = st.text_input("Password", type="password")
                col_a, col_b = st.columns(2)
                with col_a:
                    submit = st.form_submit_button("Login", use_container_width=True)
                with col_b:
                    demo = st.form_submit_button(
                        "🎯 Demo Login", use_container_width=True
                    )

            if demo:
                result = login_user("demo@layz.in", "demo1234")
                if result["success"]:
                    st.session_state.logged_in = True
                    st.session_state.user = result["user"]
                    st.rerun()
                else:
                    st.error("Demo account not found. Please seed demo data first.")

            if submit:
                if not email or not password:
                    st.error("Please enter email and password.")
                else:
                    result = login_user(email.strip().lower(), password)
                    if result["success"]:
                        st.session_state.logged_in = True
                        st.session_state.user = result["user"]
                        st.rerun()
                    else:
                        st.error(result.get("message", "Login failed."))

        with tab_register:
            with st.form("register_form"):
                r_name = st.text_input("Your Name")
                r_email = st.text_input("Email", placeholder="owner@example.com")
                r_phone = st.text_input("Phone", placeholder="10-digit mobile")
                r_pg = st.text_input("PG / Hostel Name")
                r_pass = st.text_input("Password", type="password")
                r_pass2 = st.text_input("Confirm Password", type="password")
                reg_submit = st.form_submit_button(
                    "Create Account", use_container_width=True
                )

            if reg_submit:
                if not all([r_name, r_email, r_phone, r_pg, r_pass, r_pass2]):
                    st.error("All fields are required.")
                elif r_pass != r_pass2:
                    st.error("Passwords do not match.")
                elif len(r_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    result = register_user(
                        name=r_name, email=r_email.strip().lower(),
                        phone=r_phone, pg_name=r_pg, password=r_pass,
                    )
                    if result["success"]:
                        st.success("Account created! Please login.")
                    else:
                        st.error(result.get("message", "Registration failed."))


def show_sidebar(user: dict):
    with st.sidebar:
        st.markdown(
            """
            <div style='padding:1rem 0 0.5rem 0; text-align:center;'>
                <span style='font-size:1.8rem; font-weight:800; color:#8b5cf6;'>LayZ</span>
                <br><span style='font-size:0.7rem; color:#b8b1d9;'>PG Management</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        sub_status = user.get("subscription_status", "Trial")
        status_color = {
            "Active": "#22c55e", "Trial": "#f59e0b",
            "Expired": "#ef4444", "Blocked": "#ef4444",
        }.get(sub_status, "#b8b1d9")
        st.markdown(
            f"<div style='text-align:center;'>"
            f"<span style='background:{status_color}22; color:{status_color}; "
            f"padding:2px 10px; border-radius:999px; font-size:0.75rem; border:1px solid {status_color}55;'>"
            f"● {sub_status}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='text-align:center; color:#b8b1d9; font-size:0.8rem; margin-top:4px;'>"
            f"{user.get('pg_name','My PG')}</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.rerun()


# ─── Main routing ──────────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    show_login()
else:
    user = st.session_state.user
    show_sidebar(user)

    blocked = check_subscription(user)
    if blocked:
        st.stop()

    st.markdown(
        f"""
        <div style='padding:1rem 0;'>
            <h2 style='color:#f5f3ff; font-weight:700;'>
                👋 Welcome back, {user.get('name','Owner')}
            </h2>
            <p style='color:#b8b1d9;'>
                Use the sidebar to navigate. Start with <b>Dashboard</b> for a quick overview.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("👈 Navigate using the sidebar pages to manage your PG.")
