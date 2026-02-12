"""
비동기 작업 큐 관리 (간단한 in-memory 구현)
프로덕션에서는 Redis/Celery 권장
"""
import uuid
import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """작업 상태"""
    PENDING = "pending"        # 대기 중
    PROCESSING = "processing"  # 처리 중
    COMPLETED = "completed"    # 완료
    FAILED = "failed"          # 실패
    CANCELLED = "cancelled"    # 취소됨


class TranscribeJob:
    """개별 작업 정보"""
    def __init__(self, file_path: str, language: str = "ko", is_stream: bool = False):
        self.job_id = str(uuid.uuid4())
        self.file_path = file_path
        self.language = language
        self.is_stream = is_stream
        self.status = JobStatus.PENDING
        self.progress = 0  # 0-100
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Dict] = None
        self.error: Optional[str] = None
    
    def to_dict(self):
        """작업 정보를 딕셔너리로 변환"""
        return {
            "job_id": self.job_id,
            "file_path": self.file_path,
            "language": self.language,
            "is_stream": self.is_stream,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error
        }


class TranscribeJobQueue:
    """작업 큐 관리"""
    def __init__(self, max_concurrent: int = 2):
        self.jobs: Dict[str, TranscribeJob] = {}
        self.queue = asyncio.Queue()
        self.max_concurrent = max_concurrent
        self.active_workers = 0
        logger.info(f"[JobQueue] 초기화 완료 (동시 작업: {max_concurrent})")
    
    async def enqueue(self, file_path: str, language: str = "ko", is_stream: bool = False) -> str:
        """작업을 큐에 추가"""
        job = TranscribeJob(file_path, language, is_stream)
        self.jobs[job.job_id] = job
        await self.queue.put(job)
        logger.info(f"[JobQueue] 작업 추가: {job.job_id} (파일: {file_path})")
        return job.job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """작업 상태 조회"""
        job = self.jobs.get(job_id)
        if not job:
            return None
        return job.to_dict()
    
    def get_all_jobs(self) -> Dict[str, Dict]:
        """모든 작업 조회"""
        return {job_id: job.to_dict() for job_id, job in self.jobs.items()}
    
    async def process_job(self, job: TranscribeJob, process_func):
        """작업 처리"""
        try:
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now()
            job.progress = 10
            logger.info(f"[JobQueue] 처리 시작: {job.job_id}")
            
            # 실제 처리 (process_func은 job 객체를 받아서 진행률 업데이트)
            result = await process_func(job)
            
            job.result = result
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.completed_at = datetime.now()
            logger.info(f"[JobQueue] 처리 완료: {job.job_id}")
        
        except asyncio.CancelledError:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now()
            logger.info(f"[JobQueue] 작업 취소됨: {job.job_id}")
        
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now()
            logger.error(f"[JobQueue] 처리 실패: {job.job_id} - {e}", exc_info=True)
    
    async def worker_loop(self, process_func):
        """
        워커 루프 (별도의 asyncio 태스크로 실행)
        큐에서 작업을 가져와서 처리
        """
        while True:
            try:
                # 동시 실행 제한 확인
                if self.active_workers >= self.max_concurrent:
                    await asyncio.sleep(0.5)
                    continue
                
                # 타임아웃으로 큐 확인 (블로킹되지 않도록)
                try:
                    job = self.queue.get_nowait()
                except asyncio.QueueEmpty:
                    await asyncio.sleep(0.5)
                    continue
                
                # 동시 작업 수 증가
                self.active_workers += 1
                logger.info(f"[JobQueue-Worker] 처리 시작 (활성 워커: {self.active_workers})")
                
                # 작업 처리
                await self.process_job(job, process_func)
                
                # 동시 작업 수 감소
                self.active_workers -= 1
                
            except Exception as e:
                logger.error(f"[JobQueue-Worker] 오류 발생: {e}", exc_info=True)
                self.active_workers = max(0, self.active_workers - 1)
                await asyncio.sleep(1)


# 전역 작업 큐
transcribe_queue = TranscribeJobQueue(max_concurrent=2)
