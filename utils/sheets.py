"""
utils/sheets.py
Google Sheets backend for LayZ using gspread.
All reads return pandas DataFrames. Writes maintain referential consistency manually.
"""

from __future__ import annotations

import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
import time
from typing import Any, Optional

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SPREADSHEET_NAME = "LayZ_DB"

# ── Sheet column definitions (used for init) ──────────────────────────────────
SHEET_HEADERS: dict[str, list[str]] = {
    "Users": [
        "user_id","name","email","phone","password_hash","role","pg_name",
        "subscription_status","plan_name","trial_start_date","expiry_date",
        "razorpay_customer_id","razorpay_subscription_id","payment_link",
        "is_active","created_at",
    ],
    "Settings": [
        "setting_id","owner_email","default_rent_due_day","grace_period_days",
        "auto_reminder_enabled","late_fee_enabled","late_fee_amount",
        "created_at","updated_at",
    ],
    "Buildings": [
        "building_id","owner_email","building_name","address","city","state",
        "pincode","is_active","created_at","updated_at",
    ],
    "Rooms": [
        "room_id","owner_email","building_id","room_label","room_number","floor",
        "sharing_type","capacity_beds","status","notes","created_at","updated_at",
    ],
    "Beds": [
        "bed_id","owner_email","building_id","room_id","bed_label","status",
        "tenant_id","monthly_rent","move_in_date","created_at","updated_at",
    ],
    "Tenants": [
        "tenant_id","owner_email","building_id","room_id","bed_id","tenant_name",
        "phone","email","move_in_date","move_out_date","tenant_status",
        "id_proof_url","id_proof_type","monthly_rent","security_deposit",
        "deposit_paid","emergency_contact_name","emergency_contact_phone",
        "company_or_college","hometown","notes","created_at","updated_at",
    ],
    "RentMonths": [
        "rent_id","owner_email","tenant_id","building_id","room_id","bed_id",
        "month_year","rent_month_date","amount","due_date","paid_on",
        "payment_method","transaction_ref","status","notes","reminder_sent",
        "reminder_sent_at","created_at","updated_at",
    ],
    "Expenses": [
        "expense_id","owner_email","building_id","expense_title","category",
        "amount","expense_date","vendor_payee","receipt_url","notes",
        "created_at","updated_at",
    ],
    "ActivityLog": [
        "log_id","owner_email","actor_email","action_type","entity_type",
        "entity_id","action_details","created_at",
    ],
    "Notifications": [
        "notification_id","owner_email","tenant_id","phone","channel",
        "message","status","sent_at","created_at",
    ],
}


@st.cache_resource(show_spinner=False)
def connect_to_gsheets() -> Optional[gspread.Client]:
    """Connect to Google Sheets via service account stored in st.secrets."""
    try:
        creds_dict = dict(st.secrets["google_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.warning(f"⚠️ Google Sheets not connected: {e}. Running in demo mode.")
        return None


def get_spreadsheet() -> Optional[gspread.Spreadsheet]:
    """Return the LayZ_DB spreadsheet object."""
    client = connect_to_gsheets()
    if client is None:
        return None
    try:
        name = st.secrets.get("app", {}).get("spreadsheet_name", SPREADSHEET_NAME)
        return client.open(name)
    except Exception as e:
        st.error(f"Cannot open spreadsheet '{SPREADSHEET_NAME}': {e}")
        return None


def get_sheet(sheet_name: str) -> Optional[gspread.Worksheet]:
    """Get or create a worksheet by name."""
    spreadsheet = get_spreadsheet()
    if spreadsheet is None:
        return None
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        # Auto-create with correct headers
        headers = SHEET_HEADERS.get(sheet_name, [])
        ws = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(headers) + 2)
        if headers:
            ws.append_row(headers)
        return ws
    except Exception as e:
        st.error(f"Sheet error ({sheet_name}): {e}")
        return None


# ─── In-memory demo store (used when Sheets unavailable) ─────────────────────
_DEMO_STORE: dict[str, list[dict]] = {k: [] for k in SHEET_HEADERS}


def _demo_read(sheet_name: str) -> pd.DataFrame:
    rows = _DEMO_STORE.get(sheet_name, [])
    if not rows:
        return pd.DataFrame(columns=SHEET_HEADERS.get(sheet_name, []))
    return pd.DataFrame(rows)


def _demo_append(sheet_name: str, data: dict):
    _DEMO_STORE.setdefault(sheet_name, []).append(data)


def _demo_update(sheet_name: str, key_field: str, key_value: Any, data: dict):
    rows = _DEMO_STORE.get(sheet_name, [])
    for row in rows:
        if str(row.get(key_field)) == str(key_value):
            row.update(data)
            break


def _demo_delete(sheet_name: str, key_field: str, key_value: Any):
    rows = _DEMO_STORE.get(sheet_name, [])
    _DEMO_STORE[sheet_name] = [
        r for r in rows if str(r.get(key_field)) != str(key_value)
    ]


# ─── Core read / write helpers ────────────────────────────────────────────────

def read_sheet(sheet_name: str) -> pd.DataFrame:
    """Read a sheet and return as DataFrame. Falls back to demo store."""
    ws = get_sheet(sheet_name)
    if ws is None:
        return _demo_read(sheet_name)
    try:
        records = ws.get_all_records()
        if not records:
            return pd.DataFrame(columns=SHEET_HEADERS.get(sheet_name, []))
        df = pd.DataFrame(records)
        # Replace empty strings with NaN for consistency
        df.replace("", pd.NA, inplace=True)
        return df
    except Exception as e:
        st.warning(f"Read error ({sheet_name}): {e}")
        return _demo_read(sheet_name)


def append_row(sheet_name: str, data_dict: dict) -> bool:
    """Append a new row. Columns follow SHEET_HEADERS order."""
    ws = get_sheet(sheet_name)
    headers = SHEET_HEADERS.get(sheet_name, list(data_dict.keys()))
    row = [str(data_dict.get(h, "")) for h in headers]
    if ws is None:
        _demo_append(sheet_name, data_dict)
        return True
    try:
        ws.append_row(row, value_input_option="USER_ENTERED")
        _invalidate_cache(sheet_name)
        return True
    except Exception as e:
        st.error(f"Write error ({sheet_name}): {e}")
        return False


def update_row(sheet_name: str, key_field: str, key_value: Any, data_dict: dict) -> bool:
    """Find row by key_field=key_value and update columns from data_dict."""
    ws = get_sheet(sheet_name)
    if ws is None:
        _demo_update(sheet_name, key_field, key_value, data_dict)
        return True
    try:
        df = read_sheet(sheet_name)
        if df.empty or key_field not in df.columns:
            return False
        df[key_field] = df[key_field].astype(str)
        matches = df[df[key_field] == str(key_value)]
        if matches.empty:
            return False
        # Sheet rows are 1-indexed; row 1 is headers
        sheet_row_idx = matches.index[0] + 2
        headers = list(df.columns)
        for col, val in data_dict.items():
            if col in headers:
                col_idx = headers.index(col) + 1
                ws.update_cell(sheet_row_idx, col_idx, str(val) if val is not None else "")
        _invalidate_cache(sheet_name)
        return True
    except Exception as e:
        st.error(f"Update error ({sheet_name}): {e}")
        return False


def delete_row(sheet_name: str, key_field: str, key_value: Any) -> bool:
    """Delete a row by key_field=key_value."""
    ws = get_sheet(sheet_name)
    if ws is None:
        _demo_delete(sheet_name, key_field, key_value)
        return True
    try:
        df = read_sheet(sheet_name)
        if df.empty or key_field not in df.columns:
            return False
        df[key_field] = df[key_field].astype(str)
        matches = df[df[key_field] == str(key_value)]
        if matches.empty:
            return False
        sheet_row_idx = matches.index[0] + 2
        ws.delete_rows(sheet_row_idx)
        _invalidate_cache(sheet_name)
        return True
    except Exception as e:
        st.error(f"Delete error ({sheet_name}): {e}")
        return False


def upsert_row(sheet_name: str, key_field: str, key_value: Any, data_dict: dict) -> bool:
    """Insert or update a row based on key_field."""
    df = read_sheet(sheet_name)
    if not df.empty and key_field in df.columns:
        df[key_field] = df[key_field].astype(str)
        if str(key_value) in df[key_field].values:
            return update_row(sheet_name, key_field, key_value, data_dict)
    return append_row(sheet_name, data_dict)


def new_id() -> str:
    """Generate a short unique ID."""
    return str(uuid.uuid4())[:8].upper()


def now_str() -> str:
    """Current datetime as string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _invalidate_cache(sheet_name: str):
    """Clear cached reads (call after writes)."""
    # Streamlit caching doesn't expose per-key invalidation easily,
    # so we use a version counter in session_state.
    key = f"cache_v_{sheet_name}"
    st.session_state[key] = st.session_state.get(key, 0) + 1


def log_activity(
    owner_email: str,
    actor_email: str,
    action_type: str,
    entity_type: str,
    entity_id: str,
    details: str = "",
):
    """Write an activity log entry."""
    append_row(
        "ActivityLog",
        {
            "log_id": new_id(),
            "owner_email": owner_email,
            "actor_email": actor_email,
            "action_type": action_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action_details": details,
            "created_at": now_str(),
        },
    )
