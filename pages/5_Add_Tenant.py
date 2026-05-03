"""
pages/5_Add_Tenant.py
Add new tenant with building / room / bed selection.
Building, Room, Bed selectors are OUTSIDE the form so they trigger
immediate reruns and the bed list always reflects the chosen room.
"""

import streamlit as st
import pandas as pd
from datetime import date

from utils.auth import require_login, get_current_user
from utils.billing import check_subscription
from utils.styles import inject_css, page_header
from utils.helpers import (
    get_owner_buildings, get_owner_rooms, get_owner_beds, create_tenant,
)

inject_css()
require_login()
user = get_current_user()
if check_subscription(user):
    st.stop()

owner_email = user.get("email", "")
page_header("\U0001f464 Add Tenant", "Add a new tenant to a room and bed")

buildings = get_owner_buildings(owner_email)
if buildings.empty:
    st.warning("Please add at least one building and room before adding tenants.")
    st.stop()

# ── Location selectors (OUTSIDE form — each change triggers immediate rerun) ──
st.markdown("#### \U0001f3e0 Location")
loc1, loc2, loc3 = st.columns(3)

b_names = buildings["building_name"].tolist()
b_ids   = buildings["building_id"].tolist()

with loc1:
    sel_b = st.selectbox("Building *", b_names, key="at_building")
    sel_b_id = b_ids[b_names.index(sel_b)]

rooms = get_owner_rooms(owner_email, sel_b_id)

with loc2:
    if rooms.empty:
        st.warning("No rooms in this building.")
        sel_r_id = ""
        sel_r    = "\u2014"
        st.selectbox("Room *", ["\u2014"], key="at_room")
    else:
        r_names = rooms["room_label"].tolist()
        r_ids   = rooms["room_id"].tolist()
        sel_r   = st.selectbox("Room *", r_names, key="at_room")
        sel_r_id = r_ids[r_names.index(sel_r)]

# Beds refresh automatically because sel_r_id changes on every rerun
beds = get_owner_beds(owner_email, room_id=sel_r_id) if sel_r_id else pd.DataFrame()
vacant_beds = (
    beds[beds["status"] == "Vacant"]
    if not beds.empty and "status" in beds.columns
    else beds
)

with loc3:
    if vacant_beds.empty:
        st.warning("No vacant beds in this room." if sel_r_id else "Select a room first.")
        sel_bed_id = ""
        st.selectbox("Bed *", ["\u2014"], key="at_bed")
    else:
        bed_names  = vacant_beds["bed_label"].tolist()
        bed_ids    = vacant_beds["bed_id"].tolist()
        sel_bed    = st.selectbox("Bed *", bed_names, key="at_bed")
        sel_bed_id = bed_ids[bed_names.index(sel_bed)]

st.divider()

# ── Tenant details form ───────────────────────────────────────────────────────────
with st.form("add_tenant_form"):
    st.markdown("#### \U0001f464 Tenant Details")
    col4, col5 = st.columns(2)
    with col4:
        t_name       = st.text_input("Tenant Name *")
        phone        = st.text_input("Phone *", placeholder="10-digit mobile")
        email_t      = st.text_input("Email (optional)")
        move_in      = st.date_input("Move-in Date *", value=date.today())
    with col5:
        monthly_rent = st.number_input("Monthly Rent (\u20b9) *", min_value=0, value=5000, step=100)
        deposit      = st.number_input("Security Deposit (\u20b9)", min_value=0, value=0, step=500)
        deposit_paid = st.checkbox("Deposit Received")
        id_type      = st.selectbox("ID Proof Type", ["", "Aadhaar", "PAN", "Passport", "Driving License"])

    st.markdown("---")
    st.markdown("#### \U0001f4cb Optional Details")
    col6, col7 = st.columns(2)
    with col6:
        company         = st.text_input("Company / College")
        hometown        = st.text_input("Hometown")
    with col7:
        emergency_name  = st.text_input("Emergency Contact Name")
        emergency_phone = st.text_input("Emergency Contact Phone")
    notes = st.text_area("Notes", height=80)

    st.markdown("---")
    submitted = st.form_submit_button("\u2705 Add Tenant", use_container_width=True)

# ── Handle submit ─────────────────────────────────────────────────────────────────
if submitted:
    errors = []
    if not t_name.strip():   errors.append("Tenant name is required.")
    if not phone.strip():    errors.append("Phone is required.")
    if not sel_b_id:         errors.append("Select a building.")
    if not sel_r_id:         errors.append("Select a room.")
    if not sel_bed_id:       errors.append("Select a bed.")
    if monthly_rent <= 0:    errors.append("Monthly rent must be greater than 0.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        tid = create_tenant(
            owner_email,
            {
                "tenant_name":              t_name.strip(),
                "phone":                    phone.strip(),
                "email":                    email_t.strip(),
                "building_id":              sel_b_id,
                "room_id":                  sel_r_id,
                "bed_id":                   sel_bed_id,
                "move_in_date":             move_in.strftime("%Y-%m-%d"),
                "monthly_rent":             str(monthly_rent),
                "security_deposit":         str(deposit),
                "deposit_paid":             "TRUE" if deposit_paid else "FALSE",
                "id_proof_type":            id_type,
                "company_or_college":       company,
                "hometown":                 hometown,
                "emergency_contact_name":   emergency_name,
                "emergency_contact_phone":  emergency_phone,
                "notes":                    notes,
            },
            actor=owner_email,
        )
        if tid:
            st.success(f"\u2705 Tenant '{t_name}' added successfully! ID: {tid}")
            st.balloons()
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Add Another Tenant"):
                    # Clear location selectors so next tenant starts fresh
                    for k in ["at_building", "at_room", "at_bed"]:
                        st.session_state.pop(k, None)
                    st.rerun()
            with col_b:
                if st.button("View All Tenants"):
                    st.switch_page("pages/4_Tenants.py")
        else:
            st.error("Failed to add tenant. Please try again.")
