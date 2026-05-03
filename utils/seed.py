"""
utils/seed.py
Seed demo data for LayZ: 1 owner, 2 buildings, 8 rooms, 18 beds, 10 tenants.
Run from Settings page or on first startup in demo mode.
"""

from __future__ import annotations

import streamlit as st
from datetime import datetime, timedelta
from utils.sheets import append_row, new_id, now_str, today_str, _DEMO_STORE
from utils.auth import hash_password


DEMO_EMAIL = "demo@layz.in"
DEMO_PASS = "demo1234"


def seed_demo_data() -> dict:
    """Insert demo data rows into Google Sheets (or demo store)."""
    today = datetime.now()

    # ── Owner ──────────────────────────────────────────────────────────────────
    user_id = new_id()
    append_row("Users", {
        "user_id": user_id,
        "name": "Ravi Kumar",
        "email": DEMO_EMAIL,
        "phone": "9876543210",
        "password_hash": hash_password(DEMO_PASS),
        "role": "Owner",
        "pg_name": "Ravi's PG",
        "subscription_status": "Active",
        "plan_name": "LayZ Pro",
        "trial_start_date": today_str(),
        "expiry_date": (today + timedelta(days=90)).strftime("%Y-%m-%d"),
        "razorpay_customer_id": "",
        "razorpay_subscription_id": "",
        "payment_link": "https://rzp.io/demo",
        "is_active": "TRUE",
        "created_at": now_str(),
    })

    # ── Settings ───────────────────────────────────────────────────────────────
    append_row("Settings", {
        "setting_id": new_id(),
        "owner_email": DEMO_EMAIL,
        "default_rent_due_day": "5",
        "grace_period_days": "3",
        "auto_reminder_enabled": "FALSE",
        "late_fee_enabled": "FALSE",
        "late_fee_amount": "0",
        "created_at": now_str(),
        "updated_at": now_str(),
    })

    # ── Buildings ──────────────────────────────────────────────────────────────
    b1_id = new_id()
    b2_id = new_id()
    for b in [
        {"building_id": b1_id, "building_name": "Sunrise PG", "address": "12 MG Road",
         "city": "Bengaluru", "state": "Karnataka", "pincode": "560001"},
        {"building_id": b2_id, "building_name": "Green Nest", "address": "45 Indiranagar",
         "city": "Bengaluru", "state": "Karnataka", "pincode": "560038"},
    ]:
        append_row("Buildings", {**b, "owner_email": DEMO_EMAIL,
                                  "is_active": "TRUE", "created_at": now_str(), "updated_at": now_str()})

    # ── Rooms & Beds ───────────────────────────────────────────────────────────
    rooms_data = [
        (b1_id, "R101", "101", "1", "Single", 1),
        (b1_id, "R102", "102", "1", "Double", 2),
        (b1_id, "R103", "103", "1", "Triple", 3),
        (b1_id, "R104", "104", "2", "Double", 2),
        (b2_id, "R201", "201", "2", "Single", 1),
        (b2_id, "R202", "202", "2", "Double", 2),
        (b2_id, "R203", "203", "3", "Triple", 3),
        (b2_id, "R204", "204", "3", "Double", 2),
    ]
    room_ids = []
    bed_ids_all = []
    for bid_bld, label, num, floor, sharing, cap in rooms_data:
        rid = new_id()
        room_ids.append(rid)
        append_row("Rooms", {
            "room_id": rid, "owner_email": DEMO_EMAIL, "building_id": bid_bld,
            "room_label": label, "room_number": num, "floor": floor,
            "sharing_type": sharing, "capacity_beds": cap, "status": "Vacant",
            "notes": "", "created_at": now_str(), "updated_at": now_str(),
        })
        beds = []
        for i in range(1, cap + 1):
            beid = new_id()
            beds.append(beid)
            append_row("Beds", {
                "bed_id": beid, "owner_email": DEMO_EMAIL, "building_id": bid_bld,
                "room_id": rid, "bed_label": f"Bed {i}", "status": "Vacant",
                "tenant_id": "", "monthly_rent": "", "move_in_date": "",
                "created_at": now_str(), "updated_at": now_str(),
            })
        bed_ids_all.append(beds)

    # ── Tenants (10) ───────────────────────────────────────────────────────────
    tenant_data = [
        ("Arjun Sharma",    "9876500001", "arjun@email.com",   b1_id, room_ids[0], bed_ids_all[0][0], "8500"),
        ("Priya Nair",      "9876500002", "",                  b1_id, room_ids[1], bed_ids_all[1][0], "6000"),
        ("Karan Mehta",     "9876500003", "",                  b1_id, room_ids[1], bed_ids_all[1][1], "6000"),
        ("Sneha Reddy",     "9876500004", "sneha@email.com",   b1_id, room_ids[2], bed_ids_all[2][0], "5500"),
        ("Rohan Gupta",     "9876500005", "",                  b1_id, room_ids[2], bed_ids_all[2][1], "5500"),
        ("Ananya Singh",    "9876500006", "",                  b1_id, room_ids[3], bed_ids_all[3][0], "6500"),
        ("Vikram Patel",    "9876500007", "vpatel@email.com",  b2_id, room_ids[4], bed_ids_all[4][0], "9000"),
        ("Meera Joshi",     "9876500008", "",                  b2_id, room_ids[5], bed_ids_all[5][0], "6000"),
        ("Aditya Rao",      "9876500009", "",                  b2_id, room_ids[6], bed_ids_all[6][0], "5000"),
        ("Divya Krishnan",  "9876500010", "",                  b2_id, room_ids[6], bed_ids_all[6][1], "5000"),
    ]

    move_in = (today - timedelta(days=60)).strftime("%Y-%m-%d")
    tenant_ids = []
    for t_name, phone, email, bid_bld, rid, beid, rent in tenant_data:
        tid = new_id()
        tenant_ids.append(tid)
        append_row("Tenants", {
            "tenant_id": tid, "owner_email": DEMO_EMAIL,
            "building_id": bid_bld, "room_id": rid, "bed_id": beid,
            "tenant_name": t_name, "phone": phone, "email": email,
            "move_in_date": move_in, "move_out_date": "", "tenant_status": "Active",
            "id_proof_url": "", "id_proof_type": "Aadhaar",
            "monthly_rent": rent, "security_deposit": str(int(rent) * 2),
            "deposit_paid": "TRUE", "emergency_contact_name": "", "emergency_contact_phone": "",
            "company_or_college": "", "hometown": "", "notes": "",
            "created_at": now_str(), "updated_at": now_str(),
        })
        # Update bed
        append_row  # beds already created; update inline:
        from utils.sheets import update_row
        update_row("Beds", "bed_id", beid, {
            "status": "Occupied", "tenant_id": tid,
            "monthly_rent": rent, "move_in_date": move_in, "updated_at": now_str(),
        })

    # Update room statuses
    from utils.sheets import update_row
    occupied_rooms = [room_ids[0], room_ids[1], room_ids[2], room_ids[3],
                      room_ids[4], room_ids[5], room_ids[6]]
    for r in occupied_rooms:
        update_row("Rooms", "room_id", r, {"status": "Occupied", "updated_at": now_str()})

    # ── Rent records: current + previous month ─────────────────────────────────
    due_day = 5
    statuses_curr = ["Paid", "Paid", "Due", "Overdue", "Due", "Paid", "Paid", "Due", "Due", "Partial"]
    statuses_prev = ["Paid"] * 10

    for month_offset, statuses in [(0, statuses_curr), (1, statuses_prev)]:
        dt = (today.replace(day=1) - timedelta(days=month_offset * 30))
        month_year = dt.strftime("%b %Y")
        due_date = dt.replace(day=due_day).strftime("%Y-%m-%d")
        for i, (tid, (_, _, _, bid_bld, rid, beid, rent)) in enumerate(
            zip(tenant_ids, tenant_data)
        ):
            status = statuses[i]
            paid_on = (dt + timedelta(days=3)).strftime("%Y-%m-%d") if status in ("Paid", "Partial") else ""
            append_row("RentMonths", {
                "rent_id": new_id(), "owner_email": DEMO_EMAIL,
                "tenant_id": tid, "building_id": bid_bld, "room_id": rid, "bed_id": beid,
                "month_year": month_year,
                "rent_month_date": dt.replace(day=1).strftime("%Y-%m-%d"),
                "amount": rent, "due_date": due_date,
                "paid_on": paid_on,
                "payment_method": "UPI" if paid_on else "",
                "transaction_ref": f"UPI{new_id()}" if paid_on else "",
                "status": status, "notes": "",
                "reminder_sent": "FALSE", "reminder_sent_at": "",
                "created_at": now_str(), "updated_at": now_str(),
            })

    # ── Expenses ───────────────────────────────────────────────────────────────
    expense_data = [
        (b1_id, "Electricity Bill",    "Utilities",    4200, -5),
        (b1_id, "Water Charges",       "Utilities",    800,  -8),
        (b1_id, "Plumber Visit",       "Maintenance",  1500, -3),
        (b1_id, "WiFi Bill",           "Internet",     1200, -10),
        (b2_id, "Electricity Bill",    "Utilities",    3800, -6),
        (b2_id, "Housekeeping Staff",  "Salaries",     8000, -1),
        (b2_id, "Painting Work",       "Maintenance",  5500, -15),
        (b2_id, "Gas Cylinder",        "Utilities",    1050, -4),
    ]
    for bid_bld, title, cat, amt, day_offset in expense_data:
        exp_date = (today + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        append_row("Expenses", {
            "expense_id": new_id(), "owner_email": DEMO_EMAIL,
            "building_id": bid_bld, "expense_title": title, "category": cat,
            "amount": amt, "expense_date": exp_date,
            "vendor_payee": "", "receipt_url": "", "notes": "",
            "created_at": now_str(), "updated_at": now_str(),
        })

    return {"success": True, "message": "Demo data seeded successfully."}
