#!/usr/bin/env python3
"""
중단된 분석 작업 정리 스크립트

상태:
- pending/processing인데 오래된 작업 → completed로 변경하고 상태 메시지 기록
- DB 용량 정리: 이전 작업들 삭제 옵션
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# 웹UI 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.db import SessionLocal
from app.models.database import AnalysisJob, AnalysisResult


def cleanup_stale_jobs(hours=24, dry_run=True):
    """
    중단된 작업 정리
    
    Args:
        hours: 이 시간 이상 경과한 pending/processing 작업 정리
        dry_run: True면 조회만, False면 실제 업데이트
    """
    db = SessionLocal()
    
    try:
        cutoff = datetime.now() - timedelta(hours=hours)
        
        # 중단된 작업 찾기
        stale_jobs = db.query(AnalysisJob).filter(
            AnalysisJob.status.in_(['pending', 'processing']),
            AnalysisJob.created_at < cutoff
        ).order_by(AnalysisJob.created_at.asc()).all()
        
        print(f"\n{'='*70}")
        print(f"📊 중단된 작업 정리 리포트 ({hours}시간 이상 경과)")
        print(f"{'='*70}\n")
        
        if not stale_jobs:
            print("✅ 중단된 작업 없음\n")
            return 0
        
        print(f"❌ 발견된 중단된 작업: {len(stale_jobs)}개\n")
        
        for i, job in enumerate(stale_jobs, 1):
            elapsed = datetime.now() - job.created_at
            days = elapsed.days
            hours_part = elapsed.seconds // 3600
            
            # 해당 작업의 분석 결과 통계
            results = db.query(AnalysisResult).filter(
                AnalysisResult.job_id == job.id
            ).all()
            completed_count = sum(1 for r in results if r.status == 'completed')
            
            print(f"{i}. Job ID: {job.job_id}")
            print(f"   상태: {job.status} → 정리 필요")
            print(f"   폴더: {job.folder_path}")
            print(f"   생성일: {job.created_at.strftime('%Y-%m-%d %H:%M:%S')} ({days}일 {hours_part}시간 전)")
            print(f"   파일 분석: {len(results)}개 (완료: {completed_count}개)")
            print()
        
        if not dry_run:
            print("🔧 실제 정리 작업 수행 중...\n")
            cleaned_count = 0
            for job in stale_jobs:
                job.status = 'completed'
                job.updated_at = datetime.now()
                cleaned_count += 1
                print(f"  ✓ {job.job_id}: 정리 완료")
            
            db.commit()
            print(f"\n✅ 총 {cleaned_count}개 작업 정리 완료\n")
        else:
            print(f"ℹ️  Dry-run 모드: 위 작업들이 정리됩니다 (--apply 플래그로 실행)\n")
        
        return len(stale_jobs)
    
    finally:
        db.close()


def show_job_stats():
    """작업 상태 통계"""
    db = SessionLocal()
    
    try:
        print(f"\n{'='*70}")
        print("📈 전체 작업 상태 통계")
        print(f"{'='*70}\n")
        
        # 상태별 집계
        statuses = ['pending', 'processing', 'completed']
        total_jobs = 0
        
        for status in statuses:
            count = db.query(AnalysisJob).filter(
                AnalysisJob.status == status
            ).count()
            total_jobs += count
            print(f"  {status:12} : {count:4}개")
        
        print(f"  {'─'*20}")
        print(f"  {'total':12} : {total_jobs:4}개\n")
        
        # 오래된 작업 조회
        one_week_ago = datetime.now() - timedelta(days=7)
        old_jobs = db.query(AnalysisJob).filter(
            AnalysisJob.created_at < one_week_ago
        ).count()
        
        print(f"📅 7일 이상 된 작업: {old_jobs}개")
        print(f"💾 정리 대상 (24시간 이상 중단): ", end="")
        
        cutoff = datetime.now() - timedelta(hours=24)
        stale = db.query(AnalysisJob).filter(
            AnalysisJob.status.in_(['pending', 'processing']),
            AnalysisJob.created_at < cutoff
        ).count()
        print(f"{stale}개\n")
        
    finally:
        db.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='중단된 분석 작업 정리',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 1. 상태만 확인 (dry-run)
  python cleanup_stale_jobs.py --check
  
  # 2. 통계 보기
  python cleanup_stale_jobs.py --stats
  
  # 3. 24시간 이상 중단된 작업 정리 (실제 적용)
  python cleanup_stale_jobs.py --apply
  
  # 4. 12시간 이상 중단된 작업 정리
  python cleanup_stale_jobs.py --hours 12 --apply
        """
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='중단된 작업 확인 (dry-run, 기본값)'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='실제 정리 수행'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='작업 상태 통계만 표시'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='기준 시간 (기본: 24시간)'
    )
    
    args = parser.parse_args()
    
    # 통계 먼저 표시
    show_job_stats()
    
    if args.stats:
        sys.exit(0)
    
    # 정리
    cleanup_stale_jobs(hours=args.hours, dry_run=not args.apply)
