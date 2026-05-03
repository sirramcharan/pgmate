"""
pages/7_Just_Paid.py
Quick-action page: find a tenant and mark their rent paid in 2 clicks.
Optimized for speed and minimal friction.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date

from utils.auth import require_login, get_current_user
from utils.billing import check_subscription
from utils.styles import inject_css, page_header
from utils.helpers import (
    get_owner_rent_records, get_owner_tenants, mark_rent_paid,
)
from utils.sheets import read_sheet

inject_css()
require_login()
user = get_current_user()
if check_subscription(user):
    st.stop()

owner_email = user.get("email", "")
page_header(
    "⚡ Just Paid",
    "Someone just paid? Find them and mark it in one click.",
)

today = datetime.now()
month_year = today.strftime("%b %Y")

# ── Quick search ───────────────────────────────────────────────────────────────
search = st.text_input(
    "🔍 Search tenant",
    placeholder="Type name, phone, or room…",
    label_visibility="collapsed",
)

# ── Load pending records ───────────────────────────────────────────────────────
rent_df = get_owner_rent_records(owner_email, month_year)
tenants_df = get_owner_tenants(owner_email)
rooms_df = read_sheet("Rooms")

if rent_df.empty:
    st.info(f"No rent records for {month_year}. Go to Rent Collection → Generate Month.")
    st.stop()

# Only pending / overdue
pending = rent_df[rent_df["status"].isin(["Due", "Overdue", "Partial"])] \
    if "status" in rent_df.columns else rent_df

if pending.empty:
    st.success(f"🎉 All tenants have paid for {month_year}!")
    st.stop()

# Merge with tenant info
if not tenants_df.empty and "tenant_id" in tenants_df.columns:
    merged = pending.merge(
        tenants_df[["tenant_id", "tenant_name", "phone", "room_id"]],
        on="tenant_id", how="left",
    )
    if not rooms_df.empty and "room_id" in rooms_df.columns:
        merged = merged.merge(rooms_df[["room_id", "room_label"]], on="room_id", how="left")
else:
    merged = pending.copy()
    for c in ["tenant_name", "phone", "room_label"]:
        if c not in merged.columns:
            merged[c] = "—"

# Search filter
if search:
    mask = pd.Series([False] * len(merged), index=merged.index)
    for col in ["tenant_name", "phone", "room_label"]:
        if col in merged.columns:
            mask |= merged[col].astype(str).str.lower().str.contains(search.lower(), na=False)
    merged = merged[mask]

st.markdown(
    f"<p style='color:#b8b1d9;'>{len(merged)} pending payment(s) for <b>{month_year}</b></p>",
    unsafe_allow_html=True,
)
st.divider()

# ── Compact row-per-tenant list ────────────────────────────────────────────────
for _, row in merged.iterrows():
    rent_id = row.get("rent_id", "")
    t_name = str(row.get("tenant_name", "—"))
    phone = str(row.get("phone", "—"))
    room = str(row.get("room_label", "—"))
    amount = row.get("amount", 0)
    status = str(row.get("status", "Due"))

    s_color = "#f59e0b" if status == "Due" else "#ef4444" if status == "Overdue" else "#8b5cf6"

    col_name, col_amt, col_btn = st.columns([3, 1.5, 2.5])
    with col_name:
        st.markdown(
            f"<div style='padding:0.5rem 0;'>"
            f"<b style='color:#f5f3ff; font-size:1rem;'>{t_name}</b> "
            f"<span style='color:#b8b1d9; font-size:0.82rem;'>· {phone}</span><br>"
            f"<span style='color:#b8b1d9; font-size:0.8rem;'>🚪 {room}</span> "
            f"<span style='background:{s_color}22; color:{s_color}; padding:1px 8px; "
            f"border-radius:999px; font-size:0.72rem;'>{status}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_amt:
        st.markdown(
            f"<div style='padding:0.5rem 0; text-align:center;'>"
            f"<b style='color:#f5f3ff; font-size:1.1rem;'>₹{amount}</b>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_btn:
        # One-click Paid (Cash default)
        if st.button(f"✅ Paid – Cash", key=f"quick_cash_{rent_id}", use_container_width=True):
            mark_rent_paid(
                rent_id, float(str(amount).replace(",", "") or 0),
                "Cash", today.strftime("%Y-%m-%d"),
                owner_email=owner_email,
            )
            st.success(f"{t_name} – marked paid!")
            st.rerun()

        with st.expander("⋯ More options"):
            with st.form(f"jp_{rent_id}"):
                jp_amt = st.number_input("Amount", value=float(str(amount).replace(",","") or 0), step=100.0)
                jp_method = st.selectbox("Method", ["Cash", "UPI", "Bank Transfer", "Other"])
                jp_date = st.date_input("Date", value=date.today())
                jp_ref = st.text_input("UPI / Ref ID (optional)")
                if st.form_submit_button("✅ Confirm"):
                    mark_rent_paid(
                        rent_id, jp_amt, jp_method,
                        jp_date.strftime("%Y-%m-%d"), jp_ref,
                        owner_email=owner_email,
                    )
                    st.success("Marked paid!")
                    st.rerun()

    st.divider()
