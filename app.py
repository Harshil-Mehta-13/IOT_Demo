import streamlit as st
import pandas as pd
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import pytz
from datetime import datetime, timedelta

# --- Config & Styling ---
st.set_page_config(page_title="Air Compressor Dashboard", page_icon="⚙️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* General Body & Font */
    body {
        font-family: 'Segoe UI', sans-serif;
        color: #E0E0E0;
    }
    /* Hide Streamlit elements */
    #MainMenu, footer, header {
        visibility: hidden;
    }
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    /* --- Sidebar --- */
    .sidebar-title {
        font-weight: bold;
        font-size: 20px;
        margin-bottom: 15px;
        padding: 10px;
        border-radius: 8px;
        background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
        color: #1a1a1a;
        text-align: center;
    }
    /* --- Header --- */
    .header-container {
        background-color: #1E1E1E;
        padding: 15px 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid #333;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .last-update {
        font-size: 14px;
        color: #AAAAAA;
    }
    .overall-status-title {
        font-size: 16px;
        font-weight: 600;
        text-align: right;
        color: #AAAAAA;
    }
    .overall-status-value {
        font-size: 32px;
        font-weight: 700;
        text-align: right;
        padding: 5px 15px;
        border-radius: 8px;
        color: white;
    }
    /* --- KPI Cards --- */
    .kpi-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #333;
        height: 180px; /* Fixed height for alignment */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .kpi-title {
        font-size: 18px;
        font-weight: 600;
        color: #E0E0E0;
    }
    .kpi-value {
        font-size: 42px;
        font-weight: 700;
        text-align: center;
    }
    /* --- Status Colors --- */
    .status-normal { background-color: #2ec27e; }
    .status-warning { background-color: #ffcc00; }
    .status-critical { background-color: #ff4b4b; }
    .color-normal { color: #2ec27e; }
    .color-warning { color: #ffcc00; }
    .color-critical { color: #ff4b4b; }
</style>
""", unsafe_allow_html=True)

# --- Supabase Setup ---
@st.cache_resource(ttl=30)
def init_supabase():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        st.error("Could not connect to Supabase. Please check your secrets configuration.")
        return None
supabase_client = init_supabase()

# --- Constants & Thresholds ---
STATUS_THRESHOLDS = {
    "temperature": {"warn": 60, "crit": 80, "range": [0, 100]},
    "pressure": {"warn": 9, "crit": 12, "range": [0, 15]},
    "vibration": {"warn": 3, "crit": 5, "range": [0, 8]},
}
STATUS_COLORS = {"normal":"#2ec27e", "warning":"#ffcc00", "critical":"#ff4b4b"}
PARAM_UNITS = {"temperature": "°C", "pressure": "Bar", "vibration": "mm/s"}

# --- Helper Functions ---
def get_status(val, param):
    key = param.lower()
    if key not in STATUS_THRESHOLDS or pd.isna(val): return "normal"
    t = STATUS_THRESHOLDS[key]
    if val >= t["crit"]: return "critical"
    if val >= t["warn"]: return "warning"
    return "normal"

def get_overall_status(latest_row):
    statuses = [get_status(latest_row[p], p) for p in STATUS_THRESHOLDS.keys()]
    if "critical" in statuses: return "critical"
    if "warning" in statuses: return "warning"
    return "normal"

def create_sparkline(df, param):
    status = get_status(df[param].iloc[-1], param)
    fig = go.Figure(go.Scatter(
        x=df.index, y=df[param], mode='lines',
        line=dict(color=STATUS_COLORS[status], width=2),
        fill='tozeroy',
        fillcolor=f'rgba({int(STATUS_COLORS[status][1:3], 16)}, {int(STATUS_COLORS[status][3:5], 16)}, {int(STATUS_COLORS[status][5:7], 16)}, 0.1)'
    ))
    fig.update_layout(
        height=50, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
    )
    return fig

def create_main_trend_chart(df, param):
    t = STATUS_THRESHOLDS[param]
    status_color = STATUS_COLORS[get_status(df[param].iloc[-1], param)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[param], name=param, mode="lines+markers", line=dict(width=3, color=status_color), marker=dict(size=5)))
    fig.add_hline(y=t["warn"], line_dash="dash", line_color="orange", annotation_text="Warning Threshold")
    fig.add_hline(y=t["crit"], line_dash="dash", line_color="red", annotation_text="Critical Threshold")
    fig.update_layout(
        title=f"{param.capitalize()} Trend Analysis (Last 120 Readings)",
        height=450, template="plotly_dark",
        yaxis=dict(range=t["range"], title=PARAM_UNITS[param]),
        xaxis=dict(title="Timestamp"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def fetch_data():
    if not supabase_client: return pd.DataFrame()
    try:
        resp = supabase_client.table("air_compressor").select("*").order("timestamp", desc=True).limit(120).execute()
        if not resp.data: return pd.DataFrame()
        df = pd.DataFrame(resp.data)
        ist = pytz.timezone('Asia/Kolkata')
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(ist)
        return df.set_index("timestamp").sort_index()
    except Exception as e:
        st.error(f"Error fetching data from Supabase: {e}")
        return pd.DataFrame()

# --- Sidebar ---
with st.sidebar:
    st.markdown("<div class='sidebar-title'>Navigation</div>", unsafe_allow_html=True)
    app_mode = st.radio("View Mode", ["Live Dashboard", "Database Explorer"])

# --- Main Application ---
if app_mode == "Live Dashboard":
    st_autorefresh(interval=5000, key="dashboard_refresh")
    data = fetch_data()

    if data.empty:
        st.warning("No data received from sensors. Please check the connection.")
    else:
        latest = data.iloc[-1]
        overall_status = get_overall_status(latest)

        # --- Header ---
        with st.container():
            st.markdown('<div class="header-container">', unsafe_allow_html=True)
            c1, c2 = st.columns([2, 1])
            with c1:
                st.title("⚙️ Air Compressor Real-Time Monitor")
                st.markdown(f'<p class="last-update">Last Update: {latest.name.strftime("%d %b %Y, %I:%M:%S %p")}</p>', unsafe_allow_html=True)
            with c2:
                st.markdown('<p class="overall-status-title">Overall System Status</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="overall-status-value status-{overall_status}">{overall_status.upper()}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")

        # --- KPI Cards ---
        cols = st.columns(3)
        for i, p in enumerate(STATUS_THRESHOLDS.keys()):
            with cols[i]:
                status = get_status(latest[p], p)
                st.markdown(f'<div class="kpi-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="kpi-title">{p.capitalize()}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="kpi-value color-{status}">{latest[p]:.2f} <span style="font-size: 24px;">{PARAM_UNITS[p]}</span></div>', unsafe_allow_html=True)
                sparkline = create_sparkline(data, p)
                st.plotly_chart(sparkline, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")

        # --- Main Chart ---
        param_to_show = st.selectbox(
            "Select Parameter for Detailed Trend Analysis",
            options=list(STATUS_THRESHOLDS.keys()),
            format_func=lambda x: x.capitalize()
        )
        if param_to_show:
            st.plotly_chart(create_main_trend_chart(data, param_to_show), use_container_width=True)

elif app_mode == "Database Explorer":
    st.subheader("Explore Raw Sensor Data")
    if not supabase_client:
        st.error("Supabase client not initialized. Cannot fetch data.")
    else:
        start_col, end_col, param_col = st.columns(3)
        with start_col: start_date = st.date_input("Start Date", datetime.now().date()-timedelta(days=7))
        with end_col: end_date = st.date_input("End Date", datetime.now().date())
        with param_col: selected_params = st.multiselect("Select Parameters", list(STATUS_THRESHOLDS.keys()), default=list(STATUS_THRESHOLDS.keys()))
        
        try:
            ist = pytz.timezone("Asia/Kolkata")
            start_dt = ist.localize(datetime.combine(start_date, datetime.min.time())).astimezone(pytz.utc)
            end_dt = ist.localize(datetime.combine(end_date, datetime.max.time())).astimezone(pytz.utc)
            
            resp = supabase_client.table("air_compressor").select("*").gte("timestamp", start_dt.isoformat()).lte("timestamp", end_dt.isoformat()).execute()
            df = pd.DataFrame(resp.data)

            if df.empty:
                st.warning("No data found in the selected date range.")
            else:
                display_cols = ["timestamp"] + selected_params if selected_params else ["timestamp"]
                st.dataframe(df[display_cols], use_container_width=True, height=500)
                csv = df[display_cols].to_csv(index=False).encode('utf-8')
                st.download_button("Download as CSV", csv, "air_compressor_data.csv", "text/csv", key="download-csv")
        except Exception as e:
            st.error(f"An error occurred while fetching data: {e}")

