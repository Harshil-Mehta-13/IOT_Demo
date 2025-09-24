import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pytz

# -----------------------
# Page config
# -----------------------
st.set_page_config(
    page_title="Air Compressor Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------
# Supabase connection
# -----------------------
@st.cache_resource(ttl=30)
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase_client = init_connection()

# -----------------------
# Helper functions
# -----------------------
def get_live_data():
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    # Try last 1 hour
    response = supabase_client.table("air_compressor") \
        .select("*") \
        .gte("timestamp", one_hour_ago.isoformat()) \
        .order("timestamp", desc=True) \
        .execute()
    df = pd.DataFrame(response.data)

    # Fallback to last 100 rows if last 1 hour is empty
    if df.empty:
        response = supabase_client.table("air_compressor") \
            .select("*") \
            .order("timestamp", desc=True) \
            .limit(100) \
            .execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            st.warning("⚠️ No data available in the last 1 hour. Showing last 100 entries instead.")

    if not df.empty:
        ist = pytz.timezone("Asia/Kolkata")
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(ist)
        df = df.set_index("timestamp").sort_index()

    return df

def get_status_color(value, param):
    if param == "temperature":
        return "#ff4b4b" if value > 80 else "#ffcc00" if value > 60 else "#2ec27e"
    if param == "pressure":
        return "#ff4b4b" if value > 12 else "#ffcc00" if value > 9 else "#2ec27e"
    if param == "vibration":
        return "#ff4b4b" if value > 5 else "#ffcc00" if value > 3 else "#2ec27e"
    return "#2ec27e"

def get_status_text(value, param):
    if param == "temperature":
        return "Critical" if value > 80 else "Warning" if value > 60 else "Normal"
    if param == "pressure":
        return "Critical" if value > 12 else "Warning" if value > 9 else "Normal"
    if param == "vibration":
        return "Critical" if value > 5 else "Warning" if value > 3 else "Normal"
    return "Normal"

def create_chart(df, param, title, color, warn=None, crit=None, height=300):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df[param],
        mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=5),
        name=title
    ))

    if warn:
        fig.add_hline(y=warn, line_dash="dash", line_color="orange",
                      annotation_text="Warning", annotation_position="top left")
    if crit:
        fig.add_hline(y=crit, line_dash="dash", line_color="red",
                      annotation_text="Critical", annotation_position="top left")

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="white")),
        template="plotly_dark",
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=False,
        xaxis_title="Time",
        yaxis_title=param.capitalize()
    )
    return fig

# -----------------------
# Sidebar
# -----------------------
st.sidebar.title("Navigation")
app_mode = st.sidebar.radio("Go to", ["Live Dashboard", "Database"])

# -----------------------
# Live Dashboard
# -----------------------
if app_mode == "Live Dashboard":
    st.title("Air Compressor Monitoring Dashboard ⚙️")

    live_df = get_live_data()

    if live_df.empty:
        st.error("❌ No data available. Please check your ESP32 connection.")
    else:
        latest = live_df.iloc[-1]

        kpi_col, chart_col = st.columns([1, 2])

        with kpi_col:
            st.subheader("📊 KPIs (Latest Values)")
            st.metric("🌡️ Temperature (°C)", f"{latest['temperature']:.2f}")
            st.markdown(
                f"**Status:** <span style='color:{get_status_color(latest['temperature'],'temperature')};'>{get_status_text(latest['temperature'],'temperature')}</span>",
                unsafe_allow_html=True
            )
            st.metric("🧭 Pressure (bar)", f"{latest['pressure']:.2f}")
            st.markdown(
                f"**Status:** <span style='color:{get_status_color(latest['pressure'],'pressure')};'>{get_status_text(latest['pressure'],'pressure')}</span>",
                unsafe_allow_html=True
            )
            st.metric("📳 Vibration", f"{latest['vibration']:.2f}")
            st.markdown(
                f"**Status:** <span style='color:{get_status_color(latest['vibration'],'vibration')};'>{get_status_text(latest['vibration'],'vibration')}</span>",
                unsafe_allow_html=True
            )

        with chart_col:
            st.subheader("📈 Trends")
            st.plotly_chart(create_chart(live_df, "temperature", "Temperature Trend", "#00BFFF", 60, 80, 300), use_container_width=True)
            st.plotly_chart(create_chart(live_df, "pressure", "Pressure Trend", "#88d8b0", 9, 12, 300), use_container_width=True)
            st.plotly_chart(create_chart(live_df, "vibration", "Vibration Trend", "#6a5acd", 3, 5, 300), use_container_width=True)

    # Auto-refresh every 10 seconds
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=10000, limit=None, key="live_refresh")
    except ImportError:
        st.info("Auto-refresh not available. Please refresh manually.")

# -----------------------
# Database Page (Optional)
# -----------------------
elif app_mode == "Database":
    st.subheader("📂 Database View")
    st.write("You can add your database filtering and CSV export UI here if needed.")
