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

