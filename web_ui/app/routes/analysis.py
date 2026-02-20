"""
분석 API 엔드포인트
Phase 3: 분석 시작, 진행률, 결과 조회
"""

from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import asyncio

from app.services.analysis_service import AnalysisService
from app.utils.db import get_db
from app.models.analysis_schemas import (
    AnalysisStartRequest, AnalysisStartResponse, AnalysisProgressResponse, AnalysisResultListResponse
)


router = APIRouter(
    prefix="/api/analysis",
    tags=["analysis"],
    responses={401: {"description": "Unauthorized"}, 404: {"description": "Not Found"}}
)


@router.post("/start", response_model=AnalysisStartResponse, status_code=202)
async def start_analysis(
    request_data: AnalysisStartRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    분석 시작
    
    Args:
        request_data: 분석 요청
    
    Returns:
        AnalysisStartResponse
    """
    # 세션에서 사번 추출
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    try:
        # 분석 시작
        response = AnalysisService.start_analysis(emp_id, request_data, db)
        
        # 백그라운드에서 분석 실행
        files = db.query(request_data.__class__).all()  # TODO: 올바르게 파일 목록 가져오기
        background_tasks.add_task(
            AnalysisService.process_analysis_async,
            response.job_id,
            emp_id,
            request_data.folder_path,
            [f.filename for f in files],  # TODO: 파일 목록 가져오기
            request_data.include_classification,
            request_data.include_validation,
            db
        )
        
        return response
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{job_id}", response_model=AnalysisProgressResponse)
async def get_progress(
    job_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    분석 진행률 조회
    
    Args:
        job_id: 분석 작업 ID
    
    Returns:
        AnalysisProgressResponse
    """
    # 세션에서 사번 추출
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    try:
        return AnalysisService.get_progress(job_id, emp_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{job_id}", response_model=AnalysisResultListResponse)
async def get_results(
    job_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    분석 결과 조회
    
    Args:
        job_id: 분석 작업 ID
    
    Returns:
        AnalysisResultListResponse
    """
    # 세션에서 사번 추출
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    try:
        return AnalysisService.get_results(job_id, emp_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
