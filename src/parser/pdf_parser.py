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

from src.utils.data_cleaning import clean_amount, extract_merchant, determine_cr_dr, extract_amount_from_description

# Try to import transaction validator (optional - will gracefully degrade if Ollama not available)
try:
    from src.ai.transaction_validator import TransactionValidator
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False
    TransactionValidator = None

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
        # Remove columns with too many nulls, but be smarter about it
        # Keep columns that have numeric data even if they have many nulls (like balance columns)
        cols_to_keep = []
        for col_idx in range(dfs.shape[1]):
            col = dfs.iloc[:, col_idx]
            null_pct = col.isnull().mean()
            
            # Check if column contains numeric data (amounts, balances)
            has_numeric = col.astype(str).str.contains(r'\d+[.,]\d+', na=False, regex=True).any()
            
            # Keep column if:
            # 1. Less than 80% nulls (normal case), OR
            # 2. Has numeric data (likely amount/balance column even with many nulls in headers)
            if null_pct < 0.8 or has_numeric:
                cols_to_keep.append(col_idx)
        
        if cols_to_keep:
            dfs = dfs.iloc[:, cols_to_keep]
        else:
            # Fallback: keep all columns if our logic removed everything
            pass
        
        # Drop rows with too few non-null values
        dfs = dfs.dropna(axis=0, thresh=2)
        
        if dfs.empty:
            continue
        
        # Handle columns - for 7 columns, check if last column is empty/useless
        # Structure is usually: date, desc1, desc2, desc3, amount, balance, extra
        # We want to keep: date, desc1, desc2, desc3, amount, balance
        if dfs.shape[1] == 7:
            # Check if last column is mostly empty or contains non-numeric data
            last_col = dfs.iloc[:, -1]
            last_col_non_null = last_col.notna().sum()
            # If last column is mostly empty (less than 10% non-null), drop it
            if last_col_non_null < len(dfs) * 0.1:
                dfs = dfs.drop(dfs.columns[-1], axis=1)
            # Otherwise, check if it looks like balance data (contains numbers)
            else:
                # Check if column 5 (index 5) looks more like balance (has more numeric values)
                col5_numeric = dfs.iloc[:, 5].astype(str).str.contains(r'\d+\.?\d*', na=False).sum()
                col6_numeric = dfs.iloc[:, 6].astype(str).str.contains(r'\d+\.?\d*', na=False).sum()
                # If column 6 has fewer numbers, it's likely the extra column
                if col6_numeric < col5_numeric:
                    dfs = dfs.drop(dfs.columns[-1], axis=1)
        elif dfs.shape[1] > 7:
            # For more than 7 columns, drop last columns until we have 6
            while dfs.shape[1] > 6:
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
    
    # Extract opening and closing balances (before we calculate amounts from differences)
    # We'll get these after cleaning, but before calculating amounts
    bal_s = None
    bal_e = None
    
    # Clean amounts and balances
    df_fin['amount_cleaned'] = df_fin['amount'].apply(clean_amount)
    df_fin['balance_cleaned'] = df_fin['balance'].apply(clean_amount)
    
    # Convert to numeric
    df_fin['amount_cleaned'] = pd.to_numeric(df_fin['amount_cleaned'], errors='coerce')
    df_fin['balance_cleaned'] = pd.to_numeric(df_fin['balance_cleaned'], errors='coerce')
    
    # Sort by date to ensure correct order for balance calculations
    df_fin = df_fin.sort_values('trns_date').reset_index(drop=True)
    
    # CRITICAL FIX: Calculate transaction amounts from balance changes, not from the "amount" column
    # The "amount" column in PDFs often contains the balance, not the transaction amount
    # Transaction amount = absolute difference between consecutive balances
    
    # First, detect if amount column actually contains balance values
    # If amount equals balance for most rows, the columns are likely swapped or amount contains balances
    amount_equals_balance = (df_fin['amount_cleaned'] == df_fin['balance_cleaned']).sum()
    pct_match = amount_equals_balance / len(df_fin) if len(df_fin) > 0 else 0
    
    # If more than 50% of amounts equal balances, the "amount" column likely contains balances
    if pct_match > 0.5:
        print(f"WARNING: {pct_match*100:.1f}% of amounts equal balances. 'Amount' column likely contains balance values.")
        # Swap: use balance_cleaned as the source for calculating amounts, and amount_cleaned as balance
        # Actually, if they're equal, we need to use balance_cleaned to calculate differences
        # But first, let's check if balance_cleaned has valid data
        if df_fin['balance_cleaned'].notna().sum() < 2:
            # Balance column is empty, so amount column might actually be the balance
            print("Balance column is empty. Treating 'amount' column as balance column.")
            df_fin['balance_cleaned'] = df_fin['amount_cleaned'].copy()
    
    # Check if we have valid balance data
    valid_balances = df_fin['balance_cleaned'].notna() & (df_fin['balance_cleaned'] != 0)
    has_valid_balances = valid_balances.sum() > 1  # Need at least 2 valid balances to calculate differences
    
    if has_valid_balances:
        # Calculate amounts from balance differences
        df_fin['balance_diff'] = df_fin['balance_cleaned'].diff().abs()
        df_fin['balance_change'] = df_fin['balance_cleaned'].diff()
        
        # Replace amount_cleaned with balance_diff for all rows where we can calculate it
        mask_calculable = df_fin['balance_diff'].notna() & (df_fin['balance_diff'] > 0)
        df_fin.loc[mask_calculable, 'amount_cleaned'] = df_fin.loc[mask_calculable, 'balance_diff']
        
        # For rows where balance_diff is not available (first row), try to use original amount
        # But if original amount equals balance, it's likely wrong - use a small default or calculate from first balance
        mask_first_row = ~mask_calculable
        if mask_first_row.any():
            first_row_mask = mask_first_row & (df_fin['amount_cleaned'] == df_fin['balance_cleaned'])
            # For first transaction, if amount equals balance, try to estimate from first balance
            # If first balance is available, use it as a starting point
            if first_row_mask.any() and df_fin['balance_cleaned'].iloc[0] > 0:
                # Can't calculate first amount without opening balance, so keep original or set to 0
                df_fin.loc[first_row_mask, 'amount_cleaned'] = 0.0
    else:
        # No valid balances - this means balance column wasn't parsed correctly
        # In this case, we need to detect if amount column actually contains balances
        # If amount values are very large (like account balances), they're likely wrong
        print("WARNING: Balance column not parsed correctly. Amounts may be incorrect.")
        
        # Try to detect if amount column contains balance values by checking if they're too large
        # or if they match a pattern of running balances (monotonically increasing/decreasing)
        amount_values = df_fin['amount_cleaned'].abs()
        if len(amount_values) > 5:
            # Check if amounts look like balances (very large, or following a pattern)
            median_amount = amount_values.median()
            # If median is very large (>100k), likely balances not amounts
            if median_amount > 100000:
                print(f"WARNING: Amounts appear to be balance values (median: {median_amount:,.2f}). Cannot calculate transaction amounts without balance column.")
                # Set amounts to 0 as we can't determine them
                df_fin['amount_cleaned'] = 0.0
            # If amounts equal balances exactly, they're wrong
            elif (df_fin['amount_cleaned'] == df_fin['balance_cleaned']).all():
                print("WARNING: All amounts equal balances. This indicates parsing error.")
                df_fin['amount_cleaned'] = 0.0
        
        # Set balance_change to None since we can't calculate it
        df_fin['balance_change'] = None
    
    # Store calculated CR/DR based on balance direction
    df_fin['calculated_cr_dr'] = df_fin['balance_change'].apply(
        lambda x: 'CR' if pd.notna(x) and x > 0 else ('DR' if pd.notna(x) and x < 0 else None)
    )
    
    # Extract opening and closing balances (after cleaning and sorting)
    if not df_fin.empty:
        bal_s = float(df_fin['balance_cleaned'].iloc[0]) if pd.notna(df_fin['balance_cleaned'].iloc[0]) else 0.0
        bal_e = float(df_fin['balance_cleaned'].iloc[-1]) if pd.notna(df_fin['balance_cleaned'].iloc[-1]) else 0.0
    else:
        bal_s = 0.0
        bal_e = 0.0
    
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
    
    # Extract amounts from descriptions for rows where amount is missing or zero
    # This helps fill in amounts that weren't properly parsed from the amount column
    df_fin['desc_extracted_amount'] = None
    df_fin['desc_extracted_cr_dr'] = None
    
    for idx, row in df_fin.iterrows():
        amount = row.get('amount_cleaned', 0.0)
        # If amount is missing, zero, or suspiciously large (likely a balance), try to extract from descriptions
        if pd.isna(amount) or amount == 0.0 or (abs(amount) > 1_000_000 and abs(amount) == abs(row.get('balance_cleaned', 0.0))):
            desc_amount, desc_cr_dr = extract_amount_from_description(
                row.get('trns_desc_1'),
                row.get('trns_desc_2'),
                row.get('trns_desc_3')
            )
            if desc_amount is not None and desc_amount > 0:
                df_fin.at[idx, 'desc_extracted_amount'] = desc_amount
                df_fin.at[idx, 'desc_extracted_cr_dr'] = desc_cr_dr
    
    # Update amount_cleaned with extracted amounts where original was missing/zero
    mask_missing_amount = (df_fin['amount_cleaned'].isna()) | (df_fin['amount_cleaned'] == 0.0) | (
        (df_fin['amount_cleaned'].abs() > 1_000_000) & 
        (df_fin['amount_cleaned'].abs() == df_fin['balance_cleaned'].abs())
    )
    mask_has_extracted = df_fin['desc_extracted_amount'].notna() & (df_fin['desc_extracted_amount'] > 0)
    
    fill_mask = mask_missing_amount & mask_has_extracted
    if fill_mask.any():
        filled_count = fill_mask.sum()
        print(f"Filled {filled_count} missing/zero amounts from description columns")
        df_fin.loc[fill_mask, 'amount_cleaned'] = df_fin.loc[fill_mask, 'desc_extracted_amount']
    
    # Determine CR/DR - use calculated CR/DR from balance changes if available, 
    # then extracted CR/DR from descriptions, otherwise use original method
    if 'calculated_cr_dr' in df_fin.columns:
        # Start with calculated CR/DR from balance changes
        df_fin['cr_dr_indicator'] = df_fin['calculated_cr_dr'].copy()
        
        # Fill missing with extracted CR/DR from descriptions
        mask_missing_cr_dr = df_fin['cr_dr_indicator'].isna()
        mask_has_extracted_cr_dr = df_fin['desc_extracted_cr_dr'].notna()
        df_fin.loc[mask_missing_cr_dr & mask_has_extracted_cr_dr, 'cr_dr_indicator'] = \
            df_fin.loc[mask_missing_cr_dr & mask_has_extracted_cr_dr, 'desc_extracted_cr_dr']
        
        # Fill remaining missing with original method
        mask_still_missing = df_fin['cr_dr_indicator'].isna()
        if mask_still_missing.any():
            df_fin.loc[mask_still_missing, 'cr_dr_indicator'] = \
                df_fin.loc[mask_still_missing, 'amount'].apply(determine_cr_dr)
    else:
        # No calculated CR/DR, use extracted or original
        df_fin['cr_dr_indicator'] = df_fin['desc_extracted_cr_dr'].fillna(
            df_fin['amount'].apply(determine_cr_dr)
        )
    
    # Validate transactions using AI (Ollama) - especially for transactions where amounts were extracted from descriptions
    import config
    if (VALIDATOR_AVAILABLE and TransactionValidator and 
        getattr(config, 'AI_TRANSACTION_VALIDATION_ENABLED', True)):
        try:
            validator = TransactionValidator()
            # Only validate transactions where we extracted amounts from descriptions or where amounts seem suspicious
            df_fin = validator.validate_batch(df_fin, validate_all=False)
            print("AI validation completed")
        except Exception as e:
            print(f"Warning: Transaction validation failed: {e}. Continuing without validation.")
    
    # Clean up temporary columns
    if 'desc_extracted_amount' in df_fin.columns:
        df_fin = df_fin.drop('desc_extracted_amount', axis=1)
    if 'desc_extracted_cr_dr' in df_fin.columns:
        df_fin = df_fin.drop('desc_extracted_cr_dr', axis=1)
    
    # Clean up temporary columns
    if 'balance_diff' in df_fin.columns:
        df_fin = df_fin.drop('balance_diff', axis=1)
    if 'balance_change' in df_fin.columns:
        df_fin = df_fin.drop('balance_change', axis=1)
    if 'calculated_cr_dr' in df_fin.columns:
        df_fin = df_fin.drop('calculated_cr_dr', axis=1)
    
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

