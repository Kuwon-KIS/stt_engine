"""
STT Engine API Pydantic Models

응답 및 요청 데이터 스키마 정의
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# Processing Steps Status
# ============================================================================

class ProcessingStepsStatus(BaseModel):
    """각 처리 단계별 완료 여부"""
    stt: bool = Field(True, description="STT 완료 여부")
    privacy_removal: bool = Field(False, description="Privacy Removal 완료 여부")
    classification: bool = Field(False, description="Classification 완료 여부")
    element_detection: bool = Field(False, description="요소 탐지 완료 여부")
    
    class Config:
        example = {
            "stt": True,
            "privacy_removal": True,
            "classification": False,
            "element_detection": False
        }


# ============================================================================
# Privacy Removal Result
# ============================================================================

class PrivacyRemovalResult(BaseModel):
    """Privacy Removal 결과"""
    privacy_exist: str = Field(
        ..., 
        description="개인정보 존재 여부 (Y/N)",
        pattern="^[YN]$"
    )
    exist_reason: str = Field(
        default="",
        description="개인정보 존재 사유 (예: 전화번호, 주소 등)"
    )
    text: str = Field(
        ...,
        description="개인정보 제거된 텍스트"
    )
    privacy_types: Optional[List[str]] = Field(
        default=None,
        description="발견된 개인정보 유형 목록"
    )
    
    class Config:
        example = {
            "privacy_exist": "Y",
            "exist_reason": "전화번호: 010-1234-5678 포함",
            "text": "안녕하세요. 제 전화번호는 [전화번호] 입니다.",
            "privacy_types": ["phone"]
        }


# ============================================================================
# Classification Result
# ============================================================================

class ClassificationResult(BaseModel):
    """Classification 결과"""
    code: str = Field(
        ...,
        description="분류 코드 (CLASS_PRE_SALES, CLASS_GENERAL 등)"
    )
    category: str = Field(
        ...,
        description="카테고리명 (사용자 친화적)"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="신뢰도 (0-100)"
    )
    reason: Optional[str] = Field(
        default=None,
        description="분류 사유"
    )
    
    class Config:
        example = {
            "code": "CLASS_PRE_SALES",
            "category": "사전판매",
            "confidence": 85.5,
            "reason": "제품 구매 의사 및 가격 문의 포함"
        }


# ============================================================================
# AI Agent Result
# ============================================================================

class AIAgentResult(BaseModel):
    """AI Agent 처리 결과"""
    agent_response: Optional[str] = Field(
        default=None,
        description="Agent의 응답 텍스트"
    )
    agent_type: Optional[str] = Field(
        default=None,
        description="사용된 Agent 타입 (external, vllm, dummy)"
    )
    chat_thread_id: Optional[str] = Field(
        default=None,
        description="채팅 스레드 ID (대화 연속성)"
    )
    processing_time_sec: Optional[float] = Field(
        default=None,
        description="처리 시간 (초)"
    )
    extracted_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="추출된 정보"
    )
    action_items: Optional[List[str]] = Field(
        default=None,
        description="액션 항목"
    )
    summary: Optional[str] = Field(
        default=None,
        description="통화 요약"
    )
    sentiment: Optional[str] = Field(
        default=None,
        description="감정 분석 결과"
    )
    
    class Config:
        example = {
            "extracted_info": {
                "product": "스마트폰",
                "price_range": "100만원대",
                "customer_interest": "high"
            },
            "action_items": [
                "고객 폴로우업 일정 확인",
                "제품 스펙 안내 메일 발송"
            ],
            "summary": "신규 고객의 스마트폰 제품 구매 상담",
            "sentiment": "positive"
        }


# ============================================================================
# Memory Info
# ============================================================================

class MemoryInfo(BaseModel):
    """메모리 상태 정보"""
    available_mb: float = Field(..., description="사용 가능한 메모리 (MB)")
    used_percent: float = Field(..., ge=0.0, le=100.0, description="메모리 사용률 (%)")
    
    class Config:
        example = {
            "available_mb": 8192.5,
            "used_percent": 45.2
        }


# ============================================================================
# Performance Metrics
# ============================================================================

class PerformanceMetrics(BaseModel):
    """성능 지표"""
    cpu_percent: Optional[float] = Field(default=None, description="CPU 사용률 (%)")
    memory_mb: Optional[float] = Field(default=None, description="메모리 사용량 (MB)")
    gpu_percent: Optional[float] = Field(default=None, description="GPU 사용률 (%)")
    
    class Config:
        example = {
            "cpu_percent": 45.2,
            "memory_mb": 2048.5,
            "gpu_percent": 30.5
        }


# ============================================================================
# Transcribe Response (단건)
# ============================================================================

class TranscribeResponse(BaseModel):
    """음성인식 응답"""
    success: bool = Field(..., description="처리 성공 여부")
    text: str = Field(..., description="인식된 텍스트")
    language: str = Field(..., description="감지된 언어 코드")
    duration: Optional[float] = Field(None, description="오디오 길이 (초)")
    backend: str = Field(..., description="사용된 백엔드")
    
    # 파일 정보
    file_path: Optional[str] = Field(None, description="처리한 파일 경로")
    file_size_mb: float = Field(..., description="파일 크기 (MB)")
    
    # Dummy Fallback 정보
    is_dummy: bool = Field(False, description="STT Dummy fallback 여부")
    dummy_reason: Optional[str] = Field(None, description="STT Dummy 사용 이유")
    is_agent_dummy: bool = Field(False, description="Agent Dummy fallback 여부")
    agent_dummy_reason: Optional[str] = Field(None, description="Agent Dummy 사용 이유")
    is_partial_failure: bool = Field(False, description="부분 실패 여부 (STT는 성공하나 Agent 실패)")
    partial_failure_reason: Optional[str] = Field(None, description="부분 실패 사유")
    
    # 선택적 처리 결과
    privacy_removal: Optional[PrivacyRemovalResult] = Field(
        None,
        description="Privacy Removal 결과"
    )
    classification: Optional[ClassificationResult] = Field(
        None,
        description="Classification 결과"
    )
    
    # 불완전판매요소 검증 결과
    incomplete_elements: Optional[Dict[str, Any]] = Field(
        None,
        description="불완전판매요소 검증 결과"
    )
    
    # 요소 탐지 결과 (불완전판매, 부당권유 판매 등)
    element_detection: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="요소 탐지 결과 (불완전판매, 부당권유 판매 등)"
    )
    element_detection_api_type: Optional[str] = Field(
        None,
        description="요소 탐지 API 방식 (external, local)"
    )
    element_detection_llm_type: Optional[str] = Field(
        None,
        description="요소 탐지 LLM 타입 (local 모드 시: openai, vllm, ollama)"
    )
    
    # 에러 정보
    error: Optional[str] = Field(None, description="에러 메시지")
    error_type: Optional[str] = Field(None, description="에러 타입")
    
    # 처리 단계 메타데이터
    processing_steps: ProcessingStepsStatus = Field(
        ...,
        description="각 단계별 처리 상태"
    )
    
    # 성능 정보
    processing_time_seconds: float = Field(..., description="처리 시간 (초)")
    processing_mode: Optional[str] = Field(
        "normal",
        description="처리 모드 (normal/streaming)"
    )
    memory_info: Optional[MemoryInfo] = Field(None, description="메모리 상태")
    performance: Optional[PerformanceMetrics] = Field(None, description="성능 지표")
    
    class Config:
        example = {
            "success": True,
            "text": "안녕하세요, 제품 구매 문의입니다.",
            "language": "ko",
            "duration": 5.2,
            "backend": "faster-whisper",
            "file_path": "/app/audio/test.wav",
            "file_size_mb": 1.5,
            "is_dummy": False,
            "is_agent_dummy": False,
            "is_partial_failure": False,
            "privacy_removal": {
                "privacy_exist": "N",
                "exist_reason": "",
                "text": "안녕하세요, 제품 구매 문의입니다."
            },
            "classification": {
                "code": "CLASS_PRE_SALES",
                "category": "사전판매",
                "confidence": 92.3,
                "reason": "제품 구매 의사 표현"
            },
            "processing_steps": {
                "stt": True,
                "privacy_removal": True,
                "classification": True,
                "ai_agent": False
            },
            "processing_time_seconds": 8.5,
            "processing_mode": "normal",
            "file_size_mb": 1.5,
            "memory_info": {
                "available_mb": 8192.5,
                "used_percent": 45.2
            }
        }


# ============================================================================
# Error Response
# ============================================================================

class ErrorDetail(BaseModel):
    """에러 상세 정보"""
    code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    details: Optional[Dict[str, Any]] = Field(None, description="추가 상세 정보")


class ErrorResponse(BaseModel):
    """에러 응답"""
    success: bool = Field(False, description="처리 성공 여부")
    error: ErrorDetail = Field(..., description="에러 정보")
    processing_steps: ProcessingStepsStatus = Field(
        ...,
        description="처리된 단계까지의 상태"
    )
    
    class Config:
        example = {
            "success": False,
            "error": {
                "code": "STT_MEMORY_ERROR",
                "message": "메모리 부족으로 처리할 수 없습니다.",
                "details": {
                    "available_memory_mb": 512.0,
                    "required_memory_mb": 2048.0
                }
            },
            "processing_steps": {
                "stt": False,
                "privacy_removal": False,
                "classification": False,
                "ai_agent": False
            }
        }


# ============================================================================
# Batch Processing
# ============================================================================

class BatchFileResult(BaseModel):
    """배치 파일 처리 결과"""
    filename: str = Field(..., description="파일명")
    filepath: str = Field(..., description="파일 경로")
    status: str = Field(..., description="처리 상태 (pending/processing/done/error)")
    result: Optional[TranscribeResponse] = Field(None, description="처리 결과")
    error: Optional[ErrorDetail] = Field(None, description="에러 정보 (실패 시)")
    processing_time_seconds: Optional[float] = Field(None, description="처리 시간")


class BatchProgress(BaseModel):
    """배치 진행 상황"""
    total: int = Field(..., description="전체 파일 개수")
    completed: int = Field(..., description="완료된 파일 개수")
    failed: int = Field(..., description="실패한 파일 개수")
    in_progress: int = Field(..., description="처리 중인 파일 개수")
    pending: int = Field(..., description="대기 중인 파일 개수")
    progress_percent: float = Field(..., ge=0.0, le=100.0, description="진행률 (%)")


class BatchResponse(BaseModel):
    """배치 처리 응답"""
    batch_id: str = Field(..., description="배치 작업 ID")
    status: str = Field(..., description="작업 상태")
    files: List[BatchFileResult] = Field(..., description="파일 처리 결과")
    progress: BatchProgress = Field(..., description="진행 상황")
    created_at: datetime = Field(..., description="작업 생성 시간")
    started_at: Optional[datetime] = Field(None, description="작업 시작 시간")
    completed_at: Optional[datetime] = Field(None, description="작업 완료 시간")
    total_processing_time_seconds: Optional[float] = Field(None, description="전체 처리 시간")
    
    class Config:
        example = {
            "batch_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "completed",
            "files": [
                {
                    "filename": "test1.wav",
                    "filepath": "/app/audio/test1.wav",
                    "status": "done",
                    "result": {
                        "success": True,
                        "text": "...",
                    },
                    "processing_time_seconds": 5.2
                }
            ],
            "progress": {
                "total": 5,
                "completed": 5,
                "failed": 0,
                "in_progress": 0,
                "pending": 0,
                "progress_percent": 100.0
            },
            "created_at": "2024-02-20T10:30:00",
            "started_at": "2024-02-20T10:31:00",
            "completed_at": "2024-02-20T10:40:30",
            "total_processing_time_seconds": 570.5
        }
