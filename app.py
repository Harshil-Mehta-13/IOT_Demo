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
#MainMenu, footer, header {visibility: hidden;}
.metric-container {
    background-color: #1E1E1E; border-radius: 8px; padding: 16px; margin-bottom: 14px;
    color: white; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    user-select:none;
}
.status-badge {
    font-weight: 700; border-radius: 12px; padding: 3px 10px; font-size: 13px; display: inline-block;
}
.status-normal {background-color: #2ec27e; color: white;}
.status-warning {background-color: #ffcc00; color: black;}
.status-critical {background-color: #ff4b4b; color: white;}
</style>
""", unsafe_allow_html=True)

# --- Supabase Setup ---
@st.cache_resource(ttl=30)
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
supabase_client = init_supabase()

def fetch_data(limit=120):
    """Fetch latest data from Supabase"""
    try:
        resp = (supabase_client.table("air_compressor").select("*").order("timestamp", desc=True).limit(limit).execute())
        if not resp.data:
            return pd.DataFrame()
        df = pd.DataFrame(resp.data)
        ist = pytz.timezone('Asia/Kolkata')
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(ist)
        return df.set_index("timestamp").sort_index()
    except Exception as e:
        st.error(f"Fetching data error: {e}")
        return pd.DataFrame()

# Thresholds and colors setup
STATUS_THRESHOLDS = {
    "temperature": {"warn": 60, "crit": 80, "range": [0, 100]},
    "pressure": {"warn": 9, "crit": 12, "range": [0, 15]},
    "vibration": {"warn": 3, "crit": 5, "range": [0, 8]},
}
STATUS_CLASSES = ["status-normal", "status-warning", "status-critical"]
STATUS_COLORS = {"status-normal":"#2ec27e", "status-warning":"#ffcc00", "status-critical":"#ff4b4b"}

def get_status(value, param):
    thresh = STATUS_THRESHOLDS[param]
    if value > thresh["crit"]:
        return "Critical", "status-critical"
    elif value > thresh["warn"]:
        return "Warning", "status-warning"
    else:
        return "Normal", "status-normal"

def kpi_card(param, value):
    status_text, status_class = get_status(value, param)
    st.markdown(f"""
    <div class="metric-container">
        <h3>{param.capitalize()}</h3>
        <h1>{value:.2f}</h1>
        <span class="status-badge {status_class}">{status_text}</span>
    </div>
    """, unsafe_allow_html=True)

def create_gauge(param, value):
    status_text, status_class = get_status(value, param)
    r = STATUS_THRESHOLDS[param]["range"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value, title={'text': param.capitalize()},
        gauge={
            'axis': {'range': r},
            'bar': {'color': STATUS_COLORS[status_class]},
            'steps': [
                {'range': [r[0], r[0]+0.6*(r[1]-r[0])], 'color': "lightgreen"},
                {'range': [r[0]+0.6*(r[1]-r[0]), r[0]+0.8*(r[1]-r[0])], 'color': "yellow"},
                {'range': [r[0]+0.8*(r[1]-r[0]), r[1]], 'color': "red"},
            ]
        }
    ))
    fig.update_layout(height=300, margin=dict(t=30,b=0,l=0,r=0), template="plotly_dark")
    return fig

def create_trend_chart(df, param):
    thresh = STATUS_THRESHOLDS[param]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[param], mode="lines", line=dict(width=3, color=STATUS_COLORS[get_status(df[param].iloc[-1], param)[1]])))
    fig.add_hline(y=thresh["warn"], line_dash="dot", line_color="orange", annotation_text="Warning", annotation_position="top left")
    fig.add_hline(y=thresh["crit"], line_dash="dot", line_color="red", annotation_text="Critical", annotation_position="top left")
    fig.update_layout(
        title=f"{param.capitalize()} Trend",
        height=500,
        margin=dict(l=30, r=30, t=50, b=30),
        template="plotly_dark",
        yaxis=dict(range=thresh["range"]),
        xaxis_title="Time",
        showlegend=False,
        transition=dict(duration=500, easing='cubic-in-out'),
        title_x=0.5,
    )
    return fig

# --- Main ---
st.title("⚙️ Air Compressor Monitoring Dashboard")

with st.sidebar:
    st.header("Navigation")
    app_mode = st.radio("View Mode", ["Live Dashboard", "Database"])

if app_mode == "Live Dashboard":
    # Auto-refresh every 5 seconds
    st_autorefresh(interval=5000, key="refresh")

    data = fetch_data()
    if data.empty:
        st.warning("No data available. Check your ESP32 connection.")
    else:
        latest = data.iloc[-1]

        # -- KPIs Row --
        kpi_cols = st.columns(3)
        for i, param in enumerate(["temperature", "pressure", "vibration"]):
            with kpi_cols[i]:
                kpi_card(param, latest[param])

        st.markdown("---")

        # -- Gauges Row --
        gauge_cols = st.columns(3)
        for i, param in enumerate(["temperature", "pressure", "vibration"]):
            with gauge_cols[i]:
                st.plotly_chart(create_gauge(param, latest[param]), use_container_width=True)

        st.markdown("---")

        # -- Tabbed Trends --
        tabs = st.tabs(["Temperature", "Pressure", "Vibration"])
        for param, tab in zip(["temperature", "pressure", "vibration"], tabs):
            with tab:
                st.plotly_chart(create_trend_chart(data, param), use_container_width=True)

        st.info("Dashboard refreshes every 5 seconds.")

elif app_mode == "Database":
    st.subheader("Explore Raw Data")

    col_start, col_end, col_param = st.columns(3)
    with col_start:
        start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=7))
    with col_end:
        end_date = st.date_input("End Date", value=datetime.now().date())
    with col_param:
        params = ["temperature", "pressure", "vibration"]
        selected_params = st.multiselect("Select Parameters", options=params, default=params)

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    try:
        ist = pytz.timezone("Asia/Kolkata")
        start_dt_utc = ist.localize(start_dt).astimezone(pytz.utc)
        end_dt_utc = ist.localize(end_dt).astimezone(pytz.utc)

        resp = (
            supabase_client.table("air_compressor")
            .select("*")
            .gte("timestamp", start_dt_utc.isoformat())
            .lte("timestamp", end_dt_utc.isoformat())
            .execute()
        )
        df = pd.DataFrame(resp.data)

        if df.empty:
            st.warning("No data for selected date range.")
        else:
            if selected_params:
                df = df[["timestamp"] + selected_params]
            st.dataframe(df, use_container_width=True, height=500)
            csv = df.to_csv().encode("utf-8")
            st.download_button("Download CSV", csv, "filtered_data.csv", "text/csv", key="download")

    except Exception as e:
        st.error(f"Error fetching data: {e}")
