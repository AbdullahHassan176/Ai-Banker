"""PDF parser for bank statements"""
import tabula
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.parser import parse
import sys
from pathlib import Path
import warnings

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.data_cleaning import clean_amount, extract_merchant, determine_cr_dr

warnings.filterwarnings("ignore")


def detect_currency_from_data(df: pd.DataFrame) -> str:
    """
    Detect currency from the parsed data by looking for currency symbols
    
    Returns:
        str: 'ZAR' or 'AED' based on detected currency symbols
    """
    # Check amount and balance columns for currency indicators
    amount_text = df['amount'].astype(str).str.upper() if 'amount' in df.columns else pd.Series()
    balance_text = df['balance'].astype(str).str.upper() if 'balance' in df.columns else pd.Series()
    
    all_text = pd.concat([amount_text, balance_text], ignore_index=True)
    
    # Count occurrences of currency indicators
    aed_count = all_text.str.contains('AED|EMIRATES|ENBD', na=False).sum()
    zar_count = all_text.str.contains(r'\bR\s*\d|ZAR|RAND', na=False).sum()
    
    # If AED indicators found, return AED
    if aed_count > 0:
        return 'AED'
    # If R/ZAR indicators found, return ZAR
    elif zar_count > 0:
        return 'ZAR'
    # Default to ZAR
    else:
        return 'ZAR'


def parse_pdf(file_path: str, account_name: str = None):
    """
    Parse a PDF bank statement and extract transaction data
    
    Args:
        file_path: Path to the PDF file
        account_name: Optional account name for currency detection
    
    Returns:
        tuple: (dataframe, opening_balance, closing_balance, start_date, end_date, detected_currency)
    """
    try:
        # Read PDF
        df_list = tabula.read_pdf(
            file_path,
            stream=True,
            guess=True,
            pages='all',
            multiple_tables=True,
            pandas_options={'header': None}
        )
    except Exception as e:
        raise Exception(f"Error reading PDF: {e}")
    
    if not df_list:
        raise Exception("No data extracted from PDF")
    
    # Clean up each page
    cleaned_dfs = []
    seen_row_hashes = set()  # Track seen rows to avoid duplicates across pages
    
    for dfs in df_list:
        # Remove columns with too many nulls
        dfs = dfs[dfs.columns[dfs.isnull().mean() < 0.8]]
        # Drop rows with too few non-null values
        dfs = dfs.dropna(axis=0, thresh=2)
        
        if dfs.empty:
            continue
        
        # Handle columns - remove extra columns if more than 6
        if dfs.shape[1] > 6:
            # Remove last columns until we have 6 or fewer
            while dfs.shape[1] > 6:
                dfs = dfs.drop(dfs.columns[-1], axis=1)
        elif dfs.shape[1] == 7:
            # For 7 columns, drop the last one
            dfs = dfs.drop(dfs.columns[-1], axis=1)
        
        if dfs.shape[1] >= 4:  # Need at least 4 columns
            # Create a hash of each row to detect duplicates across pages
            # Use first few columns (date, description, amount) as key
            def create_row_hash(row):
                # Use first 4 columns or all columns if less than 4
                cols_to_hash = min(4, len(row))
                return hash(tuple(str(row.iloc[i]) if pd.notna(row.iloc[i]) else '' for i in range(cols_to_hash)))
            
            dfs['_row_hash'] = dfs.apply(create_row_hash, axis=1)
            
            # Filter out rows we've already seen
            dfs_filtered = dfs[~dfs['_row_hash'].isin(seen_row_hashes)]
            
            # Add new row hashes to seen set
            seen_row_hashes.update(dfs['_row_hash'].unique())
            
            # Remove the hash column
            dfs_filtered = dfs_filtered.drop('_row_hash', axis=1)
            
            if not dfs_filtered.empty:
                cleaned_dfs.append(dfs_filtered)
    
    if not cleaned_dfs:
        raise Exception("No valid data found in PDF")
    
    # Combine all dataframes
    df_fin = pd.concat(cleaned_dfs, axis=0, sort=False, ignore_index=True)
    
    # Remove header rows
    df_fin = df_fin[~df_fin.iloc[:, 0].astype(str).str.contains("Date", case=False, na=False)]
    
    # Determine number of columns and assign names
    num_cols = df_fin.shape[1]
    
    if num_cols == 7:
        # 7 columns: usually date, desc1, desc2, desc3, desc4, amount, balance
        # Drop one description column (usually desc4) and keep first 3 descriptions
        df_fin.columns = ['date', 'trns_desc_1', 'trns_desc_2', 'trns_desc_3', 'trns_desc_4', 'amount', 'balance']
        # Combine desc3 and desc4, then drop desc4
        df_fin['trns_desc_3'] = df_fin['trns_desc_3'].astype(str) + ' ' + df_fin['trns_desc_4'].astype(str)
        df_fin = df_fin.drop('trns_desc_4', axis=1)
        num_cols = 6
    
    if num_cols == 6:
        df_fin.columns = ['date', 'trns_desc_1', 'trns_desc_2', 'trns_desc_3', 'amount', 'balance']
    elif num_cols == 5:
        df_fin.columns = ['date', 'trns_desc_1', 'trns_desc_2', 'amount', 'balance']
        df_fin['trns_desc_3'] = None
    elif num_cols == 4:
        df_fin.columns = ['date', 'trns_desc_1', 'amount', 'balance']
        df_fin['trns_desc_2'] = None
        df_fin['trns_desc_3'] = None
    else:
        raise ValueError(f"Unexpected number of columns: {num_cols}")
    
    # Get dates - filter out non-date rows
    df_fin['date'] = df_fin['date'].astype(str).str.strip()
    df_fin = df_fin[df_fin['date'].str.len() > 0]
    
    # Filter out rows that are clearly not dates (like "Opening Balance", headers, etc.)
    date_keywords = ['opening', 'balance', 'closing', 'goods', 'cash', 'transfers', 'date', 'description', 'amount']
    df_fin = df_fin[~df_fin['date'].str.lower().isin([kw.lower() for kw in date_keywords])]
    df_fin = df_fin[~df_fin['date'].str.contains('|'.join(date_keywords), case=False, na=False)]
    
    if df_fin.empty:
        raise Exception("No transactions found after cleaning")
    
    # Parse dates - only try to parse rows that look like dates
    def safe_parse_date(x):
        if pd.isna(x) or x is None:
            return None
        x_str = str(x).strip()
        # Skip if it's clearly not a date
        if any(kw in x_str.lower() for kw in date_keywords):
            return None
        try:
            return parse(x_str)
        except:
            return None
    
    try:
        df_fin['trns_date'] = df_fin['date'].apply(safe_parse_date)
        # Remove rows where date parsing failed
        df_fin = df_fin[df_fin['trns_date'].notna()]
    except Exception as e:
        raise Exception(f"Error parsing dates: {e}")
    
    if df_fin.empty:
        raise Exception("No valid transactions found after date parsing")
    
    # Get statement period
    start_date = df_fin['trns_date'].min()
    end_date = df_fin['trns_date'].max()
    
    # Extract balances
    bal_s = df_fin['balance'].iloc[0] if not df_fin.empty else 0.0
    bal_e = df_fin['balance'].iloc[-1] if not df_fin.empty else 0.0
    
    # Clean balances
    if pd.isna(bal_s):
        bal_s = 0.0
    else:
        bal_s = clean_amount(bal_s)
    
    if pd.isna(bal_e):
        bal_e = 0.0
    else:
        bal_e = clean_amount(bal_e)
    
    # Clean amounts
    df_fin['amount_cleaned'] = df_fin['amount'].apply(clean_amount)
    df_fin['balance_cleaned'] = df_fin['balance'].apply(clean_amount)
    
    # Filter out rows where description contains balance-related keywords
    balance_keywords = ['opening balance', 'closing balance', 'brought forward', 'carried forward', 
                        'balance brought', 'balance carried', 'opening bal', 'closing bal']
    desc_combined = (df_fin['trns_desc_1'].astype(str) + ' ' + 
                     df_fin['trns_desc_2'].astype(str) + ' ' + 
                     df_fin['trns_desc_3'].astype(str)).str.lower()
    df_fin = df_fin[~desc_combined.str.contains('|'.join(balance_keywords), case=False, na=False)]
    
    # Filter out transactions where amount exactly equals balance (likely balance rows, not transactions)
    df_fin = df_fin[df_fin['amount_cleaned'] != df_fin['balance_cleaned']]
    
    # Calculate reasonable transaction amount threshold using statistical methods
    # Transaction amounts should typically be much smaller than account balances
    if not df_fin.empty and len(df_fin) > 5:
        # Calculate median and IQR of transaction amounts to detect outliers
        amounts = df_fin['amount_cleaned'].abs()
        q1 = amounts.quantile(0.25)
        q3 = amounts.quantile(0.75)
        iqr = q3 - q1
        
        # Use IQR method: values beyond Q3 + 3*IQR are likely outliers (balance values)
        # But also consider that very large balances might skew this, so use a more conservative approach
        if iqr > 0:
            outlier_threshold = q3 + (3 * iqr)
            # Also check against balance: if amount is > 50% of max balance, it's suspicious
            max_balance = df_fin['balance_cleaned'].abs().max()
            balance_threshold = max_balance * 0.5 if max_balance > 0 else float('inf')
            
            # Use the more conservative threshold
            reasonable_max = min(outlier_threshold, balance_threshold, 5_000_000)  # Cap at 5M
            
            # Filter out suspiciously large amounts (likely balance values)
            df_fin = df_fin[amounts <= reasonable_max]
    
    # Filter out transactions with zero amounts that have no description (likely invalid rows)
    df_fin = df_fin[
        (df_fin['amount_cleaned'] != 0) | 
        (df_fin['trns_desc_1'].notna() & (df_fin['trns_desc_1'].astype(str).str.strip() != ''))
    ]
    
    if df_fin.empty:
        raise Exception("No valid transactions found after filtering balance rows")
    
    # Remove duplicate transactions based on date, amount, and description
    # This handles cases where the same transaction appears on multiple pages
    before_dedup = len(df_fin)
    
    # Create a unique key from date, amount, and first description
    df_fin['_dedup_key'] = (
        df_fin['trns_date'].astype(str) + '_' + 
        df_fin['amount_cleaned'].astype(str) + '_' + 
        df_fin['trns_desc_1'].astype(str).str[:50]  # First 50 chars of description
    )
    
    # Remove duplicates, keeping the first occurrence
    df_fin = df_fin.drop_duplicates(subset=['_dedup_key'], keep='first')
    df_fin = df_fin.drop('_dedup_key', axis=1)
    
    after_dedup = len(df_fin)
    if before_dedup != after_dedup:
        print(f"Removed {before_dedup - after_dedup} duplicate transactions from PDF parsing")
    
    if df_fin.empty:
        raise Exception("No valid transactions found after deduplication")
    
    # Determine CR/DR
    df_fin['cr_dr_indicator'] = df_fin['amount'].apply(determine_cr_dr)
    
    # Extract merchant
    df_fin['merchant'] = df_fin.apply(
        lambda row: extract_merchant(
            row.get('trns_desc_1'),
            row.get('trns_desc_2'),
            row.get('trns_desc_3')
        ),
        axis=1
    )
    
    # Extract transaction type (first part of description)
    df_fin['trns_type'] = df_fin['trns_desc_1'].apply(
        lambda x: str(x).split()[0] if pd.notna(x) and len(str(x).split()) > 0 else None
    )
    
    # Month-year
    df_fin['month_year'] = df_fin['trns_date'].dt.strftime('%Y-%m')
    
    # Unpaid indicator (default to False)
    df_fin['unpaid_ind'] = 0
    
    # Ensure required columns exist
    required_cols = ['trns_date', 'trns_desc_1', 'trns_desc_2', 'trns_desc_3',
                     'amount_cleaned', 'balance_cleaned', 'cr_dr_indicator', 'merchant',
                     'trns_type', 'month_year', 'unpaid_ind']
    
    for col in required_cols:
        if col not in df_fin.columns:
            df_fin[col] = None
    
    # Detect currency from PDF content
    detected_currency = detect_currency_from_data(df_fin)
    
    # If account name provided, use it for currency detection (more reliable)
    if account_name:
        account_upper = account_name.upper()
        if 'ENBD' in account_upper or 'EMIRATES' in account_upper or 'AED' in account_upper:
            detected_currency = 'AED'
        elif 'ZAR' in account_upper or 'RAND' in account_upper:
            detected_currency = 'ZAR'
    
    return df_fin, bal_s, bal_e, start_date, end_date, detected_currency

