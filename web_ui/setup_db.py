#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
SQLAlchemy ORM 모델을 사용하여 최신 스키마로 DB 생성
"""
import os
from pathlib import Path
from app.utils.db import Base, engine, SessionLocal
from app.models.database import Employee, FileUpload, AnalysisJob, AnalysisResult, AnalysisProgress
from config import DB_PATH

def main():
    # 이전 DB 완전 삭제
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print(f"✅ 이전 데이터베이스 삭제: {DB_PATH}")
    
    # SQLAlchemy를 사용하여 모든 테이블 생성
    Base.metadata.create_all(engine)
    print("✅ 모든 테이블 생성 완료 (SQLAlchemy ORM)")
    
    # 테이블 구조 확인
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    print("\n=== 생성된 테이블 목록 ===")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  📋 {table[0]}")
    
    print("\n=== analysis_results 스키마 ===")
    cursor.execute("PRAGMA table_info(analysis_results);")
    cols = cursor.fetchall()
    for col in cols[:5]:  # 처음 5개만 표시
        print(f"  {col[1]:30} {col[2]:15}")
    print(f"  ... ({len(cols)} 컬럼 total)")
    
    conn.close()
    
    # 기본 테스트 사용자 추가
    db = SessionLocal()
    try:
        # 테스트 사용자 3명 (100001-100003)
        test_users = [
            Employee(emp_id='100001', name='테스트1', dept='영업부', is_admin=0, storage_quota=5368709120),
            Employee(emp_id='100002', name='테스트2', dept='IT부', is_admin=0, storage_quota=5368709120),
            Employee(emp_id='100003', name='테스트3', dept='마케팅부', is_admin=0, storage_quota=5368709120)
        ]
        db.add_all(test_users)
        db.commit()
        print("\n✅ 기본 테스트 사용자 3명 추가 (100001-100003)")
        print("   - 100001 (영업부): 테스트1")
        print("   - 100002 (IT부): 테스트2")
        print("   - 100003 (마케팅부): 테스트3")
        print("   ※ 관리자는 별도 관리 페이지에서 패스워드로 접근")
    except Exception as e:
        print(f"\n⚠️  사용자 추가 실패 (이미 존재할 수 있음): {e}")
        db.rollback()
    finally:
        db.close()
    
    print("\n✅ 데이터베이스 초기화 완료!")

if __name__ == "__main__":
    main()

