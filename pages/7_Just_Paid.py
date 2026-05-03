"""
pages/7_Just_Paid.py
Quick-action page: find a tenant and mark their rent paid in 2 clicks.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date

from utils.auth import require_login, get_current_user
from utils.billing import check_subscription
from utils.styles import inject_css, page_header
from utils.helpers import get_owner_rent_records, get_owner_tenants, mark_rent_paid
from utils.sheets import read_sheet

inject_css()
require_login()
user = get_current_user()
if check_subscription(user):
    st.stop()

owner_email = user.get("email", "")
page_header(
    "\u26a1 Just Paid",
    "Someone just paid? Find them and mark it in one click.",
)

today = datetime.now()
month_year = today.strftime("%b %Y")

# ── Quick search ───────────────────────────────────────────────────────────────
search = st.text_input(
    "\U0001f50d Search tenant",
    placeholder="Type name, phone, or room\u2026",
    label_visibility="collapsed",
)

# ── Load data ──────────────────────────────────────────────────────────────────
rent_df = get_owner_rent_records(owner_email, month_year)
tenants_df = get_owner_tenants(owner_email)
rooms_df = read_sheet("Rooms")

if rent_df.empty:
    st.info(f"No rent records for {month_year}. Go to Rent Collection \u2192 Generate Month.")
    st.stop()

# Only pending / overdue
pending = (
    rent_df[rent_df["status"].isin(["Due", "Overdue", "Partial"])]
    if "status" in rent_df.columns
    else rent_df
)

if pending.empty:
    st.success(f"\U0001f389 All tenants have paid for {month_year}!")
    st.stop()

# ── Safe merge with tenant + room info ─────────────────────────────────────────
merged = pending.copy()

# Ensure baseline columns exist so nothing crashes downstream
for col in ["tenant_name", "phone", "room_id", "room_label"]:
    if col not in merged.columns:
        merged[col] = ""

if not tenants_df.empty and "tenant_id" in tenants_df.columns:
    # Only pull columns that actually exist in tenants_df
    tenant_cols = ["tenant_id"]
    for c in ["tenant_name", "phone", "room_id"]:
        if c in tenants_df.columns:
            tenant_cols.append(c)

    merged = merged.merge(
        tenants_df[tenant_cols],
        on="tenant_id",
        how="left",
        suffixes=("", "_t"),
    )
    # Keep the tenant-side value if the pending df had blanks
    for c in ["tenant_name", "phone", "room_id"]:
        if f"{c}_t" in merged.columns:
            merged[c] = merged[c].fillna(merged[f"{c}_t"])
            merged.drop(columns=[f"{c}_t"], inplace=True)

# Merge room label
if (
    not rooms_df.empty
    and "room_id" in rooms_df.columns
    and "room_label" in rooms_df.columns
    and "room_id" in merged.columns
):
    merged = merged.merge(
        rooms_df[["room_id", "room_label"]],
        on="room_id",
        how="left",
        suffixes=("", "_r"),
    )
    if "room_label_r" in merged.columns:
        merged["room_label"] = merged["room_label"].fillna(merged["room_label_r"])
        merged.drop(columns=["room_label_r"], inplace=True)

# Final safety fill — replace NaN with "—"
for col in ["tenant_name", "phone", "room_label"]:
    merged[col] = merged[col].fillna("—").astype(str)

# ── Search filter ───────────────────────────────────────────────────────────────
if search:
    mask = pd.Series([False] * len(merged), index=merged.index)
    for col in ["tenant_name", "phone", "room_label"]:
        mask |= merged[col].str.lower().str.contains(search.lower(), na=False)
    merged = merged[mask]

st.markdown(
    f"<p style='color:#b8b1d9;'>{len(merged)} pending payment(s) for <b>{month_year}</b></p>",
    unsafe_allow_html=True,
)
st.divider()

# ── Compact row-per-tenant list ─────────────────────────────────────────────────────
for _, row in merged.iterrows():
    rent_id   = str(row.get("rent_id", ""))
    t_name    = str(row.get("tenant_name", "—"))
    phone     = str(row.get("phone", "—"))
    room      = str(row.get("room_label", "—"))
    amount    = row.get("amount", 0)
    status    = str(row.get("status", "Due"))

    s_color = "#f59e0b" if status == "Due" else "#ef4444" if status == "Overdue" else "#8b5cf6"

    col_name, col_amt, col_btn = st.columns([3, 1.5, 2.5])
    with col_name:
        st.markdown(
            f"<div style='padding:0.5rem 0;'>"
            f"<b style='color:#f5f3ff; font-size:1rem;'>{t_name}</b> "
            f"<span style='color:#b8b1d9; font-size:0.82rem;'>\u00b7 {phone}</span><br>"
            f"<span style='color:#b8b1d9; font-size:0.8rem;'>\U0001f6aa {room}</span> "
            f"<span style='background:{s_color}22; color:{s_color}; padding:1px 8px; "
            f"border-radius:999px; font-size:0.72rem;'>{status}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_amt:
        st.markdown(
            f"<div style='padding:0.5rem 0; text-align:center;'>"
            f"<b style='color:#f5f3ff; font-size:1.1rem;'>\u20b9{amount}</b>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("\u2705 Paid \u2013 Cash", key=f"quick_cash_{rent_id}", use_container_width=True):
            mark_rent_paid(
                rent_id,
                float(str(amount).replace(",", "") or 0),
                "Cash",
                today.strftime("%Y-%m-%d"),
                owner_email=owner_email,
            )
            st.success(f"{t_name} \u2013 marked paid!")
            st.rerun()

        with st.expander("\u22ef More options"):
            with st.form(f"jp_{rent_id}"):
                jp_amt    = st.number_input("Amount", value=float(str(amount).replace(",", "") or 0), step=100.0)
                jp_method = st.selectbox("Method", ["Cash", "UPI", "Bank Transfer", "Other"])
                jp_date   = st.date_input("Date", value=date.today())
                jp_ref    = st.text_input("UPI / Ref ID (optional)")
                if st.form_submit_button("\u2705 Confirm"):
                    mark_rent_paid(
                        rent_id, jp_amt, jp_method,
                        jp_date.strftime("%Y-%m-%d"), jp_ref,
                        owner_email=owner_email,
                    )
                    st.success("Marked paid!")
                    st.rerun()

    st.divider()
