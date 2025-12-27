"""Database operations for AI Banker"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.models import Statement, Transaction, Insight, Anomaly, get_session, init_db


class DBManager:
    """Database manager for CRUD operations"""
    
    def __init__(self):
        """Initialize database"""
        init_db()
    
    def add_statement(self, account_name: str, account_number: str, file_path: str,
                     start_date: datetime, end_date: datetime,
                     opening_balance: float, closing_balance: float,
                     currency: str = 'ZAR') -> Statement:
        """Add a new statement to the database"""
        session = get_session()
        try:
            # Auto-detect currency from account name if not provided
            if not currency:
                account_upper = account_name.upper()
                if 'ENBD' in account_upper or 'EMIRATES' in account_upper or 'AED' in account_upper:
                    currency = 'AED'
                else:
                    currency = 'ZAR'
            
            statement = Statement(
                account_name=account_name,
                account_number=account_number,
                file_path=file_path,
                period_start=start_date,
                period_end=end_date,
                opening_balance=opening_balance,
                closing_balance=closing_balance,
                upload_date=datetime.utcnow(),
                currency=currency
            )
            session.add(statement)
            session.commit()
            session.refresh(statement)
            return statement
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def add_transactions(self, statement_id: int, transactions_df: pd.DataFrame) -> List[Transaction]:
        """Add transactions from a DataFrame to the database, checking for duplicates"""
        session = get_session()
        try:
            # First, get existing transactions for this statement to check for duplicates
            existing_transactions = session.query(Transaction).filter(
                Transaction.statement_id == statement_id
            ).all()
            
            # Create a set of existing transaction keys (date, amount, description_1)
            existing_keys = {
                (t.date, round(float(t.amount), 2), (t.description_1 or '')[:50])
                for t in existing_transactions
            }
            
            transactions = []
            skipped_count = 0
            
            for _, row in transactions_df.iterrows():
                # Handle NaN values - replace with 0.0 for required numeric fields
                amount = row.get('amount_cleaned', 0.0)
                if pd.isna(amount) or amount is None:
                    amount = 0.0
                else:
                    amount = float(amount)
                
                balance = row.get('balance_cleaned', 0.0)
                if pd.isna(balance) or balance is None:
                    balance = 0.0
                else:
                    balance = float(balance)
                
                # Handle NaN for optional string fields
                description_1 = row.get('trns_desc_1')
                if pd.isna(description_1):
                    description_1 = None
                else:
                    description_1 = str(description_1)
                
                description_2 = row.get('trns_desc_2')
                if pd.isna(description_2):
                    description_2 = None
                else:
                    description_2 = str(description_2)
                
                description_3 = row.get('trns_desc_3')
                if pd.isna(description_3):
                    description_3 = None
                else:
                    description_3 = str(description_3)
                
                transaction_type = row.get('trns_type')
                if pd.isna(transaction_type):
                    transaction_type = None
                else:
                    transaction_type = str(transaction_type)
                
                merchant = row.get('merchant')
                if pd.isna(merchant):
                    merchant = None
                else:
                    merchant = str(merchant)
                
                merchant_category = row.get('merchant_category')
                if pd.isna(merchant_category):
                    merchant_category = None
                else:
                    merchant_category = str(merchant_category)
                
                # Handle both column names for backward compatibility
                cr_dr = row.get('cr_dr_indicator') or row.get('cr_dr_ind', 'DR')
                
                # Check for duplicate: same date, amount (rounded to 2 decimals), and description
                trns_date = pd.to_datetime(row['trns_date'])
                duplicate_key = (trns_date, round(amount, 2), (description_1 or '')[:50])
                
                if duplicate_key in existing_keys:
                    skipped_count += 1
                    continue  # Skip duplicate transaction
                
                transaction = Transaction(
                    statement_id=statement_id,
                    date=trns_date,
                    description_1=description_1,
                    description_2=description_2,
                    description_3=description_3,
                    amount=amount,
                    balance=balance,
                    transaction_type=transaction_type,
                    merchant=merchant,
                    merchant_category=merchant_category,
                    cr_dr_indicator=cr_dr,
                    month_year=row['month_year'],
                    unpaid_indicator=bool(row.get('unpaid_ind', 0))
                )
                transactions.append(transaction)
                # Add to existing_keys to prevent duplicates within the same batch
                existing_keys.add(duplicate_key)
            
            if skipped_count > 0:
                print(f"Skipped {skipped_count} duplicate transactions")
            
            if transactions:
                session.add_all(transactions)
                session.commit()
            
            return transactions
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_statements(self) -> List[Statement]:
        """Get all statements"""
        session = get_session()
        try:
            return session.query(Statement).order_by(desc(Statement.period_end)).all()
        finally:
            session.close()
    
    def get_statement(self, statement_id: int) -> Optional[Statement]:
        """Get a statement by ID"""
        session = get_session()
        try:
            return session.query(Statement).filter(Statement.id == statement_id).first()
        finally:
            session.close()
    
    def get_transactions(self, statement_id: Optional[int] = None, currency: Optional[str] = None) -> pd.DataFrame:
        """Get transactions, optionally filtered by statement_id or currency"""
        session = get_session()
        try:
            query = session.query(Transaction)
            if statement_id:
                query = query.filter(Transaction.statement_id == statement_id)
            
            # Filter by currency if provided
            if currency:
                query = query.join(Statement).filter(Statement.currency == currency)
            
            transactions = query.all()
            data = []
            for t in transactions:
                data.append({
                    'id': t.id,
                    'statement_id': t.statement_id,
                    'date': t.date,
                    'description_1': t.description_1,
                    'description_2': t.description_2,
                    'description_3': t.description_3,
                    'amount': t.amount,
                    'balance': t.balance,
                    'transaction_type': t.transaction_type,
                    'merchant': t.merchant,
                    'merchant_category': t.merchant_category,
                    'cr_dr_indicator': t.cr_dr_indicator,
                    'month_year': t.month_year,
                    'unpaid_indicator': t.unpaid_indicator
                })
            return pd.DataFrame(data)
        finally:
            session.close()
    
    def add_insight(self, statement_id: int, insight_type: str, content: str, metadata: Optional[Dict] = None) -> Insight:
        """Add an insight"""
        session = get_session()
        try:
            import json
            metadata_json = json.dumps(metadata) if metadata else None
            insight = Insight(
                statement_id=statement_id,
                insight_type=insight_type,
                content=content,
                metadata_json=metadata_json
            )
            session.add(insight)
            session.commit()
            session.refresh(insight)
            return insight
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_insights(self, statement_id: Optional[int] = None) -> List[Insight]:
        """Get insights, optionally filtered by statement_id"""
        session = get_session()
        try:
            query = session.query(Insight)
            if statement_id:
                query = query.filter(Insight.statement_id == statement_id)
            return query.order_by(desc(Insight.created_at)).all()
        finally:
            session.close()
    
    def add_anomaly(self, statement_id: int, anomaly_type: str, description: str,
                   severity: str, transaction_id: Optional[int] = None,
                   metadata: Optional[Dict] = None) -> Anomaly:
        """Add an anomaly"""
        session = get_session()
        try:
            import json
            metadata_json = json.dumps(metadata) if metadata else None
            anomaly = Anomaly(
                statement_id=statement_id,
                transaction_id=transaction_id,
                anomaly_type=anomaly_type,
                description=description,
                severity=severity,
                metadata_json=metadata_json
            )
            session.add(anomaly)
            session.commit()
            session.refresh(anomaly)
            return anomaly
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_anomalies(self, statement_id: Optional[int] = None) -> List[Anomaly]:
        """Get anomalies, optionally filtered by statement_id"""
        session = get_session()
        try:
            query = session.query(Anomaly)
            if statement_id:
                query = query.filter(Anomaly.statement_id == statement_id)
            return query.order_by(desc(Anomaly.created_at)).all()
        finally:
            session.close()

