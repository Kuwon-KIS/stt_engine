#!/usr/bin/env python
"""
데이터베이스 초기화 스크립트
"""
import sys
import os
sys.path.insert(0, '.')

# 이전 데이터베이스 삭제
if os.path.exists('app/database.db'):
    os.remove('app/database.db')
    print("✅ 이전 데이터베이스 삭제됨")

# 모든 모델을 명시적으로 임포트
from app.models.database import Base, Employee, FileUpload, AnalysisJob, AnalysisResult, AnalysisProgress
from app.utils.db import engine, SessionLocal

print("새로운 데이터베이스 생성 중...")
Base.metadata.create_all(bind=engine)
print("✅ 새로운 데이터베이스 생성됨")

# 테스트 데이터 추가
db = SessionLocal()

# 기본 테스트 사용자 추가 (이미 있으면 무시)
for emp_id, name in [("100001", "테스트1"), ("100002", "테스트2"), ("100003", "테스트3")]:
    existing = db.query(Employee).filter_by(emp_id=emp_id).first()
    if not existing:
        test_emp = Employee(emp_id=emp_id, name=name, dept="테스트팀")
        db.add(test_emp)
        print(f"✅ {name} 추가됨")
    else:
        print(f"✅ {name} 이미 존재함")

db.commit()

# 스키마 확인
import sqlite3
conn = sqlite3.connect('app/database.db')
cursor = conn.cursor()

print("\n=== 생성된 테이블 목록 ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"  {table[0]}")

print("\n=== analysis_jobs 테이블 칼럼 ===")
cursor.execute("PRAGMA table_info(analysis_jobs)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]:20} {col[2]}")

has_files_hash = any(col[1] == 'files_hash' for col in columns)
print(f"\n{'✅' if has_files_hash else '❌'} files_hash column exists: {has_files_hash}")

conn.close()
db.close()
