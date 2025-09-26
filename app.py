import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.graph_objects as go
import pytz
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

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
        padding-top: 0rem;
        padding-bottom: 2rem;
    }
    #MainMenu, footer { visibility: hidden; }
    
    .title-container {
        margin-top: -70px;
    }
    .title-text {
        font-size: 36px;
        font-weight: 700;
        color: #e0e1dd;
        margin-bottom: 5px;
    }
    .subtitle-text {
        font-size: 14px;
        color: #778da9;
        margin-bottom: 25px;
    }
    hr {
        border-top: 1px solid #415a77;
        margin: 1rem 0;
    }

    .status-normal { background-color: #2a9d8f; }
    .status-warning { background-color: #e9c46a; color: #0d1b2a !important; }
    .status-critical { background-color: #e76f51; }
    .text-normal { color: #2a9d8f; }
    .text-warning { color: #e9c46a; }
    .text-critical { color: #e76f51; }
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
    "temperature": {"name": "Motor Temperature", "unit": "°C", "warn": 60, "crit": 80, "range": [0, 100]},
    "pressure": {"name": "Output Pressure", "unit": "bar", "warn": 9, "crit": 12, "range": [0, 15]},
    "vibration": {"name": "Vibration Level", "unit": "mm/s", "warn": 3, "crit": 5, "range": [0, 8]},
}
STATUS_COLORS = {"normal": "#2a9d8f", "warning": "#e9c46a", "critical": "#e76f51"}

# --- Helper Functions ---
@st.cache_data(ttl=5)
def fetch_data():
    if not supabase_client:
        return pd.DataFrame()
    try:
        resp = supabase_client.table("air_compressor").select("*").order("timestamp", desc=True).limit(200).execute()
        if not resp.data:
            return pd.DataFrame()
        
        df = pd.DataFrame(resp.data)
        ist = pytz.timezone('Asia/Kolkata')
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(ist)
        return df.set_index("timestamp").sort_index()
    except Exception:
        return pd.DataFrame()

def get_status(val, param):
    key = param.lower()
    if key not in STATUS_THRESHOLDS or pd.isna(val): return "normal"
    t = STATUS_THRESHOLDS[key]
    if val >= t["crit"]: return "critical"
    if val >= t["warn"]: return "warning"
    return "normal"

def create_meter_gauge(value, param):
    t = STATUS_THRESHOLDS[param]
    status = get_status(value, param)
    color = STATUS_COLORS[status]
    title_text = f"{t['name']} ({t['unit']})"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value if value else 0,
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'font': {'size': 36, 'color': color}},
        gauge={
            'axis': {'range': t['range'], 'tickwidth': 1, 'tickcolor': "#778da9"},
            'bar': {'color': color, 'thickness': 1},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 1,
            'bordercolor': "#415a77",
            'steps': [
                {'range': [t['range'][0], t['warn']], 'color': 'rgba(42, 157, 143, 0.2)'},
                {'range': [t['warn'], t['crit']], 'color': 'rgba(233, 196, 106, 0.2)'},
                {'range': [t['crit'], t['range'][1]], 'color': 'rgba(231, 111, 81, 0.2)'},
            ]}))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", 
        height=250, 
        margin=dict(l=30, r=30, t=50, b=30),
        title={
            'text': title_text,
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 15, 'color': '#aab3c2'}
        }
    )
    return fig

def create_individual_trend_chart(df, param):
    fig = go.Figure()
    t = STATUS_THRESHOLDS[param]
    title_text = f"{t['name']} Trend"
    
    if not df.empty:
        status_color = STATUS_COLORS[get_status(df[param].iloc[-1], param)]
        mode = "lines+markers" if len(df) < 20 else "lines"
        fig.add_trace(go.Scatter(x=df.index, y=df[param], name=t['name'], mode=mode, line=dict(width=3, color=status_color)))
        fig.add_hline(y=t["warn"], line_dash="dash", line_color="#e9c46a", annotation_text="Warning", annotation_position="bottom right")
        fig.add_hline(y=t["crit"], line_dash="dash", line_color="#e76f51", annotation_text="Critical", annotation_position="bottom right")
    
    fig.update_layout(
        template="plotly_dark", 
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0.2)",
        height=280,
        margin=dict(l=40, r=20, t=50, b=40),
        showlegend=False,
        font=dict(color="#e0e1dd"),
        yaxis={'range': [0, t['range'][1]]},
        title={
            'text': title_text,
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 15, 'color': '#aab3c2'}
        }
    )
    return fig

# --- Sidebar ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #e0e1dd;'>CONTROL</h1>", unsafe_allow_html=True)
    app_mode = st.radio("System View", ["Live Monitor", "Data Explorer"], label_visibility="hidden")

# --- Main Application ---
if app_mode == "Live Monitor":
    # Auto refresh every 5 seconds
    st_autorefresh(interval=5000, key="refresh")

    # --- Draw layout ---
    header_placeholder = st.empty()
    gauge_placeholders = [col.empty() for col in st.columns(3)]
    st.markdown("<hr>", unsafe_allow_html=True)
    chart_placeholders = [col.empty() for col in st.columns(3)]

    # --- Fetch & render ---
    data = fetch_data()

    with header_placeholder.container():
        if data.empty:
            st.error("SYSTEM OFFLINE - NO DATA RECEIVED")
        else:
            latest = data.iloc[-1]
            st.markdown(f'''
            <div class="title-container">
                <div class="title-text">COMPRESSOR UNIT C-1337 MONITOR</div>
                <div class="subtitle-text">Last Communication: {latest.name.strftime("%Y-%m-%d %H:%M:%S")}</div>
            </div>
            ''', unsafe_allow_html=True)
            
            latest_timestamp = data.index.max()
            one_hour_ago = latest_timestamp - timedelta(hours=1)
            chart_data = data[data.index >= one_hour_ago]

            # Gauges
            for i, p in enumerate(STATUS_THRESHOLDS.keys()):
                with gauge_placeholders[i]:
                    st.plotly_chart(create_meter_gauge(latest[p], p), use_container_width=True, config={'displayModeBar': False})

            # Charts
            for i, p in enumerate(STATUS_THRESHOLDS.keys()):
                with chart_placeholders[i]:
                    st.plotly_chart(create_individual_trend_chart(chart_data, p), use_container_width=True, config={'displayModeBar': False})

elif app_mode == "Data Explorer":
    st.subheader("Explore Raw Sensor Data")
    
    ist = pytz.timezone("Asia/Kolkata")
    today_ist = datetime.now(ist).date()

    start_col, end_col, param_col = st.columns(3)
    with start_col: start_date = st.date_input("Start Date", today_ist)
    with end_col: end_date = st.date_input("End Date", today_ist)
    with param_col: 
        selected_params = st.multiselect(
            "Select Parameter(s):", 
            options=list(STATUS_THRESHOLDS.keys()), 
            default=list(STATUS_THRESHOLDS.keys()),
            format_func=lambda p: STATUS_THRESHOLDS[p]['name']
        )
    
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
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_convert(ist)
                df['timestamp'] = df['timestamp'].dt.strftime('%d-%m-%Y %H:%M:%S')
                
                display_cols = ["timestamp"] + selected_params if selected_params else ["timestamp"]
                st.dataframe(df[display_cols], use_container_width=True, height=500)
                csv = df[display_cols].to_csv(index=False).encode('utf-8')
                st.download_button("Download as CSV", csv, "air_compressor_data.csv", "text/csv", key="download-csv")
        except Exception as e:
            st.error(f"An error occurred while fetching data: {e}")
    else:
        st.error("Supabase client not initialized. Cannot fetch data.")
