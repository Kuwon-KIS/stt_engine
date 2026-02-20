"""
배치 처리 서비스
"""
import asyncio
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """배치 작업 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FileStatus(str, Enum):
    """파일 처리 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


@dataclass
class BatchFile:
    """배치 파일 정보"""
    name: str
    path: str
    status: str = FileStatus.PENDING.value
    processing_time_sec: Optional[float] = None
    error_message: Optional[str] = None
    result_text: Optional[str] = None
    duration_sec: Optional[float] = None  # 오디오 길이
    word_count: Optional[int] = None  # 글자 수
    performance: Optional[dict] = None  # CPU/RAM/GPU 성능 메트릭
    processing_steps: Optional[dict] = None  # 각 단계별 처리 결과 {stt: done, privacy_removal: done, ...}
    classification: Optional[dict] = None  # 음성 내용 분류 결과
    incomplete_elements: Optional[dict] = None  # 불완전판매요소 검증 결과


@dataclass
class BatchJob:
    """배치 작업 정보"""
    batch_id: str
    files: List[BatchFile]
    status: str = JobStatus.PENDING.value
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processed_count: int = 0
    failed_count: int = 0
    processing_steps_options: Optional[dict] = None  # 요청한 처리 단계 옵션 {privacy_removal: True, classification: True, ...}
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def total(self) -> int:
        return len(self.files)
    
    @property
    def completed(self) -> int:
        return sum(1 for f in self.files if f.status == FileStatus.DONE.value)
    
    @property
    def in_progress(self) -> int:
        return sum(1 for f in self.files if f.status == FileStatus.PROCESSING.value)
    
    @property
    def failed(self) -> int:
        return sum(1 for f in self.files if f.status == FileStatus.ERROR.value)
    
    @property
    def pending(self) -> int:
        return sum(1 for f in self.files if f.status == FileStatus.PENDING.value)
    
    def get_estimated_remaining_sec(self, avg_time_per_file: float = 30) -> float:
        """예상 남은 시간 계산"""
        remaining = self.pending + self.in_progress
        return remaining * avg_time_per_file


class BatchService:
    """배치 처리 서비스"""
    
    def __init__(self):
        self.jobs: dict[str, BatchJob] = {}
    
    def create_job(self, files: List[BatchFile]) -> str:
        """
        배치 작업 생성
        
        Returns:
            배치 ID
        """
        batch_id = str(uuid.uuid4())
        job = BatchJob(batch_id=batch_id, files=files)
        self.jobs[batch_id] = job
        
        logger.info(f"[Batch Service] 배치 작업 생성: {batch_id} ({len(files)}개 파일)")
        return batch_id
    
    def get_job(self, batch_id: str) -> Optional[BatchJob]:
        """배치 작업 조회"""
        return self.jobs.get(batch_id)
    
    def start_job(self, batch_id: str):
        """배치 작업 시작"""
        job = self.get_job(batch_id)
        if job:
            job.status = JobStatus.RUNNING.value
            job.started_at = datetime.now()
            logger.info(f"[Batch Service] 배치 작업 시작: {batch_id}")
    
    def complete_job(self, batch_id: str):
        """배치 작업 완료"""
        job = self.get_job(batch_id)
        if job:
            job.status = JobStatus.COMPLETED.value
            job.completed_at = datetime.now()
            logger.info(f"[Batch Service] 배치 작업 완료: {batch_id} "
                       f"(성공: {job.completed}, 실패: {job.failed})")
    
    def update_file_status(
        self,
        batch_id: str,
        filename: str,
        status: str,
        processing_time_sec: Optional[float] = None,
        error_message: Optional[str] = None,
        result_text: Optional[str] = None,
        duration_sec: Optional[float] = None,
        word_count: Optional[int] = None,
        performance: Optional[dict] = None
    ):
        """파일 처리 상태 업데이트"""
        job = self.get_job(batch_id)
        if job:
            for file in job.files:
                if file.name == filename:
                    file.status = status
                    file.processing_time_sec = processing_time_sec
                    file.error_message = error_message
                    file.result_text = result_text
                    file.duration_sec = duration_sec
                    file.word_count = word_count
                    file.performance = performance
                    
                    if status == FileStatus.DONE.value:
                        logger.info(f"[Batch Service] {filename} 처리 완료 ({processing_time_sec:.2f}초, {word_count}자)")
                    elif status == FileStatus.ERROR.value:
                        logger.error(f"[Batch Service] {filename} 처리 실패: {error_message}")
                    break
    
    async def process_batch(
        self,
        batch_id: str,
        processor_fn: Callable,
        parallel_count: int = 2
    ):
        """
        배치 처리 실행
        
        Args:
            batch_id: 배치 ID
            processor_fn: 파일 처리 함수 (async, file_path 파라미터)
            parallel_count: 동시 처리 수
        """
        job = self.get_job(batch_id)
        if not job:
            logger.error(f"[Batch Service] 배치 작업 없음: {batch_id}")
            return
        
        self.start_job(batch_id)
        
        # 처리할 파일 큐
        pending_files = [f for f in job.files if f.status == FileStatus.PENDING.value]
        
        try:
            # 병렬 처리 (세마포어로 동시성 제한)
            semaphore = asyncio.Semaphore(parallel_count)
            
            async def process_with_limit(file: BatchFile):
                async with semaphore:
                    await self._process_file(batch_id, file, processor_fn)
            
            # 모든 파일 처리
            await asyncio.gather(
                *[process_with_limit(f) for f in pending_files]
            )
        
        except Exception as e:
            logger.error(f"[Batch Service] 배치 처리 중 에러: {e}", exc_info=True)
        
        finally:
            self.complete_job(batch_id)
    
    async def _process_file(
        self,
        batch_id: str,
        file: BatchFile,
        processor_fn: Callable
    ):
        """파일 처리 (내부)"""
        try:
            import time
            
            self.update_file_status(batch_id, file.name, FileStatus.PROCESSING.value)
            
            start_time = time.time()
            result = await processor_fn(file.path)
            processing_time = time.time() - start_time
            
            if result.get("success"):
                # 결과에서 필요한 정보 추출
                result_text = result.get("text", "")
                duration_sec = result.get("duration", None)
                word_count = len(result_text) if result_text else 0
                performance = result.get("performance")  # API 서버로부터 받은 성능 메트릭
                
                self.update_file_status(
                    batch_id,
                    file.name,
                    FileStatus.DONE.value,
                    processing_time_sec=processing_time,
                    result_text=result_text,
                    duration_sec=duration_sec,
                    word_count=word_count,
                    performance=performance
                )
            else:
                error_msg = result.get("message", "알 수 없는 오류")
                self.update_file_status(
                    batch_id,
                    file.name,
                    FileStatus.ERROR.value,
                    error_message=error_msg
                )
        
        except Exception as e:
            logger.error(f"[Batch Service] {file.name} 처리 실패: {e}")
            self.update_file_status(
                batch_id,
                file.name,
                FileStatus.ERROR.value,
                error_message=str(e)
            )
    
    def get_progress(self, batch_id: str) -> Optional[dict]:
        """배치 진행 상황 조회"""
        job = self.get_job(batch_id)
        if not job:
            return None
        
        return {
            "batch_id": batch_id,
            "total": job.total,
            "completed": job.completed,
            "failed": job.failed,
            "in_progress": job.in_progress,
            "pending": job.pending,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "estimated_remaining_sec": job.get_estimated_remaining_sec(),
            "files": [
                {
                    "name": f.name,
                    "status": f.status,
                    "processing_time_sec": f.processing_time_sec,
                    "error_message": f.error_message,
                    "result_text": f.result_text,
                    "duration_sec": f.duration_sec,
                    "word_count": f.word_count
                }
                for f in job.files
            ]
        }


# 싱글톤 인스턴스
batch_service = BatchService()
