"""AI-powered transaction validation using Ollama"""
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config

# Try to import requests for local models
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


class TransactionValidator:
    """Validate transactions using AI to ensure amounts match descriptions"""
    
    def __init__(self):
        """Initialize the validator"""
        self.use_local = REQUESTS_AVAILABLE
        if self.use_local:
            print(f"Transaction validator initialized (using {config.LOCAL_MODEL_NAME})")
        else:
            print("Transaction validator: requests library not available, validation disabled")
    
    def validate_transaction(
        self, 
        amount: float,
        description_1: str,
        description_2: str,
        description_3: str,
        cr_dr_indicator: str,
        balance: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Validate a transaction using AI to check if:
        1. The extracted amount matches what's described in the transaction descriptions
        2. The CR/DR indicator makes sense given the amount and description
        3. The transaction is logically consistent
        
        Returns:
            dict with keys:
                - 'is_valid': bool - whether the transaction appears valid
                - 'confidence': str - 'high', 'medium', 'low'
                - 'suggested_amount': float or None - if amount seems wrong, suggest correction
                - 'suggested_cr_dr': str or None - if CR/DR seems wrong, suggest correction
                - 'reason': str - explanation of validation result
                - 'error': str or None - error message if validation failed
        """
        if not self.use_local:
            return {
                'is_valid': True,
                'confidence': 'low',
                'suggested_amount': None,
                'suggested_cr_dr': None,
                'reason': 'Validation not available (Ollama not configured)',
                'error': None
            }
        
        try:
            # Combine descriptions
            desc_combined = f"{description_1 or ''} {description_2 or ''} {description_3 or ''}".strip()
            
            prompt = f"""You are a bank transaction validator. Analyze this transaction and determine if it makes sense.

Transaction Details:
- Amount: {amount}
- Type: {cr_dr_indicator} (CR = Credit/Money In, DR = Debit/Money Out)
- Description 1: {description_1 or 'N/A'}
- Description 2: {description_2 or 'N/A'}
- Description 3: {description_3 or 'N/A'}
- Combined Description: {desc_combined}
{f'- Balance: {balance}' if balance is not None else ''}

Your task:
1. Check if the amount ({amount}) matches any amount mentioned in the descriptions
2. Verify if the CR/DR indicator makes sense (credits usually show money coming in, debits show money going out)
3. Determine if this transaction is logically consistent

Respond in JSON format with this exact structure:
{{
    "is_valid": true/false,
    "confidence": "high"/"medium"/"low",
    "suggested_amount": number or null,
    "suggested_cr_dr": "CR"/"DR"/null,
    "reason": "brief explanation"
}}

If the amount in the description differs from {amount}, provide the correct amount in suggested_amount.
If the CR/DR seems wrong, provide the correct one in suggested_cr_dr.
Only respond with valid JSON, nothing else."""

            response = requests.post(
                f"{config.LOCAL_MODEL_URL}/api/generate",
                json={
                    "model": config.LOCAL_MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for more deterministic results
                    }
                },
                timeout=15
            )
            
            if response.status_code == 200:
                response_text = response.json().get("response", "").strip()
                
                # Try to extract JSON from response (might have extra text)
                import json
                import re
                
                # Find JSON in response - look for the opening brace and try to find matching closing brace
                # This handles nested JSON better
                result = None
                brace_count = 0
                start_idx = response_text.find('{')
                if start_idx != -1:
                    for i in range(start_idx, len(response_text)):
                        if response_text[i] == '{':
                            brace_count += 1
                        elif response_text[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = response_text[start_idx:i+1]
                                try:
                                    result = json.loads(json_str)
                                    break
                                except json.JSONDecodeError:
                                    continue
                    
                    # Fallback to simple regex if brace matching failed
                    if result is None:
                        json_match = re.search(r'\{.*?"is_valid".*?\}', response_text, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(0)
                            try:
                                result = json.loads(json_str)
                            except json.JSONDecodeError:
                                pass
                
                if result:
                    # Validate and normalize result
                    try:
                        return {
                            'is_valid': bool(result.get('is_valid', True)),
                            'confidence': result.get('confidence', 'medium').lower(),
                            'suggested_amount': float(result['suggested_amount']) if result.get('suggested_amount') is not None else None,
                            'suggested_cr_dr': result.get('suggested_cr_dr', '').upper() if result.get('suggested_cr_dr') else None,
                            'reason': result.get('reason', 'Validated by AI'),
                            'error': None
                        }
                    except (ValueError, KeyError, TypeError) as e:
                        return {
                            'is_valid': True,  # Default to valid if we can't parse
                            'confidence': 'low',
                            'suggested_amount': None,
                            'suggested_cr_dr': None,
                            'reason': f'Could not parse AI response: {str(e)}',
                            'error': str(e)
                        }
                else:
                    # No JSON found, try to infer from text
                    response_lower = response_text.lower()
                    is_valid = 'invalid' not in response_lower and 'error' not in response_lower
                    return {
                        'is_valid': is_valid,
                        'confidence': 'low',
                        'suggested_amount': None,
                        'suggested_cr_dr': None,
                        'reason': 'AI response format unclear, defaulting to valid',
                        'error': 'Could not extract JSON from response'
                    }
            else:
                return {
                    'is_valid': True,  # Default to valid on API error
                    'confidence': 'low',
                    'suggested_amount': None,
                    'suggested_cr_dr': None,
                    'reason': f'Ollama API returned status {response.status_code}',
                    'error': f'HTTP {response.status_code}'
                }
                
        except requests.exceptions.ConnectionError:
            # Ollama not running - silently fail and default to valid
            return {
                'is_valid': True,
                'confidence': 'low',
                'suggested_amount': None,
                'suggested_cr_dr': None,
                'reason': 'Ollama not available, skipping validation',
                'error': 'Connection refused'
            }
        except Exception as e:
            return {
                'is_valid': True,  # Default to valid on error
                'confidence': 'low',
                'suggested_amount': None,
                'suggested_cr_dr': None,
                'reason': f'Validation error: {str(e)}',
                'error': str(e)
            }
    
    def validate_batch(
        self,
        transactions_df: pd.DataFrame,
        validate_all: bool = False
    ) -> pd.DataFrame:
        """
        Validate a batch of transactions.
        
        Args:
            transactions_df: DataFrame with columns: amount_cleaned, trns_desc_1, trns_desc_2, 
                            trns_desc_3, cr_dr_indicator, balance_cleaned
            validate_all: If False, only validate transactions where amount was extracted from description.
                         If True, validate all transactions.
        
        Returns:
            DataFrame with added validation columns:
                - validation_is_valid
                - validation_confidence
                - validation_suggested_amount
                - validation_suggested_cr_dr
                - validation_reason
        """
        if transactions_df.empty:
            return transactions_df
        
        # Add validation columns
        transactions_df['validation_is_valid'] = True
        transactions_df['validation_confidence'] = 'low'
        transactions_df['validation_suggested_amount'] = None
        transactions_df['validation_suggested_cr_dr'] = None
        transactions_df['validation_reason'] = 'Not validated'
        
        # Determine which transactions to validate
        if validate_all:
            validate_mask = pd.Series([True] * len(transactions_df), index=transactions_df.index)
        else:
            # Only validate transactions where amount was extracted from description
            # We'll check if amount is suspicious (0, very large, or equals balance)
            validate_mask = (
                (transactions_df['amount_cleaned'].isna()) |
                (transactions_df['amount_cleaned'] == 0.0) |
                (
                    (transactions_df['amount_cleaned'].abs() > 1_000_000) &
                    (transactions_df['amount_cleaned'].abs() == transactions_df['balance_cleaned'].abs())
                )
            )
        
        validate_count = validate_mask.sum()
        if validate_count == 0:
            print("No transactions need validation")
            return transactions_df
        
        print(f"Validating {validate_count} transactions with Ollama...")
        
        validated_count = 0
        for idx, row in transactions_df[validate_mask].iterrows():
            result = self.validate_transaction(
                amount=float(row.get('amount_cleaned', 0.0)),
                description_1=str(row.get('trns_desc_1', '')),
                description_2=str(row.get('trns_desc_2', '')),
                description_3=str(row.get('trns_desc_3', '')),
                cr_dr_indicator=str(row.get('cr_dr_indicator', 'DR')),
                balance=float(row.get('balance_cleaned')) if pd.notna(row.get('balance_cleaned')) else None
            )
            
            # Store validation results
            transactions_df.at[idx, 'validation_is_valid'] = result['is_valid']
            transactions_df.at[idx, 'validation_confidence'] = result['confidence']
            transactions_df.at[idx, 'validation_suggested_amount'] = result['suggested_amount']
            transactions_df.at[idx, 'validation_suggested_cr_dr'] = result['suggested_cr_dr']
            transactions_df.at[idx, 'validation_reason'] = result['reason']
            
            validated_count += 1
            if validated_count % 10 == 0:
                print(f"  Validated {validated_count}/{validate_count} transactions...")
        
        print(f"Validation complete: {validated_count} transactions validated")
        
        # Apply suggested corrections for high-confidence validations
        high_confidence_mask = (
            validate_mask &
            (transactions_df['validation_confidence'] == 'high') &
            (transactions_df['validation_is_valid'] == False)
        )
        
        corrections_applied = 0
        if high_confidence_mask.any():
            # Apply suggested amounts
            amount_corrections = high_confidence_mask & transactions_df['validation_suggested_amount'].notna()
            if amount_corrections.any():
                corrections_applied += amount_corrections.sum()
                transactions_df.loc[amount_corrections, 'amount_cleaned'] = \
                    transactions_df.loc[amount_corrections, 'validation_suggested_amount']
                print(f"  Applied {amount_corrections.sum()} amount corrections")
            
            # Apply suggested CR/DR
            crdr_corrections = high_confidence_mask & transactions_df['validation_suggested_cr_dr'].notna()
            if crdr_corrections.any():
                corrections_applied += crdr_corrections.sum()
                transactions_df.loc[crdr_corrections, 'cr_dr_indicator'] = \
                    transactions_df.loc[crdr_corrections, 'validation_suggested_cr_dr']
                print(f"  Applied {crdr_corrections.sum()} CR/DR corrections")
        
        if corrections_applied > 0:
            print(f"Total corrections applied: {corrections_applied}")
        
        return transactions_df

