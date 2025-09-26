import streamlit as st
import pandas as pd
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import pytz
from datetime import datetime, timedelta

# --- Config & Styling ---
st.set_page_config(page_title="Compressor Control", page_icon="🔩", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
    
    /* --- Main Body & Theme --- */
    body {
        background-color: #010409;
        font-family: 'Orbitron', sans-serif; /* Futuristic font */
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    /* Hide Streamlit elements */
    #MainMenu, footer, header { visibility: hidden; }

    /* --- Custom Containers --- */
    .hud-container {
        background-color: rgba(13, 29, 43, 0.8);
        border: 1px solid #00c7ff;
        box-shadow: 0 0 15px #00c7ff;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .title-text {
        font-size: 36px;
        font-weight: 700;
        color: #FFFFFF;
        text-shadow: 0 0 10px #00c7ff, 0 0 20px #00c7ff;
        margin-bottom: 5px;
    }
    .subtitle-text {
        font-size: 14px;
        color: #AAAAAA;
        margin-bottom: 20px;
    }

    /* --- Status Indicator --- */
    .status-indicator {
        text-align: center;
        padding: 20px;
    }
    .status-indicator-title {
        color: #AAAAAA;
        font-size: 16px;
    }
    .status-indicator-value {
        font-size: 48px;
        font-weight: 700;
        padding: 10px 20px;
        border-radius: 8px;
        display: inline-block;
        margin-top: 10px;
    }
    
    /* --- System Log --- */
    .log-title {
        color: #00c7ff;
        font-size: 18px;
        margin-bottom: 10px;
        border-bottom: 1px solid #00c7ff;
        padding-bottom: 5px;
    }
    .log-entry {
        font-family: 'monospace';
        font-size: 13px;
        padding: 2px 0;
    }

    /* --- Status Colors --- */
    .status-normal { background-color: #2ec27e; box-shadow: 0 0 15px #2ec27e; }
    .status-warning { background-color: #ffcc00; box-shadow: 0 0 15px #ffcc00; color: #010409 !important; }
    .status-critical { background-color: #ff4b4b; box-shadow: 0 0 15px #ff4b4b; }
    .text-normal { color: #2ec27e; }
    .text-warning { color: #ffcc00; }
    .text-critical { color: #ff4b4b; }
</style>
""", unsafe_allow_html=True)

# --- Supabase Setup ---
@st.cache_resource(ttl=30)
def init_supabase():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        st.error("Supabase connection failed. Check secrets.")
        return None
supabase_client = init_supabase()

# --- Constants & Thresholds ---
STATUS_THRESHOLDS = {
    "temperature": {"warn": 60, "crit": 80, "range": [0, 100]},
    "pressure": {"warn": 9, "crit": 12, "range": [0, 15]},
    "vibration": {"warn": 3, "crit": 5, "range": [0, 8]},
}
STATUS_COLORS = {"normal": "#2ec27e", "warning": "#ffcc00", "critical": "#ff4b4b"}

# --- Helper Functions ---
def fetch_data():
    if not supabase_client:
        st.error("Supabase client not initialized. Cannot fetch data.")
        return pd.DataFrame()
    try:
        # Fetch a reasonable number of recent records for the live dashboard
        resp = supabase_client.table("air_compressor").select("*").order("timestamp", desc=True).limit(200).execute()
        if not resp.data:
            return pd.DataFrame()
        
        df = pd.DataFrame(resp.data)
        ist = pytz.timezone('Asia/Kolkata')
        # Convert UTC timestamp from Supabase to datetime objects and then to IST
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(ist)
        return df.set_index("timestamp").sort_index()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

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

def create_meter_gauge(value, param):
    t = STATUS_THRESHOLDS[param]
    status = get_status(value, param)
    color = STATUS_COLORS[status]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': param.capitalize(), 'font': {'size': 20, 'color': "white"}},
        number={'font': {'size': 40, 'color': color}},
        gauge={
            'axis': {'range': t['range'], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': color, 'thickness': 0.3},
            'bgcolor': "#010409",
            'borderwidth': 2,
            'bordercolor': "#00c7ff",
            'steps': [
                {'range': [t['range'][0], t['warn']], 'color': 'rgba(46, 194, 126, 0.2)'},
                {'range': [t['warn'], t['crit']], 'color': 'rgba(255, 204, 0, 0.2)'},
                {'range': [t['crit'], t['range'][1]], 'color': 'rgba(255, 75, 75, 0.2)'},
            ]}))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"}, height=250, margin=dict(l=30, r=30, t=50, b=30))
    return fig

def create_main_trend_chart(df, param_to_show):
    fig = go.Figure()
    if not df.empty:
        for p in param_to_show:
            t = STATUS_THRESHOLDS[p]
            status_color = STATUS_COLORS[get_status(df[p].iloc[-1], p)]
            fig.add_trace(go.Scatter(x=df.index, y=df[p], name=p.capitalize(), mode="lines", line=dict(width=3, color=status_color)))
    
    fig.update_layout(
        title={'text': "PARAMETER TREND ANALYSIS (LAST HOUR)", 'y':0.9, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top'},
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13, 29, 43, 0.5)",
        height=400, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def generate_system_log(df):
    log_entries = []
    if not df.empty:
        # Reverse dataframe to check from oldest to newest
        df_rev = df.iloc[::-1]
        for param in STATUS_THRESHOLDS.keys():
            prev_status = "normal"
            for timestamp, row in df_rev.iterrows():
                current_status = get_status(row[param], param)
                if current_status != prev_status:
                    message = f"[{timestamp.strftime('%H:%M:%S')}] {param.upper()} status changed to <span class='text-{current_status}'>{current_status.upper()}</span> at {row[param]:.2f}"
                    log_entries.append(message)
                prev_status = current_status
    # Show last 5 most recent events
    return log_entries[-5:][::-1]

# --- Sidebar ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00c7ff;'>CONTROL</h1>", unsafe_allow_html=True)
    app_mode = st.radio("System View", ["Live Monitor", "Data Explorer"], label_visibility="hidden")

# --- Main Application ---
if app_mode == "Live Monitor":
    st_autorefresh(interval=5000, key="dashboard_refresh")
    data = fetch_data()

    if data.empty:
        st.error("SYSTEM OFFLINE - NO DATA RECEIVED")
    else:
        latest = data.iloc[-1]
        overall_status = get_overall_status(latest)

        # --- Header ---
        st.markdown(f'<div class="title-text">COMPRESSOR UNIT C-1337</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="subtitle-text">Last Comms: {latest.name.strftime("%Y-%m-%d %H:%M:%S")}</div>', unsafe_allow_html=True)
        
        # --- Main Layout ---
        col1, col2 = st.columns([2, 3])
        
        with col1:
            with st.container():
                st.markdown('<div class="hud-container">', unsafe_allow_html=True)
                st.markdown('<div class="status-indicator">', unsafe_allow_html=True)
                st.markdown('<div class="status-indicator-title">OVERALL SYSTEM STATUS</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="status-indicator-value status-{overall_status}">{overall_status.upper()}</div>', unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)
            
            for p in STATUS_THRESHOLDS.keys():
                 with st.container():
                    st.markdown('<div class="hud-container">', unsafe_allow_html=True)
                    st.plotly_chart(create_meter_gauge(latest[p], p), use_container_width=True, config={'displayModeBar': False})
                    st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            with st.container():
                st.markdown('<div class="hud-container">', unsafe_allow_html=True)
                params_to_plot = st.multiselect(
                    "Select parameters to plot:",
                    options=list(STATUS_THRESHOLDS.keys()),
                    default=list(STATUS_THRESHOLDS.keys()),
                    format_func=lambda x: x.capitalize()
                )
                
                # Filter data for the last 1 hour for the chart
                ist = pytz.timezone('Asia/Kolkata')
                now_in_ist = datetime.now(ist)
                one_hour_ago = now_in_ist - timedelta(hours=1)
                chart_data = data[data.index >= one_hour_ago]

                if not chart_data.empty:
                    st.plotly_chart(create_main_trend_chart(chart_data, params_to_plot), use_container_width=True)
                else:
                    st.warning("No data recorded in the last hour.")
                
                st.markdown('</div>', unsafe_allow_html=True)

            with st.container():
                st.markdown('<div class="hud-container">', unsafe_allow_html=True)
                st.markdown('<div class="log-title">RECENT SYSTEM EVENTS</div>', unsafe_allow_html=True)
                log_entries = generate_system_log(data)
                for entry in log_entries:
                    st.markdown(f'<div class="log-entry">{entry}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)


elif app_mode == "Data Explorer":
    st.subheader("Explore Raw Sensor Data")
    
    # Set timezone for default date
    ist = pytz.timezone("Asia/Kolkata")
    today_ist = datetime.now(ist).date()

    start_col, end_col, param_col = st.columns(3)
    with start_col: start_date = st.date_input("Start Date", today_ist)
    with end_col: end_date = st.date_input("End Date", today_ist)
    with param_col: selected_params = st.multiselect("Select Parameter(s):", list(STATUS_THRESHOLDS.keys()), default=list(STATUS_THRESHOLDS.keys()))
    
    if supabase_client:
        try:
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            start_utc = ist.localize(start_dt).astimezone(pytz.utc)
            end_utc = ist.localize(end_dt).astimezone(pytz.utc)

            resp = supabase_client.table("air_compressor").select("*").gte("timestamp", start_utc.isoformat()).lte("timestamp", end_utc.isoformat()).order("timestamp", desc=True).execute()
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
    else:
        st.error("Supabase client not initialized. Cannot fetch data.")

