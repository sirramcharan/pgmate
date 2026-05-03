"""
pages/6_Rent_Collection.py
Full rent collection view with filters, KPIs, mark-as-paid flow.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date

from utils.auth import require_login, get_current_user
from utils.billing import check_subscription
from utils.styles import inject_css, page_header, badge
from utils.helpers import (
    get_owner_rent_records, get_owner_tenants, get_owner_buildings,
    mark_rent_paid, generate_monthly_rent_records,
    make_whatsapp_link, build_rent_reminder_message,
)
from utils.sheets import read_sheet

inject_css()
require_login()
user = get_current_user()
if check_subscription(user):
    st.stop()

owner_email = user.get("email", "")
pg_name = user.get("pg_name", "PG")
page_header("💰 Rent Collection", "Track and record rent payments")

# ── Month selector ────────────────────────────────────────────────────────────
today = datetime.now()
months = [(today.replace(day=1) - pd.DateOffset(months=i)).strftime("%b %Y") for i in range(6)]
col_m, col_b, col_s, col_search, col_gen = st.columns([1.5, 1.5, 1.5, 2, 1.5])
with col_m:
    sel_month = st.selectbox("Month", months)
with col_b:
    buildings = get_owner_buildings(owner_email)
    b_opts = ["All Buildings"] + buildings["building_name"].tolist() if not buildings.empty else ["All Buildings"]
    sel_bname = st.selectbox("Building", b_opts)
with col_s:
    sel_status = st.selectbox("Status", ["All", "Due", "Overdue", "Paid", "Partial"])
with col_search:
    search = st.text_input("Search", placeholder="Name / phone / room")
with col_gen:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📋 Generate Month", use_container_width=True):
        n = generate_monthly_rent_records(owner_email)
        st.success(f"Generated {n} records.")
        st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────────
rent_df = get_owner_rent_records(owner_email, sel_month)
tenants_df = get_owner_tenants(owner_email)
rooms_df = read_sheet("Rooms")
buildings_df = read_sheet("Buildings")

# Merge
if not rent_df.empty and not tenants_df.empty and "tenant_id" in tenants_df.columns:
    merged = rent_df.merge(
        tenants_df[["tenant_id", "tenant_name", "phone", "room_id", "bed_id", "building_id"]],
        on="tenant_id", how="left",
        suffixes=("", "_t"),
    )
    # Use tenant's building_id if rent's is missing
    if "building_id" not in merged.columns:
        merged["building_id"] = merged.get("building_id_t", "")
    if not rooms_df.empty and "room_id" in rooms_df.columns:
        merged = merged.merge(rooms_df[["room_id", "room_label"]], on="room_id", how="left")
    if not buildings_df.empty and "building_id" in buildings_df.columns:
        merged = merged.merge(buildings_df[["building_id", "building_name"]], on="building_id", how="left")
else:
    merged = rent_df.copy()
    for c in ["tenant_name", "phone", "room_label", "building_name"]:
        if c not in merged.columns:
            merged[c] = "—"

# Filters
if sel_bname != "All Buildings" and "building_name" in merged.columns:
    merged = merged[merged["building_name"] == sel_bname]
if sel_status != "All" and "status" in merged.columns:
    merged = merged[merged["status"] == sel_status]
if search:
    mask = pd.Series([False] * len(merged), index=merged.index)
    for col in ["tenant_name", "phone", "room_label"]:
        if col in merged.columns:
            mask |= merged[col].astype(str).str.lower().str.contains(search.lower(), na=False)
    merged = merged[mask]

# ── KPI cards ─────────────────────────────────────────────────────────────────
st.divider()
all_month = get_owner_rent_records(owner_email, sel_month)
if not all_month.empty and "amount" in all_month.columns:
    all_month["amount"] = pd.to_numeric(all_month["amount"], errors="coerce").fillna(0)
    total_due = all_month["amount"].sum()
    collected = all_month[all_month["status"] == "Paid"]["amount"].sum() if "status" in all_month.columns else 0
    pending_count = len(all_month[all_month["status"].isin(["Due", "Overdue"])]) if "status" in all_month.columns else 0
    overdue_count = len(all_month[all_month["status"] == "Overdue"]) if "status" in all_month.columns else 0
else:
    total_due = collected = pending_count = overdue_count = 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("💵 Total Due", f"₹{total_due:,.0f}")
k2.metric("✅ Collected", f"₹{collected:,.0f}")
k3.metric("⏳ Pending", pending_count)
k4.metric("🔴 Overdue", overdue_count)
st.divider()

# ── Rent table ────────────────────────────────────────────────────────────────
if merged.empty:
    st.info(f"No rent records for {sel_month}. Click 'Generate Month' to create them.")
else:
    st.markdown(f"**{len(merged)} record(s)**")
    csv = merged.to_csv(index=False)
    st.download_button("⬇ Export CSV", csv, f"rent_{sel_month}.csv", "text/csv")

    for _, row in merged.iterrows():
        rent_id = row.get("rent_id", "")
        t_name = str(row.get("tenant_name", "—"))
        phone = str(row.get("phone", "—"))
        room_lbl = str(row.get("room_label", "—"))
        bld_name = str(row.get("building_name", "—"))
        amount = row.get("amount", 0)
        status = str(row.get("status", "Due"))
        due_date = str(row.get("due_date", ""))[:10]
        paid_on = str(row.get("paid_on", ""))[:10]

        s_color = {
            "Paid": "#22c55e", "Due": "#f59e0b",
            "Overdue": "#ef4444", "Partial": "#8b5cf6"
        }.get(status, "#b8b1d9")
        s_badge = f"<span class='badge' style='background:{s_color}22; color:{s_color}; border:1px solid {s_color}55;'>{status}</span>"

        col_info, col_amt, col_actions = st.columns([3, 1.5, 2])
        with col_info:
            st.markdown(
                f"<div class='layz-card' style='padding:0.6rem 1rem; margin-bottom:0;'>"
                f"<b style='color:#f5f3ff;'>{t_name}</b> "
                f"<span style='color:#b8b1d9; font-size:0.82rem;'>· {phone}</span><br>"
                f"<span style='color:#b8b1d9; font-size:0.8rem;'>{bld_name} → {room_lbl}</span> "
                f"&nbsp; {s_badge}"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_amt:
            st.markdown(
                f"<div class='layz-card' style='padding:0.6rem 1rem; margin-bottom:0; text-align:center;'>"
                f"<b style='font-size:1.1rem; color:#f5f3ff;'>₹{amount}</b><br>"
                f"<span style='color:#b8b1d9; font-size:0.75rem;'>Due: {due_date}</span><br>"
                f"<span style='color:#22c55e; font-size:0.75rem;'>{('Paid: '+paid_on) if paid_on and paid_on!='nan' else ''}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_actions:
            if status not in ("Paid",):
                with st.expander("💵 Mark Paid"):
                    with st.form(f"pay_{rent_id}"):
                        pay_amt = st.number_input("Amount Paid", min_value=0.0, value=float(amount), step=100.0, key=f"amt_{rent_id}")
                        pay_method = st.selectbox("Method", ["Cash", "UPI", "Bank Transfer", "Other"], key=f"mth_{rent_id}")
                        pay_date = st.date_input("Date", value=date.today(), key=f"dt_{rent_id}")
                        pay_ref = st.text_input("Ref (optional)", key=f"ref_{rent_id}")
                        pay_notes = st.text_input("Notes", key=f"nt_{rent_id}")
                        if st.form_submit_button("✅ Confirm Payment"):
                            ok = mark_rent_paid(
                                rent_id, pay_amt, pay_method,
                                pay_date.strftime("%Y-%m-%d"),
                                pay_ref, pay_notes, owner_email,
                            )
                            if ok:
                                st.success("Marked paid!")
                                st.rerun()

            # WhatsApp
            if status != "Paid":
                msg = build_rent_reminder_message(t_name, str(amount), sel_month, pg_name)
                wa = make_whatsapp_link(phone, msg)
                st.markdown(
                    f"<a href='{wa}' target='_blank'>"
                    f"<button style='width:100%; background:#25D366; color:#fff; border:none; "
                    f"border-radius:6px; padding:0.3rem 0.5rem; cursor:pointer; font-size:0.82rem;'>"
                    f"📲 Remind</button></a>",
                    unsafe_allow_html=True,
                )

        st.markdown("<br style='margin:2px 0;'>", unsafe_allow_html=True)
