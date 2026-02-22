"""
분석 API 엔드포인트
Phase 3: 분석 시작, 진행률, 결과 조회
"""

from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import asyncio
import threading
import traceback
import logging

from app.services.analysis_service import AnalysisService
from app.utils.db import get_db
from app.models.analysis_schemas import (
    AnalysisStartRequest, AnalysisStartResponse, AnalysisProgressResponse, AnalysisResultListResponse
)
from app.models.database import FileUpload

logger = logging.getLogger(__name__)


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
        logger.info(f"분석 시작 요청: emp_id={emp_id}, folder_path={request_data.folder_path}")
        
        # 분석 시작
        response = AnalysisService.start_analysis(emp_id, request_data, db)
        logger.info(f"분석 시작 성공: job_id={response.job_id}")
        
        # 해당 폴더의 파일 목록 조회
        files = db.query(FileUpload).filter(
            FileUpload.emp_id == emp_id,
            FileUpload.folder_path == request_data.folder_path
        ).all()
        
        file_list = [f.filename for f in files]
        
        # 백그라운드에서 분석 실행 (스레드 사용)
        def run_analysis():
            # 새로운 세션 생성
            from app.utils.db import SessionLocal
            new_db = SessionLocal()
            try:
                logger.info(f"[스레드] 분석 시작: job_id={response.job_id}, files={file_list}")
                logger.info(f"[스레드] asyncio.run() 호출 전")
                asyncio.run(
                    AnalysisService.process_analysis_async(
                        response.job_id,
                        emp_id,
                        request_data.folder_path,
                        file_list,
                        request_data.include_classification,
                        request_data.include_validation,
                        new_db
                    )
                )
                logger.info(f"[스레드] asyncio.run() 반환 후")
                logger.info(f"[스레드] 분석 완료: job_id={response.job_id}")
            except Exception as e:
                logger.error(f"[스레드] 분석 에러: {str(e)}", exc_info=True)
                import traceback
                logger.error(f"[스레드] Traceback:\n{traceback.format_exc()}")
            finally:
                new_db.close()
        
        thread = threading.Thread(target=run_analysis, daemon=True)
        thread.start()
        
        return response
    
    except ValueError as e:
        logger.error(f"분석 시작 ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"분석 시작 에러: {str(e)}\n{traceback.format_exc()}")
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


@router.get("/history")
async def get_analysis_history(
    folder_path: str = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    분석 이력 조회
    
    Args:
        folder_path: 폴더 경로 (선택사항, 미지정 시 모든 이력)
    
    Returns:
        분석 이력 목록
    """
    # 세션에서 사번 추출
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    try:
        return AnalysisService.get_analysis_history(emp_id, folder_path, db)
    except Exception as e:
        logger.error(f"분석 이력 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    try:
        return AnalysisService.get_results(job_id, emp_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
