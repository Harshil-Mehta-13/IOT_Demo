# app.py
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
@st.cache_resource(ttl=30)
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase_client = init_connection()

# --- Helper Functions ---
def get_live_data(limit=200):
    try:
        response = (
            supabase_client.table("air_compressor")
            .select("*")
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        data = response.data
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        ist = pytz.timezone("Asia/Kolkata")
        # Be robust: parse timestamps as UTC then convert to IST
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(ist)
        df = df.set_index("timestamp").sort_index()
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def get_historical_data(start_time):
    try:
        response = (
            supabase_client.table("air_compressor")
            .select("*")
            .gte("timestamp", start_time.isoformat())
            .order("timestamp", desc=True)
            .execute()
        )
        data = response.data
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        ist = pytz.timezone("Asia/Kolkata")
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(ist)
        df = df.set_index("timestamp").sort_index()
        return df
    except Exception as e:
        st.error(f"Error fetching historical data: {e}")
        return pd.DataFrame()

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

def create_chart(df, param_name, title, color, warn_thresh=None, crit_thresh=None, height=200):
    fig = go.Figure()
    # guard if param missing
    if param_name not in df.columns:
        return fig
    fig.add_trace(go.Scatter(x=df.index, y=df[param_name], mode="lines", name=title, line=dict(color=color)))
    if warn_thresh is not None:
        fig.add_hline(y=warn_thresh, line_dash="dash", line_color="orange", annotation_text="Warning", annotation_position="top left")
    if crit_thresh is not None:
        fig.add_hline(y=crit_thresh, line_dash="dash", line_color="red", annotation_text="Critical", annotation_position="top left")
    fig.update_layout(
        height=height,
        margin={"l": 10, "r": 10, "t": 30, "b": 20},
        title=dict(text=title, font=dict(size=14)),
        template="plotly_dark",
        showlegend=False,
        xaxis_title=None,
        yaxis_title=None
    )
    return fig

# --- Sidebar / Navigation ---
with st.sidebar:
    st.header("Navigation")
    app_mode = st.radio("Choose a page", ["Live Dashboard", "Database"])

# --- Live Dashboard ---
if app_mode == "Live Dashboard":
    st.title("Air Compressor Monitoring Dashboard ⚙️")

    # --- Auto-refresh (prefer streamlit-autorefresh; fallback to manual button) ---
    auto_refresh_interval_ms = 5000  # 5000 ms = 5 seconds

    try:
        # recommended: add streamlit-autorefresh to requirements.txt on Streamlit Cloud
        from streamlit_autorefresh import st_autorefresh
        # This triggers the page to refresh automatically on the browser side.
        st_autorefresh(interval=auto_refresh_interval_ms, limit=None, key="autorefresh")
    except Exception:
        st.info("Auto-refresh not enabled (install `streamlit-autorefresh` in requirements.txt to enable). Use the Refresh button.")
        if st.button("Refresh now"):
            try:
                # attempt a programmatic rerun if available
                st.experimental_rerun()
            except Exception:
                # If experimental rerun isn't available just continue (user can reload)
                pass

    live_df = get_live_data(limit=500)

    if live_df.empty:
        st.warning("No data available. Please check your ESP32 / network / supabase table.")
    else:
        # Use the latest timestamp in the data to compute last 1 hour window
        now = live_df.index.max()
        one_hour_ago = now - pd.Timedelta(hours=1)
        last_hour_df = live_df[live_df.index >= one_hour_ago]

        if last_hour_df.empty:
            st.warning("No records in the last 1 hour.")
        else:
            # Layout: Charts (left) — KPIs (right)
            chart_col, kpi_col = st.columns([2, 1])

            with kpi_col:
                st.subheader("Current Status")
                latest = last_hour_df.iloc[-1]

                # Clean presentation of metrics stacked
                st.metric(label="🌡️ Temp (°C)", value=f"{latest.get('temperature', float('nan')):.2f}" if 'temperature' in latest else "N/A")
                st.markdown(
                    f"**Status:** <span style='color:{get_status_color(latest.get('temperature',0),'temperature')};'>"
                    f"{get_status_text(latest.get('temperature',0),'temperature')}</span>",
                    unsafe_allow_html=True
                )

                st.metric(label="PSI Pressure (bar)", value=f"{latest.get('pressure', float('nan')):.2f}" if 'pressure' in latest else "N/A")
                st.markdown(
                    f"**Status:** <span style='color:{get_status_color(latest.get('pressure',0),'pressure')};'>"
                    f"{get_status_text(latest.get('pressure',0),'pressure')}</span>",
                    unsafe_allow_html=True
                )

                st.metric(label="📳 Vibration", value=f"{latest.get('vibration', float('nan')):.2f}" if 'vibration' in latest else "N/A")
                st.markdown(
                    f"**Status:** <span style='color:{get_status_color(latest.get('vibration',0),'vibration')};'>"
                    f"{get_status_text(latest.get('vibration',0),'vibration')}</span>",
                    unsafe_allow_html=True
                )

            with chart_col:
                st.subheader("Trends (Last 1 Hour)")
                # Keep charts compact so they fit without scrolling
                st.plotly_chart(create_chart(last_hour_df, "temperature", "Temperature (°C)", "#00BFFF", warn_thresh=60, crit_thresh=80, height=200), use_container_width=True)
                st.plotly_chart(create_chart(last_hour_df, "pressure", "Pressure (bar)", "#88d8b0", warn_thresh=9, crit_thresh=12, height=200), use_container_width=True)
                st.plotly_chart(create_chart(last_hour_df, "vibration", "Vibration", "#6a5acd", warn_thresh=3, crit_thresh=5, height=200), use_container_width=True)

# --- Database page (keeps your original behavior but with robust tz handling) ---
elif app_mode == "Database":
    st.subheader("Raw Database Data")

    col_start, col_end, col_param = st.columns(3)
    with col_start:
        start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=7))
    with col_end:
        end_date = st.date_input("End Date", value=datetime.now().date())
    with col_param:
        parameters = ['temperature', 'pressure', 'vibration']
        selected_params = st.multiselect("Select Parameter(s) to Filter:", options=parameters, default=parameters)

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    try:
        ist = pytz.timezone('Asia/Kolkata')
        start_dt_utc = ist.localize(start_dt, is_dst=None).astimezone(pytz.utc)
        end_dt_utc = ist.localize(end_dt, is_dst=None).astimezone(pytz.utc)

        response = supabase_client.table("air_compressor").select("*").gte("timestamp", start_dt_utc.isoformat()).lte("timestamp", end_dt_utc.isoformat()).execute()
        filtered_df = pd.DataFrame(response.data)
        if filtered_df.empty:
            st.warning("No records found for the selected date range.")
        else:
            # Convert & display
            filtered_df["timestamp"] = pd.to_datetime(filtered_df["timestamp"], utc=True).dt.tz_convert(ist)
            if selected_params:
                cols_to_display = ['timestamp'] + selected_params
                filtered_df = filtered_df[cols_to_display]
            else:
                st.warning("Please select at least one parameter.")
                filtered_df = pd.DataFrame()

            if not filtered_df.empty:
                st.dataframe(filtered_df, use_container_width=True, height=500)
                csv = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download Filtered CSV", csv, "filtered_data.csv", "text/csv", key='download_filtered')
    except Exception as e:
        st.error(f"Error fetching data: {e}")
