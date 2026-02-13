"""
Pydantic 데이터 모델
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

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
    path: str = Field(default="/app/web_ui/data/batch_input", description="배치 입력 파일 디렉토리 (절대 경로)")
    extension: str = Field(default=".wav")
    language: str = Field(default="ko")
    parallel_count: int = Field(default=2, ge=1, le=8)


class BatchStartResponse(BaseModel):
    """배치 처리 시작 응답"""
    batch_id: str
    total_files: int
    status: str


class BatchProgressResponse(BaseModel):
    """배치 진행 상황"""
    batch_id: str
    total: int
    completed: int
    failed: int
    in_progress: int
    current_file: Optional[str] = None
    estimated_remaining_sec: float
    files: List[dict]


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
