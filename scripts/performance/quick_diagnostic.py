#!/usr/bin/env python
"""
빠른 성능 진단 스크립트 (Docker 테스트용)

특징:
- 로그 거의 없음
- 현재 상황만 파악
- 실행 시간 < 10초
- 필수 정보만 출력

사용법:
  python quick_diagnostic.py
"""

import sys
import time
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

try:
    from app.utils.db import SessionLocal
    from app.models.database import AnalysisJob, AnalysisResult, Employee
except ImportError as e:
    print(f"❌ 데이터베이스 연결 실패: {e}")
    sys.exit(1)

print("=" * 60)
print("🔍 성능 진단 (현황 파악)")
print("=" * 60)

db = SessionLocal()

try:
    # 1. 데이터 현황
    print("\n📊 데이터 현황:")
    emp_count = db.query(Employee).count()
    job_count = db.query(AnalysisJob).count()
    result_count = db.query(AnalysisResult).count()
    
    print(f"  • 직원: {emp_count}명")
    print(f"  • 작업: {job_count}개")
    print(f"  • 결과: {result_count}개")
    
    if job_count > 0:
        avg = result_count / job_count
        print(f"  • 작업당 평균 결과: {avg:.1f}개")
    
    # 2. 최근 작업 상태
    print("\n📋 최근 작업 상태:")
    recent_jobs = db.query(AnalysisJob).order_by(AnalysisJob.created_at.desc()).limit(3).all()
    
    if recent_jobs:
        for job in recent_jobs:
            status_emoji = {
                'pending': '⏳',
                'processing': '⚙️',
                'completed': '✅',
                'failed': '❌'
            }.get(job.status, '❓')
            
            result_count = db.query(AnalysisResult).filter(AnalysisResult.job_id == job.job_id).count()
            file_count = len(job.file_ids) if job.file_ids else 0
            
            print(f"  {status_emoji} {job.job_id[:8]}... | {job.status:10} | {result_count}/{file_count}")
    else:
        print("  (작업 없음)")
    
    # 3. 응답 시간 테스트 (간단한 쿼리만)
    print("\n⚡ 응답 시간 테스트:")
    
    # 3-1. 직원 조회
    start = time.time()
    db.query(Employee).first()
    emp_time = (time.time() - start) * 1000
    print(f"  • 직원 조회: {emp_time:.2f}ms", "✅" if emp_time < 50 else "⚠️" if emp_time < 100 else "❌")
    
    # 3-2. 작업 조회
    start = time.time()
    db.query(AnalysisJob).first()
    job_time = (time.time() - start) * 1000
    print(f"  • 작업 조회: {job_time:.2f}ms", "✅" if job_time < 50 else "⚠️" if job_time < 100 else "❌")
    
    # 3-3. 결과 조회
    start = time.time()
    db.query(AnalysisResult).first()
    result_time = (time.time() - start) * 1000
    print(f"  • 결과 조회: {result_time:.2f}ms", "✅" if result_time < 50 else "⚠️" if result_time < 100 else "❌")
    
    # 4. 성능 로깅 확인
    print("\n📝 로깅 상태:")
    log_file = WEB_UI_ROOT / "logs" / "performance.log"
    if log_file.exists():
        size_kb = log_file.stat().st_size / 1024
        print(f"  ✅ 성능 로그 활성화 ({size_kb:.1f}KB)")
    else:
        print(f"  ⚠️  성능 로그 아직 생성 안 됨 (앱 재시작 후 생성)")
    
    print("\n" + "=" * 60)
    print("✅ 진단 완료")
    print("=" * 60 + "\n")

except Exception as e:
    print(f"\n❌ 에러: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    db.close()
