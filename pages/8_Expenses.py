"""
pages/8_Expenses.py
Expense tracker: add, filter, view, delete expenses.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date

from utils.auth import require_login, get_current_user
from utils.billing import check_subscription
from utils.styles import inject_css, page_header
from utils.helpers import (
    get_owner_buildings, get_owner_expenses, create_expense, delete_expense,
)

inject_css()
require_login()
user = get_current_user()
if check_subscription(user):
    st.stop()

owner_email = user.get("email", "")
page_header("💸 Expenses", "Track your PG running costs")

CATEGORIES = [
    "Utilities", "Maintenance", "Salaries", "Internet", "Cleaning",
    "Furniture", "Security", "Taxes", "Insurance", "Miscellaneous",
]

# ── Add expense form ──────────────────────────────────────────────────────────
buildings = get_owner_buildings(owner_email)
b_names = buildings["building_name"].tolist() if not buildings.empty else ["Default"]
b_ids = buildings["building_id"].tolist() if not buildings.empty else [""]

with st.expander("➕ Add New Expense", expanded=False):
    with st.form("add_expense_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            sel_b = st.selectbox("Building *", b_names)
            sel_b_id = b_ids[b_names.index(sel_b)] if b_ids else ""
            title = st.text_input("Expense Title *", placeholder="e.g. Electricity Bill")
        with col2:
            category = st.selectbox("Category *", CATEGORIES)
            amount = st.number_input("Amount (₹) *", min_value=0.0, step=100.0)
        with col3:
            exp_date = st.date_input("Date *", value=date.today())
            vendor = st.text_input("Vendor / Payee (optional)")
        notes = st.text_input("Notes (optional)")
        submitted = st.form_submit_button("Add Expense", use_container_width=True)

    if submitted:
        if not title or amount <= 0:
            st.error("Title and amount are required.")
        else:
            ok = create_expense(owner_email, {
                "building_id": sel_b_id,
                "expense_title": title,
                "category": category,
                "amount": str(amount),
                "expense_date": exp_date.strftime("%Y-%m-%d"),
                "vendor_payee": vendor,
                "notes": notes,
            })
            if ok:
                st.success(f"Expense '{title}' added!")
                st.rerun()

st.divider()

# ── Filters ───────────────────────────────────────────────────────────────────
today = datetime.now()
months = [(today.replace(day=1) - pd.DateOffset(months=i)).strftime("%b %Y") for i in range(6)]

col_m, col_b, col_c = st.columns(3)
with col_m:
    sel_month = st.selectbox("Month", ["All"] + months)
with col_b:
    sel_b_filter = st.selectbox("Building", ["All"] + b_names)
with col_c:
    sel_cat = st.selectbox("Category", ["All"] + CATEGORIES)

# ── Load + filter ─────────────────────────────────────────────────────────────
expenses = get_owner_expenses(owner_email)

if not expenses.empty and "expense_date" in expenses.columns:
    expenses["expense_date"] = pd.to_datetime(expenses["expense_date"], errors="coerce")

    if sel_month != "All":
        dt = pd.to_datetime(sel_month, format="%b %Y")
        expenses = expenses[
            (expenses["expense_date"].dt.month == dt.month)
            & (expenses["expense_date"].dt.year == dt.year)
        ]
    if sel_b_filter != "All" and not buildings.empty and "building_id" in buildings.columns:
        bid_sel = buildings[buildings["building_name"] == sel_b_filter]["building_id"].values
        if len(bid_sel):
            expenses = expenses[expenses["building_id"] == bid_sel[0]]
    if sel_cat != "All" and "category" in expenses.columns:
        expenses = expenses[expenses["category"] == sel_cat]

# ── KPIs ──────────────────────────────────────────────────────────────────────
this_month_all = get_owner_expenses(owner_email)
if not this_month_all.empty and "expense_date" in this_month_all.columns:
    this_month_all["expense_date"] = pd.to_datetime(this_month_all["expense_date"], errors="coerce")
    this_m = this_month_all[
        (this_month_all["expense_date"].dt.month == today.month)
        & (this_month_all["expense_date"].dt.year == today.year)
    ].copy()
    this_m["amount"] = pd.to_numeric(this_m["amount"], errors="coerce").fillna(0)
    total_this_month = this_m["amount"].sum()
    top_cat = this_m.groupby("category")["amount"].sum().idxmax() if not this_m.empty and "category" in this_m.columns else "—"
else:
    total_this_month = 0
    top_cat = "—"

k1, k2, k3 = st.columns(3)
k1.metric("💸 Total This Month", f"₹{total_this_month:,.0f}")
k2.metric("🏆 Top Category", top_cat)
k3.metric("📋 Records Shown", len(expenses))

st.divider()

# ── Expense table ─────────────────────────────────────────────────────────────
if expenses.empty:
    st.info("No expenses found for the selected filters.")
else:
    expenses_show = expenses.copy()
    expenses_show["amount"] = pd.to_numeric(expenses_show["amount"], errors="coerce").fillna(0)

    if not buildings.empty and "building_id" in expenses_show.columns:
        expenses_show = expenses_show.merge(
            buildings[["building_id", "building_name"]], on="building_id", how="left"
        )

    csv = expenses_show.to_csv(index=False)
    st.download_button("⬇ Export CSV", csv, "expenses.csv", "text/csv")
    st.markdown(f"**Total: ₹{expenses_show['amount'].sum():,.0f}**")
    st.markdown("<br>", unsafe_allow_html=True)

    for _, row in expenses_show.iterrows():
        eid = row.get("expense_id", "")
        col_a, col_b_col, col_c_col, col_d = st.columns([2.5, 1.5, 1.5, 1])
        with col_a:
            st.markdown(
                f"<div style='padding:0.4rem 0;'>"
                f"<b style='color:#f5f3ff;'>{row.get('expense_title','—')}</b><br>"
                f"<span style='color:#b8b1d9; font-size:0.8rem;'>"
                f"{row.get('building_name', row.get('building_id',''))} · {row.get('vendor_payee','')}"
                f"</span></div>",
                unsafe_allow_html=True,
            )
        with col_b_col:
            cat = str(row.get("category", ""))
            st.markdown(
                f"<span class='badge badge-purple'>{cat}</span>",
                unsafe_allow_html=True,
            )
        with col_c_col:
            exp_d = str(row.get("expense_date", ""))[:10]
            amt = row.get("amount", 0)
            st.markdown(
                f"<b style='color:#f5f3ff;'>₹{amt:,.0f}</b><br>"
                f"<span style='color:#b8b1d9; font-size:0.8rem;'>{exp_d}</span>",
                unsafe_allow_html=True,
            )
        with col_d:
            if st.button("🗑", key=f"del_exp_{eid}", help="Delete this expense"):
                delete_expense(eid)
                st.success("Deleted.")
                st.rerun()

        st.markdown("<hr style='border-color:#3d3558; margin:4px 0;'>", unsafe_allow_html=True)
