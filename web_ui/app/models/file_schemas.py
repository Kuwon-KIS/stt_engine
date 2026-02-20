"""
파일 관련 Pydantic 스키마
Phase 2: 파일 업로드, 목록 조회 등의 요청/응답 모델
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# === 요청 모델 ===

class FileUploadRequest(BaseModel):
    """파일 업로드 요청"""
    folder_name: Optional[str] = Field(
        None,
        description="폴더 이름 (없으면 오늘 날짜 자동 사용)"
    )


# === 응답 모델 ===

class FileInfo(BaseModel):
    """파일 정보"""
    filename: str = Field(..., description="파일명")
    file_size_mb: float = Field(..., description="파일 크기 (MB)")
    uploaded_at: datetime = Field(..., description="업로드 시간")
    
    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    """파일 업로드 응답"""
    success: bool = Field(..., description="성공 여부")
    filename: str = Field(..., description="파일명")
    file_size_mb: float = Field(..., description="파일 크기 (MB)")
    folder_path: str = Field(..., description="폴더 경로")
    uploaded_at: datetime = Field(..., description="업로드 시간")
    message: str = Field(..., description="메시지")


class FileListResponse(BaseModel):
    """파일 목록 조회 응답"""
    folder_path: str = Field(..., description="폴더 경로")
    files: List[FileInfo] = Field(..., description="파일 목록")
    total_size_mb: float = Field(..., description="폴더 총 크기 (MB)")


class FolderListResponse(BaseModel):
    """폴더 목록 조회 응답"""
    folders: List[str] = Field(..., description="폴더 목록")


class FileDeleteResponse(BaseModel):
    """파일 삭제 응답"""
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="메시지")


class FolderCreateResponse(BaseModel):
    """폴더 생성 응답"""
    success: bool = Field(..., description="성공 여부")
    folder_path: str = Field(..., description="생성된 폴더 경로")
    message: str = Field(..., description="메시지")
