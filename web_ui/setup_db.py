#!/usr/bin/env python
import os
import sqlite3

# 이전 DB 삭제
if os.path.exists('app/database.db'):
    os.remove('app/database.db')
    print("✅ 이전 데이터베이스 삭제")

# SQLite DB 생성
conn = sqlite3.connect('app/database.db')
cursor = conn.cursor()

# employees 테이블
cursor.execute('''CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    dept VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
)''')

# analysis_jobs 테이블 (files_hash 포함)
cursor.execute('''CREATE TABLE analysis_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(50) UNIQUE NOT NULL,
    emp_id VARCHAR(10) NOT NULL,
    folder_path VARCHAR(500) NOT NULL,
    file_ids JSON,
    files_hash VARCHAR(64),
    status VARCHAR(20) DEFAULT "pending",
    options JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    FOREIGN KEY(emp_id) REFERENCES employees(emp_id)
)''')

# analysis_results 테이블
cursor.execute('''CREATE TABLE analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(50) NOT NULL,
    file_id VARCHAR(500) NOT NULL,
    stt_text TEXT,
    stt_metadata JSON,
    classification_code VARCHAR(20),
    privacy_result JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES analysis_jobs(job_id)
)''')

# analysis_progress 테이블
cursor.execute('''CREATE TABLE analysis_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(50) UNIQUE NOT NULL,
    total_files INTEGER DEFAULT 0,
    processed_files INTEGER DEFAULT 0,
    current_file VARCHAR(500),
    status VARCHAR(20) DEFAULT "pending",
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES analysis_jobs(job_id)
)''')

# file_uploads 테이블
cursor.execute('''CREATE TABLE file_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id VARCHAR(10) NOT NULL,
    folder_path VARCHAR(500) NOT NULL,
    filename VARCHAR(500) NOT NULL,
    file_size_mb REAL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(emp_id) REFERENCES employees(emp_id)
)''')

conn.commit()

# 기본 테스트 사용자 추가
cursor.execute("INSERT INTO employees (emp_id, name, dept) VALUES (?, ?, ?)", ("100001", "테스트1", "테스트팀"))
cursor.execute("INSERT INTO employees (emp_id, name, dept) VALUES (?, ?, ?)", ("100002", "테스트2", "테스트팀"))
cursor.execute("INSERT INTO employees (emp_id, name, dept) VALUES (?, ?, ?)", ("100003", "테스트3", "테스트팀"))
conn.commit()

print("✅ 모든 테이블 생성 완료")
print("✅ 기본 테스트 사용자 3명 추가 (100001-100003)")

# 확인
cursor.execute("PRAGMA table_info(analysis_jobs)")
cols = cursor.fetchall()
print("\n=== analysis_jobs 칼럼 ===")
for col in cols:
    print(f"  {col[1]:20} {col[2]}")

has_files_hash = any(col[1] == 'files_hash' for col in cols)
print(f"\n{'✅' if has_files_hash else '❌'} files_hash: {has_files_hash}")

conn.close()
