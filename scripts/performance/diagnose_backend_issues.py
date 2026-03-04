#!/usr/bin/env python
"""
백엔드 성능 문제 진단 스크립트
N+1 쿼리, 메모리 사용, 직렬화 오버헤드 측정

사용 방법:
  python diagnose_backend_issues.py
"""

import sys
import os
import time
import json
from pathlib import Path
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Docker 환경: /app 기준, 로컬 개발: 상대 경로
if Path("/app").exists():
    WEB_UI_ROOT = Path("/app")
    sys.path.insert(0, "/app")
else:
    SCRIPT_DIR = Path(__file__).parent
    WEB_UI_ROOT = SCRIPT_DIR.parent.parent / "web_ui"
    sys.path.insert(0, str(WEB_UI_ROOT))

# 의존성 임포트
try:
    from app.utils.db import SessionLocal, engine
    from app.services.analysis_service import AnalysisService
    from app.models.database import AnalysisJob, AnalysisResult, Employee
except ImportError as e:
    print(f"❌ 필요한 모듈을 임포트할 수 없습니다: {e}")
    sys.exit(1)

# ============================================================================
# SQLAlchemy 쿼리 추적
# ============================================================================

query_log = []

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """SQL 쿼리 추적"""
    global query_log
    query_log.append({
        'sql': statement[:100],  # 처음 100자만
        'params': str(parameters)[:50]
    })

def print_query_log():
    """쿼리 로그 출력"""
    if not query_log:
        return
    
    print(f"\n📊 실행된 SQL 쿼리 ({len(query_log)}개):")
    
    # 쿼리 유형별 분류
    select_count = sum(1 for q in query_log if 'SELECT' in q['sql'].upper())
    insert_count = sum(1 for q in query_log if 'INSERT' in q['sql'].upper())
    update_count = sum(1 for q in query_log if 'UPDATE' in q['sql'].upper())
    
    print(f"  - SELECT: {select_count}개")
    print(f"  - INSERT: {insert_count}개")
    print(f"  - UPDATE: {update_count}개")
    
    # N+1 패턴 감지
    if select_count > 10:
        print(f"  ⚠️  SELECT 쿼리가 많음 ({select_count}개) → N+1 패턴 가능성")
    
    # 상세 쿼리 목록
    print(f"\n📝 상세 쿼리:")
    for i, q in enumerate(query_log[:20], 1):  # 처음 20개만
        print(f"  [{i:2d}] {q['sql']}...")
    
    if len(query_log) > 20:
        print(f"  ... 외 {len(query_log) - 20}개")

# ============================================================================
# 진단 함수
# ============================================================================

def diagnose_n_plus_one():
    """N+1 쿼리 문제 진단"""
    print("\n" + "="*70)
    print("1️⃣  N+1 쿼리 문제 진단")
    print("="*70)
    
    global query_log
    query_log = []
    
    db = SessionLocal()
    
    try:
        # 직원별 job count를 구하는 로직 (현재 구현)
        print("\n🔍 현재 구현 방식 (N+1 문제 가능성):")
        
        emp_with_most_jobs = db.query(Employee).all()
        print(f"  1. 모든 직원 조회: {len(emp_with_most_jobs)}개")
        
        emp_job_counts = {}
        for emp in emp_with_most_jobs:
            # 각 직원마다 별도 쿼리
            count = db.query(AnalysisJob).filter(AnalysisJob.emp_id == emp.emp_id).count()
            emp_job_counts[emp.emp_id] = count
        
        print(f"  2. 각 직원별 job count 쿼리: {len(emp_with_most_jobs)}개")
        print(f"\n  ⚠️  총 쿼리: 1 + {len(emp_with_most_jobs)} = {len(query_log)}개")
        
        print_query_log()
        
        # 개선된 방식 (단일 쿼리)
        print("\n" + "-"*70)
        print("🚀 개선된 구현 방식 (단일 쿼리):")
        
        query_log = []
        
        from sqlalchemy import func
        
        job_counts = db.query(
            AnalysisJob.emp_id,
            func.count(AnalysisJob.job_id).label('count')
        ).group_by(AnalysisJob.emp_id).all()
        
        print(f"  1. GROUP BY를 사용한 단일 쿼리: {len(job_counts)}개 결과")
        print(f"\n  ✅ 총 쿼리: {len(query_log)}개")
        
        print_query_log()
        
        print("\n" + "-"*70)
        print("📊 비교:")
        print(f"  현재 방식: {len(emp_with_most_jobs) + 1}개 쿼리")
        print(f"  개선 방식: 1개 쿼리")
        print(f"  ✅ 개선 효과: {len(emp_with_most_jobs)}개 쿼리 제거 ({(len(emp_with_most_jobs) / (len(emp_with_most_jobs) + 1) * 100):.1f}% 감소)")
        
    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def diagnose_memory_usage():
    """메모리 오버헤드 진단"""
    print("\n" + "="*70)
    print("2️⃣  메모리 사용량 진단")
    print("="*70)
    
    import sys
    
    db = SessionLocal()
    
    try:
        # 최근 5개 job 찾기
        jobs = db.query(AnalysisJob).order_by(
            AnalysisJob.created_at.desc()
        ).limit(5).all()
        
        if not jobs:
            print("⚠️  테스트용 job이 없습니다.")
            return
        
        print(f"\n🔍 최근 {len(jobs)}개 job의 결과 로드 비용 분석:")
        
        for i, job in enumerate(jobs, 1):
            results = db.query(AnalysisResult).filter(
                AnalysisResult.job_id == job.job_id
            ).all()
            
            # 메모리 크기 추정
            total_size = sum(sys.getsizeof(r) for r in results)
            
            # JSON 직렬화 오버헤드 (ORM 객체를 딕셔너리로 변환)
            results_dict = [
                {
                    'id': r.id,
                    'job_id': r.job_id,
                    'file_id': r.file_id,
                    'stt_text': r.stt_text if hasattr(r, 'stt_text') else '',
                }
                for r in results
            ]
            json_str = json.dumps(results_dict, default=str)
            json_size = len(json_str.encode('utf-8'))
            
            print(f"\n  [{i}] job_id={job.job_id[:8]}... 결과 {len(results)}개")
            print(f"      - 객체 메모리: {total_size / 1024:.2f}KB")
            print(f"      - JSON 크기: {json_size / 1024:.2f}KB")
            
            if len(results) > 500:
                print(f"      ⚠️  결과가 많음 → 모든 필드 로드 시 메모리 낭비")
            
            if json_size > 1024 * 1024:
                print(f"      ❌ JSON이 1MB 초과 → 네트워크 전송 느림")
        
        print(f"\n💡 개선 방안:")
        print(f"  1. LIMIT 추가: 페이지당 50-100개만 로드")
        print(f"  2. 필드 선택: SELECT 필요한 칼럼만")
        print(f"  3. Pagination: offset/limit 사용")
        
    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def diagnose_unnecessary_data():
    """불필요한 데이터 전송 진단"""
    print("\n" + "="*70)
    print("3️⃣  불필요한 데이터 전송 진단")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        results = db.query(AnalysisResult).limit(5).all()
        
        if not results:
            print("⚠️  테스트용 결과가 없습니다.")
            return
        
        print(f"\n🔍 AnalysisResult 필드 분석:")
        
        if results:
            result = results[0]
            
            print(f"\n  주요 필드:")
            # ORM 모델의 실제 칼럼만 확인
            important_fields = ['id', 'job_id', 'file_id', 'stt_text', 'stt_metadata', 'created_at', 'updated_at']
            for field_name in important_fields:
                if hasattr(result, field_name):
                    try:
                        value = getattr(result, field_name, None)
                        if value is not None:
                            value_str = str(value)[:50]
                            print(f"    - {field_name}: {value_str}...")
                    except:
                        pass
            
            # JSON 직렬화 시 크기 (모든 속성을 딕셔너리로 변환)
            from sqlalchemy.inspection import inspect as sa_inspect
            mapper = sa_inspect(type(result))
            full_data = {col.name: getattr(result, col.name) for col in mapper.columns}
            full_json = json.dumps(full_data, default=str)
            full_size = len(full_json.encode('utf-8'))
            
            # 필수 필드만 선택
            minimal_data = {
                'id': result.id,
                'job_id': result.job_id,
                'file_id': result.file_id,
                'stt_text': result.stt_text if hasattr(result, 'stt_text') else '',
            }
            minimal_json = json.dumps(minimal_data, default=str)
            minimal_size = len(minimal_json.encode('utf-8'))
            
            print(f"\n  📊 크기 비교 (1개 결과):")
            print(f"    - 전체 필드: {full_size}B")
            print(f"    - 필수 필드만: {minimal_size}B")
            print(f"    - 절약 가능: {full_size - minimal_size}B ({(1 - minimal_size/full_size)*100:.1f}%)")
            
            if len(results) >= 100:
                print(f"\n  100개 결과 기준:")
                print(f"    - 전체 필드: {(full_size * 100) / 1024:.2f}KB")
                print(f"    - 필수 필드만: {(minimal_size * 100) / 1024:.2f}KB")
                print(f"    - 절약 가능: {((full_size - minimal_size) * 100) / 1024:.2f}KB")
            
            print(f"\n  💡 개선 방안:")
            print(f"  1. API 응답에서 필수 필드만 반환")
            print(f"  2. 선택적 필드 (상세 메타데이터)는 별도 API로 분리")
            print(f"  3. stt_metadata, improper_detection_results 같은 큰 필드는 요청 시만 로드")
        
    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def diagnose_serialization():
    """JSON 직렬화 오버헤드 진단"""
    print("\n" + "="*70)
    print("4️⃣  JSON 직렬화 성능 진단")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        results = db.query(AnalysisResult).limit(10).all()
        
        if not results:
            print("⚠️  테스트용 결과가 없습니다.")
            return
        
        print(f"\n🔍 {len(results)}개 결과 직렬화 성능:")
        
        # 방법 1: 전체 필드 변환
        start = time.time()
        from sqlalchemy.inspection import inspect as sa_inspect
        mapper = sa_inspect(type(results[0]))
        for _ in range(10):
            data = [{col.name: getattr(r, col.name) for col in mapper.columns} for r in results]
            json.dumps(data, default=str)
        time_full = (time.time() - start) / 10
        
        # 방법 2: 필드 선택 (최소화)
        start = time.time()
        for _ in range(10):
            data = [
                {
                    'id': r.id,
                    'job_id': r.job_id,
                    'stt_text': r.stt_text if hasattr(r, 'stt_text') else '',
                }
                for r in results
            ]
            json.dumps(data, default=str)
        time_minimal = (time.time() - start) / 10
        
        print(f"\n  전체 필드 → JSON: {time_full*1000:.2f}ms")
        print(f"  필수 필드만 → JSON: {time_minimal*1000:.2f}ms")
        if time_full > 0:
            print(f"  개선 효과: {((time_full - time_minimal) / time_full * 100):.1f}% 빠름")
        
    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def diagnose_backend():
    """백엔드 진단 실행 (다른 스크립트에서 호출 가능)"""
    diagnose_n_plus_one()
    diagnose_memory_usage()
    diagnose_unnecessary_data()
    diagnose_serialization()
    
    print("\n" + "="*70)
    print("📋 종합 분석 결과")
    print("="*70)
    print("""
✅ 각 문제별 우선순위:
  1. ⚠️  N+1 쿼리 → 가장 영향 큼, GROUP BY로 쉽게 해결
  2. ⚠️  응답 데이터 크기 → API pagination으로 해결
  3. ⚠️  불필요한 필드 → 응답 필드 선택으로 해결
  4. ⚠️  메모리 사용 → LIMIT으로 해결

📌 즉시 개선 가능 항목:
  - get_analysis_history() GROUP BY 개선
  - API 응답 필드 최적화
  - Pagination 추가
""")

if __name__ == "__main__":
    diagnose_backend()
