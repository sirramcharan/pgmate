"""
pages/9_Analytics.py
Analytics dashboard with Plotly charts for LayZ.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.auth import require_login, get_current_user
from utils.billing import check_subscription
from utils.styles import inject_css, page_header
from utils.helpers import get_dashboard_metrics
from utils.analytics import (
    get_monthly_rent_trend,
    get_bed_occupancy_summary,
    get_expense_by_category,
    get_building_revenue,
    get_occupancy_trend,
)

inject_css()
require_login()
user = get_current_user()
if check_subscription(user):
    st.stop()

owner_email = user.get("email", "")
page_header("📊 Analytics", "Visual insights into your PG performance")

# ── Shared Plotly dark theme ───────────────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#b8b1d9", family="Inter, sans-serif"),
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(gridcolor="#3d3558", showgrid=True),
    yaxis=dict(gridcolor="#3d3558", showgrid=True),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)

COLORS = {
    "accent": "#8b5cf6",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "muted": "#6b7280",
}

# ── Top KPI row ───────────────────────────────────────────────────────────────
with st.spinner("Loading analytics…"):
    m = get_dashboard_metrics(owner_email)

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("🏢 Buildings", m["buildings"])
k2.metric("👤 Active Tenants", m["active_tenants"])
k3.metric("📊 Occupancy", f"{m['occupancy_pct']}%")
k4.metric("✅ Collection Rate",
          f"{round(m['collected']/(m['collected']+m['pending']+0.001)*100,1)}%")
k5.metric("💸 Expenses", f"₹{m['expenses_this_month']:,.0f}")
k6.metric("💰 Net Cash Flow", f"₹{m['net_cash_flow']:,.0f}")

st.divider()

# ── Chart row 1 ───────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

# Chart 1: Monthly rent expected vs collected
with col_left:
    st.markdown("#### 📈 Rent: Expected vs Collected (6 months)")
    trend_df = get_monthly_rent_trend(owner_email, 6)
    if not trend_df.empty:
        fig = go.Figure()
        fig.add_bar(
            x=trend_df["month"], y=trend_df["expected"],
            name="Expected", marker_color=COLORS["muted"], opacity=0.7,
        )
        fig.add_bar(
            x=trend_df["month"], y=trend_df["collected"],
            name="Collected", marker_color=COLORS["success"],
        )
        fig.update_layout(
            barmode="group",
            **CHART_LAYOUT,
            yaxis_title="Amount (₹)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No rent data available.")

# Chart 2: Bed occupancy donut
with col_right:
    st.markdown("#### 🛏 Bed Occupancy")
    occ = get_bed_occupancy_summary(owner_email)
    total_beds = occ["occupied"] + occ["vacant"]
    if total_beds > 0:
        fig2 = go.Figure(go.Pie(
            labels=["Occupied", "Vacant"],
            values=[occ["occupied"], occ["vacant"]],
            hole=0.6,
            marker=dict(colors=[COLORS["success"], COLORS["muted"]]),
            textinfo="label+percent",
            textfont=dict(color="#f5f3ff"),
        ))
        fig2.update_layout(
            **CHART_LAYOUT,
            annotations=[dict(
                text=f"{occ['occupied']}/{total_beds}",
                x=0.5, y=0.5, font_size=20,
                font_color="#f5f3ff", showarrow=False,
            )],
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No bed data yet.")

# ── Chart row 2 ───────────────────────────────────────────────────────────────
col3, col4 = st.columns(2)

# Chart 3: Expenses by category
with col3:
    st.markdown("#### 💸 Expenses by Category (this month)")
    exp_df = get_expense_by_category(owner_email)
    if not exp_df.empty:
        fig3 = px.pie(
            exp_df, names="category", values="amount",
            color_discrete_sequence=px.colors.sequential.Purples_r,
            hole=0.4,
        )
        fig3.update_traces(textfont_color="#f5f3ff")
        fig3.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No expenses recorded this month.")

# Chart 4: Occupancy trend
with col4:
    st.markdown("#### 📉 Occupancy Trend (6 months)")
    occ_trend = get_occupancy_trend(owner_email, 6)
    if not occ_trend.empty:
        fig4 = go.Figure(go.Scatter(
            x=occ_trend["month"],
            y=occ_trend["occupancy_pct"],
            mode="lines+markers",
            line=dict(color=COLORS["accent"], width=3),
            marker=dict(size=8, color=COLORS["accent"]),
            fill="tozeroy",
            fillcolor="rgba(139,92,246,0.15)",
        ))
        fig4.update_layout(
            **CHART_LAYOUT,
            yaxis_title="Occupancy %",
            yaxis_range=[0, 110],
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No occupancy data yet.")

# ── Chart row 3: Building revenue bar ────────────────────────────────────────
st.markdown("#### 🏆 Revenue by Building (this month)")
rev_df = get_building_revenue(owner_email)
if not rev_df.empty and rev_df["collected"].sum() > 0:
    fig5 = px.bar(
        rev_df.sort_values("collected", ascending=True),
        x="collected", y="building_name",
        orientation="h",
        color="collected",
        color_continuous_scale=["#3d3558", "#8b5cf6"],
        labels={"collected": "Collected (₹)", "building_name": "Building"},
    )
    fig5.update_layout(**CHART_LAYOUT, coloraxis_showscale=False)
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("No collection data this month.")
