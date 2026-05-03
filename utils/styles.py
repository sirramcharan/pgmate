"""
utils/styles.py
Dark premium theme for LayZ.
"""

import streamlit as st


def inject_css():
    st.markdown(
        """
        <style>
        /* ── Root palette ──────────────────────────────────────────────── */
        :root {
            --bg:      #13111c;
            --surface: #1e1a2e;
            --surface2:#2a2540;
            --accent:  #8b5cf6;
            --accent2: #7c3aed;
            --text:    #f5f3ff;
            --muted:   #b8b1d9;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger:  #ef4444;
            --border:  #3d3558;
        }

        /* ── App background ────────────────────────────────────────────── */
        .stApp { background-color: var(--bg); color: var(--text); }

        /* ── Sidebar ───────────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background-color: var(--surface) !important;
            border-right: 1px solid var(--border);
        }
        section[data-testid="stSidebar"] * { color: var(--muted) !important; }

        /* ── Buttons ───────────────────────────────────────────────────── */
        .stButton > button {
            background: var(--accent);
            color: #fff;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            transition: background 0.2s;
        }
        .stButton > button:hover { background: var(--accent2); }

        /* ── Inputs ────────────────────────────────────────────────────── */
        .stTextInput input, .stSelectbox select,
        .stNumberInput input, .stDateInput input,
        .stTextArea textarea {
            background: var(--surface2) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
        }

        /* ── Tabs ──────────────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {
            background: var(--surface);
            border-radius: 8px;
            gap: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            background: transparent;
            color: var(--muted);
            border-radius: 6px;
        }
        .stTabs [aria-selected="true"] {
            background: var(--accent) !important;
            color: #fff !important;
        }

        /* ── Metric cards ──────────────────────────────────────────────── */
        [data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem;
        }
        [data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 0.8rem; }
        [data-testid="stMetricValue"] { color: var(--text) !important; font-weight: 700; }

        /* ── Dataframe / table ─────────────────────────────────────────── */
        .stDataFrame { border-radius: 12px; overflow: hidden; }

        /* ── Divider ───────────────────────────────────────────────────── */
        hr { border-color: var(--border); }

        /* ── Custom card ───────────────────────────────────────────────── */
        .layz-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 0.75rem;
            transition: border-color 0.2s;
        }
        .layz-card:hover { border-color: var(--accent); }

        /* ── Badge helper classes ──────────────────────────────────────── */
        .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
        }
        .badge-green  { background:#22c55e22; color:#22c55e; border:1px solid #22c55e55; }
        .badge-red    { background:#ef444422; color:#ef4444; border:1px solid #ef444455; }
        .badge-amber  { background:#f59e0b22; color:#f59e0b; border:1px solid #f59e0b55; }
        .badge-purple { background:#8b5cf622; color:#8b5cf6; border:1px solid #8b5cf655; }
        .badge-gray   { background:#6b728022; color:#9ca3af; border:1px solid #6b728055; }

        /* ── Progress bar override ─────────────────────────────────────── */
        .stProgress > div > div { background-color: var(--accent); border-radius: 999px; }

        /* ── Expander ──────────────────────────────────────────────────── */
        .streamlit-expanderHeader { color: var(--text) !important; }

        /* ── Success / error / info boxes ──────────────────────────────── */
        .stAlert { border-radius: 10px; }

        /* ── Form borders ──────────────────────────────────────────────── */
        [data-testid="stForm"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1rem;
        }

        /* ── Page title helper ─────────────────────────────────────────── */
        .page-title {
            font-size: 1.6rem;
            font-weight: 800;
            color: var(--text);
            margin-bottom: 0.25rem;
        }
        .page-subtitle {
            color: var(--muted);
            font-size: 0.9rem;
            margin-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def card(content_html: str, extra_style: str = "") -> None:
    st.markdown(
        f"<div class='layz-card' style='{extra_style}'>{content_html}</div>",
        unsafe_allow_html=True,
    )


def badge(label: str, color: str = "purple") -> str:
    """Return an HTML badge string."""
    cls = {
        "green": "badge-green",
        "red": "badge-red",
        "amber": "badge-amber",
        "purple": "badge-purple",
        "gray": "badge-gray",
    }.get(color, "badge-purple")
    return f"<span class='badge {cls}'>{label}</span>"


def page_header(title: str, subtitle: str = ""):
    st.markdown(
        f"<div class='page-title'>{title}</div>"
        + (f"<div class='page-subtitle'>{subtitle}</div>" if subtitle else ""),
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    mapping = {
        "Paid": ("Paid", "green"),
        "Due": ("Due", "amber"),
        "Overdue": ("Overdue", "red"),
        "Partial": ("Partial", "purple"),
        "Active": ("Active", "green"),
        "Inactive": ("Inactive", "gray"),
        "Occupied": ("Occupied", "green"),
        "Vacant": ("Vacant", "gray"),
        "Full": ("Full", "red"),
        "Maintenance": ("Maintenance", "amber"),
    }
    label, color = mapping.get(status, (status, "gray"))
    return badge(label, color)
