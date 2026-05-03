"""
pages/2_Buildings.py
Manage buildings: view, add, edit, delete.
"""

import streamlit as st
import pandas as pd

from utils.auth import require_login, get_current_user
from utils.billing import check_subscription
from utils.styles import inject_css, page_header, badge
from utils.helpers import (
    get_owner_buildings, create_building, update_building, delete_building,
)
from utils.sheets import read_sheet

inject_css()
require_login()
user = get_current_user()
if check_subscription(user):
    st.stop()

owner_email = user.get("email", "")
page_header("🏢 Buildings", "Manage your PG buildings")

# ── Add building form ─────────────────────────────────────────────────────────
with st.expander("➕ Add New Building", expanded=False):
    with st.form("add_building_form"):
        c1, c2 = st.columns(2)
        with c1:
            bname = st.text_input("Building Name *")
            address = st.text_input("Address")
            city = st.text_input("City")
        with c2:
            state = st.text_input("State")
            pincode = st.text_input("Pincode")
        submitted = st.form_submit_button("Add Building", use_container_width=True)

    if submitted:
        if not bname:
            st.error("Building name is required.")
        else:
            ok = create_building(owner_email, {
                "building_name": bname, "address": address,
                "city": city, "state": state, "pincode": pincode,
            }, actor=owner_email)
            if ok:
                st.success(f"Building '{bname}' added!")
                st.rerun()
            else:
                st.error("Failed to add building.")

st.divider()

# ── Buildings list ────────────────────────────────────────────────────────────
buildings = get_owner_buildings(owner_email)
beds_df = read_sheet("Beds")
rooms_df = read_sheet("Rooms")

if buildings.empty:
    st.info("No buildings yet. Add your first building above.")
else:
    st.markdown(f"**{len(buildings)} building(s) found**")

    for _, b in buildings.iterrows():
        bid = b.get("building_id", "")
        bname = b.get("building_name", "—")

        b_beds = beds_df[beds_df["building_id"] == bid] \
            if not beds_df.empty and "building_id" in beds_df.columns else pd.DataFrame()
        b_rooms = rooms_df[rooms_df["building_id"] == bid] \
            if not rooms_df.empty and "building_id" in rooms_df.columns else pd.DataFrame()

        total_beds = len(b_beds)
        occupied = len(b_beds[b_beds["status"] == "Occupied"]) \
            if not b_beds.empty and "status" in b_beds.columns else 0
        vacant = total_beds - occupied
        pct = round(occupied / total_beds * 100) if total_beds else 0

        occ_badge = (
            badge("Full", "red") if pct == 100
            else badge(f"{pct}% Occupied", "green") if pct > 0
            else badge("Vacant", "gray")
        )

        with st.container():
            col_info, col_stats, col_actions = st.columns([2.5, 2, 1.5])

            with col_info:
                st.markdown(
                    f"<div class='layz-card' style='margin-bottom:0;'>"
                    f"<b style='font-size:1.1rem; color:#f5f3ff;'>{bname}</b>"
                    f" {occ_badge}<br>"
                    f"<span style='color:#b8b1d9; font-size:0.85rem;'>"
                    f"📍 {b.get('address','')}, {b.get('city','')}, {b.get('state','')} – {b.get('pincode','')}"
                    f"</span></div>",
                    unsafe_allow_html=True,
                )

            with col_stats:
                st.markdown(
                    f"<div class='layz-card' style='margin-bottom:0;'>"
                    f"🏠 <b>{len(b_rooms)}</b> rooms &nbsp; "
                    f"🛏 <b>{total_beds}</b> beds<br>"
                    f"✅ <b style='color:#22c55e;'>{occupied}</b> occupied &nbsp; "
                    f"⬜ <b style='color:#b8b1d9;'>{vacant}</b> vacant"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.progress(pct / 100 if total_beds else 0)

            with col_actions:
                with st.expander("⚙️ Actions"):
                    st.markdown(f"**Edit {bname}**")
                    with st.form(f"edit_b_{bid}"):
                        e_name = st.text_input("Name", value=bname)
                        e_addr = st.text_input("Address", value=str(b.get("address", "")))
                        e_city = st.text_input("City", value=str(b.get("city", "")))
                        e_state = st.text_input("State", value=str(b.get("state", "")))
                        e_pin = st.text_input("Pincode", value=str(b.get("pincode", "")))
                        if st.form_submit_button("Save"):
                            update_building(owner_email, bid, {
                                "building_name": e_name, "address": e_addr,
                                "city": e_city, "state": e_state, "pincode": e_pin,
                            })
                            st.success("Updated!")
                            st.rerun()

                    st.markdown("---")
                    confirm_key = f"del_confirm_{bid}"
                    if st.button("🗑 Delete Building", key=f"del_{bid}"):
                        st.session_state[confirm_key] = True

                    if st.session_state.get(confirm_key):
                        st.warning("This will NOT delete rooms/tenants in Sheets (manual cleanup needed). Confirm?")
                        if st.button("✅ Yes, Delete", key=f"del_yes_{bid}"):
                            delete_building(owner_email, bid)
                            st.session_state.pop(confirm_key, None)
                            st.success("Deleted.")
                            st.rerun()
                        if st.button("❌ Cancel", key=f"del_no_{bid}"):
                            st.session_state.pop(confirm_key, None)

        st.markdown("<br>", unsafe_allow_html=True)
