"""Data cleaning utilities for bank statements"""
import re
import string
import pandas as pd
import numpy as np


def clean_trns_desc(text):
    """Clean transaction description text"""
    if pd.isna(text) or text is None:
        return ""
    text = str(text).lower()
    # Remove anything within square brackets
    text = re.sub(r'\[.*?\]', '', text)
    # Remove punctuation
    text = re.sub('[%s]' % re.escape(string.punctuation), '', text)
    # Remove numbers
    text = re.sub(r'\d+', '', text)
    # Remove common words
    text = re.sub('purch', '', text)
    text = re.sub('aankp', '', text)
    text = re.sub('puchc', '', text)
    text = re.sub('aankg', '', text)
    return text.strip()


def clean_amount(amount_str):
    """Clean and parse amount string"""
    if pd.isna(amount_str) or amount_str is None:
        return 0.0
    
    amount_str = str(amount_str).strip()
    # Remove currency symbols and commas
    amount_str = re.sub(r'[^\d.-]', '', amount_str)
    
    try:
        return float(amount_str)
    except (ValueError, TypeError):
        return 0.0


def extract_merchant(description_1, description_2, description_3):
    """Extract merchant name from transaction descriptions"""
    merchant = ""
    if pd.notna(description_1):
        merchant += str(description_1).strip() + " "
    if pd.notna(description_2):
        merchant += str(description_2).strip() + " "
    if pd.notna(description_3):
        merchant += str(description_3).strip()
    
    return merchant.strip()


def determine_cr_dr(amount_str):
    """Determine if transaction is Credit (CR) or Debit (DR)"""
    if pd.isna(amount_str):
        return "DR"
    
    amount_str = str(amount_str).upper()
    if "CR" in amount_str or "CREDIT" in amount_str:
        return "CR"
    elif "DR" in amount_str or "DEBIT" in amount_str:
        return "DR"
    else:
        # Default to DR if unclear
        return "DR"


def extract_amount_from_description(description_1, description_2, description_3):
    """
    Extract amount from description columns when amount column is missing or zero.
    Looks for patterns like:
    - "628.91Cr", "230.09", "1,000.00"
    - "R16,525.75", "AED 1,234.56"
    - "12.95 Expressvpn.Co" (amount at start)
    - "Pmt 1,000.00" (amount at end)
    - "nan 5.65Cr" (with nan prefix)
    
    Returns:
        tuple: (amount, cr_dr_indicator) or (None, None) if no amount found
    """
    descriptions = [description_1, description_2, description_3]
    
    best_amount = None
    best_cr_dr = None
    best_confidence = 0  # Higher confidence for more specific patterns
    
    for desc in descriptions:
        if pd.isna(desc) or desc is None:
            continue
            
        desc_str = str(desc).strip()
        if not desc_str or desc_str.lower() == 'nan':
            continue
        
        # Check for Cr/Dr indicator in description
        desc_upper = desc_str.upper()
        has_cr = 'CR' in desc_upper or 'CREDIT' in desc_upper
        has_dr = 'DR' in desc_upper or 'DEBIT' in desc_upper
        
        # Pattern 1: Amount with currency prefix (R, AED, etc.) - highest confidence
        # e.g., "R16,525.75", "AED 1,234.56"
        currency_pattern = r'(?:R|AED|ZAR)\s*([\d,]+\.\d{2})'
        matches = re.findall(currency_pattern, desc_str, re.IGNORECASE)
        if matches:
            amount_str = matches[-1]
            amount_cleaned = clean_amount(amount_str)
            if 0.01 <= abs(amount_cleaned) <= 10_000_000 and (best_amount is None or 3 > best_confidence):
                best_amount = amount_cleaned
                best_confidence = 3
                if has_cr:
                    best_cr_dr = 'CR'
                elif has_dr:
                    best_cr_dr = 'DR'
        
        # Pattern 2: Number with decimal followed by Cr/Dr - high confidence
        # e.g., "628.91Cr", "5.65Cr", "230.09"
        crdr_pattern = r'([\d,]+\.\d{2})\s*(Cr|Dr|CR|DR)'
        matches = re.findall(crdr_pattern, desc_str, re.IGNORECASE)
        if matches:
            amount_str, crdr_ind = matches[-1]
            amount_cleaned = clean_amount(amount_str)
            if 0.01 <= abs(amount_cleaned) <= 10_000_000 and (best_amount is None or 2 > best_confidence):
                best_amount = amount_cleaned
                best_confidence = 2
                if crdr_ind.upper() == 'CR':
                    best_cr_dr = 'CR'
                else:
                    best_cr_dr = 'DR'
        
        # Pattern 3: Number with decimal at end of string (likely amount)
        # e.g., "POS Purchase 12.95"
        end_pattern = r'([\d,]+\.\d{2})\s*$'
        matches = re.findall(end_pattern, desc_str)
        if matches:
            amount_str = matches[-1]
            amount_cleaned = clean_amount(amount_str)
            if 0.01 <= abs(amount_cleaned) <= 10_000_000 and (best_amount is None or 1 > best_confidence):
                best_amount = amount_cleaned
                best_confidence = 1
                if has_cr:
                    best_cr_dr = 'CR'
                elif has_dr:
                    best_cr_dr = 'DR'
        
        # Pattern 4: Number with decimal at start of string
        # e.g., "12.95 Expressvpn.Co"
        start_pattern = r'^([\d,]+\.\d{2})\s+'
        matches = re.findall(start_pattern, desc_str)
        if matches:
            amount_str = matches[0]
            amount_cleaned = clean_amount(amount_str)
            if 0.01 <= abs(amount_cleaned) <= 10_000_000 and (best_amount is None or 1 > best_confidence):
                best_amount = amount_cleaned
                best_confidence = 1
                if has_cr:
                    best_cr_dr = 'CR'
                elif has_dr:
                    best_cr_dr = 'DR'
        
        # Pattern 5: General number with decimal (lower confidence, use as fallback)
        # e.g., "1,000.00" anywhere in text
        general_pattern = r'([\d,]+\.\d{2})'
        matches = re.findall(general_pattern, desc_str)
        if matches and best_amount is None:
            # Try each match, prefer larger amounts that are reasonable
            for amount_str in matches:
                amount_cleaned = clean_amount(amount_str)
                if 0.01 <= abs(amount_cleaned) <= 10_000_000:
                    # Prefer amounts that are not too large (likely not account numbers)
                    if abs(amount_cleaned) < 1_000_000:
                        best_amount = amount_cleaned
                        best_confidence = 0
                        if has_cr:
                            best_cr_dr = 'CR'
                        elif has_dr:
                            best_cr_dr = 'DR'
                        break
    
    return best_amount, best_cr_dr