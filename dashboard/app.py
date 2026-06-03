# ── app.py ────────────────────────────────────────────────────
# Professional SOC Dashboard — HDFS Anomaly Detection System
# Dark Navy/Blue Theme — University of Bamenda

import streamlit as st
import pandas as pd
import os, sys, io, contextlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from pipeline import predict
from alerting import save_alerts, get_alerts_summary

# ══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="HDFS Anomaly Detection | UBa SOC",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path fill='%231565C0' d='M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z'/></svg>",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════
# SVG ICON LIBRARY — professional, no emojis
# ══════════════════════════════════════════════════════════════
# Each returns an inline SVG string sized to fit the card icon slot
def icon(name, color="#64B5F6", size=22):
    s = size
    icons = {
        # Shield — used for branding
        "shield": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2L4 6V12C4 16.42 7.56 20.57 12 22C16.44 20.57 20 16.42 20 12V6L12 2Z" fill="{color}"/><path d="M10 14.4L7.6 12L6.4 13.2L10 16.8L17.6 9.2L16.4 8L10 14.4Z" fill="white"/></svg>',
        # Bell — alerts
        "bell": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 22C13.1 22 14 21.1 14 20H10C10 21.1 10.9 22 12 22ZM18 16V11C18 7.93 16.36 5.36 13.5 4.68V4C13.5 3.17 12.83 2.5 12 2.5C11.17 2.5 10.5 3.17 10.5 4V4.68C7.63 5.36 6 7.92 6 11V16L4 18V19H20V18L18 16Z" fill="{color}"/></svg>',
        # Warning triangle — critical
        "warning": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1 21H23L12 2L1 21ZM13 18H11V16H13V18ZM13 14H11V10H13V14Z" fill="{color}"/></svg>',
        # Folder — files
        "folder": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M10 4H4C2.9 4 2 4.9 2 6V18C2 19.1 2.9 20 4 20H20C21.1 20 22 19.1 22 18V8C22 6.9 21.1 6 20 6H12L10 4Z" fill="{color}"/></svg>',
        # Clock — timestamp
        "clock": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20ZM12.5 7H11V13L16.25 16.15L17 14.92L12.5 12.25V7Z" fill="{color}"/></svg>',
        # Check circle — normal/online
        "check": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM10 17L5 12L6.41 10.59L10 14.17L17.59 6.58L19 8L10 17Z" fill="{color}"/></svg>',
        # Pulse/radar — system active
        "radar": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20ZM12 6C8.69 6 6 8.69 6 12C6 15.31 8.69 18 12 18C15.31 18 18 15.31 18 12C18 8.69 15.31 6 12 6ZM12 16C9.79 16 8 14.21 8 12C8 9.79 9.79 8 12 8C14.21 8 16 9.79 16 12C16 14.21 14.21 16 12 16ZM12 10C10.9 10 10 10.9 10 12C10 13.1 10.9 14 12 14C13.1 14 14 13.1 14 12C14 13.1 13.1 10 12 10Z" fill="{color}"/></svg>',
        # Upload arrow
        "upload": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4C9.11 4 6.6 5.64 5.35 8.04C2.34 8.36 0 10.91 0 14C0 17.31 2.69 20 6 20H19C21.76 20 24 17.76 24 15C24 12.36 21.95 10.22 19.35 10.04ZM14 13V17H10V13H7L12 8L17 13H14Z" fill="{color}"/></svg>',
        # List/log lines
        "list": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3 13H5V11H3V13ZM3 17H5V15H3V17ZM3 9H5V7H3V9ZM7 13H21V11H7V13ZM7 17H21V15H7V17ZM7 7V9H21V7H7Z" fill="{color}"/></svg>',
        # Info circle
        "info": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM13 17H11V11H13V17ZM13 9H11V7H13V9Z" fill="{color}"/></svg>',
        # Database
        "database": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 3C7.58 3 4 4.79 4 7V17C4 19.21 7.58 21 12 21C16.42 21 20 19.21 20 17V7C20 4.79 16.42 3 12 3ZM18 17C18 17.5 15.87 19 12 19C8.13 19 6 17.5 6 17V14.77C7.61 15.55 9.72 16 12 16C14.28 16 16.39 15.55 18 14.77V17ZM18 12.45C16.7 13.4 14.42 14 12 14C9.58 14 7.3 13.4 6 12.45V9.64C7.47 10.47 9.61 11 12 11C14.39 11 16.53 10.47 18 9.64V12.45ZM12 9C8.13 9 6 7.5 6 7C6 6.5 8.13 5 12 5C15.87 5 18 6.5 18 7C18 7.5 15.87 9 12 9Z" fill="{color}"/></svg>',
        # Chip/processor
        "chip": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9 3H7V1H5V3H3V5H1V7H3V9H1V11H3V13H1V15H3V17H5V19H7V21H9V19H11V21H13V19H15V21H17V19H19V17H21V15H19V13H21V11H19V9H21V7H19V5H17V3H15V1H13V3H11V1H9V3ZM17 17H7V7H17V17Z" fill="{color}"/></svg>',
        # Chart bar
        "chart": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M5 9.2H8V19H5V9.2ZM10.6 5H13.4V19H10.6V5ZM16.2 13H19V19H16.2V13Z" fill="{color}"/></svg>',
        # Refresh arrows
        "refresh": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4C7.58 4 4.01 7.58 4.01 12C4.01 16.42 7.58 20 12 20C15.73 20 18.84 17.45 19.73 14H17.65C16.83 16.33 14.61 18 12 18C8.69 18 6 15.31 6 12C6 8.69 8.69 6 12 6C13.66 6 15.14 6.69 16.22 7.78L13 11H20V4L17.65 6.35Z" fill="{color}"/></svg>',
        # Lock
        "lock": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 8H17V6C17 3.24 14.76 1 12 1C9.24 1 7 3.24 7 6V8H6C4.9 8 4 8.9 4 10V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V10C20 8.9 19.1 8 18 8ZM12 17C10.9 17 10 16.1 10 15C10 13.9 10.9 13 12 13C13.1 13 14 13.9 14 15C14 16.1 13.1 17 12 17ZM15.1 8H8.9V6C8.9 4.29 10.29 2.9 12 2.9C13.71 2.9 15.1 4.29 15.1 6V8Z" fill="{color}"/></svg>',
        # Tree (model)
        "tree": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 12H13V7H15L12 3L9 7H11V12H7V10L4 13L7 16V14H11V19H9L12 22L15 19H13V14H17V16L20 13L17 10V12Z" fill="{color}"/></svg>',
    }
    return icons.get(name, icons["info"])


# ══════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Hide Streamlit chrome ── */
#MainMenu { visibility: hidden; }
header[data-testid="stHeader"] { display: none; }
footer { visibility: hidden; }

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Segoe UI', 'Inter', sans-serif;
}
.main .block-container {
    background-color: #0B1120;
    padding-top: 1.2rem;
    padding-bottom: 2rem;
    max-width: 100%;
}
.stApp { background-color: #0B1120; }

/* ── Metric card text — adaptive, no clipping ── */
.metric-value {
    font-size: clamp(14px, 1.8vw, 24px);
    font-weight: 800;
    color: #FFFFFF;
    line-height: 1.15;
    margin-bottom: 5px;
    word-break: break-word;
    overflow-wrap: break-word;
}
.metric-label {
    font-size: 10px;
    font-weight: 700;
    color: #64B5F6;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 2px;
    word-break: break-word;
}
.metric-sub {
    font-size: 10px;
    color: #546E7A;
    word-break: break-word;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1B2A 0%, #112240 100%);
    border-right: 1px solid #1E3A5F;
}
[data-testid="stSidebar"] * { color: #A8C0D6 !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    font-size: 13px !important;
    padding: 6px 0 !important;
    font-weight: 500 !important;
}

/* ── Native metric containers ── */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #112240 0%, #0D1B2A 100%);
    border: 1px solid #1E3A5F;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #1E3A5F;
    border-radius: 8px;
    overflow: hidden;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #1565C0, #0D47A1);
    color: white !important;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    transition: all 0.2s;
    white-space: nowrap;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1976D2, #1565C0);
    box-shadow: 0 0 15px rgba(21,101,192,0.4);
    transform: translateY(-1px);
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: #112240;
    border: 1px solid #1E3A5F;
    color: white;
    border-radius: 8px;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #112240;
    border: 1px solid #1E3A5F;
    border-radius: 8px;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #112240;
    border: 2px dashed #1E3A5F;
    border-radius: 12px;
}

/* ── Divider ── */
hr { border-color: #1E3A5F; }

/* ── Status dot ── */
.dot-online {
    display: inline-block; width: 8px; height: 8px;
    background: #00E676; border-radius: 50%;
    box-shadow: 0 0 5px #00E676; margin-right: 7px;
    vertical-align: middle;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════
BASE         = os.path.join(os.path.dirname(__file__), '..')
ALERTS_PATH  = os.path.join(BASE, 'alerts', 'alerts_log.csv')
WATCH_FOLDER = os.path.join(BASE, 'watch_folder')

# ══════════════════════════════════════════════════════════════
# MATPLOTLIB DARK THEME
# ══════════════════════════════════════════════════════════════
plt.rcParams.update({
    'figure.facecolor': '#0D1B2A', 'axes.facecolor': '#112240',
    'axes.edgecolor': '#1E3A5F',   'axes.labelcolor': '#90CAF9',
    'xtick.color': '#90CAF9',      'ytick.color': '#90CAF9',
    'text.color': '#E3F2FD',       'grid.color': '#1E3A5F',
    'grid.alpha': 0.4,             'axes.grid': True,
    'axes.spines.top': False,      'axes.spines.right': False,
})

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def fmt_num(n):
    try:
        n = int(n)
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
        if n >= 10_000:    return f"{n/1_000:.1f}K"
        return f"{n:,}"
    except:
        return str(n)

def metric_card(icon_name, label, value, sub, border_color="#1565C0", icon_color="#64B5F6"):
    svg = icon(icon_name, color=icon_color, size=24)
    st.markdown(f"""
    <div style='
        background: linear-gradient(135deg, #112240 0%, #0D1B2A 100%);
        border: 1px solid {border_color};
        border-top: 3px solid {border_color};
        border-radius: 12px;
        padding: 18px 10px 14px 10px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        min-height: 115px;
        box-sizing: border-box;
    '>
        <div style='margin-bottom:6px; line-height:1;'>{svg}</div>
        <div class='metric-value'>{value}</div>
        <div class='metric-label'>{label}</div>
        <div class='metric-sub'>{sub}</div>
    </div>
    """, unsafe_allow_html=True)

def section_header(title, subtitle=""):
    st.markdown(f"""
    <div style='margin-bottom:14px; padding-bottom:8px; border-bottom:1px solid #1E3A5F;'>
        <span style='font-size:1rem; font-weight:700; color:#E3F2FD;'>{title}</span>
        {"<span style='font-size:0.78rem; color:#546E7A; margin-left:10px;'>" + subtitle + "</span>" if subtitle else ""}
    </div>
    """, unsafe_allow_html=True)

def fmt_ts(ts):
    try:
        return datetime.strptime(str(ts)[:16], "%Y-%m-%d %H:%M").strftime("%d %b %Y %H:%M")
    except:
        return str(ts)[:16]

def fmt_ts_short(ts):
    try:
        return datetime.strptime(str(ts)[:16], "%Y-%m-%d %H:%M").strftime("%d %b %H:%M")
    except:
        return str(ts)[:13]

# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    shield_svg = icon("shield", color="#1565C0", size=36)
    st.markdown(f"""
    <div style='text-align:center; padding:14px 0 20px 0;
         border-bottom:1px solid #1E3A5F; margin-bottom:18px;'>
        <div style='margin-bottom:6px;'>{shield_svg}</div>
        <div style='font-size:15px; font-weight:700; color:#E3F2FD;
             letter-spacing:0.04em;'>UBa SOC</div>
        <div style='font-size:9px; color:#546E7A; letter-spacing:0.12em;
             text-transform:uppercase; margin-top:2px;'>Security Operations Centre</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<p style='font-size:10px; color:#546E7A; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:8px;'>System Status</p>", unsafe_allow_html=True)
    st.markdown("""
    <div style='background:#0A2818; border:1px solid #1B5E20; border-radius:7px;
         padding:8px 12px; margin-bottom:7px;'>
        <span class='dot-online'></span>
        <span style='color:#69F0AE; font-size:12px; font-weight:600;'>Model Loaded</span>
    </div>
    <div style='background:#0A2818; border:1px solid #1B5E20; border-radius:7px;
         padding:8px 12px; margin-bottom:18px;'>
        <span class='dot-online'></span>
        <span style='color:#69F0AE; font-size:12px; font-weight:600;'>File Watcher Active</span>
        <div style='color:#546E7A; font-size:10px; margin-top:3px; margin-left:15px;'>
            Monitoring watch_folder/ for new log files
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<p style='font-size:10px; color:#546E7A; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:10px;'>Navigation</p>", unsafe_allow_html=True)
    page = st.radio(
        "", ["Dashboard", "Upload & Analyse", "Alerts Log", "Model Info"],
        label_visibility="collapsed"
    )

    st.markdown("""
    <div style='border-top:1px solid #1E3A5F; margin-top:20px; padding-top:14px;'>
        <p style='font-size:9px; color:#37474F; text-align:center; line-height:1.8;'>
            Centre for Cybersecurity &amp; Mathematical Cryptology<br>
            University of Bamenda<br>
            Academic Year 2025–2026
        </p>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# TOP HEADER
# ══════════════════════════════════════════════════════════════
page_meta = {
    "Dashboard":        ("DASHBOARD",        "Real-time anomaly monitoring"),
    "Upload & Analyse": ("UPLOAD & ANALYSE", "Submit log files for instant analysis"),
    "Alerts Log":       ("ALERTS LOG",       "Full detection history with filtering"),
    "Model Info":       ("MODEL INFO",       "Performance metrics and model details"),
}
pname, pdesc = page_meta.get(page, ("DASHBOARD", ""))
now = datetime.now().strftime("%d %b %Y  %H:%M")

st.markdown(f"""
<div style='
    background: linear-gradient(90deg, #0D1B2A 0%, #112240 100%);
    border: 1px solid #1E3A5F;
    border-left: 3px solid #1565C0;
    border-radius: 10px;
    padding: 14px 22px;
    margin-bottom: 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
'>
    <div>
        <div style='font-size:1.15rem; font-weight:800; color:#E3F2FD;
             letter-spacing:0.04em;'>HDFS Anomaly Detection — {pname}</div>
        <div style='font-size:0.78rem; color:#546E7A; margin-top:2px;'>{pdesc}</div>
    </div>
    <div style='text-align:right;'>
        <div style='font-size:9px; color:#37474F; text-transform:uppercase;
             letter-spacing:0.1em;'>University of Bamenda</div>
        <div style='font-size:11px; color:#546E7A; margin-top:2px;'>{now}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════
if page == "Dashboard":

    alerts_data = get_alerts_summary()

    c1, c2, c3, c4 = st.columns(4)
    if alerts_data:
        summary, df = alerts_data
        latest_raw = str(summary.get('latest_alert', ''))[:16]
        try:
            dt = datetime.strptime(latest_raw, "%Y-%m-%d %H:%M")
            latest = dt.strftime("%d %b %H:%M")
        except:
            latest = latest_raw[:13] if latest_raw else "—"

        with c1: metric_card("bell",    "Total Alerts",   fmt_num(summary['total_alerts']),   "All anomalies",  "#1565C0", "#64B5F6")
        with c2: metric_card("warning", "Critical",        fmt_num(summary['critical']),        "Conf. >= 95%",   "#B71C1C", "#EF9A9A")
        with c3: metric_card("folder",  "Files Processed", fmt_num(summary['files_processed']), "Log files",      "#1B5E20", "#A5D6A7")
        with c4: metric_card("clock",   "Latest Alert",    latest,                              "Most recent",    "#E65100", "#FFCC80")
    else:
        with c1: metric_card("bell",   "Total Alerts",   "0",      "No alerts yet",  "#1565C0", "#64B5F6")
        with c2: metric_card("warning","Critical",        "0",      "Conf. >= 95%",   "#B71C1C", "#EF9A9A")
        with c3: metric_card("folder", "Files Processed", "0",      "Log files",      "#1B5E20", "#A5D6A7")
        with c4: metric_card("radar",  "Status",          "Online", "Watching logs",  "#1B5E20", "#A5D6A7")

    st.markdown("<div style='margin-top:26px;'></div>", unsafe_allow_html=True)

    if alerts_data:
        summary, df = alerts_data
        col_left, col_right = st.columns([1.2, 0.8])

        with col_left:
            section_header("Alert Severity Distribution", f"{summary['total_alerts']:,} total alerts")

            severity_order  = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
            severity_counts = df['Severity'].value_counts().reindex(severity_order, fill_value=0)
            colors_bar      = ['#B71C1C', '#E65100', '#F57F17', '#1565C0']

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3.5),
                                           gridspec_kw={'width_ratios': [2, 1]})

            bars = ax1.bar(severity_counts.index, severity_counts.values,
                          color=colors_bar, width=0.55, zorder=3)
            max_val = severity_counts.max()
            min_nonzero = severity_counts[severity_counts > 0].min() if (severity_counts > 0).any() else 1
            use_log = (max_val > 0 and min_nonzero > 0 and max_val / min_nonzero > 100)
            if use_log:
                ax1.set_yscale('log')
                ax1.set_title("By Severity (log scale)", fontsize=10, fontweight='bold', color='#E3F2FD', pad=8)
            else:
                ax1.set_title("By Severity", fontsize=11, fontweight='bold', color='#E3F2FD', pad=8)

            for bar, count in zip(bars, severity_counts.values):
                if count > 0:
                    y = bar.get_height() * 1.05 if use_log else bar.get_height() + max_val * 0.01
                    ax1.text(bar.get_x() + bar.get_width()/2, y,
                            fmt_num(count), ha='center', va='bottom',
                            fontsize=9, fontweight='bold', color='#E3F2FD')
            ax1.set_ylabel("Count", fontsize=9)
            ax1.tick_params(labelsize=9)
            ax1.set_facecolor('#112240')

            total_al    = severity_counts.sum()
            wedge_sizes = [max(v, 0.001) for v in severity_counts.values]
            ax2.pie(wedge_sizes, colors=colors_bar, startangle=90,
                   wedgeprops=dict(width=0.55))
            ax2.text(0,  0,    fmt_num(total_al), ha='center', va='center',
                    fontsize=14, fontweight='bold', color='#E3F2FD')
            ax2.text(0, -0.22, 'total', ha='center', va='center',
                    fontsize=8, color='#546E7A')
            ax2.set_title("Proportion", fontsize=11, fontweight='bold', color='#E3F2FD', pad=8)

            fig.patch.set_facecolor('#0D1B2A')
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close()

        with col_right:
            section_header("Recent Alerts", "Last 10 detections")
            recent = df.tail(10)[['BlockId','Severity','Confidence','Timestamp']].copy()
            recent = recent.sort_values('Timestamp', ascending=False)
            recent['Confidence'] = recent['Confidence'].apply(lambda x: f"{float(x):.1f}%")
            recent['BlockId']    = recent['BlockId'].astype(str).str[:14] + "…"
            recent['Timestamp']  = recent['Timestamp'].apply(fmt_ts_short)
            st.dataframe(
                recent, use_container_width=True, hide_index=True,
                column_config={
                    "BlockId":    st.column_config.TextColumn("Block ID",  width="small"),
                    "Severity":   st.column_config.TextColumn("Severity",  width="small"),
                    "Confidence": st.column_config.TextColumn("Conf.",     width="small"),
                    "Timestamp":  st.column_config.TextColumn("Time",      width="small"),
                }
            )

        st.markdown("<div style='margin-top:22px;'></div>", unsafe_allow_html=True)
        section_header("Severity Breakdown — Percentage Share")
        b1, b2, b3, b4 = st.columns(4)
        total_al = max(summary['total_alerts'], 1)
        with b1:
            metric_card("warning", "Critical", f"{summary['critical']/total_al*100:.1f}%",
                       f"{summary['critical']:,} alerts", "#B71C1C", "#EF9A9A")
        with b2:
            metric_card("warning", "High", f"{summary['high']/total_al*100:.1f}%",
                       f"{summary['high']:,} alerts", "#E65100", "#FFCC80")
        with b3:
            metric_card("bell", "Medium", f"{summary['medium']/total_al*100:.1f}%",
                       f"{summary['medium']:,} alerts", "#F57F17", "#FFF176")
        with b4:
            low = summary.get('low', 0)
            metric_card("bell", "Low", f"{low/total_al*100:.1f}%",
                       f"{low:,} alerts", "#1565C0", "#90CAF9")

    else:
        st.markdown("""
        <div style='background:#060D1A; border:1px dashed #1E3A5F; border-radius:12px;
             padding:60px; text-align:center; margin-top:20px;'>
            <div style='font-size:0.9rem; color:#37474F; margin-bottom:10px;
                 text-transform:uppercase; letter-spacing:0.1em;'>System Active</div>
            <div style='font-size:1.1rem; font-weight:700; color:#E3F2FD; margin-bottom:6px;'>
                No alerts yet</div>
            <div style='font-size:0.85rem; color:#546E7A;'>
                Upload a log file to begin analysis.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
    col_btn, _ = st.columns([1, 5])
    with col_btn:
        if st.button("Refresh Dashboard"):
            st.rerun()

# ══════════════════════════════════════════════════════════════
# PAGE 2 — UPLOAD & ANALYSE
# ══════════════════════════════════════════════════════════════
elif page == "Upload & Analyse":

    st.markdown("""
    <div style='background:#060D1A; border:1px solid #1E3A5F; border-radius:10px;
         padding:16px 20px; margin-bottom:20px;'>
        <div style='font-size:0.9rem; color:#90CAF9;'>
            Upload an HDFS structured CSV log file. The system will automatically extract
            session features, run the Random Forest classifier, and generate severity-ranked alerts.
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Expected File Format — click to expand"):
        st.markdown("""
**Format 1 — Raw HDFS Structured Log** (required columns: `EventId`, `Content`)

| EventId | Content |
|---|---|
| E5  | Receiving block blk\\_-160899... src: /10.250.10.6 |
| E22 | Served block blk\\_-160899... to /10.250.10.6 |

**Format 2 — Pre-computed Feature Matrix** (required columns: `BlockId`, `E1` ... `E29`)

Compatible source: **LogHub HDFS v1** — `HDFS.log_structured.csv`
        """)
        st.warning("Files missing EventId or E1-E29 columns will return an error.")

    uploaded_file = st.file_uploader(
        "Drop your HDFS log file here",
        type=['csv', 'log'],
        help="Accepts CSV or LOG format — max 200 MB"
    )

    if uploaded_file:
        st.markdown(f"""
        <div style='background:#0A2818; border:1px solid #1B5E20; border-radius:8px;
             padding:10px 16px; margin-bottom:14px;'>
            <span style='color:#69F0AE; font-weight:600;'>File received: {uploaded_file.name}</span>
            <span style='color:#546E7A; font-size:0.85rem;'> — ready for analysis</span>
        </div>
        """, unsafe_allow_html=True)

        save_path = os.path.join(WATCH_FOLDER, uploaded_file.name)
        with open(save_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())

        if st.button("Run Analysis"):
            st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
            section_header("Live Processing Log")
            log_box   = st.empty()
            log_lines = []

            def append_log(msg, color="#69F0AE"):
                ts = datetime.now().strftime("%H:%M:%S")
                log_lines.append(
                    f"<span style='color:#37474F;'>[{ts}]</span>"
                    f"&nbsp;&nbsp;<span style='color:{color};'>{msg}</span>"
                )
                log_box.markdown(
                    "<div style='background:#020810; border:1px solid #1E3A5F;"
                    "border-radius:10px; padding:16px 18px;"
                    "font-family:\"Courier New\",monospace; font-size:12.5px;"
                    "max-height:280px; overflow-y:auto; line-height:2.1;'>"
                    + "<br>".join(log_lines) + "</div>",
                    unsafe_allow_html=True
                )

            try:
                append_log("Pipeline initialised", "#64B5F6")
                append_log(f"Reading: {uploaded_file.name}", "#64B5F6")

                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    results = predict(save_path)
                for line in buf.getvalue().strip().splitlines():
                    if line.strip():
                        append_log(f"  {line.strip()}", "#90CAF9")

                append_log("Feature extraction complete", "#69F0AE")
                append_log("Random Forest inference complete", "#69F0AE")

                buf2 = io.StringIO()
                with contextlib.redirect_stdout(buf2):
                    alert_count = save_alerts(results)
                for line in buf2.getvalue().strip().splitlines():
                    if line.strip():
                        append_log(f"  {line.strip()}", "#FFD54F")

                total     = len(results)
                anomalies = int((results['Prediction'] == 'Anomaly').sum())
                normals   = total - anomalies

                append_log(f"Sessions: {total:,}  |  Normal: {normals:,}  |  Anomalies: {anomalies:,}",
                          "#EF5350" if anomalies > 0 else "#69F0AE")
                append_log(f"Anomaly rate: {anomalies/total*100:.2f}%", "#FFD54F")
                append_log("Alerts saved to alerts/alerts_log.csv", "#69F0AE")
                append_log("Analysis complete", "#64B5F6")

                st.markdown("<div style='margin-top:22px;'></div>", unsafe_allow_html=True)
                section_header("Analysis Results")
                r1, r2, r3 = st.columns(3)
                with r1: metric_card("database", "Sessions",  fmt_num(total),     "Log sessions analysed", "#1565C0", "#64B5F6")
                with r2: metric_card("check",    "Normal",    fmt_num(normals),   "No threat detected",    "#1B5E20", "#A5D6A7")
                with r3: metric_card("warning",  "Anomalies", fmt_num(anomalies), "Threats detected",      "#B71C1C", "#EF9A9A")

                if anomalies > 0:
                    st.markdown(f"""
                    <div style='background:#120000; border:1px solid #B71C1C; border-radius:8px;
                         padding:12px 16px; margin:14px 0; color:#EF9A9A;'>
                        <strong>{anomalies:,} anomalous sessions detected</strong>
                        — alerts have been saved to the Alerts Log.
                    </div>
                    """, unsafe_allow_html=True)
                    anom_df = results[results['Prediction'] == 'Anomaly'].copy()
                    anom_df['Confidence'] = anom_df['Confidence'].apply(lambda x: f"{float(x):.2f}%")
                    st.markdown("**Anomalous Sessions**")
                    st.dataframe(anom_df, use_container_width=True, hide_index=True)
                else:
                    st.markdown("""
                    <div style='background:#0A2818; border:1px solid #1B5E20; border-radius:8px;
                         padding:12px 16px; margin:14px 0; color:#69F0AE;'>
                        No anomalies detected. All sessions within normal parameters.
                    </div>
                    """, unsafe_allow_html=True)

                results_display = results.copy()
                results_display['Confidence'] = results_display['Confidence'].apply(lambda x: f"{float(x):.2f}%")
                st.markdown("**Full Results**")
                st.dataframe(results_display, use_container_width=True, hide_index=True)

                csv = results.to_csv(index=False)
                st.download_button("Download Results as CSV", data=csv,
                                  file_name=f"results_{uploaded_file.name}", mime='text/csv')

            except Exception as e:
                append_log(f"ERROR: {e}", "#EF5350")
                st.error(f"Error during analysis: {e}")

# ══════════════════════════════════════════════════════════════
# PAGE 3 — ALERTS LOG
# ══════════════════════════════════════════════════════════════
elif page == "Alerts Log":

    if os.path.exists(ALERTS_PATH):
        df = pd.read_csv(ALERTS_PATH)

        f1, f2 = st.columns(2)
        with f1:
            severity_filter = st.selectbox("Filter by Severity",
                                          ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
        with f2:
            file_filter = st.selectbox("Filter by File",
                                      ["All"] + sorted(df['Source_File'].unique().tolist()))

        filtered = df.copy()
        if severity_filter != "All":
            filtered = filtered[filtered['Severity'] == severity_filter]
        if file_filter != "All":
            filtered = filtered[filtered['Source_File'] == file_filter]

        crit = int((filtered['Severity'] == 'CRITICAL').sum())
        high = int((filtered['Severity'] == 'HIGH').sum())
        med  = int((filtered['Severity'] == 'MEDIUM').sum())
        low  = int((filtered['Severity'] == 'LOW').sum())

        st.markdown(f"""
        <div style='background:#060D1A; border:1px solid #1E3A5F; border-radius:8px;
             padding:10px 16px; margin-bottom:14px; font-size:0.82rem;'>
            <span style='color:#64B5F6; font-weight:700;'>Showing {len(filtered):,} alerts</span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            <span style='color:#EF5350;'>Critical: <strong>{crit:,}</strong></span>&nbsp;
            <span style='color:#FF8A65;'>High: <strong>{high:,}</strong></span>&nbsp;
            <span style='color:#FFD54F;'>Medium: <strong>{med:,}</strong></span>&nbsp;
            <span style='color:#64B5F6;'>Low: <strong>{low:,}</strong></span>
        </div>
        """, unsafe_allow_html=True)

        display_df = filtered.copy()
        display_df['Confidence'] = display_df['Confidence'].apply(lambda x: f"{float(x):.2f}%")
        display_df['BlockId']    = display_df['BlockId'].astype(str).str[:18] + "…"
        display_df['Timestamp']  = display_df['Timestamp'].apply(fmt_ts)

        st.dataframe(
            display_df, use_container_width=True, hide_index=True,
            column_config={
                "BlockId":     st.column_config.TextColumn("Block ID",    width="medium"),
                "Prediction":  st.column_config.TextColumn("Prediction",  width="small"),
                "Confidence":  st.column_config.TextColumn("Confidence",  width="small"),
                "Severity":    st.column_config.TextColumn("Severity",    width="small"),
                "Timestamp":   st.column_config.TextColumn("Timestamp",   width="medium"),
                "Source_File": st.column_config.TextColumn("Source File", width="medium"),
            }
        )

        col_dl, _ = st.columns([1, 3])
        with col_dl:
            csv = filtered.to_csv(index=False)
            st.download_button("Download Filtered Alerts", data=csv,
                              file_name="alerts_log.csv", mime='text/csv')
    else:
        st.markdown("""
        <div style='background:#060D1A; border:1px dashed #1E3A5F; border-radius:12px;
             padding:60px; text-align:center;'>
            <div style='color:#546E7A; font-size:0.85rem; text-transform:uppercase;
                 letter-spacing:0.1em; margin-bottom:10px;'>No Records</div>
            <div style='color:#E3F2FD; font-size:1.05rem; font-weight:600;'>No alerts logged yet</div>
            <div style='color:#546E7A; margin-top:6px; font-size:0.85rem;'>
                Run an analysis to see alerts here.</div>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# PAGE 4 — MODEL INFO
# ══════════════════════════════════════════════════════════════
elif page == "Model Info":

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style='background:linear-gradient(135deg,#0D1E35,#0D1B2A);
             border:1px solid #1565C0; border-top:3px solid #1565C0;
             border-radius:12px; padding:18px; margin-bottom:14px;'>
            <div style='font-size:0.95rem; font-weight:700; color:#64B5F6; margin-bottom:12px;'>
                Random Forest — Primary Model
            </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        | Property | Value |
        |---|---|
        | Algorithm | Random Forest Classifier |
        | Trees | 100 |
        | Features | 29 (E1–E29) |
        | Train / Test Split | 70% / 30% stratified |
        | Pre-SMOTE training samples | 402,542 |
        | Post-SMOTE training samples | 781,510 |
        | Test samples | 172,519 (no SMOTE) |
        | Accuracy | 99.99% |
        | F1-Score | 0.9981 |
        | Precision | 1.00 * |
        | Recall | 1.00 |
        | Attacks caught | 5,047 / 5,051 |
        | False alarms | 15 |
        """)
        st.caption("* Rounded — CV Precision mean = 0.9977 +/- 0.0008")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style='background:linear-gradient(135deg,#131313,#0D1B2A);
             border:1px solid #37474F; border-top:3px solid #546E7A;
             border-radius:12px; padding:18px; margin-bottom:14px;'>
            <div style='font-size:0.95rem; font-weight:700; color:#90A4AE; margin-bottom:12px;'>
                Isolation Forest — Baseline Model
            </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        | Property | Value |
        |---|---|
        | Algorithm | Isolation Forest |
        | Trees | 100 |
        | Features | 29 (E1–E29) |
        | Type | Unsupervised (no labels) |
        | Contamination | 0.029 (natural rate) |
        | Accuracy | 98.22% |
        | F1-Score | 0.6590 |
        | Precision | 0.75 |
        | Recall | 0.59 |
        | Attacks caught | 2,962 / 5,051 |
        | False alarms | 977 |
        """)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
    section_header("Dataset — LogHub HDFS v1")
    d1, d2, d3, d4 = st.columns(4)
    with d1: metric_card("database", "Sessions",  "575K",  "Total HDFS v1",      "#1565C0", "#64B5F6")
    with d2: metric_card("check",    "Normal",    "558K",  "97.1% of dataset",   "#1B5E20", "#A5D6A7")
    with d3: metric_card("warning",  "Anomalous", "16.8K", "2.9% of dataset",    "#B71C1C", "#EF9A9A")
    with d4: metric_card("chip",     "Features",  "29",    "E1-E29 event counts","#4A148C", "#CE93D8")

    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
    section_header("5-Fold Cross-Validation Results")
    st.success("Stable across all folds — std dev 0.0006 confirms no overfitting")
    st.markdown("""
    | Fold | F1-Score | Accuracy | Precision | Recall |
    |---|---|---|---|---|
    | Fold 1 | 0.9983 | 99.99% | 0.9977 | 0.9989 |
    | Fold 2 | 0.9984 | 99.99% | 0.9978 | 0.9990 |
    | Fold 3 | 0.9981 | 99.99% | 0.9975 | 0.9987 |
    | Fold 4 | 0.9985 | 99.99% | 0.9979 | 0.9991 |
    | Fold 5 | 0.9982 | 99.99% | 0.9976 | 0.9988 |
    | **Mean +/- Std** | **0.9983 +/- 0.0006** | **99.99%** | **0.9977 +/- 0.0008** | **0.9989 +/- 0.0003** |
    """)

    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
    section_header("Feature Importance — Top HDFS Log Events")
    img_path = os.path.join(BASE, 'feature_importance_semantic.png')
    fallback  = os.path.join(BASE, 'feature_importance.png')
    if os.path.exists(img_path):
        st.image(img_path, use_container_width=True)
    elif os.path.exists(fallback):
        st.image(fallback, use_container_width=True)

    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    section_header("Event Template Reference")
    st.markdown("""
    | Event | Importance | HDFS Log Template | Why It Matters |
    |---|---|---|---|
    | **E20** | 0.3263 | Unexpected error trying to DELETE a block | Strongest signal — block deletion failure indicates attack or corruption |
    | **E26** | 0.1305 | NameSystem addStoredBlock — blockMap updated | Abnormal replication or storage frequency |
    | **E27** | 0.0804 | NameSystem addStoredBlock — Redundant | Replication failures or storage inconsistencies |
    | **E9**  | 0.0693 | Received block of size from node | Abnormal block reception — possible data corruption |
    | **E11** | 0.0663 | PacketResponder for block terminating | Network failures or node crashes |
    """)

    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    section_header("Alert Severity Classification Logic")
    st.markdown("""
    | Severity | Confidence Threshold | Meaning | Action |
    |---|---|---|---|
    | CRITICAL | >= 95% | Near-certain threat | Immediate response |
    | HIGH | 80-94% | Strong indicator | Prompt investigation |
    | MEDIUM | 65-79% | Moderate suspicion | Scheduled review |
    | LOW | < 65% | Weak signal | Periodic monitoring |
    """)