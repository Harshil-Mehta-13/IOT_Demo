import os
import pandas as pd
import pytz
from datetime import datetime, timedelta
from supabase import create_client

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go

# --- Supabase Connection ---
SUPABASE_URL = "https://ynodggqmitbqluwmljjg.supabase.co"
SUPABASE_KEY = "<YOUR_SUPABASE_KEY>"  # Replace with your valid key
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Constants & Configuration ---
STATUS_THRESHOLDS = {
    "temperature": {"name": "Motor Temperature", "unit": "°C", "warn": 60, "crit": 80, "range": [0, 100]},
    "pressure": {"name": "Output Pressure", "unit": "bar", "warn": 9, "crit": 12, "range": [0, 15]},
    "vibration": {"name": "Vibration Level", "unit": "mm/s", "warn": 3, "crit": 5, "range": [0, 8]},
}
STATUS_COLORS = {"normal": "#00AEEF", "warning": "#F5A623", "critical": "#D0021B"}
DARK_THEME = {
    'background': '#f0f0f0',
    'component_bg': '#ffffff',
    'text': '#111111',
    'text_light': '#555555',
    'border': '#cccccc'
}

# --- Data Fetching ---
def fetch_data(start_date=None, end_date=None, desc=True, limit=200):
    try:
        query = supabase.table("air_compressor").select("*")
        if start_date:
            query = query.gte("timestamp", start_date)
        if end_date:
            end_date_inclusive = datetime.strptime(end_date, '%Y-%m-%d').date() + timedelta(days=1)
            query = query.lt("timestamp", str(end_date_inclusive))
        query = query.order("timestamp", desc=desc).limit(limit)
        resp = query.execute()
        if not resp.data:
            return pd.DataFrame()
        df = pd.DataFrame(resp.data)
        ist = pytz.timezone("Asia/Kolkata")
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(ist)
        return df.set_index("timestamp").sort_index(ascending=not desc)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- Helper Functions ---
def get_status(val, param):
    if pd.isna(val): return "normal"
    t = STATUS_THRESHOLDS[param]
    if val >= t["crit"]: return "critical"
    if val >= t["warn"]: return "warning"
    return "normal"

def create_meter_gauge(value, param):
    t = STATUS_THRESHOLDS[param]
    status = get_status(value, param)
    color = STATUS_COLORS[status]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value if pd.notna(value) else 0,
        number={'font': {'size': 40, 'color': color}, 'suffix': t['unit']},
        gauge={
            'axis': {'range': t['range'], 'tickwidth': 1, 'tickcolor': DARK_THEME['text']},
            'bar': {'color': color, 'thickness': 0.5},
            'bgcolor': 'rgba(0,0,0,0)',
            'borderwidth': 0,
            'steps': [
                {'range': [t['range'][0], t['warn']], 'color': 'rgba(0, 174, 239, 0.3)'},
                {'range': [t['warn'], t['crit']], 'color': 'rgba(245, 166, 35, 0.3)'},
                {'range': [t['crit'], t['range'][1]], 'color': 'rgba(208, 2, 27, 0.3)'},
            ]
        },
        title={'text': t['name'], 'font': {'size': 20, 'color': DARK_THEME['text']}}
    ))
    fig.update_layout(height=300, width=180, margin=dict(l=10, r=10, t=50, b=10),
                      paper_bgcolor=DARK_THEME['component_bg'], font_color=DARK_THEME['text'])
    return fig

def create_trend_chart(df, param):
    t = STATUS_THRESHOLDS[param]
    latest_val = df[param].iloc[-1] if not df.empty else None
    status = get_status(latest_val, param)
    fig = go.Figure()
    if not df.empty:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[param], mode="lines", line=dict(width=3, color=STATUS_COLORS[status]),
            fill='tozeroy', fillcolor=f"rgba({int(STATUS_COLORS[status][1:3],16)}, {int(STATUS_COLORS[status][3:5],16)}, {int(STATUS_COLORS[status][5:7],16)}, 0.1)"
        ))
    fig.add_hline(y=t["warn"], line_dash="dash", line_color=STATUS_COLORS['warning'], opacity=0.5)
    fig.add_hline(y=t["crit"], line_dash="dash", line_color=STATUS_COLORS['critical'], opacity=0.5)
    fig.update_layout(title=f"{t['name']} Trend (Last Hour)", height=500, width=1000,
                      paper_bgcolor=DARK_THEME['component_bg'], plot_bgcolor=DARK_THEME['background'],
                      font_color=DARK_THEME['text'], margin=dict(l=50, r=30, t=50, b=50),
                      yaxis={'range':[0, t['range'][1]*1.05]}, xaxis_title=None, yaxis_title=t['unit'])
    return fig

# --- Dash App Layout ---
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
app.title = "Compressor Live Monitor"

def build_explorer_layout():
    return html.Div([
        html.Div([
            html.Label("Select Date Range:", style={'marginRight': '10px', 'fontSize': '18px'}),
            dcc.DatePickerRange(id='date-picker-range', start_date=datetime.now().date() - timedelta(days=7),
                                end_date=datetime.now().date(), display_format='YYYY-MM-DD', style={'marginRight': '20px', 'fontSize':'16px'}),
            html.Label("Select Parameters:", style={'marginRight': '10px', 'fontSize':'18px'}),
            dcc.Dropdown(id='parameter-dropdown',
                         options=[{'label': v['name'], 'value': k} for k, v in STATUS_THRESHOLDS.items()],
                         value=list(STATUS_THRESHOLDS.keys()), multi=True, style={'flex': 1, 'minWidth': '300px', 'fontSize':'16px'}),
            html.Button('Query Database', id='query-button', n_clicks=0, style={'marginLeft': '20px', 'fontSize':'16px'}),
        ], style={'display': 'flex', 'padding': '20px', 'alignItems': 'center',
                  'backgroundColor': DARK_THEME['component_bg'], 'borderRadius': '5px', 'marginBottom': '20px'}),
        dcc.Loading(id="loading-explorer", children=[html.Div(id='explorer-table-container')], type="default")
    ])

app.layout = html.Div(style={'backgroundColor': DARK_THEME['background'], 'color': DARK_THEME['text'],
                             'fontFamily': 'sans-serif', 'minHeight': '100vh', 'fontSize':'16px'}, children=[
    html.Div([
        html.H1("Air Compressor Live Monitoring Dashboard", style={"textAlign": "center", "marginBottom": "5px"}),
        dcc.Tabs(id="tabs", value="live", children=[
            dcc.Tab(label="Live Monitor", value="live"),
            dcc.Tab(label="Data Explorer", value="explorer")
        ], style={'height': '44px'},
                 colors={"border": DARK_THEME['background'], "primary": STATUS_COLORS['normal'], "background": DARK_THEME['component_bg']})
    ], style={'maxWidth': '1600px', 'margin': 'auto', 'padding': '20px'}),
    html.Div(id="tab-content", style={'maxWidth': '1600px', 'margin': 'auto', 'padding': '20px'}),
    dcc.Interval(id="interval", interval=10 * 1000, n_intervals=0)
])

# --- Callbacks ---
@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab_content(tab):
    if tab == 'live':
        return html.Div(id='live-content-container')
    elif tab == 'explorer':
        return build_explorer_layout()

@app.callback(
    Output('live-content-container', 'children'),
    Input('interval', 'n_intervals'),
    State('tabs', 'value')
)
def update_live_view(n, active_tab):
    if active_tab != 'live': return dash.no_update
    
    df = fetch_data(limit=200)
    if df.empty:
        return html.Div("⚠️ No Data Received in the Last Hour",
                        style={"color": STATUS_COLORS['critical'], "textAlign": "center", "marginTop": "50px", "fontSize": "24px"})

    latest = df.iloc[-1]
    latest_time = latest.name.strftime("%Y-%m-%d %H:%M:%S")
    one_hour_ago = df.index.max() - timedelta(hours=1)
    chart_data = df[df.index >= one_hour_ago]

    return html.Div([
        html.H4(f"Last Update: {latest_time}", style={"textAlign": "center",
                                                      "color": DARK_THEME['text_light'],
                                                      'fontWeight': 'bold', 'fontSize':'18px'}),
        html.Div([
            # Parent flex container for 2 columns
            html.Div([
                # KPIs / Gauges column (30%)
                html.Div([dcc.Graph(figure=create_meter_gauge(latest[p], p), config={"displayModeBar": False})
                          for p in STATUS_THRESHOLDS.keys()],
                         style={'display': 'flex', 'flexDirection': 'column', 'gap': '20px'})
            ], style={'width': '30%', 'padding': '10px'}),

            # Trend Charts column (70%)
            html.Div([dcc.Graph(figure=create_trend_chart(chart_data, p), config={"displayModeBar": False})
                      for p in STATUS_THRESHOLDS.keys()],
                     style={'width': '70%', 'padding': '10px', 'display': 'flex', 'flexDirection': 'column', 'gap': '20px'})
        ], style={'display': 'flex', 'flexDirection': 'row'})
    ])

@app.callback(
    Output('explorer-table-container', 'children'),
    Input('query-button', 'n_clicks'),
    [State('date-picker-range', 'start_date'), State('date-picker-range', 'end_date'), State('parameter-dropdown', 'value')]
)
def update_explorer_table(n_clicks, start_date, end_date, selected_params):
    if n_clicks == 0: return "Please click 'Query Database' to fetch data."
    if not selected_params: return html.Div("⚠️ Please select at least one parameter to display.", style={"color": STATUS_COLORS['warning']})
    
    df = fetch_data(start_date=start_date, end_date=end_date, desc=False, limit=2000)
    if df.empty: return html.Div("⚠️ No Data Found for the Selected Criteria", style={"color": STATUS_COLORS['critical'], "textAlign": "center", "marginTop": "50px", "fontSize": "24px"})
    
    df_table = df.reset_index()
    df_table['timestamp'] = df_table['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    display_cols = ['timestamp'] + selected_params
    df_table = df_table[display_cols]

    return dash_table.DataTable(
        data=df_table.to_dict("records"),
        columns=[{"name": c.replace('_', ' ').title(), "id": c} for c in df_table.columns],
        page_size=20,
        style_table={"overflowX": "auto"},
        style_header={'backgroundColor': DARK_THEME['component_bg'], 'fontWeight': 'bold',
                      'border': f"1px solid {DARK_THEME['border']}", 'fontSize':'16px'},
        style_cell={'backgroundColor': DARK_THEME['background'], 'color': DARK_THEME['text'],
                    'border': f"1px solid {DARK_THEME['border']}", 'padding': '10px', 'textAlign': 'left', 'fontSize':'16px'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'}]
    )

if __name__ == "__main__":
    app.run_server(debug=True, port=8050)