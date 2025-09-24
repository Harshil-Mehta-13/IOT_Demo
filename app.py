import streamlit as st
import pandas as pd
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import pytz
from datetime import datetime, timedelta

# --- Page Config ---
st.set_page_config(
    page_title="Air Compressor Dashboard",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .metric-container {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 15px;
        margin: 10px;
        color: white;
        text-align: center;
        box-shadow: 0px 2px 6px rgba(0,0,0,0.3);
    }
    .status-text {
        font-weight: bold;
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Supabase Connection ---
@st.cache_resource(ttl="30s")
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase_client = init_connection()

def get_live_data():
    try:
        response = (
            supabase_client.table("air_compressor")
            .select("*")
            .order("timestamp", desc=True)
            .limit(120)
            .execute()
        )
        data = response.data
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        ist = pytz.timezone('Asia/Kolkata')
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(ist)
        df = df.set_index("timestamp").sort_index()
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def get_status(value, param_name):
    thresholds = {
        "temperature": {"warn": 60, "crit": 80},
        "pressure": {"warn": 9, "crit": 12},
        "vibration": {"warn": 3, "crit": 5},
    }
    warn = thresholds[param_name]["warn"]
    crit = thresholds[param_name]["crit"]
    if value > crit:
        return "Critical", "#ff4b4b"
    elif value > warn:
        return "Warning", "#ffcc00"
    else:
        return "Normal", "#2ec27e"

def create_chart(df, param_name, title, color, warn_thresh=None, crit_thresh=None, height=320):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[param_name], mode="lines", name=title, line=dict(color=color, width=2)))
    if warn_thresh:
        fig.add_hline(y=warn_thresh, line_dash="dot", line_color="orange", annotation_text="Warning", annotation_position="top left")
    if crit_thresh:
        fig.add_hline(y=crit_thresh, line_dash="dot", line_color="red", annotation_text="Critical", annotation_position="top left")
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=50, b=20),
        title=dict(text=title, font=dict(size=16, color="white")),
        template="plotly_dark",
        xaxis_title="Time",
        yaxis_title=None,
        showlegend=False,
        title_x=0.5
    )
    return fig

# --- MAIN APP ---
st.title("⚙️ Air Compressor Monitoring Dashboard")

with st.sidebar:
    st.header("📌 Navigation")
    app_mode = st.radio("Choose a view:", ["Live Dashboard", "Database"])

if app_mode == "Live Dashboard":
    st_autorefresh(interval=5000, key="air_compressor_refresh")
    live_df = get_live_data()
    if live_df.empty:
        st.warning("⚠️ No data available. Please check your ESP32 connection.")
    else:
        latest = live_df.iloc[-1]
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

        with kpi_col1:
            status, color = get_status(latest["temperature"], "temperature")
            st.markdown(
                f"""
                <div class="metric-container">
                    <h3>🌡️ Temperature</h3>
                    <h2>{latest['temperature']:.2f} °C</h2>
                    <p class="status-text" style="color:{color};">{status}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with kpi_col2:
            status, color = get_status(latest["pressure"], "pressure")
            st.markdown(
                f"""
                <div class="metric-container">
                    <h3>⏲️ Pressure</h3>
                    <h2>{latest['pressure']:.2f} bar</h2>
                    <p class="status-text" style="color:{color};">{status}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with kpi_col3:
            status, color = get_status(latest["vibration"], "vibration")
            st.markdown(
                f"""
                <div class="metric-container">
                    <h3>📳 Vibration</h3>
                    <h2>{latest['vibration']:.2f}</h2>
                    <p class="status-text" style="color:{color};">{status}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("### 📈 Historical Trends (Last 100 Readings)")
        chart_col1, chart_col2, chart_col3 = st.columns([1, 1, 1])

        with chart_col1:
            st.plotly_chart(create_chart(live_df, "temperature", "Temperature Trend", "#00BFFF", 60, 80), use_container_width=True)
        with chart_col2:
            st.plotly_chart(create_chart(live_df, "pressure", "Pressure Trend", "#88d8b0", 9, 12), use_container_width=True)
        with chart_col3:
            st.plotly_chart(create_chart(live_df, "vibration", "Vibration Trend", "#6a5acd", 3, 5), use_container_width=True)

elif app_mode == "Database":
    st.subheader("📊 Explore Raw Database Data")
    col_start, col_end, col_param = st.columns(3)
    with col_start:
        start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=7))
    with col_end:
        end_date = st.date_input("End Date", value=datetime.now().date())
    with col_param:
        parameters = ["temperature", "pressure", "vibration"]
        selected_params = st.multiselect("Select Parameter(s):", options=parameters, default=parameters)

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    try:
        ist = pytz.timezone("Asia/Kolkata")
        start_dt_utc = ist.localize(start_dt).astimezone(pytz.utc)
        end_dt_utc = ist.localize(end_dt).astimezone(pytz.utc)
        response = (
            supabase_client.table("air_compressor")
            .select("*")
            .gte("timestamp", start_dt_utc.isoformat())
            .lte("timestamp", end_dt_utc.isoformat())
            .execute()
        )
        filtered_df = pd.DataFrame(response.data)
        if filtered_df.empty:
            st.warning("⚠️ No records found for this date range.")
        else:
            if selected_params:
                cols_to_display = ["timestamp"] + selected_params
                filtered_df = filtered_df[cols_to_display]
            st.dataframe(filtered_df, use_container_width=True, height=500)
            csv = filtered_df.to_csv().encode("utf-8")
            st.download_button(
                "⬇️ Download CSV",
                csv,
                "filtered_data.csv",
                "text/csv",
                key="download_filtered"
            )
    except Exception as e:
        st.error(f"Error fetching data: {e}")
