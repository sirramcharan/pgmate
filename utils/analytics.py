"""
utils/analytics.py
Analytics and chart data calculations for LayZ.
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

from utils.helpers import (
    get_owner_buildings, get_owner_rooms, get_owner_beds,
    get_owner_tenants, get_owner_rent_records, get_owner_expenses,
)


def _safe_numeric(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce").fillna(0)


def get_monthly_rent_trend(owner_email: str, months: int = 6) -> pd.DataFrame:
    """Expected vs collected rent for last N months."""
    records = []
    today = datetime.now()
    for i in range(months - 1, -1, -1):
        dt = today.replace(day=1) - timedelta(days=i * 30)
        month_year = dt.strftime("%b %Y")
        df = get_owner_rent_records(owner_email, month_year)
        if df.empty or "amount" not in df.columns:
            records.append({"month": month_year, "expected": 0, "collected": 0})
            continue
        df["amount"] = _safe_numeric(df, "amount")
        expected = df["amount"].sum()
        collected = df[df["status"] == "Paid"]["amount"].sum() if "status" in df.columns else 0
        records.append({"month": month_year, "expected": expected, "collected": collected})
    return pd.DataFrame(records)


def get_bed_occupancy_summary(owner_email: str) -> dict:
    beds = get_owner_beds(owner_email)
    if beds.empty or "status" not in beds.columns:
        return {"occupied": 0, "vacant": 0}
    occupied = len(beds[beds["status"] == "Occupied"])
    vacant = len(beds) - occupied
    return {"occupied": occupied, "vacant": vacant}


def get_expense_by_category(owner_email: str) -> pd.DataFrame:
    expenses = get_owner_expenses(owner_email)
    if expenses.empty or "category" not in expenses.columns:
        return pd.DataFrame(columns=["category", "amount"])
    today = datetime.now()
    expenses["expense_date"] = pd.to_datetime(expenses["expense_date"], errors="coerce")
    this_month = expenses[
        (expenses["expense_date"].dt.month == today.month)
        & (expenses["expense_date"].dt.year == today.year)
    ].copy()
    if this_month.empty:
        return pd.DataFrame(columns=["category", "amount"])
    this_month["amount"] = _safe_numeric(this_month, "amount")
    return this_month.groupby("category")["amount"].sum().reset_index()


def get_building_revenue(owner_email: str) -> pd.DataFrame:
    """Total rent collected per building (current month)."""
    today = datetime.now()
    month_year = today.strftime("%b %Y")
    rent = get_owner_rent_records(owner_email, month_year)
    buildings = get_owner_buildings(owner_email)
    if rent.empty or buildings.empty:
        return pd.DataFrame(columns=["building_name", "collected"])
    rent["amount"] = _safe_numeric(rent, "amount")
    paid = rent[rent["status"] == "Paid"].copy() if "status" in rent.columns else rent
    if paid.empty or "building_id" not in paid.columns:
        return pd.DataFrame(columns=["building_name", "collected"])
    grouped = paid.groupby("building_id")["amount"].sum().reset_index()
    grouped.columns = ["building_id", "collected"]
    merged = grouped.merge(buildings[["building_id", "building_name"]], on="building_id", how="left")
    return merged[["building_name", "collected"]].sort_values("collected", ascending=False)


def get_occupancy_trend(owner_email: str, months: int = 6) -> pd.DataFrame:
    """Approximate occupancy % over last N months using rent records count as proxy."""
    records = []
    today = datetime.now()
    beds = get_owner_beds(owner_email)
    total_beds = len(beds) if not beds.empty else 1
    for i in range(months - 1, -1, -1):
        dt = today.replace(day=1) - timedelta(days=i * 30)
        month_year = dt.strftime("%b %Y")
        df = get_owner_rent_records(owner_email, month_year)
        count = len(df) if not df.empty else 0
        records.append({"month": month_year, "occupancy_pct": round(count / total_beds * 100, 1)})
    return pd.DataFrame(records)
