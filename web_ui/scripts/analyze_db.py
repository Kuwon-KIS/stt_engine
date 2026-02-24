#!/usr/bin/env python3
"""
상세 DB 분석 도구 - 중단된 작업 원인 파악

각 작업의 진행 상황을 상세히 분석해서 정리 여부를 판단하는 데 도움
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.db import SessionLocal
from app.models.database import AnalysisJob, AnalysisResult


def analyze_job_details(job_id=None):
    """작업 상세 분석"""
    db = SessionLocal()
    
    try:
        if job_id:
            jobs = db.query(AnalysisJob).filter(
                AnalysisJob.job_id == job_id
            ).all()
        else:
            # 중단된 작업만 조회
            cutoff = datetime.now() - timedelta(hours=24)
            jobs = db.query(AnalysisJob).filter(
                AnalysisJob.status.in_(['pending', 'processing']),
                AnalysisJob.created_at < cutoff
            ).order_by(AnalysisJob.created_at.asc()).all()
        
        if not jobs:
            print("✅ 분석 대상 없음\n")
            return
        
        print(f"\n{'='*80}")
        print(f"📊 작업 상세 분석")
        print(f"{'='*80}\n")
        
        for job in jobs[:5]:  # 처음 5개만
            print(f"🔍 Job: {job.job_id}")
            print(f"   상태: {job.status}")
            print(f"   폴더: {job.folder_path}")
            
            elapsed = datetime.now() - job.created_at
            print(f"   생성: {job.created_at.strftime('%Y-%m-%d %H:%M:%S')} ({elapsed.days}일 {elapsed.seconds//3600}시간 전)")
            
            if job.updated_at:
                update_elapsed = datetime.now() - job.updated_at
                print(f"   수정: {job.updated_at.strftime('%Y-%m-%d %H:%M:%S')} ({update_elapsed.days}일 {update_elapsed.seconds//3600}시간 전)")
            
            # 분석 결과 통계
            results = db.query(AnalysisResult).filter(
                AnalysisResult.job_id == job.id
            ).all()
            
            if results:
                statuses = {}
                for r in results:
                    statuses[r.status] = statuses.get(r.status, 0) + 1
                
                print(f"\n   📁 파일 분석 현황 ({len(results)}개):")
                for status, count in sorted(statuses.items()):
                    print(f"      - {status:12}: {count}개")
                
                # 상태 분석
                pending = statuses.get('pending', 0)
                processing = statuses.get('processing', 0)
                completed = statuses.get('completed', 0)
                
                if pending > 0 or processing > 0:
                    print(f"\n   ⚠️  {pending + processing}개 파일이 아직 진행 중...")
                    print(f"      → 정리하면 이 파일들의 분석이 표시되지 않을 수 있음")
                else:
                    print(f"\n   ✅ 모든 파일 분석 완료 - 안전하게 정리 가능")
            else:
                print(f"   ⚠️  분석 결과 없음 (완전히 진행되지 않음)")
            
            print()
    
    finally:
        db.close()


def get_cleanup_recommendations():
    """정리 권장사항 생성"""
    db = SessionLocal()
    
    try:
        print(f"\n{'='*80}")
        print(f"💡 정리 권장사항")
        print(f"{'='*80}\n")
        
        # 1. 오래된 pending 작업
        one_day_ago = datetime.now() - timedelta(hours=24)
        old_pending = db.query(AnalysisJob).filter(
            AnalysisJob.status == 'pending',
            AnalysisJob.created_at < one_day_ago
        ).count()
        
        if old_pending > 0:
            print(f"🔴 높은 우선순위 (정리 강력 권장)")
            print(f"   - 24시간 이상 pending 상태: {old_pending}개")
            print(f"   → 명령: cleanup_stale_jobs.py --apply --hours 24\n")
        
        # 2. 오래된 processing 작업
        old_processing = db.query(AnalysisJob).filter(
            AnalysisJob.status == 'processing',
            AnalysisJob.created_at < one_day_ago
        ).count()
        
        if old_processing > 0:
            print(f"🟠 중간 우선순위 (확인 후 정리)")
            print(f"   - 24시간 이상 processing 상태: {old_processing}개")
            print(f"   → 먼저 analyze_job_details로 확인 후 정리\n")
        
        # 3. 전체 통계
        total_jobs = db.query(AnalysisJob).count()
        completed = db.query(AnalysisJob).filter(
            AnalysisJob.status == 'completed'
        ).count()
        active = db.query(AnalysisJob).filter(
            AnalysisJob.status.in_(['pending', 'processing'])
        ).count()
        
        print(f"📈 전체 통계")
        print(f"   - 전체 작업: {total_jobs}개")
        print(f"   - 완료: {completed}개 ({100*completed/total_jobs:.1f}%)")
        print(f"   - 진행 중: {active}개\n")
        
        if old_pending == 0 and old_processing == 0:
            print("✅ 정리 필요 없음 - 모든 작업이 정상적으로 처리됨\n")
    
    finally:
        db.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='상세 DB 분석 도구'
    )
    parser.add_argument(
        '--job',
        help='특정 job_id 상세 분석'
    )
    parser.add_argument(
        '--recommend',
        action='store_true',
        help='정리 권장사항 표시'
    )
    
    args = parser.parse_args()
    
    if args.job:
        analyze_job_details(args.job)
    elif args.recommend:
        get_cleanup_recommendations()
    else:
        # 기본: 권장사항 + 상세 분석
        get_cleanup_recommendations()
        analyze_job_details()
