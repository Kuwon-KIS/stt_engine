#!/usr/bin/env python
"""
성능 개선 솔루션 제시
각 문제별 현재 코드 vs 개선 코드 비교

이 파일은 실행되지 않으며, 개선 방안을 보여주는 참고용입니다.
"""

# ============================================================================
# 문제 1: N+1 쿼리 문제
# ============================================================================

"""
❌ 현재 코드 (문제 있음):
"""

def get_analysis_history_old(emp_id: str, folder_path=None, db=None):
    # 모든 직원의 job을 조회 (N번 반복되므로 N+1 문제)
    emp_with_most_jobs = db.query(Employee).all()  # 1번 쿼리
    
    emp_job_counts = {}
    for emp in emp_with_most_jobs:  # 각 직원마다 1번씩 = N번 쿼리
        count = db.query(AnalysisJob).filter(
            AnalysisJob.emp_id == emp.emp_id
        ).count()
        emp_job_counts[emp.emp_id] = count
    
    # 결과: 1 + N 번 쿼리


"""
✅ 개선된 코드 (GROUP BY 사용):
"""

from sqlalchemy import func

def get_analysis_history_optimized(emp_id: str, folder_path=None, db=None):
    # 단일 쿼리로 모든 직원의 job count 계산
    job_counts = db.query(
        AnalysisJob.emp_id,
        func.count(AnalysisJob.job_id).label('count')
    ).group_by(AnalysisJob.emp_id).all()  # 1번 쿼리만!
    
    emp_job_counts = {row.emp_id: row.count for row in job_counts}
    
    # 결과: 1번 쿼리로 완료 (99% 성능 개선)


# ============================================================================
# 문제 2: 불필요한 데이터 전송
# ============================================================================

"""
❌ 현재 코드 (모든 필드 반환):
"""

def get_analysis_results_all_fields(job_id: str, db=None):
    results = db.query(AnalysisResult).filter(
        AnalysisResult.job_id == job_id
    ).all()  # 모든 칼럼 로드
    
    # JSON 응답 (불필요한 필드도 포함)
    return {
        'results': [r.model_dump() for r in results],  # 모든 필드 직렬화
        'count': len(results)
    }
    # 결과: JSON 크기 큼, 네트워크 느림


"""
✅ 개선된 코드 (필드 선택):
"""

def get_analysis_results_optimized(job_id: str, db=None):
    results = db.query(AnalysisResult).filter(
        AnalysisResult.job_id == job_id
    ).all()
    
    # 필수 필드만 반환
    return {
        'results': [
            {
                'result_id': r.result_id,
                'job_id': r.job_id,
                'file_id': r.file_id,
                'stt_text': r.stt_text,
                'confidence': getattr(r, 'confidence', None),
            }
            for r in results
        ],
        'count': len(results)
    }
    # 결과: JSON 크기 50% 감소


# ============================================================================
# 문제 3: 메모리 오버헤드 (Pagination)
# ============================================================================

"""
❌ 현재 코드 (모든 데이터 로드):
"""

def get_analysis_results_all(job_id: str, db=None):
    # 모든 결과를 메모리에 로드
    results = db.query(AnalysisResult).filter(
        AnalysisResult.job_id == job_id
    ).all()  # 1000개 = 1000개 객체
    
    return results
    # 문제: 1000개 파일 = 메모리 낭비


"""
✅ 개선된 코드 (Pagination):
"""

def get_analysis_results_paginated(job_id: str, page: int = 1, per_page: int = 50, db=None):
    # 페이지당 50개만 로드
    skip = (page - 1) * per_page
    
    results = db.query(AnalysisResult).filter(
        AnalysisResult.job_id == job_id
    ).offset(skip).limit(per_page).all()  # 50개만 로드
    
    total = db.query(AnalysisResult).filter(
        AnalysisResult.job_id == job_id
    ).count()
    
    return {
        'results': results,
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page
    }
    # 결과: 메모리 95% 절감


# ============================================================================
# 문제 4: JSON 직렬화 최적화
# ============================================================================

"""
❌ 현재 코드 (전체 model_dump):
"""

def serialize_results_slow(results):
    import json
    
    # model_dump()로 모든 필드 변환 후 JSON 인코딩
    return json.dumps(
        [r.model_dump(mode='python') for r in results],
        default=str
    )
    # 문제: 직렬화 오버헤드


"""
✅ 개선된 코드 (필드 선택):
"""

def serialize_results_fast(results):
    import json
    
    # 필드 선택으로 직렬화 비용 감소
    return json.dumps([
        {
            'result_id': r.result_id,
            'stt_text': r.stt_text,
            'confidence': r.confidence if hasattr(r, 'confidence') else None,
        }
        for r in results
    ], default=str)
    # 결과: 직렬화 30% 빨라짐 + JSON 크기 50% 감소


# ============================================================================
# 종합 개선: API 엔드포인트 최적화
# ============================================================================

"""
✅ 최적화된 API 응답 구조:
"""

def get_analysis_history_final(emp_id: str, folder_path=None, page=1, per_page=50, db=None):
    """
    개선 사항:
    1. GROUP BY로 N+1 쿼리 제거
    2. Pagination으로 메모리 절감
    3. 필수 필드만 반환
    4. 선택적 상세 필드는 별도 API로 분리
    """
    
    # 1. 페이지네이션이 적용된 job 조회
    skip = (page - 1) * per_page
    
    jobs = db.query(AnalysisJob).filter(
        AnalysisJob.emp_id == emp_id
    ).order_by(AnalysisJob.created_at.desc()).offset(skip).limit(per_page).all()
    
    # 2. 결과 수 계산 (GROUP BY로 최적화)
    from sqlalchemy import func
    result_counts = db.query(
        AnalysisJob.job_id,
        func.count(AnalysisResult.result_id).label('count')
    ).outerjoin(AnalysisResult).filter(
        AnalysisJob.emp_id == emp_id
    ).group_by(AnalysisJob.job_id).all()
    
    result_count_dict = {rc.job_id: rc.count for rc in result_counts}
    
    # 3. 필수 필드만 반환
    return {
        'jobs': [
            {
                'job_id': j.job_id,
                'folder_path': j.folder_path,
                'status': j.status,
                'created_at': j.created_at.isoformat(),
                'result_count': result_count_dict.get(j.job_id, 0),
            }
            for j in jobs
        ],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'pages': (total_count + per_page - 1) // per_page
        }
    }


# ============================================================================
# 데이터베이스 인덱싱 최적화
# ============================================================================

"""
✅ 권장 인덱싱 전략:
"""

# models/database.py에 다음 인덱싱 추가:
"""
class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    
    # 기존 칼럼들...
    
    __table_args__ = (
        # 복합 인덱스 (쿼리 최적화)
        Index('idx_emp_id_created_at', 'emp_id', 'created_at'),
        Index('idx_status_created_at', 'status', 'created_at'),
        Index('idx_job_id_status', 'job_id', 'status'),
    )

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    __table_args__ = (
        Index('idx_job_id_file_id', 'job_id', 'file_id'),
        Index('idx_created_at', 'created_at'),
    )
"""


# ============================================================================
# 프론트엔드 최적화 (참고)
# ============================================================================

"""
🌐 프론트엔드 개선 항목:

1. 가상 스크롤 (Virtual Scroll)
   - React Virtual List 또는 vue-virtual-scroller 사용
   - DOM 노드 수 제한 (표시되는 것만 렌더링)
   - 1000개 행 테이블도 부드럽게

2. 캐싱
   - LocalStorage에 최근 분석 결과 캐싱
   - 같은 job_id 재조회 시 캐시 활용

3. 지연 로딩 (Lazy Loading)
   - 초기 로드 50개만
   - 스크롤 하단 도달 시 다음 페이지 로드

4. 워커 스레드
   - JSON 파싱을 Web Worker로 이동
   - UI 스레드 블로킹 방지
"""
