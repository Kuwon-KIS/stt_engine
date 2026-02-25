#!/usr/bin/env python3
"""
DB Migration: Add user quota and admin features
- Adds storage_quota, storage_used, is_admin columns to employees table
- Creates admin user account
- Calculates existing storage usage
"""

import sqlite3
import os
from datetime import datetime
import shutil

DB_PATH = 'app/database.db'

def backup_db():
    """Create database backup before migration"""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        return None
    
    backup_name = f'{DB_PATH}.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    shutil.copy(DB_PATH, backup_name)
    print(f"✅ Backup created: {backup_name}")
    return backup_name

def check_columns_exist(cursor):
    """Check if migration columns already exist"""
    cursor.execute("PRAGMA table_info(employees)")
    cols = [col[1] for col in cursor.fetchall()]
    
    return {
        'storage_quota': 'storage_quota' in cols,
        'storage_used': 'storage_used' in cols,
        'is_admin': 'is_admin' in cols
    }

def migrate():
    """Execute migration"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check existing columns
        existing = check_columns_exist(cursor)
        
        print("\n=== Migration Status ===")
        print(f"storage_quota: {'✓ Already exists' if existing['storage_quota'] else '✗ Will be added'}")
        print(f"storage_used: {'✓ Already exists' if existing['storage_used'] else '✗ Will be added'}")
        print(f"is_admin: {'✓ Already exists' if existing['is_admin'] else '✗ Will be added'}")
        print()
        
        # Add new columns if they don't exist
        if not existing['storage_quota']:
            print("Adding storage_quota column...")
            cursor.execute("ALTER TABLE employees ADD COLUMN storage_quota INTEGER DEFAULT 42949672960")
            print("✅ storage_quota added (default: 40GB)")
        
        if not existing['storage_used']:
            print("Adding storage_used column...")
            cursor.execute("ALTER TABLE employees ADD COLUMN storage_used INTEGER DEFAULT 0")
            print("✅ storage_used added")
        
        if not existing['is_admin']:
            print("Adding is_admin column...")
            cursor.execute("ALTER TABLE employees ADD COLUMN is_admin INTEGER DEFAULT 0")
            print("✅ is_admin added")
        
        conn.commit()
        
        # Calculate existing storage usage
        print("\nCalculating existing storage usage...")
        cursor.execute("""
            UPDATE employees 
            SET storage_used = (
                SELECT COALESCE(SUM(file_size_mb * 1024 * 1024), 0)
                FROM file_uploads 
                WHERE file_uploads.emp_id = employees.emp_id
            )
        """)
        conn.commit()
        print("✅ Storage usage calculated")
        
        # Create or update admin user
        print("\nSetting up admin user...")
        cursor.execute("SELECT emp_id FROM employees WHERE emp_id = '999999'")
        admin_exists = cursor.fetchone()
        
        if admin_exists:
            # Update existing user to admin
            cursor.execute("""
                UPDATE employees 
                SET is_admin = 1, name = 'System Admin', dept = 'IT'
                WHERE emp_id = '999999'
            """)
            print("✅ Updated existing user 999999 to admin")
        else:
            # Create new admin user
            cursor.execute("""
                INSERT INTO employees (emp_id, name, dept, is_admin, storage_quota, storage_used) 
                VALUES ('999999', 'System Admin', 'IT', 1, 42949672960, 0)
            """)
            print("✅ Created admin user (emp_id: 999999)")
        
        conn.commit()
        
        # Verification
        print("\n=== Verification ===")
        cursor.execute("PRAGMA table_info(employees)")
        cols = cursor.fetchall()
        
        print("Current employees table columns:")
        for col in cols:
            col_name = col[1]
            col_type = col[2]
            print(f"  - {col_name:20} {col_type}")
        
        # Check if all columns exist
        col_names = [col[1] for col in cols]
        assert 'storage_quota' in col_names, "storage_quota column missing!"
        assert 'storage_used' in col_names, "storage_used column missing!"
        assert 'is_admin' in col_names, "is_admin column missing!"
        
        # Show current users
        print("\nCurrent users:")
        cursor.execute("""
            SELECT emp_id, name, dept, 
                   storage_used / (1024.0 * 1024.0 * 1024.0) as used_gb,
                   storage_quota / (1024.0 * 1024.0 * 1024.0) as quota_gb,
                   is_admin
            FROM employees
        """)
        
        for row in cursor.fetchall():
            admin_badge = " 👑" if row[5] else ""
            print(f"  - {row[0]}: {row[1]} ({row[2]}) - {row[3]:.2f}GB / {row[4]:.0f}GB{admin_badge}")
        
        print("\n✅ Migration completed successfully!")
        
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            print("⚠️ Admin user already exists, updating...")
            cursor.execute("""
                UPDATE employees 
                SET is_admin = 1 
                WHERE emp_id = '999999'
            """)
            conn.commit()
            print("✅ Admin user updated")
        else:
            print(f"❌ Integrity Error: {e}")
            conn.rollback()
            raise
    
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("DB MIGRATION: User Quota & Admin Features")
    print("=" * 50)
    
    backup_file = backup_db()
    
    if backup_file:
        print(f"\n⚠️  Backup created. If anything goes wrong, restore with:")
        print(f"   cp {backup_file} {DB_PATH}")
        print()
    
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED!")
        print(f"Error: {e}")
        if backup_file:
            print(f"\nTo rollback, run:")
            print(f"  cp {backup_file} {DB_PATH}")
        exit(1)
