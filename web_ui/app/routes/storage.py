"""
Storage quota API routes
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.utils.db import get_db
from app.services.storage_service import StorageService


router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/info")
async def get_storage_info(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    현재 사용자의 저장 용량 정보 조회
    
    Returns:
        Storage information including used, quota, available space
    """
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    result = StorageService.get_storage_info(emp_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    
    return result


@router.post("/recalculate")
async def recalculate_storage(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    저장 용량 재계산 (관리자 또는 본인)
    실제 파일 크기 합계로 storage_used 업데이트
    """
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    success = StorageService.recalculate_usage(emp_id, db)
    
    if not success:
        raise HTTPException(status_code=500, detail="재계산 실패")
    
    # 업데이트된 정보 반환
    result = StorageService.get_storage_info(emp_id, db)
    
    return {
        "success": True,
        "message": "저장 용량 재계산 완료",
        "storage_info": result
    }
