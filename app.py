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
.status-badge {
    font-weight: 700; border-radius: 12px; padding: 4px 12px; font-size: 13px; display: inline-block;
    color: white;
}
.status-normal {background-color: #2ec27e;}
.status-warning {background-color: #ffcc00; color: black;}
.status-critical {background-color: #ff4b4b;}
.metric-container {
    background-color: #1E1E1E;
    border-radius: 8px;
    padding: 10px 20px;
    margin-right: 12px;
    color: white;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    user-select:none;
    min-width:120px;
}
</style>
""", unsafe_allow_html=True)

# --- Supabase Setup ---
@st.cache_resource(ttl=30)
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
supabase_client = init_supabase()

STATUS_THRESHOLDS = {
    "temperature": {"warn": 60, "crit": 80, "range": [0, 100]},
    "pressure": {"warn": 9, "crit": 12, "range": [0, 15]},
    "vibration": {"warn": 3, "crit": 5, "range": [0, 8]},
}
STATUS_COLORS = {"normal":"#2ec27e", "warning":"#ffcc00", "critical":"#ff4b4b"}

def get_status(val, param):
    thresh = STATUS_THRESHOLDS[param]
    if val > thresh["crit"]:
        return "critical"
    elif val > thresh["warn"]:
        return "warning"
    return "normal"

def render_kpi(param, value):
    status = get_status(value, param)
    status_class = f"status-{status}"
    st.markdown(f"""
    <div class="metric-container">
        <h4>{param.capitalize()}</h4>
        <h2>{value:.2f}</h2>
        <span class="status-badge {status_class}">{status.capitalize()}</span>
    </div>
    """, unsafe_allow_html=True)

def create_pointer_gauge(param, value):
    thresh = STATUS_THRESHOLDS[param]
    status = get_status(value, param)
    color = STATUS_COLORS[status]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'font': {'size': 28, 'color': color}},
        title={'text': param.capitalize(), 'font': {'size': 22}},
        gauge={
            'axis': {'range': thresh["range"], 'tickwidth': 2, 'tickcolor': "darkgray"},
            'bar': {'color': color, 'thickness': 0.3},
            'bgcolor': "#eeeeee",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [thresh["range"][0], thresh["warn"]], 'color': "#a8e6cf"},
                {'range': [thresh["warn"], thresh["crit"]], 'color': "#ffd3b6"},
                {'range': [thresh["crit"], thresh["range"][1]], 'color': "#ff8b94"},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.8,
                'value': thresh["crit"]
            }
        }
    ))
    fig.update_layout(height=300, margin=dict(t=50, b=0, l=0, r=0), template="plotly_white")
    return fig

def create_trend_chart(df, param):
    thresh = STATUS_THRESHOLDS[param]
    status_color = STATUS_COLORS[get_status(df[param].iloc[-1], param)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[param], mode="lines", line=dict(width=3, color=status_color)))
    fig.add_hline(y=thresh["warn"], line_dash="dash", line_color="orange", annotation_text="Warning", annotation_position="top left")
    fig.add_hline(y=thresh["crit"], line_dash="dash", line_color="red", annotation_text="Critical", annotation_position="top left")
    fig.update_layout(
        title=f"{param.capitalize()} Trend",
        height=450,
        margin=dict(l=30, r=30, t=50, b=30),
        template="plotly_white",
        yaxis=dict(range=thresh["range"]),
        xaxis_title="Time",
        showlegend=False,
        title_x=0.5,
        transition=dict(duration=500, easing='cubic-in-out')
    )
    return fig

def fetch_data():
    try:
        resp = supabase_client.table("air_compressor").select("*").order("timestamp", desc=True).limit(120).execute()
        if not resp.data:
            return pd.DataFrame()
        df = pd.DataFrame(resp.data)
        ist = pytz.timezone('Asia/Kolkata')
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(ist)
        return df.set_index("timestamp").sort_index()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- Main ---
# Reserve space above title for KPIs
st.markdown("<div style='margin-top:30px;'></div>", unsafe_allow_html=True)

# KPIs Row full width above everything
data = fetch_data()
if not data.empty:
    latest = data.iloc[-1]
    kpi_cols = st.columns(3)
    for i, p in enumerate(["temperature", "pressure", "vibration"]):
        with kpi_cols[i]:
            render_kpi(p, latest[p])

# Main Title after KPIs
st.title("⚙️ Air Compressor Monitoring Dashboard")

with st.sidebar:
    st.header("Navigation")
    app_mode = st.radio("View Mode", ["Live Dashboard", "Database"])

if app_mode == "Live Dashboard":
    st_autorefresh(interval=5000, key="dashboard_refresh")

    if data.empty:
        st.warning("No data available. Please check your ESP32 connection.")
    else:
        # Two columns: gauges left, charts right
        col_gauges, col_charts = st.columns([1, 3])

        with col_gauges:
            for param in ["temperature", "pressure", "vibration"]:
                fig = create_pointer_gauge(param, latest[param])
                st.plotly_chart(fig, use_container_width=True)

        with col_charts:
            tabs = st.tabs(["Temperature", "Pressure", "Vibration"])
            for param, tab in zip(["temperature", "pressure", "vibration"], tabs):
                with tab:
                    st.plotly_chart(create_trend_chart(data, param), use_container_width=True)

elif app_mode == "Database":
    st.subheader("Explore Raw Data")

    start_col, end_col, param_col = st.columns(3)
    with start_col:
        start_date = st.date_input("Start Date", datetime.now().date() - timedelta(days=7))
    with end_col:
        end_date = st.date_input("End Date", datetime.now().date())
    with param_col:
        params = ["temperature", "pressure", "vibration"]
        selected_params = st.multiselect("Select Parameter(s):", options=params, default=params)

    try:
        ist = pytz.timezone("Asia/Kolkata")
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        start_utc = ist.localize(start_dt).astimezone(pytz.utc)
        end_utc = ist.localize(end_dt).astimezone(pytz.utc)

        resp = (
            supabase_client.table("air_compressor")
            .select("*")
            .gte("timestamp", start_utc.isoformat())
            .lte("timestamp", end_utc.isoformat())
            .execute()
        )
        df = pd.DataFrame(resp.data)

        if df.empty:
            st.warning("No data found in selected range.")
        else:
            if selected_params:
                df = df[["timestamp"] + selected_params]
            st.dataframe(df, use_container_width=True, height=500)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, "filtered_data.csv", "text/csv", key="download")
    except Exception as e:
        st.error(f"Error fetching data: {e}")
