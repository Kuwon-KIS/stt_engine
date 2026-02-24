"""
Migration: Add status and updated_at columns to analysis_results table

This migration implements Recommendation 2 from DB_STRUCTURE_ANALYSIS.md:
- Adds status column (VARCHAR(20), default 'pending')
- Adds updated_at column (DATETIME)
- Updates existing rows to status='completed'
- Creates index on status for faster filtering
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'db.sqlite')

def migrate():
    """Apply the migration"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("🔄 Starting migration: add_result_status")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(analysis_results);")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'status' in columns and 'updated_at' in columns:
            print("✅ Columns already exist. Migration already applied.")
            return
        
        # Add status column
        if 'status' not in columns:
            print("  Adding 'status' column...")
            cursor.execute("""
                ALTER TABLE analysis_results 
                ADD COLUMN status VARCHAR(20) DEFAULT 'pending';
            """)
            print("  ✅ 'status' column added")
        
        # Add updated_at column
        if 'updated_at' not in columns:
            print("  Adding 'updated_at' column...")
            cursor.execute("""
                ALTER TABLE analysis_results 
                ADD COLUMN updated_at DATETIME;
            """)
            print("  ✅ 'updated_at' column added")
        
        # Update existing rows to 'completed' status
        print("  Updating existing rows to status='completed'...")
        cursor.execute("""
            UPDATE analysis_results 
            SET status = 'completed', 
                updated_at = created_at 
            WHERE status = 'pending';
        """)
        rows_updated = cursor.rowcount
        print(f"  ✅ Updated {rows_updated} existing rows")
        
        # Create index on status for faster filtering
        print("  Creating index on status column...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_results_status 
                ON analysis_results(status);
            """)
            print("  ✅ Index created")
        except sqlite3.OperationalError as e:
            if "already exists" not in str(e):
                raise
            print("  ✅ Index already exists")
        
        conn.commit()
        print("✅ Migration completed successfully")
        
        # Verify the schema
        print("\n📋 New schema:")
        cursor.execute("PRAGMA table_info(analysis_results);")
        for row in cursor.fetchall():
            print(f"  {row[1]}: {row[2]}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

def rollback():
    """Rollback the migration (SQLite doesn't support DROP COLUMN easily)"""
    print("⚠️  Warning: SQLite doesn't support DROP COLUMN easily.")
    print("   To rollback, you would need to:")
    print("   1. Create new table without status/updated_at columns")
    print("   2. Copy data from old table")
    print("   3. Drop old table")
    print("   4. Rename new table")
    print("\n   Consider keeping a backup before migrations!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback()
    else:
        migrate()
