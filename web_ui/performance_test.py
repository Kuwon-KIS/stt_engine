#!/usr/bin/env python
"""
성능 측정 스크립트
분석 이력 조회, 진행률 조회, 결과 조회 성능 측정
"""

import time
import json
import sys
import os

# 경로 설정
sys.path.insert(0, os.path.dirname(__file__))

from app.utils.db import SessionLocal
from app.services.analysis_service import AnalysisService
from app.models.database import AnalysisJob, AnalysisResult, Employee

def format_time(seconds):
    """시간을 읽기 좋은 형식으로 변환"""
    if seconds < 0.001:
        return f"{seconds*1000000:.1f} µs"
    elif seconds < 1:
        return f"{seconds*1000:.2f} ms"
    else:
        return f"{seconds:.2f} s"

def measure_query_count(db):
    """데이터베이스 쿼리 개수 측정"""
    from sqlalchemy import event
    
    query_count = 0
    
    def count_queries(conn, cursor, statement, parameters, context, executemany):
        nonlocal query_count
        query_count += 1
    
    listener_id = event.listens_for(db.bind, "before_cursor_execute")(count_queries)
    
    return listener_id, lambda: query_count

def test_analysis_history():
    """분석 이력 조회 성능 측정"""
    print("\n" + "="*60)
    print("🔍 TEST 1: 분석 이력 조회 (get_analysis_history)")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # 테스트용 emp_id 조회
        emp = db.query(Employee).first()
        if not emp:
            print("⚠️  테스트용 직원 데이터가 없습니다.")
            return
        
        emp_id = emp.emp_id
        print(f"✓ 테스트 emp_id: {emp_id}")
        
        # 분석 이력 개수 확인
        job_count = db.query(AnalysisJob).filter(AnalysisJob.emp_id == emp_id).count()
        print(f"✓ 분석 이력 개수: {job_count}개")
        
        # 성능 측정
        start = time.time()
        result = AnalysisService.get_analysis_history(emp_id, None, db)
        elapsed = time.time() - start
        
        print(f"\n📊 성능 결과:")
        print(f"  - 응답 시간: {format_time(elapsed)}")
        print(f"  - 반환된 이력 개수: {result.get('count', 0)}개")
        
        # 응답 크기 추정
        json_size = len(json.dumps(result)) / 1024
        print(f"  - 응답 데이터 크기: {json_size:.2f} KB")
        
        # 성능 평가
        if elapsed < 0.1:
            print(f"  ✅ GOOD: {elapsed:.3f}s (< 100ms)")
        elif elapsed < 0.5:
            print(f"  ⚠️  FAIR: {elapsed:.3f}s (100ms ~ 500ms)")
        else:
            print(f"  ❌ SLOW: {elapsed:.3f}s (> 500ms)")
            
    finally:
        db.close()

def test_get_progress():
    """진행률 조회 성능 측정"""
    print("\n" + "="*60)
    print("🔍 TEST 2: 진행률 조회 (get_progress)")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # 최근 분석 작업 조회
        job = db.query(AnalysisJob).order_by(AnalysisJob.created_at.desc()).first()
        
        if not job:
            print("⚠️  테스트용 분석 작업이 없습니다.")
            return
        
        print(f"✓ 테스트 job_id: {job.job_id}")
        print(f"✓ 폴더: {job.folder_path}")
        print(f"✓ 파일 개수: {len(job.file_ids) if job.file_ids else 0}개")
        
        # 결과 개수 확인
        result_count = db.query(AnalysisResult).filter(
            AnalysisResult.job_id == job.job_id
        ).count()
        print(f"✓ 분석 결과 개수: {result_count}개")
        
        # 성능 측정
        start = time.time()
        progress = AnalysisService.get_progress(job.job_id, job.emp_id, db)
        elapsed = time.time() - start
        
        print(f"\n📊 성능 결과:")
        print(f"  - 응답 시간: {format_time(elapsed)}")
        print(f"  - 진행률: {progress.progress}%")
        print(f"  - 처리된 파일: {progress.processed_files}/{progress.total_files}")
        
        # 응답 크기 추정
        json_size = len(json.dumps(progress.dict(), default=str)) / 1024
        print(f"  - 응답 데이터 크기: {json_size:.2f} KB")
        
        # 성능 평가
        if elapsed < 0.2:
            print(f"  ✅ GOOD: {elapsed:.3f}s (< 200ms)")
        elif elapsed < 1.0:
            print(f"  ⚠️  FAIR: {elapsed:.3f}s (200ms ~ 1s)")
        else:
            print(f"  ❌ SLOW: {elapsed:.3f}s (> 1s)")
            
    finally:
        db.close()

def test_get_results():
    """분석 결과 조회 성능 측정"""
    print("\n" + "="*60)
    print("🔍 TEST 3: 분석 결과 조회 (get_results)")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # 최근 분석 작업 조회
        job = db.query(AnalysisJob).order_by(AnalysisJob.created_at.desc()).first()
        
        if not job:
            print("⚠️  테스트용 분석 작업이 없습니다.")
            return
        
        print(f"✓ 테스트 job_id: {job.job_id}")
        
        # 성능 측정
        start = time.time()
        results = AnalysisService.get_results(job.job_id, job.emp_id, db)
        elapsed = time.time() - start
        
        print(f"\n📊 성능 결과:")
        print(f"  - 응답 시간: {format_time(elapsed)}")
        print(f"  - 반환된 결과 개수: {len(results.results)}개")
        
        # 응답 크기 추정
        json_size = len(json.dumps(results.dict(), default=str)) / 1024
        print(f"  - 응답 데이터 크기: {json_size:.2f} KB")
        
        # 성능 평가
        if elapsed < 0.2:
            print(f"  ✅ GOOD: {elapsed:.3f}s (< 200ms)")
        elif elapsed < 1.0:
            print(f"  ⚠️  FAIR: {elapsed:.3f}s (200ms ~ 1s)")
        else:
            print(f"  ❌ SLOW: {elapsed:.3f}s (> 1s)")
            
    finally:
        db.close()

def test_database_stats():
    """데이터베이스 통계"""
    print("\n" + "="*60)
    print("📊 데이터베이스 통계")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        employee_count = db.query(Employee).count()
        job_count = db.query(AnalysisJob).count()
        result_count = db.query(AnalysisResult).count()
        
        print(f"✓ 직원 수: {employee_count}명")
        print(f"✓ 분석 작업 수: {job_count}개")
        print(f"✓ 분석 결과 수: {result_count}개")
        
        if job_count > 0:
            avg_results = result_count / job_count
            print(f"✓ 작업당 평균 결과 수: {avg_results:.1f}개")
            
    finally:
        db.close()

def main():
    """메인 함수"""
    print("\n" + "🚀 성능 측정 시작".center(60, "="))
    
    # 데이터베이스 통계
    test_database_stats()
    
    # 성능 테스트
    try:
        test_analysis_history()
    except Exception as e:
        print(f"❌ 분석 이력 조회 테스트 실패: {e}")
    
    try:
        test_get_progress()
    except Exception as e:
        print(f"❌ 진행률 조회 테스트 실패: {e}")
    
    try:
        test_get_results()
    except Exception as e:
        print(f"❌ 결과 조회 테스트 실패: {e}")
    
    print("\n" + "✅ 성능 측정 완료".center(60, "=") + "\n")

if __name__ == "__main__":
    main()
