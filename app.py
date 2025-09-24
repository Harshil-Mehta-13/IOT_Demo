import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.graph_objects as go
import pytz
from datetime import datetime, timedelta

# --- Page Config ---
st.set_page_config(
    page_title="Air Compressor Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Supabase Connection ---
@st.cache_resource(ttl="30s")
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase_client = init_connection()

# --- Helper Functions ---
def get_live_data():
    response = (
        supabase_client.table("air_compressor")
        .select("*")
        .order("timestamp", desc=True)
        .limit(200)
        .execute()
    )
    data = response.data
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    ist = pytz.timezone("Asia/Kolkata")
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(ist)
    df = df.set_index("timestamp").sort_index()
    return df

def get_status_color(value, param_name):
    if param_name == "temperature":
        if value > 80: return "#ff4b4b"
        elif value > 60: return "#ffcc00"
        else: return "#2ec27e"
    elif param_name == "pressure":
        if value > 12: return "#ff4b4b"
        elif value > 9: return "#ffcc00"
        else: return "#2ec27e"
    elif param_name == "vibration":
        if value > 5: return "#ff4b4b"
        elif value > 3: return "#ffcc00"
        else: return "#2ec27e"
    return "#2ec27e"

def get_status_text(value, param_name):
    if param_name == "temperature":
        if value > 80: return "Critical"
        elif value > 60: return "Warning"
        else: return "Normal"
    elif param_name == "pressure":
        if value > 12: return "Critical"
        elif value > 9: return "Warning"
        else: return "Normal"
    elif param_name == "vibration":
        if value > 5: return "Critical"
        elif value > 3: return "Warning"
        else: return "Normal"
    return "Normal"

def create_chart(df, param_name, title, color, warn_thresh=None, crit_thresh=None, height=250):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[param_name], mode="lines", name=title, line=dict(color=color)))
    if warn_thresh:
        fig.add_hline(y=warn_thresh, line_dash="dash", line_color="orange", annotation_text="Warning", annotation_position="top left")
    if crit_thresh:
        fig.add_hline(y=crit_thresh, line_dash="dash", line_color="red", annotation_text="Critical", annotation_position="top left")
    fig.update_layout(
        height=height,
        margin={"l": 10, "r": 10, "t": 30, "b": 0},
        title=dict(text=title, font=dict(size=14)),
        template="plotly_dark",
        showlegend=False,
    )
    return fig

# --- Sidebar ---
with st.sidebar:
    st.header("Navigation")
    app_mode = st.radio("Choose a page", ["Live Dashboard", "Database"])

# --- Live Dashboard ---
if app_mode == "Live Dashboard":
    st.title("Air Compressor Monitoring Dashboard ⚙️")

    # Auto-refresh every 5 seconds
    st_autorefresh = st.experimental_rerun  # fallback if autorefresh not available
    st_autorefresh = st.autorefresh(interval=5000, limit=None, key="refresh")

    live_df = get_live_data()

    if live_df.empty:
        st.warning("No data available. Please check your ESP32 connection.")
    else:
        now = live_df.index.max()
        last_hour_df = live_df[live_df.index >= (now - pd.Timedelta(hours=1))]

        if last_hour_df.empty:
            st.warning("No data in the last 1 hour.")
        else:
            latest = last_hour_df.iloc[-1]

            chart_col, kpi_col = st.columns([2, 1])

            with kpi_col:
                st.subheader("Current Status")
                st.metric("🌡️ Temp (°C)", f"{latest['temperature']:.2f}")
                st.markdown(
                    f"**Status:** <span style='color:{get_status_color(latest['temperature'],'temperature')};'>"
                    f"{get_status_text(latest['temperature'],'temperature')}</span>",
                    unsafe_allow_html=True,
                )
                st.metric("PSI Pressure (bar)", f"{latest['pressure']:.2f}")
                st.markdown(
                    f"**Status:** <span style='color:{get_status_color(latest['pressure'],'pressure')};'>"
                    f"{get_status_text(latest['pressure'],'pressure')}</span>",
                    unsafe_allow_html=True,
                )
                st.metric("📳 Vibration", f"{latest['vibration']:.2f}")
                st.markdown(
                    f"**Status:** <span style='color:{get_status_color(latest['vibration'],'vibration')};'>"
                    f"{get_status_text(latest['vibration'],'vibration')}</span>",
                    unsafe_allow_html=True,
                )

            with chart_col:
                st.subheader("Trends (Last 1 Hour)")
                st.plotly_chart(create_chart(last_hour_df, "temperature", "Temperature (°C)", "#00BFFF", 60, 80), use_container_width=True)
                st.plotly_chart(create_chart(last_hour_df, "pressure", "Pressure (bar)", "#88d8b0", 9, 12), use_container_width=True)
                st.plotly_chart(create_chart(last_hour_df, "vibration", "Vibration", "#6a5acd", 3, 5), use_container_width=True)
