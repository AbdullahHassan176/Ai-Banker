"""Dash application - Professional Financial Dashboard"""
import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.db_manager import DBManager
from src.parser.pdf_parser import parse_pdf
from src.ai.categorizer import AICategorizer
from src.ai.insights import InsightsGenerator
from src.ai.anomaly_detector import AnomalyDetector
from src.ai.forecaster import Forecaster
from src.web.components.charts import (
    transaction_trend_chart, balance_trend_chart, category_spending_chart,
    monthly_summary_chart, category_pie_chart, cash_flow_chart
)
from src.web.components.utils import (
    format_currency, calculate_metrics, filter_by_date_range,
    get_top_categories, get_account_summary
)

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Financial Dashboard"

# Custom CSS for professional design
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
                color: #ffffff;
                min-height: 100vh;
            }
            .navbar {
                background: rgba(15, 23, 42, 0.8);
                backdrop-filter: blur(10px);
                padding: 1rem 2rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            .navbar h1 {
                font-size: 1.5rem;
                font-weight: 600;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .sidebar {
                background: rgba(15, 23, 42, 0.6);
                backdrop-filter: blur(10px);
                padding: 2rem;
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                min-height: calc(100vh - 80px);
            }
            .nav-link {
                display: block;
                padding: 0.75rem 1rem;
                margin: 0.5rem 0;
                color: #cbd5e1;
                text-decoration: none;
                border-radius: 0.5rem;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            .nav-link:hover {
                background: rgba(102, 126, 234, 0.2);
                color: #ffffff;
                transform: translateX(5px);
            }
            .nav-link.active {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #ffffff;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }
            .content {
                padding: 2rem;
                background: rgba(15, 23, 42, 0.3);
            }
            .metric-card {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 1rem;
                padding: 1.5rem;
                margin: 1rem 0;
                transition: all 0.3s ease;
            }
            .metric-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                border-color: rgba(102, 126, 234, 0.5);
            }
            .metric-value {
                font-size: 2rem;
                font-weight: 700;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .metric-label {
                font-size: 0.875rem;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-top: 0.5rem;
            }
            .chart-container {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 1rem;
                padding: 1.5rem;
                margin: 1rem 0;
            }
            .upload-area {
                border: 2px dashed rgba(102, 126, 234, 0.5);
                border-radius: 1rem;
                padding: 3rem;
                text-align: center;
                background: rgba(102, 126, 234, 0.1);
                transition: all 0.3s ease;
            }
            .upload-area:hover {
                border-color: rgba(102, 126, 234, 0.8);
                background: rgba(102, 126, 234, 0.2);
            }
            .btn-primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                color: white;
                padding: 0.75rem 2rem;
                border-radius: 0.5rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
            }
            .section-title {
                font-size: 1.5rem;
                font-weight: 600;
                margin: 2rem 0 1rem 0;
                color: #ffffff;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Initialize database
db = DBManager()

# App layout
app.layout = html.Div([
    html.Div([
        html.H1("Financial Dashboard", style={'margin': 0})
    ], className='navbar'),
    
    html.Div([
        html.Div([
            dcc.Link("Dashboard", href="/", className="nav-link", id="nav-dashboard"),
            dcc.Link("Upload Statement", href="/upload", className="nav-link", id="nav-upload"),
            dcc.Link("Insights", href="/insights", className="nav-link", id="nav-insights"),
            dcc.Link("Forecast", href="/forecast", className="nav-link", id="nav-forecast"),
            dcc.Link("Anomalies", href="/anomalies", className="nav-link", id="nav-anomalies"),
            dcc.Link("History", href="/history", className="nav-link", id="nav-history"),
            dcc.Link("Wealth & Portfolio", href="/wealth", className="nav-link", id="nav-wealth"),
        ], className='sidebar', style={'width': '250px', 'float': 'left'}),
        
        html.Div([
            dcc.Location(id='url', refresh=False),
            html.Div(id='page-content', className='content')
        ], style={'margin-left': '250px', 'min-height': 'calc(100vh - 80px)'})
    ])
])

# Dashboard page
def create_dashboard_page():
    transactions_df = db.get_transactions()
    
    if transactions_df.empty:
        return html.Div([
            html.H2("Dashboard"),
            html.P("No transactions found. Please upload a bank statement to get started.")
        ])
    
    metrics = calculate_metrics(transactions_df)
    min_date = pd.to_datetime(transactions_df['date']).min().date()
    max_date = pd.to_datetime(transactions_df['date']).max().date()
    
    return html.Div([
        html.H2("Dashboard", className="section-title"),
        
        # Date filters
        html.Div([
            html.Label("Start Date:", style={'margin-right': '1rem', 'color': '#94a3b8'}),
            dcc.DatePickerSingle(
                id='start-date',
                date=min_date,
                min_date_allowed=min_date,
                max_date_allowed=max_date,
                style={'margin-right': '2rem'}
            ),
            html.Label("End Date:", style={'margin-right': '1rem', 'color': '#94a3b8'}),
            dcc.DatePickerSingle(
                id='end-date',
                date=max_date,
                min_date_allowed=min_date,
                max_date_allowed=max_date
            ),
        ], style={'margin': '2rem 0', 'display': 'flex', 'align-items': 'center'}),
        
        # Key Metrics
        html.Div([
            html.Div([
                html.Div(format_currency(metrics['total_income']), className="metric-value"),
                html.Div("Total Income", className="metric-label")
            ], className="metric-card"),
            html.Div([
                html.Div(format_currency(metrics['total_expenses']), className="metric-value"),
                html.Div("Total Expenses", className="metric-label")
            ], className="metric-card"),
            html.Div([
                html.Div(format_currency(metrics['net_flow']), className="metric-value"),
                html.Div("Net Flow", className="metric-label")
            ], className="metric-card"),
            html.Div([
                html.Div(f"{metrics['num_transactions']:,}", className="metric-value"),
                html.Div("Transactions", className="metric-label")
            ], className="metric-card"),
        ], style={'display': 'grid', 'grid-template-columns': 'repeat(4, 1fr)', 'gap': '1rem', 'margin': '2rem 0'}),
        
        # Charts
        html.Div([
            html.Div([
                dcc.Graph(id='transaction-trend-chart', figure=transaction_trend_chart(transactions_df))
            ], className="chart-container"),
            html.Div([
                dcc.Graph(id='balance-trend-chart', figure=balance_trend_chart(transactions_df))
            ], className="chart-container"),
        ], style={'display': 'grid', 'grid-template-columns': '1fr 1fr', 'gap': '1rem'}),
        
        html.Div([
            dcc.Graph(id='monthly-summary-chart', figure=monthly_summary_chart(transactions_df))
        ], className="chart-container"),
        
        html.Div([
            html.Div([
                dcc.Graph(id='category-spending-chart', figure=category_spending_chart(transactions_df))
            ], className="chart-container"),
            html.Div([
                dcc.Graph(id='category-pie-chart', figure=category_pie_chart(transactions_df))
            ], className="chart-container"),
        ], style={'display': 'grid', 'grid-template-columns': '1fr 1fr', 'gap': '1rem'}),
        
        html.Div([
            dcc.Graph(id='cash-flow-chart', figure=cash_flow_chart(transactions_df))
        ], className="chart-container"),
    ])

# Upload page
def create_upload_page():
    return html.Div([
        html.H2("Upload Bank Statement", className="section-title"),
        html.Div([
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    html.P("Drag and Drop or Click to Upload PDF"),
                ]),
                style={
                    'width': '100%',
                    'height': '200px',
                    'lineHeight': '200px',
                    'borderWidth': '2px',
                    'borderStyle': 'dashed',
                    'borderRadius': '1rem',
                    'textAlign': 'center',
                    'margin': '2rem 0',
                    'borderColor': 'rgba(102, 126, 234, 0.5)',
                    'background': 'rgba(102, 126, 234, 0.1)',
                    'cursor': 'pointer'
                },
                multiple=False
            ),
            html.Div([
                html.Label("Account Name:", style={'display': 'block', 'margin': '1rem 0', 'color': '#94a3b8'}),
                dcc.Input(id='account-name', type='text', placeholder='e.g., Main Checking Account',
                         style={'width': '100%', 'padding': '0.75rem', 'borderRadius': '0.5rem', 'border': '1px solid rgba(255,255,255,0.1)', 'background': 'rgba(255,255,255,0.05)', 'color': '#ffffff'}),
                html.Label("Account Number (Optional):", style={'display': 'block', 'margin': '1rem 0', 'color': '#94a3b8'}),
                dcc.Input(id='account-number', type='text', placeholder='e.g., 1234567890',
                         style={'width': '100%', 'padding': '0.75rem', 'borderRadius': '0.5rem', 'border': '1px solid rgba(255,255,255,0.1)', 'background': 'rgba(255,255,255,0.05)', 'color': '#ffffff'}),
                html.Button('Process Statement', id='process-btn', n_clicks=0, className='btn-primary', style={'marginTop': '1rem'}),
            ], style={'margin': '2rem 0'}),
            html.Div(id='upload-status')
        ])
    ])

# Callback for page routing
@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/upload':
        return create_upload_page()
    elif pathname == '/insights':
        return html.Div([html.H2("Insights", className="section-title"), html.P("Insights page - Coming soon")])
    elif pathname == '/forecast':
        return html.Div([html.H2("Forecast", className="section-title"), html.P("Forecast page - Coming soon")])
    elif pathname == '/anomalies':
        return html.Div([html.H2("Anomalies", className="section-title"), html.P("Anomalies page - Coming soon")])
    elif pathname == '/history':
        return html.Div([html.H2("History", className="section-title"), html.P("History page - Coming soon")])
    elif pathname == '/wealth':
        return html.Div([html.H2("Wealth & Portfolio", className="section-title"), html.P("Wealth page - Coming soon")])
    else:
        return create_dashboard_page()

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)

