"""Spending forecasting"""
import sys
from pathlib import Path
from typing import Dict
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config


class Forecaster:
    """Generate spending forecasts"""
    
    def forecast(self, df: pd.DataFrame) -> Dict:
        """Generate spending forecast"""
        if df.empty:
            return {'forecast': 0.0, 'confidence': 'low'}
        
        # Simple average-based forecast
        monthly_spending = df[df['cr_dr_indicator'] == 'DR'].groupby('month_year')['amount'].sum()
        
        if len(monthly_spending) > 0:
            avg_monthly = monthly_spending.mean()
            return {
                'forecast': float(avg_monthly),
                'confidence': 'medium' if len(monthly_spending) >= 3 else 'low',
                'based_on_months': len(monthly_spending)
            }
        
        return {'forecast': 0.0, 'confidence': 'low'}

