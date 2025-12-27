"""Database models for AI Banker"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config

Base = declarative_base()


class Statement(Base):
    """Bank statement model"""
    __tablename__ = 'statements'
    
    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    upload_date = Column(DateTime, nullable=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    opening_balance = Column(Float, nullable=False)
    closing_balance = Column(Float, nullable=False)
    account_name = Column(String, nullable=False)
    account_number = Column(String, nullable=True)
    currency = Column(String, nullable=False, default='ZAR')  # ZAR or AED
    
    # Relationships
    transactions = relationship("Transaction", back_populates="statement", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="statement", cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="statement", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Statement(id={self.id}, account={self.account_name})>"


class Transaction(Base):
    """Transaction model"""
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    statement_id = Column(Integer, ForeignKey('statements.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    description_1 = Column(String, nullable=True)
    description_2 = Column(String, nullable=True)
    description_3 = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    balance = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=True)
    merchant = Column(String, nullable=True)
    merchant_category = Column(String, nullable=True)
    cr_dr_indicator = Column(String, nullable=False)
    month_year = Column(String, nullable=False)
    unpaid_indicator = Column(Boolean, default=False)
    
    # Relationships
    statement = relationship("Statement", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, amount={self.amount}, date={self.date})>"


class Insight(Base):
    """AI-generated insights"""
    __tablename__ = 'insights'
    
    id = Column(Integer, primary_key=True)
    statement_id = Column(Integer, ForeignKey('statements.id'), nullable=False)
    insight_type = Column(String, nullable=False)  # 'spending_pattern', 'comparison', 'recommendation', etc.
    content = Column(Text, nullable=False)  # Natural language insight
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)  # JSON string for additional data
    
    # Relationships
    statement = relationship("Statement", back_populates="insights")
    
    def __repr__(self):
        return f"<Insight(id={self.id}, type={self.insight_type})>"


class Anomaly(Base):
    """Detected anomalies"""
    __tablename__ = 'anomalies'
    
    id = Column(Integer, primary_key=True)
    statement_id = Column(Integer, ForeignKey('statements.id'), nullable=False)
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)
    anomaly_type = Column(String, nullable=False)  # 'unusual_amount', 'unusual_merchant', 'timing', etc.
    description = Column(Text, nullable=False)
    severity = Column(String, nullable=False)  # 'low', 'medium', 'high'
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)  # JSON string for additional data
    
    # Relationships
    statement = relationship("Statement", back_populates="anomalies")
    
    def __repr__(self):
        return f"<Anomaly(id={self.id}, type={self.anomaly_type}, severity={self.severity})>"


def init_db():
    """Initialize the database"""
    engine = create_engine(f'sqlite:///{config.DATABASE_PATH}')
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """Get a database session"""
    engine = init_db()
    Session = sessionmaker(bind=engine)
    return Session()

