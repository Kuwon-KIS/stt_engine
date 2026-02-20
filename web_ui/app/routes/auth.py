"""
인증 API 라우터
Phase 1: 로그인, 로그아웃, 세션 확인 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.utils.db import get_db
from app.services.auth_service import AuthService

# 라우터 생성 (prefix: /api/auth)
router = APIRouter(prefix="/api/auth", tags=["auth"])


# === Pydantic 모델 ===
class LoginRequest(BaseModel):
    """로그인 요청 모델"""
    emp_id: str


class LoginResponse(BaseModel):
    """로그인 응답 모델"""
    success: bool
    emp_id: str
    name: str
    dept: str


class SessionResponse(BaseModel):
    """세션 정보 응답 모델"""
    emp_id: str
    name: str
    dept: str


class LogoutResponse(BaseModel):
    """로그아웃 응답 모델"""
    message: str


# === 엔드포인트 ===
@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, req: Request, db: Session = Depends(get_db)):
    """
    사용자 로그인
    
    - 사번 검증
    - DB에 직원 정보 기록 (최초 로그인 시) 또는 last_login 업데이트
    - 세션 쿠키 생성 (httpOnly)
    
    Args:
        request: 로그인 요청 (emp_id)
        req: FastAPI Request 객체 (세션 접근용)
        db: DB 세션
    
    Returns:
        로그인 성공 시 사용자 정보
    
    Raises:
        HTTPException (401): 잘못된 사번
    """
    # 사번 검증 및 DB 기록
    result = AuthService.validate_employee(request.emp_id, db)
    
    if not result["success"]:
        raise HTTPException(
            status_code=401,
            detail=result.get("error", "Login failed")
        )
    
    # 세션에 사용자 정보 저장 (httpOnly 쿠키로 자동 관리)
    req.session["emp_id"] = result["emp_id"]
    req.session["name"] = result["name"]
    req.session["dept"] = result["dept"]
    
    return LoginResponse(
        success=True,
        emp_id=result["emp_id"],
        name=result["name"],
        dept=result["dept"]
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(request: Request):
    """
    사용자 로그아웃
    
    - 세션 쿠키 삭제
    
    Args:
        request: FastAPI Request 객체
    
    Returns:
        로그아웃 메시지
    """
    request.session.clear()
    return LogoutResponse(message="logged out successfully")


@router.get("/session", response_model=SessionResponse)
async def get_session(request: Request):
    """
    현재 세션 정보 조회
    
    - 현재 로그인한 사용자 정보 반환
    - 미인증 사용자는 401 에러 반환
    
    Args:
        request: FastAPI Request 객체
    
    Returns:
        현재 세션의 사용자 정보
    
    Raises:
        HTTPException (401): 미인증 사용자
    """
    emp_info = AuthService.get_current_employee(request.session)
    
    if not emp_info:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    
    return SessionResponse(
        emp_id=emp_info["emp_id"],
        name=emp_info["name"],
        dept=emp_info["dept"]
    )
