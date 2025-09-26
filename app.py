import streamlit as st
import pandas as pd
from supabase import create_client
# streamlit_autorefresh is optional; if installed it will auto-refresh
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except Exception:
    HAS_AUTOREFRESH = False
import plotly.graph_objects as go
import pytz
from datetime import datetime, timedelta
import io

# -----------------------
# Page config + CSS
# -----------------------
st.set_page_config(page_title="Air Compressor Dashboard", page_icon="⚙️", layout="wide")

st.markdown(
    """
    <style>
    /* hide default menu */
    #MainMenu, footer, header {visibility: hidden;}

    /* KPI card */
    .metric-container {
        background: linear-gradient(145deg, #262626, #1a1a1a);
        border-radius: 10px;
        padding: 8px 12px;
        margin: 6px 0;
        color: #ffffff;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        font-family: 'Segoe UI', Tahoma, sans-serif;
        height: 72px;            /* fixed per-card height */
        display:flex;
        flex-direction:column;
        justify-content:center;
        align-items:center;
    }
    .metric-title { font-size:13px; color:#bdbdbd; margin:0; }
    .metric-value { font-size:20px; margin:2px 0; font-weight:600; color:#f5f5f5; }
    .status-badge { font-weight:600; border-radius:8px; padding:3px 8px; font-size:11px; color:#fff; }
    .status-normal { background:#2ec27e; }
    .status-warning { background:#ffcc00; color:#111; }
    .status-critical { background:#ff4b4b; }

    /* Sidebar styling */
    .sidebar-title { font-size:16px; font-weight:700; margin-bottom:8px; }
    .sidebar-note {
        background: linear-gradient(180deg,#2b2b2b,#222);
        padding:10px;
        border-radius:8px;
        color:#ddd;
        font-size:13px;
        margin-top:12px;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------
# Supabase connection
# -----------------------
@st.cache_resource(ttl=30)
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase_client = init_supabase()

# -----------------------
# Thresholds / utils
# -----------------------
STATUS_THRESHOLDS = {
    "temperature": {"warn": 60, "crit": 80, "range": [0, 100]},
    "pressure": {"warn": 9, "crit": 12, "range": [0, 15]},
    "vibration": {"warn": 3, "crit": 5, "range": [0, 8]},
}
STATUS_COLORS = {"normal": "#2ec27e", "warning": "#ffcc00", "critical": "#ff4b4b"}

def get_status(val, param):
    if pd.isna(val):
        return "normal"
    t = STATUS_THRESHOLDS[param]
    if val > t["crit"]:
        return "critical"
    elif val > t["warn"]:
        return "warning"
    return "normal"

def render_kpi(param, value):
    status = get_status(value, param)
    status_class = f"status-{status}"
    # Show numeric with 2 decimals if numeric, else "N/A"
    if pd.isna(value):
        val_str = "N/A"
    else:
        val_str = f"{value:.2f}"
    st.markdown(
        f"""
        <div class="metric-container">
            <div class="metric-title">{param.capitalize()}</div>
            <div style="display:flex; gap:8px; align-items:center;">
                <div class="metric-value">{val_str}</div>
                <div class="status-badge {status_class}">{status.capitalize()}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# -----------------------
# Charts / Gauges
# -----------------------
def create_gauge(value, param, min_val=None, max_val=None, height=200, font_size=20):
    t = STATUS_THRESHOLDS[param]
    rng = [min_val if min_val is not None else t["range"][0], max_val if max_val is not None else t["range"][1]]
    status = get_status(value, param)
    color = STATUS_COLORS[status]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=(0 if pd.isna(value) else value),
        number={'font': {'size': font_size, 'color': color}},
        title={'text': param.capitalize(), 'font': {'size': 14}},
        gauge={
            'axis': {'range': rng, 'tickcolor': "darkgray"},
            'bar': {'color': color, 'thickness': 0.35},
            'steps': [
                {'range': [rng[0], t["warn"]], 'color': "#e6f7ec"},
                {'range': [t["warn"], t["crit"]], 'color': "#fff0d9"},
                {'range': [t["crit"], rng[1]], 'color': "#ffe6e9"},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 3},
                'thickness': 0.8,
                'value': t["crit"]
            }
        }
    ))
    fig.update_layout(height=height, margin=dict(t=30, b=10, l=10, r=10), template="plotly_white")
    return fig

def create_trend_chart(df, param, height=300):
    t = STATUS_THRESHOLDS[param]
    if param not in df.columns or df.empty:
        # empty chart
        fig = go.Figure()
        fig.update_layout(height=height, template="plotly_white", margin=dict(t=30, b=30))
        return fig
    color = STATUS_COLORS[get_status(df[param].iloc[-1], param)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[param], mode="lines+markers", line=dict(width=2, color=color), marker=dict(size=4)))
    fig.add_hline(y=t["warn"], line_dash="dash", line_color="orange", annotation_text="Warning", annotation_position="top left")
    fig.add_hline(y=t["crit"], line_dash="dash", line_color="red", annotation_text="Critical", annotation_position="top left")
    fig.update_layout(title=f"{param.capitalize()} Trend", template="plotly_white", height=height, margin=dict(t=40, b=30, l=30, r=30), yaxis=dict(range=t["range"]), title_x=0.5)
    return fig

# -----------------------
# Data fetch with last-1-hour fallback to last-100
# -----------------------
def fetch_live_or_fallback(limit_fallback=100):
    try:
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        # try last
