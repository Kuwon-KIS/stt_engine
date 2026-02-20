"""
파일 관리 API 엔드포인트
Phase 2: 파일 업로드, 조회, 삭제 등의 REST API
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
import logging

from app.services.file_service import FileService
from app.utils.db import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/files",
    tags=["files"],
    responses={401: {"description": "Unauthorized"}, 404: {"description": "Not Found"}}
)


@router.get("/folders")
async def list_folders(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    사용자의 폴더 목록 조회
    
    Returns:
        FolderListResponse: 폴더 목록
    """
    # 세션에서 사번 추출
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    result = FileService.list_folders(emp_id, db)
    return result


@router.get("/list")
async def list_files(
    request: Request,
    folder_path: str = None,
    db: Session = Depends(get_db)
):
    """
    폴더 내 파일 목록 조회
    
    Args:
        folder_path: 폴더 경로 (선택)
    
    Returns:
        FileListResponse: 파일 목록
    """
    # 세션에서 사번 추출
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    result = FileService.list_files(emp_id, folder_path, db)
    return result


@router.post("/upload", status_code=201)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    folder_name: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    파일 업로드
    
    Args:
        file: 업로드 파일
        folder_name: 폴더 이름 (선택, 기본값: YYYY-MM-DD)
    
    Returns:
        FileUploadResponse: 업로드 결과
    """
    # 세션에서 사번 추출
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    result = FileService.upload_file(emp_id, file, folder_name, db)
    return result


@router.api_route("/{filename}", methods=["DELETE"])
async def delete_file_handler(
    filename: str,
    request: Request,
    folder_path: str = None,
    db: Session = Depends(get_db)
):
    """
    파일 삭제
    
    Args:
        filename: 삭제할 파일명
        folder_path: 폴더 경로 (선택, 없으면 최상위)
    
    Returns:
        dict: 삭제 결과
    """
    try:
        logger.info(f"DELETE 라우터 호출 - filename={filename}, folder_path={folder_path}")
        
        # 세션에서 사번 추출
        emp_id = request.session.get("emp_id")
        if not emp_id:
            logger.warning("세션 없음 - 미인증")
            raise HTTPException(status_code=401, detail="로그인이 필요합니다")
        
        logger.info(f"파일 삭제 요청: emp_id={emp_id}, filename={filename}, folder_path={folder_path}")
        
        result = FileService.delete_file(emp_id, filename, folder_path, db)
        logger.info(f"파일 삭제 성공: {result}")
        return result
    except HTTPException as e:
        logger.error(f"HTTP 예외 - status: {e.status_code}, detail: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"예상치 못한 에러: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
