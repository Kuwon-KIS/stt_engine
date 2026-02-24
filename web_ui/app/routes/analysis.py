"""
분석 API 엔드포인트
Phase 3: 분석 시작, 진행률, 결과 조회
"""

from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import traceback
import logging

from app.services.analysis_service import AnalysisService
from app.utils.db import get_db, SessionLocal
from app.models.analysis_schemas import (
    AnalysisStartRequest, AnalysisStartResponse, AnalysisProgressResponse, AnalysisResultListResponse
)
from app.models.database import FileUpload, AnalysisJob, AnalysisResult
from datetime import datetime

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
        logger.info(f"분석 시작 응답: job_id={response.job_id}, status={response.status}")
        
        # 폴더 형상 미변경 시 조기 반환
        if response.status == "unchanged":
            logger.info(f"폴더 형상 미변경: job_id={response.job_id}")
            return response
        
        # 해당 폴더의 파일 목록 조회
        files = db.query(FileUpload).filter(
            FileUpload.emp_id == emp_id,
            FileUpload.folder_path == request_data.folder_path
        ).all()
        
        file_list = [f.filename for f in files]
        
        # BackgroundTasks를 사용한 백그라운드 분석
        # FastAPI의 표준 방식으로, 안정적인 백그라운드 처리 보장
        background_tasks.add_task(
            AnalysisService.process_analysis_sync,
            response.job_id,
            emp_id,
            request_data.folder_path,
            file_list,
            request_data.include_classification,
            request_data.include_validation
        )
        logger.info(f"백그라운드 분석 태스크 등록 완료: job_id={response.job_id}")
        
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


@router.post("/rerun", status_code=202)
async def rerun_analysis(
    request: Request,
    background_tasks: BackgroundTasks,
    request_data: dict,
    db: Session = Depends(get_db)
):
    """
    선택한 파일들 재분석
    
    Args:
        request_data: {
            "job_id": str,
            "filenames": List[str],
            "folder_path": str,
            "include_classification": bool,
            "include_validation": bool
        }
    
    Returns:
        새 job_id와 메시지
    """
    # 세션에서 사번 추출
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    try:
        job_id = request_data.get("job_id")
        filenames = request_data.get("filenames", [])
        folder_path = request_data.get("folder_path")
        include_classification = request_data.get("include_classification", False)
        include_validation = request_data.get("include_validation", False)
        
        if not job_id or not filenames or not folder_path:
            raise HTTPException(status_code=400, detail="필수 파라미터가 누락되었습니다")
        
        logger.info(f"재분석 요청: emp_id={emp_id}, job_id={job_id}, folder={folder_path}, files={len(filenames)}")
        
        # 파일 소유권 검증 - 모든 파일이 해당 사용자의 폴더에 속하는지 확인
        file_count = db.query(FileUpload).filter(
            FileUpload.emp_id == emp_id,
            FileUpload.folder_path == folder_path,
            FileUpload.filename.in_(filenames)
        ).count()
        
        if file_count != len(filenames):
            raise HTTPException(status_code=403, detail="일부 파일에 대한 권한이 없습니다")
        
        # 기존 job의 상태를 'processing'으로 변경 (재실행 중임을 표시)
        job = db.query(AnalysisJob).filter(
            AnalysisJob.job_id == job_id,
            AnalysisJob.emp_id == emp_id
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다")
        
        job.status = "processing"
        db.commit()
        
        # 선택된 파일들의 결과를 'pending'으로 리셋
        reset_count = db.query(AnalysisResult).filter(
            AnalysisResult.job_id == job_id,
            AnalysisResult.file_id.in_(filenames)
        ).update({
            "status": "pending",
            "stt_text": None,
            "stt_metadata": None,
            "classification_code": None,
            "classification_category": None,
            "classification_confidence": None,
            "improper_detection_results": None,
            "incomplete_detection_results": None,
            "updated_at": datetime.utcnow()
        }, synchronize_session=False)
        
        db.commit()
        logger.info(f"재분석 준비: {reset_count}개 파일 상태 리셋 완료")
        
        # 선택된 파일들만 재처리하도록 백그라운드 태스크 등록
        background_tasks.add_task(
            AnalysisService.process_analysis_sync,
            job_id,  # 동일한 job_id 사용
            emp_id,
            folder_path,
            filenames,  # 선택된 파일만 전달
            include_classification,
            include_validation
        )
        
        logger.info(f"재분석 시작: job_id={job_id}, files={len(filenames)}")
        
        return {
            "success": True,
            "job_id": job_id,  # 동일한 job_id 반환
            "message": f"{len(filenames)}개 파일 재분석을 시작했습니다",
            "file_count": len(filenames)
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"재분석 ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"재분석 에러: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


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
