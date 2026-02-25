#!/usr/bin/env python3
"""
데이터베이스 초기화 및 마이그레이션 스크립트
서버 시작 전에 실행되어야 함
"""

import sys
import os
import sqlite3
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent))

def initialize_database():
    """데이터베이스 초기화 및 모든 마이그레이션 적용"""
    
    print("=" * 60)
    print("데이터베이스 초기화 시작")
    print("=" * 60)
    
    # 1단계: ORM을 통해 모든 테이블 생성
    print("\n[1/3] ORM을 통해 테이블 생성 중...")
    try:
        from app.utils.db import engine
        from app.models.database import Base
        
        Base.metadata.create_all(engine)
        print("✅ 모든 테이블 생성 완료")
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
        return False
    
    # DB 경로를 engine URL에서 추출
    db_path = None
    try:
        # engine.url은 "sqlite:////app/data/database.db" 형태
        url_string = str(engine.url)
        if "sqlite:///" in url_string:
            # sqlite:////path/to/db.db -> /path/to/db.db (3개 슬래시 제거, 마지막 1개는 루트)
            db_path = Path(url_string.replace("sqlite:///", ""))
        elif "sqlite://" in url_string:
            db_path = Path(url_string.replace("sqlite://", ""))
        
        if db_path and db_path.exists():
            print(f"✅ Engine URL에서 DB 경로 감지: {db_path}")
        else:
            # engine URL에서 경로를 추출했지만 파일이 없다면, 직접 생성됨
            if db_path:
                print(f"✅ Engine이 생성할 DB 경로: {db_path}")
            else:
                raise Exception("DB 경로를 추출할 수 없음")
    except Exception as e:
        print(f"⚠️  Engine URL 파싱 실패, 대체 방법 사용: {e}")
        # 대체 경로들 시도
        db_paths = [
            Path("/app/data/database.db"),  # Docker
            Path("data/database.db"),        # 로컬
            Path("app/database.db"),         # 로컬 fallback
        ]
        
        for path in db_paths:
            if path.exists():
                db_path = path
                print(f"✅ 기존 DB 파일 발견: {db_path}")
                break
    
    if not db_path:
        print(f"❌ 데이터베이스 파일을 찾을 수 없음")
        return False
    
    print(f"📁 DB 파일 위치: {db_path}")
    
    # 2단계: storage_quota 마이그레이션
    print("\n[2/3] User Quota & Admin Features 마이그레이션 중...")
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 기존 컬럼 확인
        cursor.execute("PRAGMA table_info(employees)")
        columns = [col[1] for col in cursor.fetchall()]
        
        migrations_applied = []
        
        # storage_quota 추가
        if 'storage_quota' not in columns:
            cursor.execute("ALTER TABLE employees ADD COLUMN storage_quota INTEGER DEFAULT 42949672960")  # 40GB
            migrations_applied.append("storage_quota")
            print("  ✅ storage_quota 컬럼 추가")
        else:
            print("  ℹ️  storage_quota 이미 존재")
        
        # storage_used 추가
        if 'storage_used' not in columns:
            cursor.execute("ALTER TABLE employees ADD COLUMN storage_used INTEGER DEFAULT 0")
            migrations_applied.append("storage_used")
            print("  ✅ storage_used 컬럼 추가")
        else:
            print("  ℹ️  storage_used 이미 존재")
        
        # is_admin 추가
        if 'is_admin' not in columns:
            cursor.execute("ALTER TABLE employees ADD COLUMN is_admin INTEGER DEFAULT 0")
            migrations_applied.append("is_admin")
            print("  ✅ is_admin 컬럼 추가")
        else:
            print("  ℹ️  is_admin 이미 존재")
        
        conn.commit()
        conn.close()
        
        if migrations_applied:
            print(f"✅ 마이그레이션 적용 완료: {', '.join(migrations_applied)}")
        else:
            print("✅ 모든 컬럼이 이미 존재합니다")
        
    except sqlite3.OperationalError as e:
        print(f"❌ 마이그레이션 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False
    
    # 3단계: analysis_results 마이그레이션
    print("\n[3/3] Analysis Results Status 마이그레이션 중...")
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(analysis_results)")
        columns = [col[1] for col in cursor.fetchall()]
        
        migrations_applied = []
        
        # status 추가
        if 'status' not in columns:
            cursor.execute("ALTER TABLE analysis_results ADD COLUMN status TEXT DEFAULT 'pending'")
            migrations_applied.append("status")
            print("  ✅ status 컬럼 추가")
        else:
            print("  ℹ️  status 이미 존재")
        
        # updated_at 추가
        if 'updated_at' not in columns:
            cursor.execute("ALTER TABLE analysis_results ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            migrations_applied.append("updated_at")
            print("  ✅ updated_at 컬럼 추가")
        else:
            print("  ℹ️  updated_at 이미 존재")
        
        conn.commit()
        conn.close()
        
        if migrations_applied:
            print(f"✅ 마이그레이션 적용 완료: {', '.join(migrations_applied)}")
        else:
            print("✅ 모든 컬럼이 이미 존재합니다")
        
    except sqlite3.OperationalError as e:
        print(f"❌ 마이그레이션 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 데이터베이스 초기화 완료!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = initialize_database()
    sys.exit(0 if success else 1)
