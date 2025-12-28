"""Re-process all statements in the database"""
import sys
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, str(Path(__file__).parent))

from src.database.db_manager import DBManager
from src.parser.pdf_parser import parse_pdf
from src.ai.categorizer import AICategorizer
from src.ai.insights import InsightsGenerator
from src.ai.anomaly_detector import AnomalyDetector

def reprocess_statement(statement_id, file_path):
    """Re-process a single statement"""
    start_time = time.time()
    
    try:
        db = DBManager()
        statement = db.get_statement(statement_id)
        
        if not statement:
            print(f"[SKIP] Statement {statement_id} not found")
            return False
        
        # Get currency from existing statement
        currency = getattr(statement, 'currency', 'ZAR')
        if not currency:
            # Auto-detect from account name
            account_upper = statement.account_name.upper()
            if 'ENBD' in account_upper or 'EMIRATES' in account_upper or 'AED' in account_upper:
                currency = 'AED'
            else:
                currency = 'ZAR'
        
        print(f"\n{'='*70}")
        print(f"[{statement_id}] Processing Statement ID {statement_id}")
        print(f"File: {statement.file_path}")
        print(f"Account: {statement.account_name}")
        print(f"Currency: {currency}")
        print(f"{'='*70}")
        
        # Parse PDF (with account name for better currency detection)
        print("  [1/5] Parsing PDF...", end="", flush=True)
        parse_start = time.time()
        df, bal_s, bal_e, start_date, end_date, detected_currency = parse_pdf(file_path, statement.account_name)
        parse_time = time.time() - parse_start
        print(f" [OK] Found {len(df)} transactions (took {parse_time:.1f}s)")
        
        # Use detected currency from PDF if statement doesn't have one
        if not currency or currency == 'ZAR':
            currency = detected_currency if detected_currency else currency
        
        # Categorize
        print("  [2/5] Categorizing transactions...", end="", flush=True)
        cat_start = time.time()
        categorizer = AICategorizer()
        df = categorizer.categorize_dataframe(df)
        cat_time = time.time() - cat_start
        print(f" [OK] Categorized {len(df)} transactions (took {cat_time:.1f}s)")
        
        # Update statement currency if missing
        from src.database.models import get_session, Statement, Transaction, Insight, Anomaly
        session = get_session()
        try:
            stmt = session.query(Statement).filter(Statement.id == statement_id).first()
            if stmt and (not hasattr(stmt, 'currency') or not stmt.currency):
                stmt.currency = currency
                session.commit()
                print(f"  [INFO] Updated statement currency to {currency}")
        except Exception as e:
            print(f"  [WARN] Could not update currency: {e}")
        finally:
            session.close()
        
        # Clear existing transactions, insights, and anomalies for this statement before reprocessing
        print("  [3/6] Clearing existing data...", end="", flush=True)
        clear_start = time.time()
        session = get_session()
        try:
            # Delete existing transactions
            deleted_transactions = session.query(Transaction).filter(
                Transaction.statement_id == statement_id
            ).delete()
            
            # Delete existing insights
            deleted_insights = session.query(Insight).filter(
                Insight.statement_id == statement_id
            ).delete()
            
            # Delete existing anomalies
            deleted_anomalies = session.query(Anomaly).filter(
                Anomaly.statement_id == statement_id
            ).delete()
            
            session.commit()
            clear_time = time.time() - clear_start
            print(f" [OK] Cleared {deleted_transactions} transactions, {deleted_insights} insights, {deleted_anomalies} anomalies (took {clear_time:.1f}s)")
        except Exception as e:
            session.rollback()
            print(f" [WARN] Error clearing data: {e}")
        finally:
            session.close()
        
        # Save transactions - force update by deleting all existing first
        print("  [4/6] Saving transactions...", end="", flush=True)
        save_start = time.time()
        
        # Force delete all existing transactions for this statement in a new session
        from src.database.models import get_session, Transaction
        session = get_session()
        try:
            # Force delete all transactions for this statement
            deleted_count = session.query(Transaction).filter(
                Transaction.statement_id == statement_id
            ).delete(synchronize_session=False)
            session.commit()
            if deleted_count > 0:
                print(f" [DELETED {deleted_count} old transactions]", end="", flush=True)
        except Exception as e:
            session.rollback()
            print(f" [WARN] Error deleting old transactions: {e}", end="", flush=True)
        finally:
            session.close()
        
        # Now add all transactions as new (no duplicates should exist)
        db.add_transactions(statement_id, df)
        save_time = time.time() - save_start
        print(f" [OK] Saved {len(df)} transactions (took {save_time:.1f}s)")
        
        # Generate insights
        print("  [5/6] Generating insights...", end="", flush=True)
        insights_start = time.time()
        insights_gen = InsightsGenerator()
        insights = insights_gen.generate_insights(df, statement_id)
        for insight in insights:
            db.add_insight(statement_id, insight['type'], insight['content'], insight.get('metadata'))
        insights_time = time.time() - insights_start
        print(f" [OK] Generated {len(insights)} insights (took {insights_time:.1f}s)")
        
        # Detect anomalies
        print("  [6/6] Detecting anomalies...", end="", flush=True)
        anomaly_start = time.time()
        detector = AnomalyDetector()
        anomalies = detector.detect_anomalies(df, statement_id)
        for anomaly in anomalies:
            db.add_anomaly(statement_id, anomaly['type'], anomaly['description'],
                          anomaly['severity'], anomaly.get('transaction_id'), anomaly.get('metadata'))
        anomaly_time = time.time() - anomaly_start
        print(f" [OK] Detected {len(anomalies)} anomalies (took {anomaly_time:.1f}s)")
        
        total_time = time.time() - start_time
        print(f" [OK] Statement {statement_id} processed successfully (took {total_time:.1f}s)")
        return True
        
    except Exception as e:
        total_time = time.time() - start_time
        print(f" [FAIL] Error after {total_time:.1f}s: {e}")
        return False

if __name__ == "__main__":
    db = DBManager()
    statements = db.get_statements()
    
    print(f"\n{'='*70}")
    print("RE-PROCESSING ALL STATEMENTS")
    print(f"{'='*70}")
    print(f"Total statements to process: {len(statements)}\n")
    
    overall_start = time.time()
    successful = 0
    failed = 0
    
    for i, statement in enumerate(statements, 1):
        # Calculate progress
        elapsed = time.time() - overall_start
        if i > 1:
            avg_time_per_statement = elapsed / (i - 1)
            remaining = (len(statements) - i + 1) * avg_time_per_statement
            print(f"\n{'='*70}")
            print(f"OVERALL PROGRESS: {i-1}/{len(statements)} statements processed")
            print(f"Elapsed: {int(elapsed//60)}m {int(elapsed%60)}s | Remaining: ~{int(remaining//60)}m {int(remaining%60)}s")
            print(f"{'='*70}")
        
        if reprocess_statement(statement.id, statement.file_path):
            successful += 1
        else:
            failed += 1
    
    total_time = time.time() - overall_start
    
    print(f"\n{'='*70}")
    print("RE-PROCESSING SUMMARY")
    print(f"{'='*70}")
    print(f"Total Time: {int(total_time//60)}m {int(total_time%60)}s")
    print(f"Total Statements: {len(statements)}")
    print(f"  [OK] Successful: {successful}")
    print(f"  [SKIP] Skipped: 0")
    print(f"  [FAIL] Failed: {failed}")
    print(f"{'='*70}\n")
    
    # Show transaction counts
    transactions_df = db.get_transactions()
    print(f"Total transactions in database: {len(transactions_df)}\n")
    
    print("Transaction counts per statement:")
    for statement in statements:
        count = len(db.get_transactions(statement.id))
        print(f"  Statement ID {statement.id} ({statement.account_name}): {count} transactions")
    
    print("\n[OK] All data is now in the dashboard!")
    print("Run 'streamlit run run_web.py' to view your data!")

