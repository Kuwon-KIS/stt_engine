"""
Pydantic 데이터 모델
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 성능 메트릭 관련
class PerformanceMetrics(BaseModel):
    """성능 측정 메트릭"""
    cpu_percent_avg: float = Field(description="평균 CPU 사용률 (%)")
    cpu_percent_max: float = Field(description="최대 CPU 사용률 (%)")
    ram_mb_avg: float = Field(description="평균 RAM 사용량 (MB)")
    ram_mb_peak: float = Field(description="피크 RAM 사용량 (MB)")
    gpu_vram_mb_current: float = Field(description="현재 GPU VRAM (MB)")
    gpu_vram_mb_peak: float = Field(description="피크 GPU VRAM (MB)")
    gpu_percent: float = Field(description="GPU 유틸리티 (%)")
    processing_time_sec: float = Field(description="처리 시간 (초)")


# 업로드 관련
class FileUploadResponse(BaseModel):
    """파일 업로드 응답"""
    success: bool
    file_id: str
    filename: str
    original_filename: str
    file_size_mb: float
    upload_time_sec: float
    message: Optional[str] = None


class TranscribeRequest(BaseModel):
    """STT 처리 요청"""
    file_id: str
    language: str = Field(default="ko")
    backend: Optional[str] = None
    is_stream: bool = Field(default=False, description="Streaming 모드 사용 여부")
    privacy_removal: bool = Field(default=False, description="개인정보 제거 여부")
    classification: bool = Field(default=False, description="통화 분류 여부")
    ai_agent: bool = Field(default=False, description="AI Agent 처리 여부")
    incomplete_elements_check: bool = Field(default=False, description="불완전판매요소 검증 여부")
    agent_url: Optional[str] = Field(default="", description="Agent 서버 URL")
    agent_request_format: str = Field(default="text_only", description="Agent 요청 형식 (text_only 또는 prompt_based)")


class ProcessingStepsStatus(BaseModel):
    """처리 단계별 완료 여부"""
    stt: bool = Field(description="STT 완료")
    privacy_removal: bool = Field(description="Privacy Removal 완료")
    classification: bool = Field(description="Classification 완료")
    ai_agent: bool = Field(description="AI Agent 완료")


class TranscribeResponse(BaseModel):
    """STT 처리 응답"""
    success: bool
    file_id: str
    filename: str
    text: str
    language: str
    duration_sec: float
    processing_time_sec: float
    backend: str
    word_count: Optional[int] = None  # 글자 수
    performance: Optional[PerformanceMetrics] = None  # 성능 메트릭
    processing_steps: Optional[ProcessingStepsStatus] = None  # 처리 단계 (NEW)
    privacy_removal: Optional[Dict[str, Any]] = None  # Privacy Removal 결과 (NEW)
    classification: Optional[Dict[str, Any]] = None  # Classification 결과 (NEW)
    error_code: Optional[str] = None
    failure_reason: Optional[dict] = None


# 배치 관련
class BatchFile(BaseModel):
    """배치 파일 정보"""
    name: str
    path: str
    size_mb: float
    modified: datetime
    status: str = "pending"


class BatchFileListResponse(BaseModel):
    """배치 파일 목록 응답"""
    total: int
    files: List[BatchFile]


class BatchStartRequest(BaseModel):
    """배치 처리 시작 요청"""
    path: str = Field(default="/app/data/batch_input", description="배치 입력 파일 디렉토리 (절대 경로)")
    extension: str = Field(default=".wav")
    language: str = Field(default="ko")
    parallel_count: int = Field(default=2, ge=1, le=8)
    privacy_removal: bool = Field(default=False, description="개인정보 제거 여부")
    classification: bool = Field(default=False, description="통화 분류 여부")
    ai_agent: bool = Field(default=False, description="AI Agent 처리 여부")
    incomplete_elements_check: bool = Field(default=False, description="불완전판매요소 검증 여부")
    agent_url: Optional[str] = Field(default="", description="Agent 서버 URL")
    agent_request_format: str = Field(default="text_only", description="Agent 요청 형식 (text_only 또는 prompt_based)")


class BatchStartResponse(BaseModel):
    """배치 처리 시작 응답"""
    batch_id: str
    total_files: int
    status: str


class BatchFileInfo(BaseModel):
    """배치 파일 정보"""
    name: str
    status: str
    processing_time_sec: Optional[float] = None
    error_message: Optional[str] = None
    result_text: Optional[str] = None
    duration_sec: Optional[float] = None
    word_count: Optional[int] = None


class BatchProgressResponse(BaseModel):
    """배치 진행 상황"""
    batch_id: str
    total: int
    completed: int
    failed: int
    in_progress: int
    current_file: Optional[str] = None
    estimated_remaining_sec: float
    files: List[BatchFileInfo]


# 결과 관련
class TranscriptionResult(BaseModel):
    """처리 결과"""
    file_id: str
    filename: str
    original_filename: str
    text: str
    language: str
    duration_sec: float
    processing_time_sec: float
    backend: str
    file_size_mb: float
    created_at: datetime
    status: str


class ResultExportRequest(BaseModel):
    """결과 내보내기 요청"""
    file_id: str
    format: str = Field(default="txt")  # txt, json
