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

# -----------------------
# Page config + CSS
# -----------------------
st.set_page_config(page_title="Air Compressor Dashboard", page_icon="⚙️", layout="wide")

st.markdown(
    """
    <style>
    #MainMenu, footer, header {visibility: hidden;}

    .metric-container {
        background: linear-gradient(145deg, #262626, #1a1a1a);
        border-radius: 10px;
        padding: 8px 12px;
        margin: 6px 0;
        color: #ffffff;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        font-family: 'Segoe UI', Tahoma, sans-serif;
        height: 72px;
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
    val_str = "N/A" if pd.isna(value) else f"{value:.2f}"
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
        fig = go.Figure()
        fig.update_layout(height=height, template="plotly_white", margin=dict(t=30, b=30))
        return fig
    color = STATUS_COLORS[get_status(df[param].iloc[-1], param)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[param], mode="lines+markers",
                             line=dict(width=2, color=color), marker=dict(size=4)))
    fig.add_hline(y=t["warn"], line_dash="dash", line_color="orange",
                  annotation_text="Warning", annotation_position="top left")
    fig.add_hline(y=t["crit"], line_dash="dash", line_color="red",
                  annotation_text="Critical", annotation_position="top left")
    fig.update_layout(title=f"{param.capitalize()} Trend", template="plotly_white",
                      height=height, margin=dict(t=40, b=30, l=30, r=30),
                      yaxis=dict(range=t["range"]), title_x=0.5)
    return fig

# -----------------------
# Data fetch with last-1-hour fallback to last-100
# -----------------------
def fetch_live_or_fallback(limit_fallback=100):
    try:
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        resp = (supabase_client.table("air_compressor")
                .select("*")
                .gte("timestamp", one_hour_ago.isoformat())
                .order("timestamp", desc=True)
                .execute())
        df = pd.DataFrame(resp.data)
        used_fallback = False

        if df.empty:
            resp2 = (supabase_client.table("air_compressor")
                     .select("*")
                     .order("timestamp", desc=True)
                     .limit(limit_fallback)
                     .execute())
            df = pd.DataFrame(resp2.data)
            if not df.empty:
                st.warning("⚠️ No records in the last 1 hour — showing latest {} entries instead.".format(limit_fallback))
                used_fallback = True

        if df.empty:
            return pd.DataFrame(), used_fallback

        ist = pytz.timezone("Asia/Kolkata")
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(ist)
        df = df.set_index("timestamp").sort_index()
        return df, used_fallback
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame(), False

# -----------------------
# Sidebar
# -----------------------
with st.sidebar:
    st.markdown("<div class='sidebar-title'>Dashboard Menu</div>", unsafe_allow_html=True)
    app_mode = st.radio("Select view", ["Live Dashboard", "Database"])
    st.markdown("<div class='sidebar-note'>Tip: Live Dashboard shows recent data (last 1 hour by default). Use Database to query historical ranges and download CSV.</div>", unsafe_allow_html=True)

# -----------------------
# Title
# -----------------------
st.title("Air Compressor Monitoring Dashboard")

# -----------------------
# Fetch data
# -----------------------
data, used_fallback = fetch_live_or_fallback(limit_fallback=100)

if app_mode == "Live Dashboard":
    if HAS_AUTOREFRESH:
        st_autorefresh(interval=5000, key="auto_refresh_dashboard")
    else:
        st.caption("Auto-refresh not available. Refresh the page manually.")

    if data.empty:
        st.warning("No data available. Please check ESP32 / network / Supabase.")
    else:
        latest = data.iloc[-1]

        gauges_col, kpis_col = st.columns([3, 1])

        with gauges_col:
            g1, g2, g3 = st.columns(3)
            with g1:
                st.plotly_chart(create_gauge(latest.get("temperature", float("nan")), "Temperature"), use_container_width=True)
            with g2:
                st.plotly_chart(create_gauge(latest.get("pressure", float("nan")), "Pressure"), use_container_width=True)
            with g3:
                st.plotly_chart(create_gauge(latest.get("vibration", float("nan")), "Vibration"), use_container_width=True)

        with kpis_col:
            render_kpi("temperature", latest.get("temperature", float("nan")))
            render_kpi("pressure", latest.get("pressure", float("nan")))
            render_kpi("vibration", latest.get("vibration", float("nan")))

        st.subheader("Live Trends")
        for param in ["temperature", "pressure", "vibration"]:
            st.plotly_chart(create_trend_chart(data, param, height=320), use_container_width=True)

        try:
            last_ts = data.index.max()
            st.caption(f"Last update (IST): {last_ts.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        except Exception:
            pass

elif app_mode == "Database":
    st.subheader("Explore Raw Data (Supabase)")

    left_col, mid_col, right_col = st.columns(3)
    with left_col:
        start_date = st.date_input("Start Date", value=(datetime.now().date() - timedelta(days=7)))
    with mid_col:
        end_date = st.date_input("End Date", value=datetime.now().date())
    with right_col:
        params = ["temperature", "pressure", "vibration"]
        selected_params = st.multiselect("Select Parameter(s)", options=params, default=params)

    try:
        ist = pytz.timezone("Asia/Kolkata")
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        start_utc = ist.localize(start_dt).astimezone(pytz.utc)
        end_utc = ist.localize(end_dt).astimezone(pytz.utc)

        resp = (supabase_client.table("air_compressor")
                .select("*")
                .gte("timestamp", start_utc.isoformat())
                .lte("timestamp", end_utc.isoformat())
                .order("timestamp", desc=False)
                .execute())
        df_db = pd.DataFrame(resp.data)

        if df_db.empty:
            st.warning("No records found for selected range.")
        else:
            df_db["timestamp"] = pd.to_datetime(df_db["timestamp"], utc=True).dt.tz_convert(ist)
            display_cols = ["timestamp"] + selected_params if selected_params else df_db.columns.tolist()
            df_display = df_db[display_cols]
            st.dataframe(df_display, use_container_width=True, height=450)

            csv_bytes = df_display.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", data=csv_bytes, file_name="filtered_data.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Error fetching data: {e}")
