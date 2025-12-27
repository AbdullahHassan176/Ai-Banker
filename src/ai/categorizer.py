"""AI-powered transaction categorization"""
import os
import json
from typing import Dict, Optional
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config

# Try to import OpenAI, fallback to local if not available
try:
    import openai
    OPENAI_AVAILABLE = True
except (ImportError, AttributeError):
    OPENAI_AVAILABLE = False
    openai = None

# Try to import requests for local models
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


class AICategorizer:
    """AI-powered transaction categorizer"""
    
    # Standard categories
    CATEGORIES = [
        "Groceries",
        "Transport/Fuel",
        "Fast Food",
        "Restaurant/Bars",
        "Health & Fitness",
        "Shopping",
        "Entertainment",
        "Bills & Utilities",
        "Savings & Investments",
        "Salary",
        "Transfer",
        "Airtime",
        "Construction",
        "Other"
    ]
    
    def __init__(self):
        """Initialize the categorizer"""
        self.cache: Dict[str, str] = {}
        self.use_openai = config.USE_OPENAI and OPENAI_AVAILABLE and config.OPENAI_API_KEY
        self.use_local = not self.use_openai and REQUESTS_AVAILABLE
        
        if self.use_openai and openai:
            try:
                openai.api_key = config.OPENAI_API_KEY
                print("Using OpenAI for categorization")
            except Exception:
                self.use_openai = False
                print("OpenAI initialization failed, falling back to local/rule-based")
        elif self.use_local:
            print(f"Using local model ({config.LOCAL_MODEL_NAME}) for categorization")
        else:
            print("AI categorization not available, will use rule-based fallback")
    
    def categorize_with_ai(self, merchant: str, description: str, amount: float) -> str:
        """
        Categorize a transaction using AI
        
        Args:
            merchant: Cleaned merchant name
            description: Transaction description
            amount: Transaction amount
            
        Returns:
            Category name
        """
        # Check cache first
        cache_key = merchant.lower().strip()
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Try AI categorization
        category = None
        if self.use_openai:
            category = self._categorize_with_openai(merchant, description, amount)
        elif self.use_local:
            category = self._categorize_with_local(merchant, description, amount)
        
        # Fallback to rule-based if AI fails
        if not category:
            category = self._categorize_with_rules(merchant, description)
        
        # Cache the result
        if cache_key:
            self.cache[cache_key] = category
        
        return category
    
    def _categorize_with_openai(self, merchant: str, description: str, amount: float) -> Optional[str]:
        """Categorize using OpenAI API"""
        if not openai:
            return None
        try:
            prompt = f"""Categorize this bank transaction into one of these categories: {', '.join(self.CATEGORIES)}

Merchant: {merchant}
Description: {description}
Amount: {amount}

Return only the category name, nothing else."""
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial transaction categorizer. Return only the category name."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=20,
                temperature=0.3
            )
            
            category = response.choices[0].message.content.strip()
            # Validate category
            if category in self.CATEGORIES:
                return category
            # Try to match partial
            for cat in self.CATEGORIES:
                if cat.lower() in category.lower() or category.lower() in cat.lower():
                    return cat
            return None
        except Exception as e:
            print(f"OpenAI categorization error: {e}")
            return None
    
    def _categorize_with_local(self, merchant: str, description: str, amount: float) -> Optional[str]:
        """Categorize using local model (Ollama)"""
        if not requests:
            return None
        try:
            prompt = f"""Categorize this bank transaction into one of these categories: {', '.join(self.CATEGORIES)}

Merchant: {merchant}
Description: {description}
Amount: {amount}

Return only the category name."""
            
            response = requests.post(
                f"{config.LOCAL_MODEL_URL}/api/generate",
                json={
                    "model": config.LOCAL_MODEL_NAME,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=10
            )
            
            if response.status_code == 200:
                category = response.json().get("response", "").strip()
                # Extract category from response
                for cat in self.CATEGORIES:
                    if cat.lower() in category.lower():
                        return cat
            return None
        except Exception as e:
            # Silently fail - will fall back to rule-based categorization
            # Only print if it's not a connection error (expected when Ollama isn't running)
            if "connection" not in str(e).lower() and "refused" not in str(e).lower():
                print(f"Local model categorization error: {e}")
            return None
    
    def _categorize_with_rules(self, merchant: str, description: str) -> str:
        """Fallback rule-based categorization"""
        merchant_lower = merchant.lower()
        desc_lower = description.lower() if description else ""
        combined = f"{merchant_lower} {desc_lower}"
        
        # Groceries
        if any(word in combined for word in ['woolworths', 'ok foods', 'metro', 'hypersave', 'food lovers', 
                                             'spar', 'superspar', 'checkers', 'shoprite', 'u save', 'usave',
                                             'pick n pay', 'pick a pay', 'pnp', 'pick npay', 'choppies']):
            return 'Groceries'
        
        # Transport/Fuel
        if any(word in combined for word in ['uber', 'lefa', 'cab', 'fuel', 'petro', 'gas', 'petrol']):
            return 'Transport/Fuel'
        
        # Fast Food
        if any(word in combined for word in ['pizza', 'kfc', 'hungry lion', 'chicken licken', 'fishaways',
                                             'steers', 'grill addicts', 'rocomamas', 'spur', 'wing it',
                                             'joes beerhouse', 'wimpy', 'beer barrel', 'chicken inn', 'fast food']):
            return 'Fast Food'
        
        # Restaurant/Bars
        if any(word in combined for word in ['ocean basket', 'cappello', 'restaurant', 'bar', 'cafe']):
            return 'Restaurant/Bars'
        
        # Health & Fitness
        if any(word in combined for word in ['pharmacy', 'clicks', 'dischem', 'gym', 'virgin active', 
                                             'nucleus', 'crossfit', 'fitness']):
            return 'Health & Fitness'
        
        # Construction
        if any(word in combined for word in ['buco', 'build it', 'buildit', 'cashbuild', 'ctm', 'cymot']):
            return 'Construction'
        
        # Airtime
        if 'airtime' in combined:
            return 'Airtime'
        
        # Savings & Investments
        if any(word in combined for word in ['savings', 'saving', 'invest', 'investment']):
            return 'Savings & Investments'
        
        # Salary
        if any(word in combined for word in ['salary', 'payrol', 'sal']):
            return 'Salary'
        
        return 'Other'
    
    def categorize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Categorize all transactions in a DataFrame
        
        Args:
            df: DataFrame with transactions
            
        Returns:
            DataFrame with merchant_category filled
        """
        if not config.AI_CATEGORIZATION_ENABLED:
            # Use rule-based only
            df['merchant_category'] = df.apply(
                lambda row: self._categorize_with_rules(
                    str(row.get('merchant', '')),
                    str(row.get('trns_desc_1', ''))
                ),
                axis=1
            )
            return df
        
        # Use AI categorization
        for idx, row in df.iterrows():
            merchant = str(row.get('merchant', ''))
            description = str(row.get('trns_desc_1', ''))
            amount = float(row.get('amount_cleaned', 0))
            
            category = self.categorize_with_ai(merchant, description, amount)
            df.at[idx, 'merchant_category'] = category
        
        return df
    
    def save_cache(self, filepath: str):
        """Save categorization cache to file"""
        with open(filepath, 'w') as f:
            json.dump(self.cache, f)
    
    def load_cache(self, filepath: str):
        """Load categorization cache from file"""
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                self.cache = json.load(f)

