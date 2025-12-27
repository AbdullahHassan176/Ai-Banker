"""Utility functions for web components"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.database.db_manager import DBManager


def format_currency(amount: float, currency: str = 'ZAR') -> str:
    """Format amount as currency"""
    currency_symbols = {
        'ZAR': 'R',
        'AED': 'AED',
        'USD': '$'
    }
    symbol = currency_symbols.get(currency.upper(), 'R')
    
    if currency.upper() == 'AED':
        return f"{symbol} {amount:,.2f}"
    else:
        return f"{symbol}{amount:,.2f}"


def calculate_metrics(df: pd.DataFrame) -> dict:
    """Calculate key financial metrics"""
    if df.empty:
        return {
            'total_income': 0,
            'total_expenses': 0,
            'net_flow': 0,
            'avg_monthly_income': 0,
            'avg_monthly_expenses': 0,
            'num_transactions': 0
        }
    
    income = df[df['cr_dr_indicator'] == 'CR']['amount'].sum()
    expenses = df[df['cr_dr_indicator'] == 'DR']['amount'].sum()
    net_flow = income - expenses
    
    # Calculate monthly averages more accurately
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['month_year'] = df['date'].dt.to_period('M').astype(str)
    
    # Calculate actual monthly totals and then average them
    # This gives a more accurate average when combining multiple accounts
    monthly_income = df[df['cr_dr_indicator'] == 'CR'].groupby('month_year')['amount'].sum()
    monthly_expenses = df[df['cr_dr_indicator'] == 'DR'].groupby('month_year')['amount'].sum()
    
    # Average of actual monthly values (only months with transactions)
    # This is more accurate than dividing total by number of months
    avg_monthly_income = float(monthly_income.mean()) if len(monthly_income) > 0 else 0.0
    avg_monthly_expenses = float(monthly_expenses.mean()) if len(monthly_expenses) > 0 else 0.0
    
    # Total number of unique months
    months = df['month_year'].nunique()
    
    return {
        'total_income': float(income),
        'total_expenses': float(expenses),
        'net_flow': float(net_flow),
        'avg_monthly_income': float(avg_monthly_income),
        'avg_monthly_expenses': float(avg_monthly_expenses),
        'num_transactions': len(df),
        'num_months': months
    }


def get_date_range_filter(df: pd.DataFrame) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Get date range for filtering"""
    if df.empty:
        return None, None
    
    df['date'] = pd.to_datetime(df['date'])
    return df['date'].min(), df['date'].max()


def filter_by_date_range(df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    """Filter dataframe by date range"""
    if df.empty:
        return df
    
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    if start_date:
        # Convert to datetime if it's a date object
        if isinstance(start_date, pd.Timestamp):
            start_dt = start_date
        else:
            start_dt = pd.to_datetime(start_date)
        df = df[df['date'] >= start_dt]
    if end_date:
        # Convert to datetime if it's a date object
        if isinstance(end_date, pd.Timestamp):
            end_dt = end_date
        else:
            end_dt = pd.to_datetime(end_date)
        # Add time to end of day for inclusive end date
        end_dt = end_dt + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df = df[df['date'] <= end_dt]
    
    return df


def get_top_categories(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Get top spending categories"""
    if df.empty or 'merchant_category' not in df.columns:
        return pd.DataFrame()
    
    spending = df[df['cr_dr_indicator'] == 'DR']
    if spending.empty:
        return pd.DataFrame()
    
    top_cats = spending.groupby('merchant_category')['amount'].sum().sort_values(ascending=False).head(n)
    return top_cats.reset_index()


def get_account_summary(db: DBManager) -> dict:
    """Get summary of all accounts"""
    statements = db.get_statements()
    
    # Group by currency for totals
    zar_total = sum(s.closing_balance for s in statements if getattr(s, 'currency', 'ZAR') == 'ZAR')
    aed_total = sum(s.closing_balance for s in statements if getattr(s, 'currency', 'ZAR') == 'AED')
    total_accounts = len(statements)
    
    account_details = []
    for stmt in statements:
        currency = getattr(stmt, 'currency', 'ZAR')
        account_details.append({
            'name': stmt.account_name,
            'balance': stmt.closing_balance,
            'currency': currency,
            'account_number': stmt.account_number or 'N/A',
            'period_end': stmt.period_end
        })
    
    return {
        'zar_total': zar_total,
        'aed_total': aed_total,
        'total_accounts': total_accounts,
        'accounts': account_details
    }


def get_statement_currency(statement_id: int, db: DBManager) -> str:
    """Get currency for a statement"""
    statement = db.get_statement(statement_id)
    if statement:
        return getattr(statement, 'currency', 'ZAR')
    return 'ZAR'


def get_transactions_currency(transactions_df: pd.DataFrame, db: DBManager) -> str:
    """Get currency for transactions (from first statement if available)"""
    if transactions_df.empty:
        return 'ZAR'
    
    # Try to get currency from first transaction's statement
    if 'statement_id' in transactions_df.columns:
        first_stmt_id = transactions_df['statement_id'].iloc[0]
        return get_statement_currency(first_stmt_id, db)
    
    return 'ZAR'


def filter_transactions_by_currency(transactions_df: pd.DataFrame, db: DBManager, currency: str) -> pd.DataFrame:
    """Filter transactions by currency"""
    if transactions_df.empty or 'statement_id' not in transactions_df.columns:
        return transactions_df
    
    # Get all statement IDs with the specified currency
    statements = db.get_statements()
    currency_stmt_ids = {s.id for s in statements if getattr(s, 'currency', 'ZAR') == currency}
    
    # Filter transactions
    return transactions_df[transactions_df['statement_id'].isin(currency_stmt_ids)]

