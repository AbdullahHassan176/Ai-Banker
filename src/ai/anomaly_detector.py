"""Anomaly detection for transactions"""
import sys
from pathlib import Path
from typing import List, Dict
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config


class AnomalyDetector:
    """Detect anomalies in transaction data"""
    
    def detect_anomalies(self, df: pd.DataFrame, statement_id: int) -> List[Dict]:
        """Detect anomalies in transaction DataFrame"""
        anomalies = []
        
        if df.empty:
            return anomalies
        
        # Unusual amounts
        amounts = df['amount'].abs()
        mean_amount = amounts.mean()
        std_amount = amounts.std()
        
        if std_amount > 0:
            threshold = mean_amount + 2 * std_amount
            unusual = df[amounts > threshold]
            
            for idx, row in unusual.iterrows():
                anomalies.append({
                    'type': 'unusual_amount',
                    'description': f"Unusual transaction amount: ${row['amount']:,.2f} at {row.get('merchant', 'Unknown')}",
                    'severity': 'medium',
                    'transaction_id': None,
                    'metadata': {'amount': float(row['amount']), 'threshold': float(threshold)}
                })
        
        return anomalies

