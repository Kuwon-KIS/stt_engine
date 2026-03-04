#!/usr/bin/env python
"""
성능 측정 스크립트 패키지
web_ui/performance_test.py의 의존성 정리 버전

사용 방법:
  # 기본 테스트 (basic + UI + 백엔드 진단 포함)
  python run_performance_test.py
  
  # 상세 로그 포함
  python run_performance_test.py --verbose
  
  # 특정 테스트만 실행
  python run_performance_test.py --test history
  
  # 기본 성능 테스트만 (진단 제외)
  python run_performance_test.py --no-diagnostics
"""

import sys
import os
import time
import json
import argparse
import importlib.util
from pathlib import Path

# Docker 환경: /app 기준, 로컬 개발: 상대 경로
if Path("/app").exists():
    # Docker 컨테이너 내부
    WEB_UI_ROOT = Path("/app")
    sys.path.insert(0, "/app")
else:
    # 로컬 개발
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
    print(f"   web_ui 경로: {WEB_UI_ROOT}")
    sys.exit(1)

# ============================================================================
# 진단 스크립트 임포트 (동적 로드)
# ============================================================================

def load_diagnostic_scripts():
    """진단 스크립트 동적 로드"""
    diagnostics = {}
    script_dir = Path(__file__).parent
    
    # UI 성능 진단
    ui_script = script_dir / "diagnose_ui_performance.py"
    if ui_script.exists():
        spec = importlib.util.spec_from_file_location("diagnose_ui", ui_script)
        diagnose_ui = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(diagnose_ui)
        diagnostics['ui'] = diagnose_ui
    
    # 백엔드 진단
    backend_script = script_dir / "diagnose_backend_issues.py"
    if backend_script.exists():
        spec = importlib.util.spec_from_file_location("diagnose_backend", backend_script)
        diagnose_backend = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(diagnose_backend)
        diagnostics['backend'] = diagnose_backend
    
    return diagnostics

# ============================================================================
# 유틸리티 함수
# ============================================================================

def format_time(seconds):
    """시간을 읽기 좋은 형식으로 변환"""
    if seconds < 0.001:
        return f"{seconds*1000000:.1f} µs"
    elif seconds < 1:
        return f"{seconds*1000:.2f} ms"
    else:
        return f"{seconds:.2f} s"

def evaluate_performance(elapsed, good_threshold, fair_threshold, test_name):
    """성능 평가"""
    if elapsed < good_threshold:
        return f"✅ GOOD: {format_time(elapsed)}", "GOOD"
    elif elapsed < fair_threshold:
        return f"⚠️  FAIR: {format_time(elapsed)}", "FAIR"
    else:
        return f"❌ SLOW: {format_time(elapsed)}", "SLOW"

def measure_performance(func, *args, iterations=3, **kwargs):
    """성능 측정 (다중 반복으로 정확도 향상)"""
    times = []
    for i in range(iterations):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    return {
        'result': result,
        'avg': avg_time,
        'min': min_time,
        'max': max_time,
        'iterations': iterations
    }

# ============================================================================
# 성능 테스트 함수
# ============================================================================

def test_analysis_history(verbose=False):
    """분석 이력 조회 성능 측정"""
    print("\n" + "="*70)
    print("🔍 TEST 1: 분석 이력 조회 (get_analysis_history)")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        # 가장 많은 분석 이력을 가진 직원 조회
        emp_with_most_jobs = db.query(Employee).all()
        
        if not emp_with_most_jobs:
            print("⚠️  테스트용 직원 데이터가 없습니다.")
            return "SKIP"
        
        # 각 직원별 작업 수 계산
        emp_job_counts = {}
        for emp in emp_with_most_jobs:
            count = db.query(AnalysisJob).filter(AnalysisJob.emp_id == emp.emp_id).count()
            emp_job_counts[emp.emp_id] = count
        
        # 작업이 가장 많은 직원 선택
        if not any(emp_job_counts.values()):
            print("⚠️  분석 이력이 없어 성능 측정을 건너뜁니다.")
            return "SKIP"
        
        emp_id = max(emp_job_counts, key=emp_job_counts.get)
        job_count = emp_job_counts[emp_id]
        
        print(f"✓ 테스트 emp_id: {emp_id} (가장 많은 작업: {job_count}개)")
        
        # 성능 측정 (3회 반복)
        perf_data = measure_performance(
            AnalysisService.get_analysis_history,
            emp_id, None, db,
            iterations=3
        )
        
        result = perf_data['result']
        
        print(f"\n📊 성능 결과:")
        print(f"  - 평균 응답 시간: {format_time(perf_data['avg'])}")
        print(f"  - 최소 응답 시간: {format_time(perf_data['min'])}")
        print(f"  - 최대 응답 시간: {format_time(perf_data['max'])}")
        print(f"  - 반환된 이력 개수: {result.get('count', 0)}개")
        
        # 응답 크기 추정
        json_size = len(json.dumps(result)) / 1024
        print(f"  - 응답 데이터 크기: {json_size:.2f} KB")
        
        # 성능 평가 (평균값 기준)
        evaluation, status = evaluate_performance(perf_data['avg'], 0.1, 0.5, "분석 이력")
        print(f"  {evaluation}")
        
        if verbose:
            print(f"\n📝 상세 정보:")
            print(f"  - 측정 반복 횟수: {perf_data['iterations']}회")
        
        return status
            
    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        if verbose:
            traceback.print_exc()
        return "ERROR"
    finally:
        db.close()

def test_get_progress(verbose=False):
    """진행률 조회 성능 측정 (진행 중인 작업)"""
    print("\n" + "="*70)
    print("🔍 TEST 2: 진행률 조회 (get_progress) - 진행 중인 작업")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        # 진행 중인 작업 조회 (status != 'completed')
        jobs = db.query(AnalysisJob).filter(
            AnalysisJob.status.in_(['pending', 'processing'])
        ).all()
        
        if not jobs:
            # 진행 중인 작업이 없으면 가장 최근 작업 사용
            jobs = db.query(AnalysisJob).order_by(
                AnalysisJob.created_at.desc()
            ).limit(1).all()
        
        if not jobs:
            print("⚠️  테스트용 분석 작업이 없습니다.")
            return "SKIP"
        
        # 가장 최근 작업 선택
        job = jobs[0]
        
        result_count = db.query(AnalysisResult).filter(
            AnalysisResult.job_id == job.job_id
        ).count()
        
        print(f"✓ 테스트 job_id: {job.job_id} (상태: {job.status}, 결과: {result_count}개)")
        print(f"✓ 폴더: {job.folder_path}")
        print(f"✓ 파일 개수: {len(job.file_ids) if job.file_ids else 0}개")
        
        # 성능 측정 (3회 반복)
        perf_data = measure_performance(
            AnalysisService.get_progress,
            job.job_id, job.emp_id, db,
            iterations=3
        )
        
        progress = perf_data['result']
        
        print(f"\n📊 성능 결과:")
        print(f"  - 평균 응답 시간: {format_time(perf_data['avg'])}")
        print(f"  - 최소 응답 시간: {format_time(perf_data['min'])}")
        print(f"  - 최대 응답 시간: {format_time(perf_data['max'])}")
        print(f"  - 진행률: {progress.progress}%")
        print(f"  - 처리된 파일: {progress.processed_files}/{progress.total_files}")
        
        # 응답 크기 추정
        json_size = len(json.dumps(progress.model_dump(), default=str)) / 1024
        print(f"  - 응답 데이터 크기: {json_size:.2f} KB")
        
        # 성능 평가 (평균값 기준)
        evaluation, status = evaluate_performance(perf_data['avg'], 0.2, 1.0, "진행률 조회")
        print(f"  {evaluation}")
        
        if verbose:
            print(f"\n📝 상세 정보:")
            print(f"  - 상태: {progress.status}")
            print(f"  - 측정 반복 횟수: {perf_data['iterations']}회")
        
        return status
            
    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        if verbose:
            traceback.print_exc()
        return "ERROR"
    finally:
        db.close()

def test_get_results(verbose=False):
    """분석 결과 조회 성능 측정 (완료된 작업)"""
    print("\n" + "="*70)
    print("🔍 TEST 3: 분석 결과 조회 (AnalysisResult) - 완료된 작업")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        # 완료된 작업 중 가장 많은 결과를 가진 작업 조회
        completed_jobs = db.query(AnalysisJob).filter(
            AnalysisJob.status == 'completed'
        ).all()
        
        if not completed_jobs:
            print("⚠️  완료된 분석 작업이 없습니다.")
            return "SKIP"
        
        # 각 job별 결과 수 계산
        job_result_counts = {}
        for job in completed_jobs:
            result_count = db.query(AnalysisResult).filter(
                AnalysisResult.job_id == job.job_id
            ).count()
            if result_count > 0:  # 결과가 있는 작업만 포함
                job_result_counts[job.job_id] = (job, result_count)
        
        # 결과가 가장 많은 작업 선택
        if not job_result_counts:
            print("⚠️  분석 결과가 없어 성능 측정을 건너뜁니다.")
            return "SKIP"
        
        job_id = max(job_result_counts, key=lambda x: job_result_counts[x][1])
        job, result_count = job_result_counts[job_id]
        
        print(f"✓ 테스트 job_id: {job.job_id} (상태: completed, 결과: {result_count}개)")
        
        # 성능 측정 함수 정의
        def query_results():
            return db.query(AnalysisResult).filter(
                AnalysisResult.job_id == job_id
            ).all()
        
        # 성능 측정: 3회 반복으로 평균값 계산
        perf_data = measure_performance(
            query_results,
            iterations=3
        )
        
        results = perf_data['result']
        
        print(f"\n📊 성능 결과:")
        print(f"  - 평균 응답 시간: {format_time(perf_data['avg'])}")
        print(f"  - 최소 응답 시간: {format_time(perf_data['min'])}")
        print(f"  - 최대 응답 시간: {format_time(perf_data['max'])}")
        print(f"  - 반환된 결과 개수: {len(results)}개")
        
        if results:
            # 응답 크기 추정 (간단한 직렬화)
            result_dict = [{"id": r.id, "stt_text_length": len(r.stt_text or "")} for r in results]
            json_size = len(json.dumps(result_dict, default=str)) / 1024
            print(f"  - 응답 데이터 크기: {json_size:.2f} KB")
        else:
            print(f"  - 응답 데이터 크기: 0.00 KB")
        
        # 성능 평가 (평균값 기준)
        evaluation, status = evaluate_performance(perf_data['avg'], 0.1, 0.5, "결과 조회")
        print(f"  {evaluation}")
        
        if verbose:
            print(f"\n📝 상세 정보:")
            if results:
                print(f"  - 첫 번째 결과 ID: {results[0].id}")
                print(f"  - STT 텍스트 평균 길이: {sum(len(r.stt_text or '') for r in results) / len(results):.0f} 자")
            print(f"  - 측정 반복 횟수: {perf_data['iterations']}회")
        
        return status
            
    except Exception as e:
        
        # 성능 평가
        evaluation, status = evaluate_performance(elapsed, 0.2, 1.0, "결과 조회")
        print(f"  {evaluation}")
        
        if verbose:
            print(f"\n📝 상세 정보:")
            if results:
                print(f"  - 첫 번째 결과 ID: {results[0].id}")
                print(f"  - STT 텍스트 길이: {len(results[0].stt_text or '')} 자")
        
        return status
            
    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        if verbose:
            traceback.print_exc()
        return "ERROR"
    finally:
        db.close()

def test_database_stats():
    """데이터베이스 통계"""
    print("\n" + "="*70)
    print("📊 데이터베이스 통계")
    print("="*70)
    
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

# ============================================================================
# 메인 함수
# ============================================================================

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="STT Engine 성능 측정 스크립트 (기본 테스트 + 진단 포함)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python run_performance_test.py                         # 모든 테스트 + 진단 실행
  python run_performance_test.py --verbose               # 상세 정보 포함
  python run_performance_test.py --test history          # 특정 테스트만
  python run_performance_test.py --no-diagnostics        # 진단 제외
  python run_performance_test.py --test progress --no-diagnostics  # 테스트만
        """
    )
    
    parser.add_argument(
        "--test",
        type=str,
        choices=["history", "progress", "results", "all"],
        default="all",
        help="실행할 테스트 (기본값: all)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="상세 로그 출력"
    )
    
    parser.add_argument(
        "--no-diagnostics",
        action="store_true",
        help="진단 스크립트 제외"
    )
    
    args = parser.parse_args()
    
    print("\n" + "🚀 성능 측정 시작".center(70, "="))
    
    # 데이터베이스 통계
    test_database_stats()
    
    # 테스트 실행
    results = {}
    
    try:
        if args.test in ["history", "all"]:
            results["history"] = test_analysis_history(args.verbose)
        
        if args.test in ["progress", "all"]:
            results["progress"] = test_get_progress(args.verbose)
        
        if args.test in ["results", "all"]:
            results["results"] = test_get_results(args.verbose)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자 중단")
        sys.exit(1)
    
    # 결과 요약
    print("\n" + "="*70)
    print("📋 테스트 결과 요약")
    print("="*70)
    
    good_count = sum(1 for v in results.values() if v == "GOOD")
    fair_count = sum(1 for v in results.values() if v == "FAIR")
    slow_count = sum(1 for v in results.values() if v == "SLOW")
    error_count = sum(1 for v in results.values() if v == "ERROR")
    skip_count = sum(1 for v in results.values() if v == "SKIP")
    
    print(f"✅ GOOD:  {good_count}개")
    print(f"⚠️  FAIR:  {fair_count}개")
    print(f"❌ SLOW:  {slow_count}개")
    print(f"⚠️  ERROR: {error_count}개")
    print(f"⏭️  SKIP:  {skip_count}개")
    
    print("\n" + "✅ 기본 성능 측정 완료".center(70, "=") + "\n")
    
    # 진단 스크립트 실행
    if not args.no_diagnostics:
        print("\n" + "📊 추가 진단 실행 중".center(70, "="))
        diagnostics = load_diagnostic_scripts()
        
        try:
            # UI 성능 진단
            if 'ui' in diagnostics:
                print("\n1️⃣  UI 성능 진단 시작...")
                if hasattr(diagnostics['ui'], 'diagnose_analysis_page'):
                    diagnostics['ui'].diagnose_analysis_page()
                else:
                    print("⚠️  UI 진단 함수를 찾을 수 없습니다")
            
            # 백엔드 진단
            if 'backend' in diagnostics:
                print("\n2️⃣  백엔드 성능 진단 시작...")
                if hasattr(diagnostics['backend'], 'diagnose_backend'):
                    diagnostics['backend'].diagnose_backend()
                else:
                    print("⚠️  백엔드 진단 함수를 찾을 수 없습니다")
            
            print("\n" + "✅ 진단 완료".center(70, "=") + "\n")
        
        except Exception as e:
            print(f"\n⚠️  진단 중 오류 발생: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
    
    # 종료 코드
    if error_count > 0:
        sys.exit(1)
    elif slow_count > 0:
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
