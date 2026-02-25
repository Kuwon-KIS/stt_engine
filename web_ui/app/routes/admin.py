"""
Admin routes for user management.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from app.utils.db import get_db
from app.services import admin_service
from app.constants import ADMIN_SESSION_TIMEOUT
import time


router = APIRouter(prefix="/api/admin", tags=["admin"])


# Request models
class AdminAuthRequest(BaseModel):
    password: str


class CreateUserRequest(BaseModel):
    emp_id: str
    name: str
    dept: str


class UpdateQuotaRequest(BaseModel):
    quota_gb: float


# Helper function to check admin session
def check_admin_session(request: Request):
    """Check if user has valid admin session."""
    if "admin_authenticated" not in request.session:
        raise HTTPException(
            status_code=403,
            detail="관리자 인증이 필요합니다."
        )
    
    # Check session timeout
    auth_time = request.session.get("admin_auth_time", 0)
    if time.time() - auth_time > ADMIN_SESSION_TIMEOUT:
        request.session.pop("admin_authenticated", None)
        request.session.pop("admin_auth_time", None)
        raise HTTPException(
            status_code=403,
            detail="관리자 세션이 만료되었습니다. 다시 로그인해주세요."
        )


@router.post("/auth")
async def authenticate_admin(
    request: Request,
    auth_request: AdminAuthRequest
):
    """
    Authenticate admin with password.
    """
    if admin_service.verify_admin_password(auth_request.password):
        request.session["admin_authenticated"] = True
        request.session["admin_auth_time"] = time.time()
        
        return {
            "success": True,
            "message": "관리자 인증 성공"
        }
    else:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "error": "관리자 비밀번호가 올바르지 않습니다."
            }
        )


@router.post("/logout")
async def logout_admin(request: Request):
    """
    Logout admin and clear session.
    """
    request.session.pop("admin_authenticated", None)
    request.session.pop("admin_auth_time", None)
    
    return {
        "success": True,
        "message": "관리자 로그아웃 성공"
    }


@router.post("/users")
async def create_user(
    request: Request,
    user_request: CreateUserRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new user (admin only).
    """
    check_admin_session(request)
    
    result = admin_service.create_user(
        emp_id=user_request.emp_id,
        name=user_request.name,
        dept=user_request.dept,
        db=db
    )
    
    if result["success"]:
        return result
    else:
        return JSONResponse(
            status_code=400,
            content=result
        )


@router.get("/users")
async def get_users(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get list of all users (admin only).
    """
    check_admin_session(request)
    
    users = admin_service.list_users(db)
    
    return {
        "success": True,
        "users": users
    }


@router.patch("/users/{emp_id}/quota")
async def update_user_quota(
    request: Request,
    emp_id: str,
    quota_request: UpdateQuotaRequest,
    db: Session = Depends(get_db)
):
    """
    Update user's storage quota (admin only).
    """
    check_admin_session(request)
    
    result = admin_service.update_user_quota(
        emp_id=emp_id,
        quota_gb=quota_request.quota_gb,
        db=db
    )
    
    if result["success"]:
        return result
    else:
        return JSONResponse(
            status_code=400,
            content=result
        )
