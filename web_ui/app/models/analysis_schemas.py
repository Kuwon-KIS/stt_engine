"""
분석 시스템 Pydantic 모델
Phase 3: 분석 요청, 진행률, 결과
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AnalysisStartRequest(BaseModel):
    """분석 시작 요청"""
    folder_path: str = Field(..., description="분석할 폴더 경로")
    include_classification: bool = Field(True, description="음성 분류 포함")
    include_validation: bool = Field(True, description="불완전판매요소 검증 포함")
    force_reanalysis: bool = Field(False, description="강제 재분석 여부")
    
    class Config:
        json_schema_extra = {
            "example": {
                "folder_path": "2026-02-20",
                "include_classification": True,
                "include_validation": True,
                "force_reanalysis": False
            }
        }


class AnalysisStartResponse(BaseModel):
    """분석 시작 응답"""
    success: bool = Field(..., description="성공 여부")
    job_id: str = Field(..., description="분석 작업 ID")
    message: str = Field(..., description="메시지")
    status: str = Field(default="started", description="상태 (started, unchanged)")
    analysis_available: bool = Field(default=True, description="분석 가능 여부")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "job_id": "job_123456",
                "message": "분석 시작됨",
                "status": "started",
                "analysis_available": True
            }
        }


class AnalysisProgressResponse(BaseModel):
    """분석 진행률 응답"""
    job_id: str = Field(..., description="분석 작업 ID")
    status: str = Field(..., description="상태 (pending, processing, completed, failed)")
    progress: int = Field(..., ge=0, le=100, description="진행률 (0-100)")
    current_file: Optional[str] = Field(None, description="현재 처리 중인 파일")
    total_files: int = Field(..., description="전체 파일 수")
    processed_files: int = Field(..., description="처리 완료된 파일 수")
    error_message: Optional[str] = Field(None, description="에러 메시지")
    started_at: datetime = Field(..., description="시작 시간")
    updated_at: datetime = Field(..., description="업데이트 시간")
    estimated_time_remaining: Optional[int] = Field(None, description="예상 남은 시간 (초)")
    results: Optional[List[dict]] = Field(default_factory=list, description="분석 결과 목록")


class TranscriptionResult(BaseModel):
    """음성 인식 결과"""
    filename: str = Field(..., description="파일명")
    text: str = Field(..., description="인식된 텍스트")
    confidence: float = Field(..., ge=0, le=1, description="신뢰도")
    duration: float = Field(..., description="음성 길이 (초)")


class ClassificationResult(BaseModel):
    """분류 결과"""
    category: str = Field(..., description="분류 카테고리")
    confidence: float = Field(..., ge=0, le=1, description="신뢰도")
    keywords: List[str] = Field(default_factory=list, description="키워드")


class ValidationResult(BaseModel):
    """불완전판매요소 검증 결과"""
    issues_found: bool = Field(..., description="이슈 발견 여부")
    risk_level: str = Field(..., description="위험도 (low, medium, high)")
    issues: List[dict] = Field(default_factory=list, description="발견된 이슈 목록")


class AnalysisResult(BaseModel):
    """전체 분석 결과"""
    job_id: str = Field(..., description="분석 작업 ID")
    filename: str = Field(..., description="파일명")
    status: str = Field(..., description="상태")
    transcription: Optional[TranscriptionResult] = Field(None, description="음성 인식 결과")
    classification: Optional[ClassificationResult] = Field(None, description="분류 결과")
    validation: Optional[ValidationResult] = Field(None, description="검증 결과")
    processed_at: datetime = Field(..., description="처리 시간")
    duration: float = Field(..., description="처리 소요 시간 (초)")


class AnalysisResultListResponse(BaseModel):
    """분석 결과 목록 응답"""
    job_id: str = Field(..., description="분석 작업 ID")
    folder_path: str = Field(..., description="폴더 경로")
    status: str = Field(..., description="전체 상태")
    total_files: int = Field(..., description="전체 파일 수")
    completed_files: int = Field(..., description="완료된 파일 수")
    failed_files: int = Field(..., description="실패한 파일 수")
    results: List[AnalysisResult] = Field(default_factory=list, description="분석 결과 목록")
    started_at: datetime = Field(..., description="시작 시간")
    completed_at: Optional[datetime] = Field(None, description="완료 시간")
