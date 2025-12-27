"""Migration script to add currency column to statements table"""
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

import config

def migrate():
    """Add currency column to statements table"""
    db_path = config.DATABASE_PATH
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(statements)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'currency' not in columns:
            print("Adding currency column to statements table...")
            cursor.execute("ALTER TABLE statements ADD COLUMN currency VARCHAR DEFAULT 'ZAR'")
            
            # Update existing records - detect currency from account name
            cursor.execute("SELECT id, account_name FROM statements")
            statements = cursor.fetchall()
            
            for stmt_id, account_name in statements:
                account_upper = account_name.upper()
                if 'ENBD' in account_upper or 'EMIRATES' in account_upper or 'AED' in account_upper:
                    currency = 'AED'
                else:
                    currency = 'ZAR'
                
                cursor.execute("UPDATE statements SET currency = ? WHERE id = ?", (currency, stmt_id))
            
            conn.commit()
            print(f"Updated {len(statements)} statements with currency information")
            print("Migration completed successfully!")
        else:
            print("Currency column already exists")
            
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

