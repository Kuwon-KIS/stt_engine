import os
import sqlite3

db_path = 'data/db.sqlite'
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('CREATE TABLE employees (id INTEGER PRIMARY KEY,emp_id VARCHAR(10) UNIQUE NOT NULL,name VARCHAR(100),dept VARCHAR(100),created_at DATETIME DEFAULT CURRENT_TIMESTAMP,last_login DATETIME)')
cursor.execute('CREATE TABLE analysis_jobs (id INTEGER PRIMARY KEY,job_id VARCHAR(50) UNIQUE NOT NULL,emp_id VARCHAR(10) NOT NULL,folder_path VARCHAR(500) NOT NULL,file_ids JSON,files_hash VARCHAR(64),status VARCHAR(20) DEFAULT "pending",options JSON,created_at DATETIME DEFAULT CURRENT_TIMESTAMP,started_at DATETIME,completed_at DATETIME,FOREIGN KEY(emp_id) REFERENCES employees(emp_id))')
cursor.execute('CREATE TABLE analysis_results (id INTEGER PRIMARY KEY,job_id VARCHAR(50) NOT NULL,file_id VARCHAR(500) NOT NULL,stt_text TEXT,stt_metadata JSON,classification_code VARCHAR(20),privacy_result JSON,created_at DATETIME DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(job_id) REFERENCES analysis_jobs(job_id))')
cursor.execute('CREATE TABLE analysis_progress (id INTEGER PRIMARY KEY,job_id VARCHAR(50) UNIQUE NOT NULL,total_files INTEGER DEFAULT 0,processed_files INTEGER DEFAULT 0,current_file VARCHAR(500),status VARCHAR(20) DEFAULT "pending",created_at DATETIME DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(job_id) REFERENCES analysis_jobs(job_id))')
cursor.execute('CREATE TABLE file_uploads (id INTEGER PRIMARY KEY,emp_id VARCHAR(10) NOT NULL,folder_path VARCHAR(500) NOT NULL,filename VARCHAR(500) NOT NULL,file_size_mb REAL,uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(emp_id) REFERENCES employees(emp_id))')

cursor.execute("INSERT INTO employees (emp_id,name,dept) VALUES (?,?,?)", ("100001","김철수","영업팀"))
conn.commit()

cursor.execute("PRAGMA table_info(analysis_jobs)")
cols = cursor.fetchall()
has_hash = any(c[1] == 'files_hash' for c in cols)
print(f"✅ DB created: {db_path}")
print(f"✅ files_hash: {has_hash}")

conn.close()
