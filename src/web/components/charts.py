"""Chart components for financial visualizations"""
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Dark theme colors
DARK_BG = "#0e1117"
SECONDARY_BG = "#262730"
TEXT_COLOR = "#fafafa"
PRIMARY_COLOR = "#1f77b4"
SUCCESS_COLOR = "#2ecc71"
WARNING_COLOR = "#f39c12"
DANGER_COLOR = "#e74c3c"

# Chart template
DARK_TEMPLATE = {
    "layout": {
        "paper_bgcolor": DARK_BG,
        "plot_bgcolor": SECONDARY_BG,
        "font": {"color": TEXT_COLOR},
        "xaxis": {
            "gridcolor": "#3a3f4b",
            "linecolor": "#3a3f4b",
        },
        "yaxis": {
            "gridcolor": "#3a3f4b",
            "linecolor": "#3a3f4b",
        }
    }
}


def transaction_trend_chart(df: pd.DataFrame, currency: str = 'ZAR'):
    """Transaction amount trend over time"""
    if df.empty:
        return None
    
    currency_symbol = 'R' if currency == 'ZAR' else 'AED'
    currency_label = currency_symbol if currency == 'ZAR' else f'{currency_symbol} '
    
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    fig = go.Figure()
    
    # Credits
    credits = df[df['cr_dr_indicator'] == 'CR']
    if not credits.empty:
        fig.add_trace(go.Scatter(
            x=credits['date'],
            y=credits['amount'],
            mode='markers+lines',
            name='Credits',
            line=dict(color=SUCCESS_COLOR, width=2),
            marker=dict(size=4),
            hovertemplate=f'<b>%{{x|%Y-%m-%d}}</b><br>Amount: {currency_label}%{{y:,.2f}}<extra></extra>'
        ))
    
    # Debits
    debits = df[df['cr_dr_indicator'] == 'DR']
    if not debits.empty:
        fig.add_trace(go.Scatter(
            x=debits['date'],
            y=debits['amount'],
            mode='markers+lines',
            name='Debits',
            line=dict(color=DANGER_COLOR, width=2),
            marker=dict(size=4),
            hovertemplate=f'<b>%{{x|%Y-%m-%d}}</b><br>Amount: {currency_label}%{{y:,.2f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title="Transaction Trend",
        xaxis_title="Date",
        yaxis_title=f"Amount ({currency_symbol})",
        hovermode='x unified',
        template="plotly_dark",
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


def balance_trend_chart(df: pd.DataFrame, currency: str = 'ZAR'):
    """Account balance trend over time"""
    if df.empty:
        return None
    
    currency_symbol = 'R' if currency == 'ZAR' else 'AED'
    currency_label = currency_symbol if currency == 'ZAR' else f'{currency_symbol} '
    
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    fig = go.Figure()
    
    # If we have statement_id, group by account to show separate balance lines
    if 'statement_id' in df.columns and df['statement_id'].nunique() > 1:
        # Multiple accounts - show each account separately
        colors = px.colors.qualitative.Set3
        for idx, (stmt_id, group) in enumerate(df.groupby('statement_id')):
            group = group.sort_values('date')
            fig.add_trace(go.Scatter(
                x=group['date'],
                y=group['balance'],
                mode='lines+markers',
                name=f'Account {stmt_id}',
                line=dict(color=colors[idx % len(colors)], width=2),
                marker=dict(size=4),
                hovertemplate=f'<b>%{{x|%Y-%m-%d}}</b><br>Balance: {currency_label}%{{y:,.2f}}<extra></extra>'
            ))
        fig.update_layout(showlegend=True)
    else:
        # Single account or no statement_id - show combined balance
        # For multiple accounts without statement_id, calculate running balance
        if 'statement_id' not in df.columns or df['statement_id'].nunique() == 1:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['balance'],
                mode='lines+markers',
                name='Balance',
                line=dict(color=PRIMARY_COLOR, width=3),
                marker=dict(size=5),
                fill='tonexty',
                fillcolor=f'rgba(31, 119, 180, 0.2)',
                hovertemplate=f'<b>%{{x|%Y-%m-%d}}</b><br>Balance: {currency_label}%{{y:,.2f}}<extra></extra>'
            ))
        else:
            # Calculate running balance from transactions
            df['cash_flow'] = df.apply(
                lambda row: row['amount'] if row.get('cr_dr_indicator') == 'CR' else -row['amount'],
                axis=1
            )
            # Start with first balance if available, otherwise 0
            initial_balance = df['balance'].iloc[0] if not df.empty else 0
            df['running_balance'] = initial_balance + df['cash_flow'].cumsum()
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['running_balance'],
                mode='lines+markers',
                name='Combined Balance',
                line=dict(color=PRIMARY_COLOR, width=3),
                marker=dict(size=5),
                fill='tonexty',
                fillcolor=f'rgba(31, 119, 180, 0.2)',
                hovertemplate=f'<b>%{{x|%Y-%m-%d}}</b><br>Balance: {currency_label}%{{y:,.2f}}<extra></extra>'
            ))
        fig.update_layout(showlegend=False)
    
    fig.update_layout(
        title="Account Balance Trend",
        xaxis_title="Date",
        yaxis_title=f"Balance ({currency_symbol})",
        hovermode='x unified',
        template="plotly_dark",
        height=400
    )
    
    return fig


def category_spending_chart(df: pd.DataFrame, currency: str = 'ZAR'):
    """Spending by category"""
    if df.empty:
        return None
    
    currency_symbol = 'R' if currency == 'ZAR' else 'AED'
    currency_label = currency_symbol if currency == 'ZAR' else f'{currency_symbol} '
    
    df = df.copy()
    spending = df[df['cr_dr_indicator'] == 'DR']
    
    if spending.empty or 'merchant_category' not in spending.columns:
        return None
    
    category_totals = spending.groupby('merchant_category')['amount'].sum().sort_values(ascending=False)
    
    fig = go.Figure(data=[
        go.Bar(
            x=category_totals.index,
            y=category_totals.values,
            marker_color=PRIMARY_COLOR,
            hovertemplate=f'<b>%{{x}}</b><br>Total: {currency_label}%{{y:,.2f}}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title="Spending by Category",
        xaxis_title="Category",
        yaxis_title=f"Total Amount ({currency_symbol})",
        template="plotly_dark",
        height=400,
        xaxis={'tickangle': -45}
    )
    
    return fig


def monthly_summary_chart(df: pd.DataFrame, currency: str = 'ZAR'):
    """Monthly income vs expenses"""
    if df.empty:
        return None
    
    currency_symbol = 'R' if currency == 'ZAR' else 'AED'
    currency_label = currency_symbol if currency == 'ZAR' else f'{currency_symbol} '
    
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['month_year'] = df['date'].dt.to_period('M').astype(str)
    
    monthly = df.groupby(['month_year', 'cr_dr_indicator'])['amount'].sum().reset_index()
    
    income = monthly[monthly['cr_dr_indicator'] == 'CR'].set_index('month_year')['amount']
    expenses = monthly[monthly['cr_dr_indicator'] == 'DR'].set_index('month_year')['amount']
    
    months = sorted(set(df['month_year']))
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Income',
        x=months,
        y=[income.get(m, 0) for m in months],
        marker_color=SUCCESS_COLOR,
        hovertemplate=f'<b>%{{x}}</b><br>Income: {currency_label}%{{y:,.2f}}<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        name='Expenses',
        x=months,
        y=[expenses.get(m, 0) for m in months],
        marker_color=DANGER_COLOR,
        hovertemplate=f'<b>%{{x}}</b><br>Expenses: {currency_label}%{{y:,.2f}}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Monthly Income vs Expenses",
        xaxis_title="Month",
        yaxis_title=f"Amount ({currency_symbol})",
        barmode='group',
        template="plotly_dark",
        height=400,
        hovermode='x unified'
    )
    
    return fig


def category_pie_chart(df: pd.DataFrame, currency: str = 'ZAR'):
    """Pie chart of spending categories"""
    if df.empty:
        return None
    
    currency_symbol = 'R' if currency == 'ZAR' else 'AED'
    currency_label = currency_symbol if currency == 'ZAR' else f'{currency_symbol} '
    
    df = df.copy()
    spending = df[df['cr_dr_indicator'] == 'DR']
    
    if spending.empty or 'merchant_category' not in spending.columns:
        return None
    
    category_totals = spending.groupby('merchant_category')['amount'].sum()
    
    colors = px.colors.qualitative.Set3
    
    fig = go.Figure(data=[go.Pie(
        labels=category_totals.index,
        values=category_totals.values,
        hole=0.4,
        hovertemplate=f'<b>%{{label}}</b><br>Amount: {currency_label}%{{value:,.2f}}<br>Percentage: %{{percent}}<extra></extra>'
    )])
    
    fig.update_traces(
        marker=dict(colors=colors),
        textposition='inside',
        textinfo='percent+label'
    )
    
    fig.update_layout(
        title="Spending Distribution",
        template="plotly_dark",
        height=400,
        showlegend=True
    )
    
    return fig


def cash_flow_chart(df: pd.DataFrame, currency: str = 'ZAR'):
    """Cash flow over time"""
    if df.empty:
        return None
    
    currency_symbol = 'R' if currency == 'ZAR' else 'AED'
    currency_label = currency_symbol if currency == 'ZAR' else f'{currency_symbol} '
    
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Calculate cumulative cash flow
    df['cash_flow'] = df.apply(
        lambda row: row['amount'] if row['cr_dr_indicator'] == 'CR' else -row['amount'],
        axis=1
    )
    df['cumulative_flow'] = df['cash_flow'].cumsum()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['cumulative_flow'],
        mode='lines+markers',
        name='Cumulative Cash Flow',
        line=dict(color=PRIMARY_COLOR, width=3),
        marker=dict(size=4),
        fill='tozeroy',
        fillcolor=f'rgba(31, 119, 180, 0.2)',
        hovertemplate=f'<b>%{{x|%Y-%m-%d}}</b><br>Cash Flow: {currency_label}%{{y:,.2f}}<extra></extra>'
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title="Cumulative Cash Flow",
        xaxis_title="Date",
        yaxis_title=f"Cumulative Flow ({currency_symbol})",
        hovermode='x unified',
        template="plotly_dark",
        height=400,
        showlegend=False
    )
    
    return fig

