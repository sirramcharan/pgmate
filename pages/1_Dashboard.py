"""
pages/1_Dashboard.py
LayZ Dashboard – KPIs, quick actions, recent activity, upcoming dues.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from utils.auth import require_login, get_current_user
from utils.billing import check_subscription
from utils.styles import inject_css, page_header, status_badge, badge
from utils.helpers import (
    get_dashboard_metrics, get_owner_buildings,
    get_owner_rent_records, generate_monthly_rent_records,
)
from utils.sheets import read_sheet

inject_css()
require_login()
user = get_current_user()
if check_subscription(user):
    st.stop()

# ── Page header ───────────────────────────────────────────────────────────────
owner_email = user.get("email", "")
pg_name = user.get("pg_name", "My PG")
page_header(
    f"🏠 {pg_name}",
    f"Welcome back, {user.get('name', 'Owner')} · {datetime.now().strftime('%A, %d %b %Y')}",
)

# ── Metrics ───────────────────────────────────────────────────────────────────
with st.spinner("Loading metrics…"):
    m = get_dashboard_metrics(owner_email)

c1, c2, c3, c4 = st.columns(4)
c1.metric("🏢 Buildings", m["buildings"])
c2.metric("🛏 Total Beds", m["beds"])
c3.metric("👤 Active Tenants", m["active_tenants"])
c4.metric("📊 Occupancy", f"{m['occupancy_pct']}%")

st.markdown("<br>", unsafe_allow_html=True)
c5, c6, c7, c8 = st.columns(4)
c5.metric("✅ Collected (this month)", f"₹{m['collected']:,.0f}")
c6.metric("⏳ Pending Dues", f"₹{m['pending']:,.0f}")
c7.metric("🔴 Overdue", f"₹{m['overdue']:,.0f}")
c8.metric("💸 Expenses (this month)", f"₹{m['expenses_this_month']:,.0f}")

st.divider()

# ── Quick actions ─────────────────────────────────────────────────────────────
st.markdown("### ⚡ Quick Actions")
qa1, qa2, qa3, qa4, qa5 = st.columns(5)
with qa1:
    if st.button("➕ Add Building", use_container_width=True):
        st.switch_page("pages/2_Buildings.py")
with qa2:
    if st.button("👤 Add Tenant", use_container_width=True):
        st.switch_page("pages/5_Add_Tenant.py")
with qa3:
    if st.button("📋 Generate Rent", use_container_width=True):
        count = generate_monthly_rent_records(owner_email)
        st.success(f"Generated {count} rent records for this month.")
with qa4:
    if st.button("💵 Just Paid", use_container_width=True):
        st.switch_page("pages/7_Just_Paid.py")
with qa5:
    if st.button("💰 Add Expense", use_container_width=True):
        st.switch_page("pages/8_Expenses.py")

st.divider()

# ── Two-column layout: upcoming dues + recent activity ────────────────────────
left, right = st.columns([1.2, 1])

with left:
    st.markdown("### 📅 Upcoming & Overdue Dues")
    today_str = datetime.now().strftime("%b %Y")
    rent_df = get_owner_rent_records(owner_email, today_str)
    tenants_df = read_sheet("Tenants")

    if rent_df.empty:
        st.info("No rent records this month. Use 'Generate Rent' above.")
    else:
        pending = rent_df[rent_df["status"].isin(["Due", "Overdue", "Partial"])] \
            if "status" in rent_df.columns else rent_df

        if not pending.empty and not tenants_df.empty and "tenant_id" in tenants_df.columns:
            merged = pending.merge(
                tenants_df[["tenant_id", "tenant_name", "phone"]],
                on="tenant_id", how="left",
            )
        else:
            merged = pending.copy()
            merged["tenant_name"] = "—"
            merged["phone"] = "—"

        if merged.empty:
            st.success("🎉 All dues cleared for this month!")
        else:
            for _, row in merged.head(8).iterrows():
                s = str(row.get("status", "Due"))
                color = "red" if s == "Overdue" else "amber" if s == "Due" else "purple"
                st.markdown(
                    f"<div class='layz-card' style='padding:0.75rem 1rem;'>"
                    f"<b style='color:#f5f3ff;'>{row.get('tenant_name','—')}</b> "
                    f"<span style='color:#b8b1d9; font-size:0.85rem;'>{row.get('phone','')}</span>"
                    f"<br><span style='color:#b8b1d9; font-size:0.8rem;'>₹{row.get('amount','—')}</span>"
                    f" &nbsp; {badge(s, color)}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

with right:
    st.markdown("### 🕐 Recent Activity")
    logs = read_sheet("ActivityLog")
    if not logs.empty and "owner_email" in logs.columns:
        logs = logs[logs["owner_email"] == owner_email].copy()
        logs = logs.sort_values("created_at", ascending=False).head(10) \
            if "created_at" in logs.columns else logs.head(10)
        for _, row in logs.iterrows():
            action = str(row.get("action_type", ""))
            entity = str(row.get("entity_type", ""))
            detail = str(row.get("action_details", ""))
            when = str(row.get("created_at", ""))[:16]
            icon = {
                "CREATE": "🟢", "UPDATE": "🔵", "DELETE": "🔴",
                "MARK_PAID": "✅", "VACATE": "🚪",
            }.get(action, "📌")
            st.markdown(
                f"<div style='padding:0.4rem 0; border-bottom:1px solid #3d3558;'>"
                f"{icon} <b style='color:#f5f3ff;'>{action}</b> "
                f"<span style='color:#b8b1d9;'>{entity}</span><br>"
                f"<span style='color:#b8b1d9; font-size:0.78rem;'>{detail}</span> "
                f"<span style='color:#6b7280; font-size:0.75rem;'>· {when}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No recent activity yet.")

st.divider()

# ── Buildings snapshot ────────────────────────────────────────────────────────
st.markdown("### 🏢 Buildings Snapshot")
buildings = get_owner_buildings(owner_email)
beds_df = read_sheet("Beds")
rooms_df = read_sheet("Rooms")

if buildings.empty:
    st.info("No buildings added yet. Click 'Add Building' to get started.")
else:
    cols = st.columns(min(len(buildings), 3))
    for i, (_, b) in enumerate(buildings.iterrows()):
        bid = b.get("building_id", "")
        b_beds = beds_df[beds_df["building_id"] == bid] if not beds_df.empty and "building_id" in beds_df.columns else pd.DataFrame()
        b_rooms = rooms_df[rooms_df["building_id"] == bid] if not rooms_df.empty and "building_id" in rooms_df.columns else pd.DataFrame()
        total_beds = len(b_beds)
        occupied = len(b_beds[b_beds["status"] == "Occupied"]) if not b_beds.empty and "status" in b_beds.columns else 0
        pct = round(occupied / total_beds * 100) if total_beds else 0
        with cols[i % 3]:
            st.markdown(
                f"<div class='layz-card'>"
                f"<b style='color:#f5f3ff; font-size:1rem;'>{b.get('building_name','—')}</b><br>"
                f"<span style='color:#b8b1d9; font-size:0.8rem;'>{b.get('city','')}, {b.get('state','')}</span><br><br>"
                f"🏠 {len(b_rooms)} rooms &nbsp; 🛏 {occupied}/{total_beds} beds<br>"
                f"<span style='color:#8b5cf6;'>Occupancy: {pct}%</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.progress(pct / 100)
