#!/usr/bin/env python
"""
분석 페이지 성능 진단 스크립트
API 응답 크기, 렌더링 복잡도, 병목 지점 파악

사용 방법:
  python diagnose_ui_performance.py
"""

import sys
import os
import time
import json
from pathlib import Path

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
    from app.utils.db import SessionLocal
    from app.services.analysis_service import AnalysisService
    from app.models.database import AnalysisJob, AnalysisResult, Employee
except ImportError as e:
    print(f"❌ 필요한 모듈을 임포트할 수 없습니다: {e}")
    sys.exit(1)

def format_size(bytes_size):
    """바이트를 읽기 좋은 형식으로 변환"""
    if bytes_size < 1024:
        return f"{bytes_size}B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.2f}KB"
    else:
        return f"{bytes_size / (1024 * 1024):.2f}MB"

def diagnose_analysis_page():
    """분석 페이지 성능 진단"""
    print("\n" + "="*70)
    print("🔍 분석 페이지 성능 진단")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        # 가장 많은 분석 이력을 가진 직원 찾기
        emp_with_most_jobs = db.query(Employee).all()
        
        if not emp_with_most_jobs:
            print("⚠️  테스트용 직원 데이터가 없습니다.")
            return
        
        # 각 직원별 작업 수 계산
        emp_job_counts = {}
        for emp in emp_with_most_jobs:
            count = db.query(AnalysisJob).filter(AnalysisJob.emp_id == emp.emp_id).count()
            emp_job_counts[emp.emp_id] = count
        
        if not any(emp_job_counts.values()):
            print("⚠️  분석 이력이 없습니다.")
            return
        
        emp_id = max(emp_job_counts, key=emp_job_counts.get)
        total_jobs = emp_job_counts[emp_id]
        
        print(f"\n📋 테스트 대상: emp_id={emp_id}, 총 분석 작업={total_jobs}개")
        
        # 1️⃣ 분석 이력 조회 (API 호출)
        print("\n" + "-"*70)
        print("1️⃣  API 응답 크기 분석")
        print("-"*70)
        
        start = time.time()
        history = AnalysisService.get_analysis_history(emp_id, None, db)
        api_time = time.time() - start
        
        # JSON 직렬화 크기
        json_str = json.dumps(history, default=str)
        json_size = len(json_str.encode('utf-8'))
        
        print(f"\n✓ API 응답 시간: {api_time*1000:.2f}ms")
        print(f"✓ JSON 직렬화 크기: {format_size(json_size)}")
        print(f"✓ 반환된 작업 수: {history.get('count', 0)}개")
        
        # 성능 평가
        if json_size > 5 * 1024 * 1024:  # 5MB
            print(f"❌ 응답이 너무 큽니다 (> 5MB) - 프론트엔드 렌더링 저하 예상")
        elif json_size > 1 * 1024 * 1024:  # 1MB
            print(f"⚠️  응답이 상당히 큽니다 (> 1MB) - pagination 고려")
        else:
            print(f"✅ 응답 크기 양호")
        
        # 2️⃣ 데이터 분포 분석
        print("\n" + "-"*70)
        print("2️⃣  데이터 분포 분석")
        print("-"*70)
        
        # 분석별 결과 수 분포
        jobs = db.query(AnalysisJob).filter(
            AnalysisJob.emp_id == emp_id
        ).order_by(AnalysisJob.created_at.desc()).limit(10).all()
        
        print(f"\n✓ 최근 10개 분석 작업의 결과 분포:")
        
        max_results = 0
        min_results = float('inf')
        total_results = 0
        
        for i, job in enumerate(jobs, 1):
            result_count = db.query(AnalysisResult).filter(
                AnalysisResult.job_id == job.job_id
            ).count()
            
            total_results += result_count
            max_results = max(max_results, result_count)
            min_results = min(min_results, result_count)
            
            if result_count > 100:
                print(f"  [{i:2d}] job_id={job.job_id[:8]}... 결과={result_count}개 ⚠️  (많음)")
            else:
                print(f"  [{i:2d}] job_id={job.job_id[:8]}... 결과={result_count}개")
        
        avg_results = total_results / len(jobs) if jobs else 0
        
        print(f"\n📊 통계:")
        print(f"  - 평균 결과 수: {avg_results:.1f}개")
        print(f"  - 최소 결과 수: {min_results}개")
        print(f"  - 최대 결과 수: {max_results}개")
        
        # 3️⃣ 병목 지점 식별
        print("\n" + "-"*70)
        print("3️⃣  병목 지점 분석")
        print("-"*70)
        
        bottlenecks = []
        
        # 결과가 많은 경우
        if max_results > 500:
            bottlenecks.append(f"❌ 결과가 많은 작업 있음 ({max_results}개)")
            bottlenecks.append("   → DOM 생성 시 느려질 수 있음 (가상 스크롤 권장)")
        
        # 응답 크기 큰 경우
        if json_size > 1024 * 1024:
            bottlenecks.append(f"❌ 응답 크기 큼 ({format_size(json_size)})")
            bottlenecks.append("   → Pagination 또는 Lazy loading 구현 권장")
        
        # 작업이 많은 경우
        if total_jobs > 100:
            bottlenecks.append(f"❌ 총 분석 작업이 많음 ({total_jobs}개)")
            bottlenecks.append("   → 페이지당 로딩 수 제한 권장")
        
        if bottlenecks:
            for msg in bottlenecks:
                print(f"\n{msg}")
        else:
            print("\n✅ 주요 병목 지점 없음")
        
        # 4️⃣ 성능 개선 권장사항
        print("\n" + "-"*70)
        print("4️⃣  성능 개선 권장사항")
        print("-"*70)
        
        recommendations = []
        
        # 응답 크기 기반
        if json_size > 500 * 1024:
            recommendations.append("📌 [필수] API Pagination 구현")
            recommendations.append("   - 한번에 로드할 최대 레코드 수 제한 (예: 50개)")
            recommendations.append("   - 스크롤 시 다음 페이지 로드 (Lazy loading)")
        
        # 결과 수 기반
        if max_results > 200:
            recommendations.append("\n📌 [필수] 테이블 가상 스크롤 구현")
            recommendations.append("   - DOM 노드 수 제한 (표시되는 것만 렌더링)")
            recommendations.append("   - React Virtual List, Vue Virtual Scroller 등 사용")
        
        # 캐싱
        recommendations.append("\n📌 [권장] 클라이언트 캐싱")
        recommendations.append("   - LocalStorage에 최근 분석 결과 캐싱")
        recommendations.append("   - 같은 job_id 재조회 시 캐시 활용")
        
        # 인덱싱
        recommendations.append("\n📌 [권장] 데이터베이스 인덱싱")
        recommendations.append("   - emp_id + created_at 복합 인덱스")
        recommendations.append("   - job_id 인덱스 확인")
        
        for rec in recommendations:
            print(f"\n{rec}")
        
        # 5️⃣ 프론트엔드 성능 테스트 명령어
        print("\n" + "-"*70)
        print("5️⃣  프론트엔드 성능 측정 방법")
        print("-"*70)
        
        print("\n📝 브라우저 개발자 도구에서 확인하는 방법:")
        print("  1. F12 → Performance 탭 열기")
        print("  2. '이전 분석 보기' 클릭 후 즉시 녹화 시작")
        print("  3. 페이지 완전 로드 후 녹화 중지")
        print("  4. 다음 지표 확인:")
        print("     - FCP (First Contentful Paint): 첫 콘텐츠 표시까지 시간")
        print("     - LCP (Largest Contentful Paint): 가장 큰 콘텐츠 표시까지")
        print("     - CLS (Cumulative Layout Shift): 레이아웃 변동")
        print("\n  또는 Network 탭에서:")
        print("     - GET /api/analysis/history 응답 시간 확인")
        print("     - 응답 크기 (Size) 확인")
        print("     - 응답 시간 (Time) 분석")
        
    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def run_ui_diagnostics():
    """UI 진단 실행 (다른 스크립트에서 호출 가능)"""
    diagnose_analysis_page()

if __name__ == "__main__":
    diagnose_analysis_page()
