"""
파일 관리 API 엔드포인트
Phase 2: 파일 업로드, 조회, 삭제 등의 REST API
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends, Query
from fastapi.responses import FileResponse
import logging
import os

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
    folder_path: str = Query(...),  # 필수 파라미터
    db: Session = Depends(get_db)
):
    """
    파일 삭제
    
    Args:
        filename: 삭제할 파일명 (path parameter)
        folder_path: 폴더 경로 (query parameter, 필수)
    
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


@router.get("/audio/{emp_id}/{folder_path}/{filename}")
async def get_audio_file(
    emp_id: str,
    folder_path: str,
    filename: str,
    request: Request
):
    """
    오디오 파일 스트리밍
    
    Args:
        emp_id: 사원번호
        folder_path: 폴더 경로
        filename: 파일명
    
    Returns:
        FileResponse: 오디오 파일
    """
    try:
        # 세션 확인
        session_emp_id = request.session.get("emp_id")
        if not session_emp_id:
            raise HTTPException(status_code=401, detail="로그인이 필요합니다")
        
        # 본인 파일만 접근 가능
        if session_emp_id != emp_id:
            raise HTTPException(status_code=403, detail="접근 권한이 없습니다")
        
        # 파일 경로 구성
        base_path = os.path.join("data", "uploads", emp_id, folder_path)
        file_path = os.path.join(base_path, filename)
        
        # 파일 존재 확인
        if not os.path.exists(file_path):
            logger.error(f"파일을 찾을 수 없음: {file_path}")
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
        
        # 파일 타입 결정
        _, ext = os.path.splitext(filename)
        media_type_map = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.flac': 'audio/flac',
            '.ogg': 'audio/ogg'
        }
        media_type = media_type_map.get(ext.lower(), 'audio/mpeg')
        
        logger.info(f"오디오 파일 제공: {file_path}")
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename
        )
        
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"오디오 파일 제공 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/folders", status_code=201)
async def create_folder(
    request: Request,
    folder_name: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    새 폴더 생성
    
    Args:
        folder_name: 폴더 이름
    
    Returns:
        dict: 생성 결과
    """
    # 세션에서 사번 추출
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    result = FileService.create_folder(emp_id, folder_name, db)
    return result


@router.delete("/folders/{folder_name}")
async def delete_folder(
    folder_name: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    폴더 삭제 (내부 파일 포함)
    
    Args:
        folder_name: 폴더 이름
    
    Returns:
        dict: 삭제 결과
    """
    # 세션에서 사번 추출
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    result = FileService.delete_folder(emp_id, folder_name, db)
    return result

