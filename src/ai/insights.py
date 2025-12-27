"""AI-powered insights generation"""
import sys
from pathlib import Path
from typing import List, Dict
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config


class InsightsGenerator:
    """Generate insights from transaction data"""
    
    def generate_insights(self, df: pd.DataFrame, statement_id: int) -> List[Dict]:
        """Generate insights from transaction DataFrame"""
        insights = []
        
        if df.empty:
            return insights
        
        # Spending pattern insight
        total_spending = df[df['cr_dr_indicator'] == 'DR']['amount'].sum()
        total_income = df[df['cr_dr_indicator'] == 'CR']['amount'].sum()
        net_flow = total_income - total_spending
        
        insights.append({
            'type': 'spending_pattern',
            'content': f"Total spending: ${total_spending:,.2f}, Total income: ${total_income:,.2f}. Net flow: ${net_flow:,.2f}",
            'metadata': {'total_spending': float(total_spending), 'total_income': float(total_income), 'net_flow': float(net_flow)}
        })
        
        # Category breakdown
        if 'merchant_category' in df.columns:
            category_spending = df[df['cr_dr_indicator'] == 'DR'].groupby('merchant_category')['amount'].sum().sort_values(ascending=False)
            top_category = category_spending.index[0] if len(category_spending) > 0 else None
            top_amount = category_spending.iloc[0] if len(category_spending) > 0 else 0
            
            if top_category:
                insights.append({
                    'type': 'category_analysis',
                    'content': f"Top spending category: {top_category} (${top_amount:,.2f})",
                    'metadata': {'top_category': top_category, 'top_amount': float(top_amount)}
                })
        
        return insights

