"""Complete Dash application - Professional Financial Dashboard with all features"""
import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import sys
import base64
import io
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
    get_top_categories, get_account_summary, get_transactions_currency,
    filter_transactions_by_currency
)

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Financial Dashboard"

# Custom CSS for ultra-modern design
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
                background-attachment: fixed;
                color: #ffffff;
                min-height: 100vh;
            }
            .navbar {
                background: rgba(15, 23, 42, 0.95);
                backdrop-filter: blur(20px);
                padding: 1.5rem 2rem;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                position: sticky;
                top: 0;
                z-index: 1000;
            }
            .navbar h1 {
                font-size: 1.75rem;
                font-weight: 700;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                letter-spacing: -0.5px;
            }
            .sidebar {
                background: rgba(15, 23, 42, 0.7);
                backdrop-filter: blur(20px);
                padding: 2rem 1.5rem;
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                min-height: calc(100vh - 80px);
                position: fixed;
                width: 280px;
                overflow-y: auto;
            }
            .nav-link {
                display: block;
                padding: 1rem 1.25rem;
                margin: 0.5rem 0;
                color: #cbd5e1;
                text-decoration: none;
                border-radius: 0.75rem;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                cursor: pointer;
                font-weight: 500;
                font-size: 0.95rem;
                border: 1px solid transparent;
            }
            .nav-link:hover {
                background: rgba(102, 126, 234, 0.15);
                color: #ffffff;
                transform: translateX(8px);
                border-color: rgba(102, 126, 234, 0.3);
            }
            .nav-link.active {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #ffffff;
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
                border-color: rgba(102, 126, 234, 0.5);
                transform: translateX(5px);
            }
            .content {
                padding: 2.5rem;
                margin-left: 280px;
                min-height: calc(100vh - 80px);
            }
            .metric-card {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 1.25rem;
                padding: 2rem;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }
            .metric-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                transform: scaleX(0);
                transition: transform 0.4s ease;
            }
            .metric-card:hover {
                transform: translateY(-8px);
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
                border-color: rgba(102, 126, 234, 0.5);
            }
            .metric-card:hover::before {
                transform: scaleX(1);
            }
            .metric-value {
                font-size: 2.5rem;
                font-weight: 800;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                line-height: 1.2;
            }
            .metric-label {
                font-size: 0.875rem;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                margin-top: 0.75rem;
                font-weight: 600;
            }
            .chart-container {
                background: rgba(255, 255, 255, 0.03);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 1.25rem;
                padding: 1.5rem;
                margin: 1.5rem 0;
                transition: all 0.3s ease;
            }
            .chart-container:hover {
                border-color: rgba(102, 126, 234, 0.4);
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            }
            .section-title {
                font-size: 2rem;
                font-weight: 700;
                margin: 2rem 0 2rem 0;
                color: #ffffff;
                letter-spacing: -0.5px;
            }
            .btn-primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                color: white;
                padding: 1rem 2.5rem;
                border-radius: 0.75rem;
                font-weight: 600;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }
            .btn-primary:hover {
                transform: translateY(-3px);
                box-shadow: 0 12px 30px rgba(102, 126, 234, 0.5);
            }
            .btn-primary:active {
                transform: translateY(-1px);
            }
            input, textarea {
                background: rgba(255, 255, 255, 0.05) !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                color: #ffffff !important;
                border-radius: 0.75rem !important;
                padding: 0.875rem 1.25rem !important;
                transition: all 0.3s ease !important;
            }
            input:focus, textarea:focus {
                outline: none !important;
                border-color: rgba(102, 126, 234, 0.5) !important;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
            }
            .upload-area {
                border: 3px dashed rgba(102, 126, 234, 0.4);
                border-radius: 1.25rem;
                padding: 4rem 2rem;
                text-align: center;
                background: rgba(102, 126, 234, 0.05);
                transition: all 0.3s ease;
                cursor: pointer;
            }
            .upload-area:hover {
                border-color: rgba(102, 126, 234, 0.7);
                background: rgba(102, 126, 234, 0.1);
                transform: scale(1.02);
            }
            .status-success {
                background: rgba(46, 204, 113, 0.2);
                border: 1px solid rgba(46, 204, 113, 0.5);
                border-radius: 0.75rem;
                padding: 1rem;
                margin: 1rem 0;
                color: #2ecc71;
            }
            .status-error {
                background: rgba(231, 76, 60, 0.2);
                border: 1px solid rgba(231, 76, 60, 0.5);
                border-radius: 0.75rem;
                padding: 1rem;
                margin: 1rem 0;
                color: #e74c3c;
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
        ], className='sidebar'),
        
        html.Div([
            dcc.Location(id='url', refresh=False),
            html.Div(id='page-content', className='content')
        ])
    ]),
    
    dcc.Store(id='upload-store', data=None),
    dcc.Store(id='filter-store', data=None)
])

# Helper functions for pages
def create_dashboard_page():
    all_transactions_df = db.get_transactions()
    
    if all_transactions_df.empty:
        return html.Div([
            html.H2("Dashboard", className="section-title"),
            html.P("No transactions found. Please upload a bank statement to get started.", 
                  style={'color': '#94a3b8', 'fontSize': '1.1rem'})
        ])
    
    # Get all statements to determine available currencies
    statements = db.get_statements()
    currencies = list(set(getattr(s, 'currency', 'ZAR') for s in statements))
    
    # Calculate metrics separately for each currency
    currency_metrics = {}
    for curr in currencies:
        curr_transactions = filter_transactions_by_currency(all_transactions_df, db, curr)
        if not curr_transactions.empty:
            currency_metrics[curr] = {
                'metrics': calculate_metrics(curr_transactions),
                'transactions': curr_transactions
            }
    
    # Get date range from all transactions
    min_date = pd.to_datetime(all_transactions_df['date']).min().date()
    max_date = pd.to_datetime(all_transactions_df['date']).max().date()
    
    # Build metrics cards for each currency
    metrics_cards = []
    for curr in sorted(currencies):
        if curr in currency_metrics:
            metrics = currency_metrics[curr]['metrics']
            metrics_cards.append(html.Div([
                html.H3(f"{curr} Accounts", style={'color': '#667eea', 'marginBottom': '1rem', 'fontSize': '1.25rem'}),
                html.Div([
                    html.Div([
                        html.Div(format_currency(metrics['total_income'], curr), className="metric-value"),
                        html.Div("Total Income", className="metric-label")
                    ], className="metric-card"),
                    html.Div([
                        html.Div(format_currency(metrics['total_expenses'], curr), className="metric-value"),
                        html.Div("Total Expenses", className="metric-label")
                    ], className="metric-card"),
                    html.Div([
                        html.Div(format_currency(metrics['net_flow'], curr), className="metric-value"),
                        html.Div("Net Flow", className="metric-label")
                    ], className="metric-card"),
                    html.Div([
                        html.Div(f"{metrics['num_transactions']:,}", className="metric-value"),
                        html.Div("Transactions", className="metric-label")
                    ], className="metric-card"),
                ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(200px, 1fr))', 'gap': '1rem'})
            ], style={'marginBottom': '2rem'}))
    
    return html.Div([
        html.H2("Dashboard", className="section-title"),
        
        # Date filters
        html.Div([
            html.Label("Start Date:", style={'marginRight': '1rem', 'color': '#94a3b8', 'fontWeight': '500'}),
            dcc.DatePickerSingle(
                id='start-date',
                date=min_date,
                min_date_allowed=min_date,
                max_date_allowed=max_date,
                style={'marginRight': '2rem', 'backgroundColor': 'rgba(255,255,255,0.05)', 'borderRadius': '0.75rem'}
            ),
            html.Label("End Date:", style={'marginRight': '1rem', 'color': '#94a3b8', 'fontWeight': '500'}),
            dcc.DatePickerSingle(
                id='end-date',
                date=max_date,
                min_date_allowed=min_date,
                max_date_allowed=max_date,
                style={'backgroundColor': 'rgba(255,255,255,0.05)', 'borderRadius': '0.75rem'}
            ),
        ], style={'margin': '2rem 0', 'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap', 'gap': '1rem'}),
        
        # Key Metrics - Separate by Currency
        html.Div(metrics_cards),
        
        # Charts - Show charts for each currency separately
        html.Div([
            html.Div([
                html.H3(f"{curr} Accounts - Charts", style={'color': '#667eea', 'marginBottom': '1rem', 'fontSize': '1.25rem'}),
                html.Div([
                    html.Div([
                        dcc.Graph(
                            id=f'transaction-trend-chart-{curr}',
                            figure=transaction_trend_chart(currency_metrics[curr]['transactions'], curr),
                            config={'displayModeBar': False}
                        )
                    ], className="chart-container"),
                    html.Div([
                        dcc.Graph(
                            id=f'balance-trend-chart-{curr}',
                            figure=balance_trend_chart(currency_metrics[curr]['transactions'], curr),
                            config={'displayModeBar': False}
                        )
                    ], className="chart-container"),
                ], style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '1.5rem'}),
                html.Div([
                    dcc.Graph(
                        id=f'monthly-summary-chart-{curr}',
                        figure=monthly_summary_chart(currency_metrics[curr]['transactions'], curr),
                        config={'displayModeBar': False}
                    )
                ], className="chart-container"),
                html.Div([
                    html.Div([
                        dcc.Graph(
                            id=f'category-spending-chart-{curr}',
                            figure=category_spending_chart(currency_metrics[curr]['transactions'], curr),
                            config={'displayModeBar': False}
                        )
                    ], className="chart-container"),
                    html.Div([
                        dcc.Graph(
                            id=f'category-pie-chart-{curr}',
                            figure=category_pie_chart(currency_metrics[curr]['transactions'], curr),
                            config={'displayModeBar': False}
                        )
                    ], className="chart-container"),
                ], style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '1.5rem'}),
                html.Div([
                    dcc.Graph(
                        id=f'cash-flow-chart-{curr}',
                        figure=cash_flow_chart(currency_metrics[curr]['transactions'], curr),
                        config={'displayModeBar': False}
                    )
                ], className="chart-container"),
            ], style={'marginBottom': '3rem'})
            for curr in sorted(currencies) if curr in currency_metrics
        ]),
    ])

def create_upload_page():
    return html.Div([
        html.H2("Upload Bank Statement", className="section-title"),
        html.Div([
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    html.P("Drag and Drop or Click to Upload PDF", 
                           style={'fontSize': '1.2rem', 'fontWeight': '500', 'color': '#cbd5e1'}),
                    html.P("Supported format: PDF", 
                           style={'fontSize': '0.9rem', 'color': '#94a3b8', 'marginTop': '0.5rem'})
                ]),
                style={
                    'width': '100%',
                    'height': '250px',
                    'lineHeight': '250px',
                    'borderWidth': '3px',
                    'borderStyle': 'dashed',
                    'borderRadius': '1.25rem',
                    'textAlign': 'center',
                    'margin': '2rem 0',
                    'borderColor': 'rgba(102, 126, 234, 0.4)',
                    'background': 'rgba(102, 126, 234, 0.05)',
                    'cursor': 'pointer',
                    'transition': 'all 0.3s ease'
                },
                multiple=False
            ),
            html.Div([
                html.Label("Account Name:", style={'display': 'block', 'margin': '1.5rem 0 0.75rem 0', 'color': '#94a3b8', 'fontWeight': '500'}),
                dcc.Input(id='account-name', type='text', placeholder='e.g., Main Checking Account',
                         style={'width': '100%', 'padding': '0.875rem 1.25rem', 'borderRadius': '0.75rem', 
                                'border': '1px solid rgba(255,255,255,0.1)', 'background': 'rgba(255,255,255,0.05)', 
                                'color': '#ffffff', 'fontSize': '1rem'}),
                html.Label("Account Number (Optional):", style={'display': 'block', 'margin': '1.5rem 0 0.75rem 0', 'color': '#94a3b8', 'fontWeight': '500'}),
                dcc.Input(id='account-number', type='text', placeholder='e.g., 1234567890',
                         style={'width': '100%', 'padding': '0.875rem 1.25rem', 'borderRadius': '0.75rem', 
                                'border': '1px solid rgba(255,255,255,0.1)', 'background': 'rgba(255,255,255,0.05)', 
                                'color': '#ffffff', 'fontSize': '1rem'}),
                html.Button('Process Statement', id='process-btn', n_clicks=0, className='btn-primary', 
                           style={'marginTop': '2rem', 'width': '100%'}),
            ]),
            html.Div(id='upload-status')
        ])
    ])

def create_insights_page():
    statements = db.get_statements()
    
    if not statements:
        return html.Div([
            html.H2("Insights", className="section-title"),
            html.P("No statements found. Upload a statement to generate insights.", 
                  style={'color': '#94a3b8', 'fontSize': '1.1rem'})
        ])
    
    statement_options = [{'label': f"{s.account_name} ({s.period_end.strftime('%Y-%m')})", 'value': s.id} 
                        for s in statements]
    
    return html.Div([
        html.H2("Financial Insights", className="section-title"),
        html.Div([
            html.Label("Select Statement:", style={'marginRight': '1rem', 'color': '#94a3b8', 'fontWeight': '500'}),
            dcc.Dropdown(
                id='insight-statement-selector',
                options=statement_options,
                value=statements[0].id if statements else None,
                style={'width': '400px', 'backgroundColor': 'rgba(255,255,255,0.05)', 'color': '#ffffff'}
            )
        ], style={'margin': '2rem 0'}),
        html.Div(id='insights-content')
    ])

def create_forecast_page():
    transactions_df = db.get_transactions()
    
    if transactions_df.empty:
        return html.Div([
            html.H2("Forecast", className="section-title"),
            html.P("No transaction data available for forecasting.", 
                  style={'color': '#94a3b8', 'fontSize': '1.1rem'})
        ])
    
    currency = get_transactions_currency(transactions_df, db)
    forecaster = Forecaster()
    forecast = forecaster.forecast(transactions_df)
    
    return html.Div([
        html.H2("Spending Forecast", className="section-title"),
        html.Div([
            html.Div([
                html.Div(format_currency(forecast['forecast'], currency), className="metric-value"),
                html.Div("Expected Monthly Expenses", className="metric-label")
            ], className="metric-card", style={'maxWidth': '400px'}),
        ], style={'margin': '2rem 0'}),
        html.P(f"Confidence Level: {forecast.get('confidence', 'low').title()}", 
              style={'color': '#94a3b8', 'fontSize': '1rem', 'margin': '1rem 0'}),
        html.Div([
            dcc.Graph(id='forecast-chart', figure=monthly_summary_chart(transactions_df, currency),
                     config={'displayModeBar': False})
        ], className="chart-container")
    ])

def create_anomalies_page():
    statements = db.get_statements()
    
    if not statements:
        return html.Div([
            html.H2("Anomalies", className="section-title"),
            html.P("No statements found.", style={'color': '#94a3b8', 'fontSize': '1.1rem'})
        ])
    
    statement_options = [{'label': 'All Statements', 'value': None}] + \
                       [{'label': f"{s.account_name} ({s.period_end.strftime('%Y-%m')})", 'value': s.id} 
                        for s in statements]
    
    return html.Div([
        html.H2("Transaction Anomalies", className="section-title"),
        html.Div([
            html.Label("Select Statement:", style={'marginRight': '1rem', 'color': '#94a3b8', 'fontWeight': '500'}),
            dcc.Dropdown(
                id='anomaly-statement-selector',
                options=statement_options,
                value=None,
                style={'width': '400px', 'backgroundColor': 'rgba(255,255,255,0.05)', 'color': '#ffffff'}
            )
        ], style={'margin': '2rem 0'}),
        html.Div(id='anomalies-content')
    ])

def create_history_page():
    statements = db.get_statements()
    
    if not statements:
        return html.Div([
            html.H2("History", className="section-title"),
            html.P("No statements found.", style={'color': '#94a3b8', 'fontSize': '1.1rem'})
        ])
    
    statement_options = [{'label': f"{s.account_name} ({s.period_end.strftime('%Y-%m-%d')}) - {getattr(s, 'currency', 'ZAR')}", 'value': s.id} 
                        for s in statements]
    
    all_transactions = db.get_transactions()
    currency = get_transactions_currency(all_transactions, db) if not all_transactions.empty else 'ZAR'
    
    return html.Div([
        html.H2("Historical Comparison", className="section-title"),
        html.Div([
            html.Label("Select Statements to Compare:", style={'marginRight': '1rem', 'color': '#94a3b8', 'fontWeight': '500'}),
            dcc.Dropdown(
                id='history-statement-selector',
                options=statement_options,
                value=[s.id for s in statements[:3]] if len(statements) >= 3 else [s.id for s in statements],
                multi=True,
                style={'width': '100%', 'backgroundColor': 'rgba(255,255,255,0.05)', 'color': '#ffffff'}
            )
        ], style={'margin': '2rem 0'}),
        html.Div(id='history-content'),
        html.Div([
            dcc.Graph(id='history-chart', figure=monthly_summary_chart(all_transactions, currency) if not all_transactions.empty else None,
                     config={'displayModeBar': False})
        ], className="chart-container", style={'marginTop': '2rem'})
    ])

def create_wealth_page():
    account_summary = get_account_summary(db)
    
    # Prepare chart data
    zar_accounts = [acc for acc in account_summary['accounts'] if acc.get('currency') == 'ZAR']
    aed_accounts = [acc for acc in account_summary['accounts'] if acc.get('currency') == 'AED']
    
    # Create ZAR chart
    if zar_accounts:
        zar_figure = go.Figure(data=[go.Pie(
            labels=[acc['name'] for acc in zar_accounts],
            values=[acc['balance'] for acc in zar_accounts],
            hole=0.4,
            hovertemplate='<b>%{label}</b><br>Balance: R%{value:,.2f}<br>Percentage: %{percent}<extra></extra>'
        )]).update_traces(
            textposition='inside',
            textinfo='percent+label'
        ).update_layout(
            title="ZAR Account Distribution",
            template="plotly_dark",
            height=400,
            showlegend=True,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
    else:
        zar_figure = go.Figure().update_layout(
            title="ZAR Account Distribution",
            template="plotly_dark",
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            annotations=[dict(text='No ZAR accounts', x=0.5, y=0.5, showarrow=False, font=dict(size=16, color='#94a3b8'))]
        )
    
    # Create AED chart
    if aed_accounts:
        aed_figure = go.Figure(data=[go.Pie(
            labels=[acc['name'] for acc in aed_accounts],
            values=[acc['balance'] for acc in aed_accounts],
            hole=0.4,
            hovertemplate='<b>%{label}</b><br>Balance: AED %{value:,.2f}<br>Percentage: %{percent}<extra></extra>'
        )]).update_traces(
            textposition='inside',
            textinfo='percent+label'
        ).update_layout(
            title="AED Account Distribution",
            template="plotly_dark",
            height=400,
            showlegend=True,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
    else:
        aed_figure = go.Figure().update_layout(
            title="AED Account Distribution",
            template="plotly_dark",
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            annotations=[dict(text='No AED accounts', x=0.5, y=0.5, showarrow=False, font=dict(size=16, color='#94a3b8'))]
        )
    
    return html.Div([
        html.H2("Wealth & Portfolio", className="section-title"),
        html.Div([
            html.Div([
                html.Div(format_currency(account_summary['zar_total'], 'ZAR'), className="metric-value"),
                html.Div("Total Net Worth (ZAR)", className="metric-label")
            ], className="metric-card"),
            html.Div([
                html.Div(format_currency(account_summary['aed_total'], 'AED'), className="metric-value"),
                html.Div("Total Net Worth (AED)", className="metric-label")
            ], className="metric-card"),
            html.Div([
                html.Div(f"{account_summary['total_accounts']}", className="metric-value"),
                html.Div("Total Accounts", className="metric-label")
            ], className="metric-card"),
        ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(250px, 1fr))', 'gap': '1.5rem', 'margin': '2rem 0'}),
        
        html.H3("Account Details", style={'margin': '2rem 0 1rem 0', 'color': '#ffffff', 'fontWeight': '600'}),
        dash_table.DataTable(
            id='accounts-table',
            columns=[
                {'name': 'Account Name', 'id': 'name'},
                {'name': 'Currency', 'id': 'currency'},
                {'name': 'Balance', 'id': 'balance'},
                {'name': 'Account Number', 'id': 'account_number'},
                {'name': 'Last Updated', 'id': 'period_end'}
            ],
            data=[{
                'name': acc['name'],
                'currency': acc.get('currency', 'ZAR'),
                'balance': format_currency(acc['balance'], acc.get('currency', 'ZAR')),
                'account_number': acc['account_number'] or 'N/A',
                'period_end': pd.to_datetime(acc['period_end']).strftime('%Y-%m-%d')
            } for acc in account_summary['accounts']],
            style_cell={
                'backgroundColor': 'rgba(255, 255, 255, 0.05)',
                'color': '#ffffff',
                'border': '1px solid rgba(255, 255, 255, 0.1)',
                'textAlign': 'left',
                'padding': '1rem',
                'fontFamily': 'Inter'
            },
            style_header={
                'backgroundColor': 'rgba(102, 126, 234, 0.2)',
                'fontWeight': '600',
                'border': '1px solid rgba(102, 126, 234, 0.3)'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgba(255, 255, 255, 0.02)'
                }
            ],
            style_table={'borderRadius': '1rem', 'overflow': 'hidden'}
        ),
        
        html.Div([
            html.H4("Portfolio by Currency", style={'margin': '2rem 0 1rem 0', 'color': '#ffffff', 'fontWeight': '600'}),
            html.Div([
                html.Div([
                    html.H5("ZAR Accounts", style={'color': '#667eea', 'marginBottom': '1rem'}),
                    dcc.Graph(
                        id='portfolio-chart-zar',
                        figure=zar_figure,
                        config={'displayModeBar': False}
                    )
                ], style={'flex': '1', 'margin': '0 1rem'}),
                html.Div([
                    html.H5("AED Accounts", style={'color': '#667eea', 'marginBottom': '1rem'}),
                    dcc.Graph(
                        id='portfolio-chart-aed',
                        figure=aed_figure,
                        config={'displayModeBar': False}
                    )
                ], style={'flex': '1', 'margin': '0 1rem'})
            ], style={'display': 'flex', 'gap': '1rem'})
        ], className="chart-container", style={'marginTop': '2rem'})
    ])

# Callback for page routing
@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/upload':
        return create_upload_page()
    elif pathname == '/insights':
        return create_insights_page()
    elif pathname == '/forecast':
        return create_forecast_page()
    elif pathname == '/anomalies':
        return create_anomalies_page()
    elif pathname == '/history':
        return create_history_page()
    elif pathname == '/wealth':
        return create_wealth_page()
    else:
        return create_dashboard_page()

# Upload callback
@app.callback(
    Output('upload-status', 'children'),
    Input('process-btn', 'n_clicks'),
    State('upload-data', 'contents'),
    State('account-name', 'value'),
    State('account-number', 'value'),
    State('currency-selector', 'value'),
    prevent_initial_call=True
)
def process_upload(n_clicks, contents, account_name, account_number, currency):
    if not contents or not account_name:
        return html.Div("Please upload a PDF and enter an account name.", className="status-error")
    
    try:
        # Decode base64 content
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Save to temp file
        temp_dir = Path("temp_uploads")
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        with open(temp_path, 'wb') as f:
            f.write(decoded)
        
        # Parse PDF (with account name for better currency detection)
        df, bal_s, bal_e, start_date, end_date, detected_currency = parse_pdf(str(temp_path), account_name)
        
        # Categorize
        categorizer = AICategorizer()
        df = categorizer.categorize_dataframe(df)
        
        # Use detected currency from PDF if not explicitly provided
        if not currency:
            currency = detected_currency
        # Also auto-detect from account name as fallback
        if not currency:
            account_upper = account_name.upper()
            if 'ENBD' in account_upper or 'EMIRATES' in account_upper or 'AED' in account_upper:
                currency = 'AED'
            else:
                currency = 'ZAR'
        
        # Check if a statement with the same account, period, and balances already exists
        # This prevents processing the same statement multiple times
        existing_statements = db.get_statements()
        duplicate_found = False
        for existing_stmt in existing_statements:
            if (existing_stmt.account_name == account_name and 
                existing_stmt.account_number == (account_number if account_number else None) and
                abs(existing_stmt.opening_balance - bal_s) < 0.01 and
                abs(existing_stmt.closing_balance - bal_e) < 0.01 and
                existing_stmt.period_start.date() == start_date.date() and
                existing_stmt.period_end.date() == end_date.date()):
                duplicate_found = True
                statement = existing_stmt
                # Still try to add transactions (they will be deduplicated)
                db.add_transactions(statement.id, df)
                return html.Div([
                    html.P(f"Statement already exists for {account_name} ({start_date.date()} to {end_date.date()}). ", 
                          className="status-success", style={'fontSize': '1.1rem', 'fontWeight': '500'}),
                    html.P(f"Added {len(df)} transactions (duplicates were skipped).", 
                          style={'color': '#94a3b8', 'fontSize': '0.9rem', 'marginTop': '0.5rem'})
                ])
        
        if not duplicate_found:
            # Add statement
            statement = db.add_statement(
                account_name=account_name,
                account_number=account_number if account_number else None,
                file_path=str(temp_path),
                start_date=start_date,
                end_date=end_date,
                opening_balance=bal_s,
                closing_balance=bal_e,
                currency=currency
            )
            
            # Save transactions
            db.add_transactions(statement.id, df)
        
        # Generate insights
        insights_gen = InsightsGenerator()
        insights = insights_gen.generate_insights(df, statement.id)
        for insight in insights:
            db.add_insight(statement.id, insight['type'], insight['content'], insight.get('metadata'))
        
        # Detect anomalies
        detector = AnomalyDetector()
        anomalies = detector.detect_anomalies(df, statement.id)
        for anomaly in anomalies:
            db.add_anomaly(statement.id, anomaly['type'], anomaly['description'],
                          anomaly['severity'], anomaly.get('transaction_id'), anomaly.get('metadata'))
        
        return html.Div([
            html.P(f"Successfully processed {len(df)} transactions from {account_name}!", 
                  className="status-success", style={'fontSize': '1.1rem', 'fontWeight': '500'})
        ])
        
    except Exception as e:
        return html.Div(f"Error processing statement: {str(e)}", className="status-error")

# Insights callback
@app.callback(
    Output('insights-content', 'children'),
    Input('insight-statement-selector', 'value')
)
def update_insights(statement_id):
    if not statement_id:
        return html.P("Please select a statement.", style={'color': '#94a3b8'})
    
    insights = db.get_insights(statement_id)
    
    if not insights:
        return html.P("No insights available for this statement.", style={'color': '#94a3b8'})
    
    return html.Div([
        html.Div([
            html.H4(insight.insight_type.replace('_', ' ').title(), 
                   style={'color': '#667eea', 'marginBottom': '0.5rem'}),
            html.P(insight.content, style={'color': '#cbd5e1', 'lineHeight': '1.6'})
        ], className="metric-card", style={'margin': '1rem 0'})
        for insight in insights
    ])

# Anomalies callback
@app.callback(
    Output('anomalies-content', 'children'),
    Input('anomaly-statement-selector', 'value')
)
def update_anomalies(statement_id):
    anomalies = db.get_anomalies(statement_id)
    
    if not anomalies:
        return html.P("No anomalies detected. Your transactions appear normal.", 
                     style={'color': '#94a3b8'})
    
    severity_colors = {
        'low': '#f39c12',
        'medium': '#e67e22',
        'high': '#e74c3c'
    }
    
    return html.Div([
        html.Div([
            html.H4(anomaly.anomaly_type.replace('_', ' ').title(),
                   style={'color': severity_colors.get(anomaly.severity, '#95a5a6'), 'marginBottom': '0.5rem'}),
            html.P(anomaly.description, style={'color': '#cbd5e1', 'lineHeight': '1.6'}),
            html.Small(f"Severity: {anomaly.severity.upper()}", 
                      style={'color': '#94a3b8', 'fontWeight': '600'})
        ], className="metric-card", style={'margin': '1rem 0', 'borderLeft': f'4px solid {severity_colors.get(anomaly.severity, "#95a5a6")}'})
        for anomaly in anomalies
    ])

# History callback
@app.callback(
    Output('history-content', 'children'),
    Input('history-statement-selector', 'value')
)
def update_history(statement_ids):
    if not statement_ids:
        return html.P("Please select at least one statement.", style={'color': '#94a3b8'})
    
    comparison_data = []
    for stmt_id in statement_ids:
        stmt = db.get_statement(stmt_id)
        if stmt:
            transactions = db.get_transactions(stmt_id)
            currency = getattr(stmt, 'currency', 'ZAR')
            
            # Calculate metrics only if there are transactions
            if not transactions.empty:
                metrics = calculate_metrics(transactions)
            else:
                # If no transactions, use statement balances to calculate net flow
                net_flow = stmt.closing_balance - stmt.opening_balance
                metrics = {
                    'total_income': max(0, net_flow) if net_flow > 0 else 0,
                    'total_expenses': abs(min(0, net_flow)) if net_flow < 0 else 0,
                    'net_flow': net_flow,
                    'num_transactions': 0
                }
            
            comparison_data.append({
                'Account': stmt.account_name,
                'Currency': currency,
                'Period End': stmt.period_end.strftime('%Y-%m-%d'),
                'Opening Balance': format_currency(stmt.opening_balance, currency),
                'Closing Balance': format_currency(stmt.closing_balance, currency),
                'Total Income': format_currency(metrics['total_income'], currency),
                'Total Expenses': format_currency(metrics['total_expenses'], currency),
                'Net Flow': format_currency(metrics['net_flow'], currency),
                'Transactions': metrics['num_transactions']
            })
    
    if not comparison_data:
        return html.P("No data available for selected statements.", style={'color': '#94a3b8'})
    
    return dash_table.DataTable(
        columns=[{'name': col, 'id': col} for col in comparison_data[0].keys()],
        data=comparison_data,
        style_cell={
            'backgroundColor': 'rgba(255, 255, 255, 0.05)',
            'color': '#ffffff',
            'border': '1px solid rgba(255, 255, 255, 0.1)',
            'textAlign': 'left',
            'padding': '1rem',
            'fontFamily': 'Inter'
        },
        style_header={
            'backgroundColor': 'rgba(102, 126, 234, 0.2)',
            'fontWeight': '600',
            'border': '1px solid rgba(102, 126, 234, 0.3)'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgba(255, 255, 255, 0.02)'
            }
        ],
        style_table={'borderRadius': '1rem', 'overflow': 'hidden', 'marginTop': '1rem'}
    )

if __name__ == '__main__':
    app.run(debug=True, port=8050, host='127.0.0.1')

