"""
pages/3_Rooms.py
Manage rooms and beds per building.
"""

import streamlit as st
import pandas as pd

from utils.auth import require_login, get_current_user
from utils.billing import check_subscription
from utils.styles import inject_css, page_header, badge, status_badge
from utils.helpers import (
    get_owner_buildings, get_owner_rooms, get_owner_beds,
    get_owner_tenants, create_room, update_room, delete_room,
    vacate_tenant_from_bed,
)
from utils.sheets import read_sheet, update_row, now_str

inject_css()
require_login()
user = get_current_user()
if check_subscription(user):
    st.stop()

owner_email = user.get("email", "")
page_header("🏠 Rooms & Beds", "Manage rooms and bed occupancy")

buildings = get_owner_buildings(owner_email)
if buildings.empty:
    st.warning("No buildings found. Please add a building first.")
    if st.button("➕ Add Building"):
        st.switch_page("pages/2_Buildings.py")
    st.stop()

# ── Building selector ─────────────────────────────────────────────────────────
building_names = buildings["building_name"].tolist()
building_ids = buildings["building_id"].tolist()

sel_idx = 0
if st.session_state.get("selected_building") in building_ids:
    sel_idx = building_ids.index(st.session_state["selected_building"])

selected_b_name = st.selectbox("Select Building", building_names, index=sel_idx)
selected_b_id = building_ids[building_names.index(selected_b_name)]
st.session_state["selected_building"] = selected_b_id

st.divider()

# ── Add room ──────────────────────────────────────────────────────────────────
with st.expander("➕ Add New Room", expanded=False):
    with st.form("add_room_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            r_label = st.text_input("Room Label *", placeholder="e.g. R101")
            r_number = st.text_input("Room Number", placeholder="101")
        with c2:
            r_floor = st.text_input("Floor", placeholder="1")
            r_sharing = st.selectbox("Sharing Type", ["Single", "Double", "Triple", "Dorm"])
        with c3:
            r_capacity = st.number_input("No. of Beds", min_value=1, max_value=20, value=1)
            r_notes = st.text_input("Notes", placeholder="Optional")
        submitted = st.form_submit_button("Add Room & Create Beds")

    if submitted:
        if not r_label:
            st.error("Room label is required.")
        else:
            rid = create_room(owner_email, {
                "building_id": selected_b_id, "room_label": r_label,
                "room_number": r_number, "floor": r_floor,
                "sharing_type": r_sharing, "capacity_beds": r_capacity,
                "notes": r_notes,
            }, actor=owner_email)
            if rid:
                st.success(f"Room '{r_label}' added with {r_capacity} bed(s).")
                st.rerun()

st.divider()

# ── Rooms list ────────────────────────────────────────────────────────────────
rooms = get_owner_rooms(owner_email, selected_b_id)
beds_all = get_owner_beds(owner_email, building_id=selected_b_id)
tenants_df = read_sheet("Tenants")

if rooms.empty:
    st.info("No rooms in this building. Add one above.")
else:
    st.markdown(f"**{len(rooms)} room(s) in {selected_b_name}**")
    for _, room in rooms.iterrows():
        rid = room.get("room_id", "")
        r_label = room.get("room_label", "—")
        sharing = room.get("sharing_type", "")
        capacity = int(room.get("capacity_beds", 1))
        status = str(room.get("status", "Vacant"))

        # Beds for this room
        r_beds = beds_all[beds_all["room_id"] == rid] if not beds_all.empty and "room_id" in beds_all.columns else pd.DataFrame()
        occupied_count = len(r_beds[r_beds["status"] == "Occupied"]) if not r_beds.empty and "status" in r_beds.columns else 0
        pct = round(occupied_count / capacity * 100) if capacity else 0

        status_color = (
            "green" if status == "Occupied" or status == "Full"
            else "amber" if status == "Partially Occupied"
            else "red" if status == "Maintenance"
            else "gray"
        )

        with st.container():
            st.markdown(
                f"<div class='layz-card'>"
                f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
                f"<div>"
                f"<b style='font-size:1rem; color:#f5f3ff;'>{r_label}</b> "
                f"&nbsp; {badge(sharing, 'purple')} &nbsp; {badge(status, status_color)}<br>"
                f"<span style='color:#b8b1d9; font-size:0.82rem;'>"
                f"Floor {room.get('floor','—')} · Room {room.get('room_number','—')} · "
                f"{occupied_count}/{capacity} beds occupied</span>"
                f"</div></div></div>",
                unsafe_allow_html=True,
            )
            st.progress(pct / 100)

            # ── Bed cards ──────────────────────────────────────────────────────
            if not r_beds.empty:
                bed_cols = st.columns(min(capacity, 4))
                for j, (_, bed) in enumerate(r_beds.iterrows()):
                    bid_bed = bed.get("bed_id", "")
                    b_label = bed.get("bed_label", f"Bed {j+1}")
                    b_status = str(bed.get("status", "Vacant"))
                    b_rent = bed.get("monthly_rent", "—")
                    b_tenant_id = str(bed.get("tenant_id", "")).strip()

                    tenant_name = "—"
                    if b_tenant_id and b_tenant_id not in ("", "nan", "None") and not tenants_df.empty:
                        t_row = tenants_df[tenants_df["tenant_id"] == b_tenant_id]
                        if not t_row.empty:
                            tenant_name = t_row.iloc[0].get("tenant_name", "—")

                    bed_color = "#22c55e" if b_status == "Occupied" else "#6b7280"
                    with bed_cols[j % min(capacity, 4)]:
                        st.markdown(
                            f"<div style='background:#2a2540; border:1px solid {bed_color}44; border-radius:10px; padding:0.75rem; margin-bottom:0.5rem;'>"
                            f"<b style='color:#f5f3ff;'>{b_label}</b> "
                            f"<span style='color:{bed_color}; font-size:0.75rem;'>● {b_status}</span><br>"
                            f"<span style='color:#b8b1d9; font-size:0.82rem;'>{tenant_name}</span><br>"
                            f"<span style='color:#8b5cf6; font-size:0.8rem;'>₹{b_rent}/mo</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        if b_status == "Occupied":
                            if st.button("🚪 Vacate", key=f"vac_{bid_bed}", use_container_width=True):
                                vacate_tenant_from_bed(bid_bed)
                                # Also update tenant status
                                if b_tenant_id and b_tenant_id not in ("", "nan", "None"):
                                    update_row("Tenants", "tenant_id", b_tenant_id, {
                                        "tenant_status": "Inactive",
                                        "move_out_date": now_str()[:10],
                                        "updated_at": now_str(),
                                    })
                                st.success("Bed vacated.")
                                st.rerun()
                        else:
                            if st.button("👤 Assign", key=f"assign_{bid_bed}", use_container_width=True):
                                st.info("Use the 'Add Tenant' page and select this room/bed.")

            # Edit / Delete room
            with st.expander(f"⚙️ Edit / Delete {r_label}"):
                with st.form(f"edit_r_{rid}"):
                    er_label = st.text_input("Room Label", value=r_label)
                    er_floor = st.text_input("Floor", value=str(room.get("floor", "")))
                    er_notes = st.text_input("Notes", value=str(room.get("notes", "")))
                    if st.form_submit_button("Save Changes"):
                        update_room(owner_email, rid, {"room_label": er_label, "floor": er_floor, "notes": er_notes})
                        st.success("Room updated.")
                        st.rerun()
                if st.button("🗑 Delete Room", key=f"del_r_{rid}"):
                    if not r_beds.empty and occupied_count > 0:
                        st.error("Cannot delete room with occupied beds. Vacate tenants first.")
                    else:
                        delete_room(owner_email, rid)
                        st.success("Room deleted.")
                        st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
