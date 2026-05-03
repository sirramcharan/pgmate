"""
utils/helpers.py
Core business logic: buildings, rooms, beds, tenants, rent, expenses.
All functions filter by owner_email for data isolation.
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime, date, timedelta
from typing import Optional
import urllib.parse

from utils.sheets import (
    read_sheet, append_row, update_row, delete_row, upsert_row,
    new_id, now_str, today_str, log_activity,
)


# ─── Owners / Settings ────────────────────────────────────────────────────────

def get_owner_settings(owner_email: str) -> dict:
    df = read_sheet("Settings")
    if df.empty or "owner_email" not in df.columns:
        return {"default_rent_due_day": 5, "grace_period_days": 3}
    row = df[df["owner_email"] == owner_email]
    if row.empty:
        return {"default_rent_due_day": 5, "grace_period_days": 3}
    return row.iloc[0].to_dict()


def save_owner_settings(owner_email: str, data: dict) -> bool:
    df = read_sheet("Settings")
    if not df.empty and "owner_email" in df.columns:
        existing = df[df["owner_email"] == owner_email]
        if not existing.empty:
            sid = existing.iloc[0].get("setting_id", new_id())
            data["updated_at"] = now_str()
            return update_row("Settings", "setting_id", sid, data)
    data["setting_id"] = new_id()
    data["owner_email"] = owner_email
    data["created_at"] = now_str()
    data["updated_at"] = now_str()
    return append_row("Settings", data)


# ─── Buildings ────────────────────────────────────────────────────────────────

def get_owner_buildings(owner_email: str) -> pd.DataFrame:
    df = read_sheet("Buildings")
    if df.empty or "owner_email" not in df.columns:
        return pd.DataFrame()
    return df[df["owner_email"] == owner_email].copy()


def create_building(owner_email: str, data: dict, actor: str = "") -> bool:
    bid = new_id()
    row = {
        "building_id": bid,
        "owner_email": owner_email,
        "building_name": data.get("building_name", ""),
        "address": data.get("address", ""),
        "city": data.get("city", ""),
        "state": data.get("state", ""),
        "pincode": data.get("pincode", ""),
        "is_active": "TRUE",
        "created_at": now_str(),
        "updated_at": now_str(),
    }
    ok = append_row("Buildings", row)
    if ok:
        log_activity(owner_email, actor or owner_email, "CREATE", "Building", bid,
                     f"Created building: {data.get('building_name')}")
    return ok


def update_building(owner_email: str, building_id: str, data: dict) -> bool:
    data["updated_at"] = now_str()
    return update_row("Buildings", "building_id", building_id, data)


def delete_building(owner_email: str, building_id: str) -> bool:
    ok = delete_row("Buildings", "building_id", building_id)
    if ok:
        log_activity(owner_email, owner_email, "DELETE", "Building", building_id, "")
    return ok


# ─── Rooms ────────────────────────────────────────────────────────────────────

def get_owner_rooms(owner_email: str, building_id: str = "") -> pd.DataFrame:
    df = read_sheet("Rooms")
    if df.empty or "owner_email" not in df.columns:
        return pd.DataFrame()
    df = df[df["owner_email"] == owner_email].copy()
    if building_id:
        df = df[df["building_id"] == building_id]
    return df


def create_room(owner_email: str, data: dict, actor: str = "") -> Optional[str]:
    rid = new_id()
    capacity = int(data.get("capacity_beds", 1))
    row = {
        "room_id": rid,
        "owner_email": owner_email,
        "building_id": data.get("building_id", ""),
        "room_label": data.get("room_label", ""),
        "room_number": data.get("room_number", ""),
        "floor": data.get("floor", ""),
        "sharing_type": data.get("sharing_type", "Single"),
        "capacity_beds": capacity,
        "status": "Vacant",
        "notes": data.get("notes", ""),
        "created_at": now_str(),
        "updated_at": now_str(),
    }
    ok = append_row("Rooms", row)
    if ok:
        create_beds_for_room(owner_email, data.get("building_id", ""), rid, capacity)
        log_activity(owner_email, actor or owner_email, "CREATE", "Room", rid,
                     f"Room: {data.get('room_label')}")
        return rid
    return None


def update_room(owner_email: str, room_id: str, data: dict) -> bool:
    data["updated_at"] = now_str()
    return update_row("Rooms", "room_id", room_id, data)


def delete_room(owner_email: str, room_id: str) -> bool:
    return delete_row("Rooms", "room_id", room_id)


# ─── Beds ─────────────────────────────────────────────────────────────────────

def get_owner_beds(owner_email: str, room_id: str = "", building_id: str = "") -> pd.DataFrame:
    df = read_sheet("Beds")
    if df.empty or "owner_email" not in df.columns:
        return pd.DataFrame()
    df = df[df["owner_email"] == owner_email].copy()
    if room_id:
        df = df[df["room_id"] == room_id]
    if building_id:
        df = df[df["building_id"] == building_id]
    return df


def create_beds_for_room(
    owner_email: str, building_id: str, room_id: str, count: int
) -> list[str]:
    bed_ids = []
    for i in range(1, count + 1):
        bid = new_id()
        append_row(
            "Beds",
            {
                "bed_id": bid,
                "owner_email": owner_email,
                "building_id": building_id,
                "room_id": room_id,
                "bed_label": f"Bed {i}",
                "status": "Vacant",
                "tenant_id": "",
                "monthly_rent": "",
                "move_in_date": "",
                "created_at": now_str(),
                "updated_at": now_str(),
            },
        )
        bed_ids.append(bid)
    return bed_ids


def assign_tenant_to_bed(bed_id: str, tenant_id: str, monthly_rent: str, move_in: str) -> bool:
    return update_row(
        "Beds", "bed_id", bed_id,
        {
            "status": "Occupied",
            "tenant_id": tenant_id,
            "monthly_rent": monthly_rent,
            "move_in_date": move_in,
            "updated_at": now_str(),
        },
    )


def vacate_tenant_from_bed(bed_id: str) -> bool:
    return update_row(
        "Beds", "bed_id", bed_id,
        {
            "status": "Vacant",
            "tenant_id": "",
            "monthly_rent": "",
            "move_in_date": "",
            "updated_at": now_str(),
        },
    )


def _refresh_room_status(room_id: str):
    beds = read_sheet("Beds")
    if beds.empty or "room_id" not in beds.columns:
        return
    room_beds = beds[beds["room_id"] == room_id]
    if room_beds.empty:
        return
    total = len(room_beds)
    occupied = len(room_beds[room_beds["status"] == "Occupied"])
    status = "Vacant" if occupied == 0 else ("Full" if occupied == total else "Partially Occupied")
    update_row("Rooms", "room_id", room_id, {"status": status, "updated_at": now_str()})


# ─── Tenants ──────────────────────────────────────────────────────────────────

def get_owner_tenants(owner_email: str, building_id: str = "") -> pd.DataFrame:
    df = read_sheet("Tenants")
    if df.empty or "owner_email" not in df.columns:
        return pd.DataFrame()
    df = df[df["owner_email"] == owner_email].copy()
    if building_id:
        df = df[df["building_id"] == building_id]
    return df


def create_tenant(owner_email: str, data: dict, actor: str = "") -> Optional[str]:
    tid = new_id()
    row = {
        "tenant_id": tid,
        "owner_email": owner_email,
        "building_id": data.get("building_id", ""),
        "room_id": data.get("room_id", ""),
        "bed_id": data.get("bed_id", ""),
        "tenant_name": data.get("tenant_name", ""),
        "phone": data.get("phone", ""),
        "email": data.get("email", ""),
        "move_in_date": data.get("move_in_date", today_str()),
        "move_out_date": "",
        "tenant_status": "Active",
        "id_proof_url": data.get("id_proof_url", ""),
        "id_proof_type": data.get("id_proof_type", ""),
        "monthly_rent": data.get("monthly_rent", ""),
        "security_deposit": data.get("security_deposit", ""),
        "deposit_paid": data.get("deposit_paid", "FALSE"),
        "emergency_contact_name": data.get("emergency_contact_name", ""),
        "emergency_contact_phone": data.get("emergency_contact_phone", ""),
        "company_or_college": data.get("company_or_college", ""),
        "hometown": data.get("hometown", ""),
        "notes": data.get("notes", ""),
        "created_at": now_str(),
        "updated_at": now_str(),
    }
    ok = append_row("Tenants", row)
    if not ok:
        return None

    assign_tenant_to_bed(
        data.get("bed_id", ""), tid,
        data.get("monthly_rent", ""),
        data.get("move_in_date", today_str()),
    )
    _refresh_room_status(data.get("room_id", ""))
    generate_rent_for_tenant(owner_email, row)
    log_activity(
        owner_email, actor or owner_email, "CREATE", "Tenant", tid,
        f"Added tenant: {data.get('tenant_name')}"
    )
    return tid


def vacate_tenant(owner_email: str, tenant_id: str, move_out_date: str, actor: str = "") -> bool:
    ok = update_row(
        "Tenants", "tenant_id", tenant_id,
        {"tenant_status": "Inactive", "move_out_date": move_out_date, "updated_at": now_str()},
    )
    if ok:
        beds = read_sheet("Beds")
        if not beds.empty and "tenant_id" in beds.columns:
            match = beds[beds["tenant_id"] == tenant_id]
            if not match.empty:
                bid = match.iloc[0]["bed_id"]
                rid = match.iloc[0]["room_id"]
                vacate_tenant_from_bed(bid)
                _refresh_room_status(rid)
        log_activity(owner_email, actor or owner_email, "VACATE", "Tenant", tenant_id, "")
    return ok


# ─── Rent ─────────────────────────────────────────────────────────────────────

def get_owner_rent_records(owner_email: str, month_year: str = "") -> pd.DataFrame:
    df = read_sheet("RentMonths")
    if df.empty or "owner_email" not in df.columns:
        return pd.DataFrame()
    df = df[df["owner_email"] == owner_email].copy()
    if month_year:
        df = df[df["month_year"] == month_year]
    return df


def generate_rent_for_tenant(owner_email: str, tenant: dict) -> Optional[str]:
    today = datetime.now()
    month_year = today.strftime("%b %Y")

    df = read_sheet("RentMonths")
    if not df.empty and "tenant_id" in df.columns:
        existing = df[
            (df["tenant_id"] == tenant.get("tenant_id", ""))
            & (df["month_year"] == month_year)
        ]
        if not existing.empty:
            return existing.iloc[0].get("rent_id")

    settings = get_owner_settings(owner_email)
    due_day = int(settings.get("default_rent_due_day", 5))
    due_date = today.replace(day=min(due_day, 28)).strftime("%Y-%m-%d")

    rent_id = new_id()
    append_row(
        "RentMonths",
        {
            "rent_id": rent_id,
            "owner_email": owner_email,
            "tenant_id": tenant.get("tenant_id", ""),
            "building_id": tenant.get("building_id", ""),
            "room_id": tenant.get("room_id", ""),
            "bed_id": tenant.get("bed_id", ""),
            "month_year": month_year,
            "rent_month_date": today.replace(day=1).strftime("%Y-%m-%d"),
            "amount": tenant.get("monthly_rent", ""),
            "due_date": due_date,
            "paid_on": "",
            "payment_method": "",
            "transaction_ref": "",
            "status": "Due",
            "notes": "",
            "reminder_sent": "FALSE",
            "reminder_sent_at": "",
            "created_at": now_str(),
            "updated_at": now_str(),
        },
    )
    return rent_id


def generate_monthly_rent_records(owner_email: str) -> int:
    tenants = get_owner_tenants(owner_email)
    if tenants.empty:
        return 0
    active = tenants[tenants.get("tenant_status", pd.Series(dtype=str)) == "Active"] \
        if "tenant_status" in tenants.columns else tenants
    count = 0
    for _, t in active.iterrows():
        rid = generate_rent_for_tenant(owner_email, t.to_dict())
        if rid:
            count += 1
    return count


def mark_rent_paid(
    rent_id: str,
    amount_paid: float,
    payment_method: str,
    paid_on: str,
    transaction_ref: str = "",
    notes: str = "",
    owner_email: str = "",
) -> bool:
    df = read_sheet("RentMonths")
    if df.empty or "rent_id" not in df.columns:
        return False
    match = df[df["rent_id"] == rent_id]
    if match.empty:
        return False
    due = float(str(match.iloc[0].get("amount", 0)).replace(",", "") or 0)
    status = "Paid" if amount_paid >= due else "Partial"
    ok = update_row(
        "RentMonths", "rent_id", rent_id,
        {
            "paid_on": paid_on,
            "payment_method": payment_method,
            "transaction_ref": transaction_ref,
            "status": status,
            "notes": notes,
            "updated_at": now_str(),
        },
    )
    if ok:
        log_activity(owner_email, owner_email, "MARK_PAID", "Rent", rent_id,
                     f"Paid ₹{amount_paid} via {payment_method}")
    return ok


# ─── Expenses ─────────────────────────────────────────────────────────────────

def get_owner_expenses(owner_email: str) -> pd.DataFrame:
    df = read_sheet("Expenses")
    if df.empty or "owner_email" not in df.columns:
        return pd.DataFrame()
    return df[df["owner_email"] == owner_email].copy()


def create_expense(owner_email: str, data: dict) -> bool:
    eid = new_id()
    row = {
        "expense_id": eid,
        "owner_email": owner_email,
        "building_id": data.get("building_id", ""),
        "expense_title": data.get("expense_title", ""),
        "category": data.get("category", ""),
        "amount": data.get("amount", ""),
        "expense_date": data.get("expense_date", today_str()),
        "vendor_payee": data.get("vendor_payee", ""),
        "receipt_url": data.get("receipt_url", ""),
        "notes": data.get("notes", ""),
        "created_at": now_str(),
        "updated_at": now_str(),
    }
    return append_row("Expenses", row)


def delete_expense(expense_id: str) -> bool:
    return delete_row("Expenses", "expense_id", expense_id)


# ─── Dashboard metrics ────────────────────────────────────────────────────────

def get_dashboard_metrics(owner_email: str) -> dict:
    buildings = get_owner_buildings(owner_email)
    rooms = get_owner_rooms(owner_email)
    beds = get_owner_beds(owner_email)
    tenants = get_owner_tenants(owner_email)

    today = datetime.now()
    month_year = today.strftime("%b %Y")
    rent = get_owner_rent_records(owner_email, month_year)
    expenses = get_owner_expenses(owner_email)

    n_buildings = len(buildings)
    n_rooms = len(rooms)
    n_beds = len(beds)

    active_tenants = (
        len(tenants[tenants["tenant_status"] == "Active"])
        if not tenants.empty and "tenant_status" in tenants.columns
        else len(tenants)
    )
    occupied_beds = (
        len(beds[beds["status"] == "Occupied"])
        if not beds.empty and "status" in beds.columns
        else 0
    )
    occupancy_pct = round(occupied_beds / n_beds * 100, 1) if n_beds else 0

    collected = 0.0
    pending = 0.0
    overdue = 0.0
    if not rent.empty and "status" in rent.columns and "amount" in rent.columns:
        rent["amount"] = pd.to_numeric(rent["amount"], errors="coerce").fillna(0)
        collected = rent[rent["status"] == "Paid"]["amount"].sum()
        pending = rent[rent["status"] == "Due"]["amount"].sum()
        overdue = rent[rent["status"] == "Overdue"]["amount"].sum()

    monthly_expenses = 0.0
    if not expenses.empty and "expense_date" in expenses.columns:
        expenses["expense_date"] = pd.to_datetime(expenses["expense_date"], errors="coerce")
        this_month = expenses[
            (expenses["expense_date"].dt.month == today.month)
            & (expenses["expense_date"].dt.year == today.year)
        ]
        if not this_month.empty and "amount" in this_month.columns:
            this_month = this_month.copy()
            this_month["amount"] = pd.to_numeric(this_month["amount"], errors="coerce").fillna(0)
            monthly_expenses = this_month["amount"].sum()

    return {
        "buildings": n_buildings,
        "rooms": n_rooms,
        "beds": n_beds,
        "active_tenants": active_tenants,
        "occupied_beds": occupied_beds,
        "occupancy_pct": occupancy_pct,
        "collected": collected,
        "pending": pending,
        "overdue": overdue,
        "expenses_this_month": monthly_expenses,
        "net_cash_flow": collected - monthly_expenses,
    }


# ─── WhatsApp ─────────────────────────────────────────────────────────────────

def make_whatsapp_link(phone: str, message: str) -> str:
    """Generate a wa.me link with +91 prefix for Indian numbers."""
    # Strip all non-digits
    clean_phone = "".join(filter(str.isdigit, phone))
    # If 10-digit Indian number, prepend country code 91
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone
    # If someone entered 0XXXXXXXXXX (11 digits starting with 0), fix it
    elif len(clean_phone) == 11 and clean_phone.startswith("0"):
        clean_phone = "91" + clean_phone[1:]
    # If already has 91 prefix (12 digits), leave as is
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded}"


def build_rent_reminder_message(
    tenant_name: str, amount: str, month_year: str, pg_name: str
) -> str:
    return (
        f"Hi {tenant_name}, your rent of \u20b9{amount} for {month_year} at "
        f"{pg_name} is pending. Please pay at the earliest. Thank you."
    )
