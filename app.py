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
        border-radius: 8px;
        padding: 10px 15px;
        margin-bottom: 12px;
        color: white;
        text-align: left;
        box-shadow: 0px 1px 5px rgba(0,0,0,0.2);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .status-text {
        font-weight: 600;
        font-size: 13px;
        margin-top: 3px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Supabase Connection ---
@st.cache_resource(ttl=30)
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
    axis_ranges = {
        "temperature": [0, 100],
        "pressure": [0, 15],
        "vibration": [0, 8],
    }
    y_range = axis_ranges.get(param_name, None)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[param_name], mode="lines", line=dict(color=color, width=2)))
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
        yaxis=dict(range=y_range),
        showlegend=False,
        title_x=0.5,
        transition=dict(duration=500, easing='cubic-in-out')
    )
    return fig

# --- Main App ---
st.title("⚙️ Air Compressor Monitoring Dashboard")

with st.sidebar:
    st.header("📌 Navigation")
    app_mode = st.radio("Choose a view:", ["Live Dashboard", "Database"])

if app_mode == "Live Dashboard":
    # Auto refresh every 5 seconds without blocking
    st_autorefresh(interval=5000, key="air_compressor_refresh")

    live_df = get_live_data()

    if live_df.empty:
        st.warning("⚠️ No data available. Please check your ESP32 connection.")
    else:
        latest = live_df.iloc[-1]

        # Two columns: KPIs left narrow, charts right wide
        kpi_col, chart_col = st.columns([1, 3])

        with kpi_col:
            # Smaller stacked KPI cards
            for param in ["temperature", "pressure", "vibration"]:
                status, color = get_status(latest[param], param)
                st.markdown(f"""
                    <div class="metric-container">
                        <h4 style="margin:0;">{param.capitalize()}</h4>
                        <h2 style="margin:0;">{latest[param]:.2f}</h2>
                        <p class="status-text" style="color:{color}; margin:0;">{status}</p>
                    </div>
                """, unsafe_allow_html=True)

        with chart_col:
            st.markdown("### 📈 Historical Trends (Last 100 Readings)")
            chart_cols = st.columns(3)
            params = ["temperature", "pressure", "vibration"]
            colors = ["#00BFFF", "#88d8b0", "#6a5acd"]
            warns = [60, 9, 3]
            crits = [80, 12, 5]
            titles = ["Temperature Trend", "Pressure Trend", "Vibration Trend"]

            for i, col in enumerate(chart_cols):
                with col:
                    st.plotly_chart(
                        create_chart(
                            live_df,
                            params[i],
                            titles[i],
                            colors[i],
                            warn_thresh=warns[i],
                            crit_thresh=crits[i],
                        ),
                        use_container_width=True,
                    )

        st.info("✅ Dashboard refreshes every 5 seconds smoothly.")

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
