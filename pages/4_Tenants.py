"""
pages/4_Tenants.py
Tenant list with filters, profile view, vacate action.
"""

import streamlit as st
import pandas as pd

from utils.auth import require_login, get_current_user
from utils.billing import check_subscription
from utils.styles import inject_css, page_header, badge, status_badge
from utils.helpers import (
    get_owner_tenants, get_owner_buildings, vacate_tenant,
    get_owner_rent_records, make_whatsapp_link, build_rent_reminder_message,
)
from utils.sheets import read_sheet

inject_css()
require_login()
user = get_current_user()
if check_subscription(user):
    st.stop()

owner_email = user.get("email", "")
pg_name = user.get("pg_name", "PG")
page_header("👥 Tenants", "Manage your tenants")

# ── Filters ───────────────────────────────────────────────────────────────────
buildings = get_owner_buildings(owner_email)
b_options = ["All Buildings"] + buildings["building_name"].tolist() if not buildings.empty else ["All Buildings"]

col_f1, col_f2, col_f3, col_f4 = st.columns(4)
with col_f1:
    sel_building = st.selectbox("Building", b_options)
with col_f2:
    sel_status = st.selectbox("Status", ["All", "Active", "Inactive"])
with col_f3:
    search = st.text_input("Search", placeholder="Name or phone")
with col_f4:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Add Tenant", use_container_width=True):
        st.switch_page("pages/5_Add_Tenant.py")

# ── Load + filter tenants ─────────────────────────────────────────────────────
building_id_filter = ""
if sel_building != "All Buildings" and not buildings.empty:
    row = buildings[buildings["building_name"] == sel_building]
    if not row.empty:
        building_id_filter = row.iloc[0]["building_id"]

tenants = get_owner_tenants(owner_email, building_id=building_id_filter)

rooms_df = read_sheet("Rooms")
buildings_df = read_sheet("Buildings")

if not tenants.empty:
    if sel_status != "All" and "tenant_status" in tenants.columns:
        tenants = tenants[tenants["tenant_status"] == sel_status]
    if search:
        mask = pd.Series([False] * len(tenants), index=tenants.index)
        for col in ["tenant_name", "phone", "email"]:
            if col in tenants.columns:
                mask |= tenants[col].astype(str).str.lower().str.contains(search.lower(), na=False)
        tenants = tenants[mask]

if tenants.empty:
    st.info("No tenants match your filters.")
else:
    st.markdown(f"**{len(tenants)} tenant(s) found**")

    # CSV export
    csv = tenants.to_csv(index=False)
    st.download_button("⬇ Export CSV", csv, "tenants.csv", "text/csv")

    st.divider()

    for _, t in tenants.iterrows():
        tid = t.get("tenant_id", "")
        t_name = t.get("tenant_name", "—")
        phone = str(t.get("phone", "—"))
        t_status = str(t.get("tenant_status", "Active"))
        rent = t.get("monthly_rent", "—")
        move_in = str(t.get("move_in_date", ""))[:10]
        bid_t = t.get("building_id", "")
        rid_t = t.get("room_id", "")

        # Resolve building and room names
        b_name = "—"
        if not buildings_df.empty and "building_id" in buildings_df.columns:
            b_row = buildings_df[buildings_df["building_id"] == bid_t]
            if not b_row.empty:
                b_name = b_row.iloc[0].get("building_name", "—")

        r_name = "—"
        if not rooms_df.empty and "room_id" in rooms_df.columns:
            r_row = rooms_df[rooms_df["room_id"] == rid_t]
            if not r_row.empty:
                r_name = r_row.iloc[0].get("room_label", "—")

        status_color = "green" if t_status == "Active" else "gray"

        with st.expander(
            f"{'🟢' if t_status=='Active' else '⚫'} {t_name}  ·  {phone}  ·  {b_name} – {r_name}  ·  ₹{rent}/mo"
        ):
            col1, col2, col3 = st.columns([2, 2, 1.5])
            with col1:
                st.markdown(f"**📛 Name:** {t_name}")
                st.markdown(f"**📱 Phone:** {phone}")
                st.markdown(f"**📧 Email:** {t.get('email','—')}")
                st.markdown(f"**🏠 Building:** {b_name}")
                st.markdown(f"**🚪 Room:** {r_name} &nbsp; Bed: {t.get('bed_id','—')[:6]}")
                st.markdown(f"**📅 Move-in:** {move_in}")

            with col2:
                st.markdown(f"**💵 Monthly Rent:** ₹{rent}")
                st.markdown(f"**🔒 Deposit:** ₹{t.get('security_deposit','—')} "
                            f"({'Paid' if str(t.get('deposit_paid','')).upper()=='TRUE' else 'Unpaid'})")
                st.markdown(f"**🪪 ID Proof:** {t.get('id_proof_type','—')}")
                st.markdown(f"**🏫 Company/College:** {t.get('company_or_college','—')}")
                st.markdown(f"**🏡 Hometown:** {t.get('hometown','—')}")
                st.markdown(f"**📝 Notes:** {t.get('notes','—')}")

            with col3:
                # WhatsApp reminder link
                month_year = pd.Timestamp.now().strftime("%b %Y")
                msg = build_rent_reminder_message(t_name, str(rent), month_year, pg_name)
                wa_link = make_whatsapp_link(phone, msg)
                st.markdown(
                    f"<a href='{wa_link}' target='_blank'>"
                    f"<button style='width:100%; background:#25D366; color:#fff; border:none; "
                    f"border-radius:8px; padding:0.5rem; cursor:pointer; font-weight:600;'>"
                    f"📲 WhatsApp</button></a>",
                    unsafe_allow_html=True,
                )

                if t_status == "Active":
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🚪 Mark Move-out", key=f"move_out_{tid}"):
                        vacate_tenant(owner_email, tid, pd.Timestamp.now().strftime("%Y-%m-%d"))
                        st.success(f"{t_name} moved out.")
                        st.rerun()

            # Rent history
            st.markdown("---")
            st.markdown("**📋 Recent Rent History**")
            rent_df = get_owner_rent_records(owner_email)
            if not rent_df.empty and "tenant_id" in rent_df.columns:
                t_rent = rent_df[rent_df["tenant_id"] == tid].copy()
                if "created_at" in t_rent.columns:
                    t_rent = t_rent.sort_values("created_at", ascending=False)
                cols_show = ["month_year", "amount", "due_date", "paid_on", "payment_method", "status"]
                cols_show = [c for c in cols_show if c in t_rent.columns]
                if not t_rent.empty:
                    st.dataframe(t_rent[cols_show].head(6), use_container_width=True)
                else:
                    st.info("No rent records yet.")
            else:
                st.info("No rent records.")
