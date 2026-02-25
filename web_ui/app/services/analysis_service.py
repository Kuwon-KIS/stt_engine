"""
분석 시스템 서비스
Phase 3: 분석 작업 관리 및 실행
"""

import asyncio
import uuid
import json
import hashlib
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
import aiohttp

from app.models.database import Employee, FileUpload, AnalysisJob, AnalysisResult, AnalysisProgress
from app.models.analysis_schemas import (
    AnalysisStartRequest, AnalysisStartResponse, AnalysisProgressResponse,
    AnalysisResultListResponse, TranscriptionResult, ClassificationResult, ValidationResult
)
from app.utils.file_utils import get_user_upload_dir
from app.services.stt_service import stt_service
from config import STT_API_URL, MAX_CONCURRENT_ANALYSIS

# Test configuration - set to 0 to disable, or value between 0.0-1.0 for failure rate
TEST_FAILURE_RATE = 0.25 # 0.25 = 25% failure rate for testing fallback (dummy) responses only


class AnalysisService:
    """분석 서비스"""
    
    # 진행 중인 작업 추적
    _jobs: Dict[str, Dict] = {}
    
    # In-memory tracker for currently processing files
    # Format: {job_id: {"file1.wav", "file2.wav"}} - set of files being processed concurrently
    _current_processing: Dict[str, set] = {}
    
    @staticmethod
    def calculate_files_hash(file_list: List[str]) -> str:
        """
        파일 목록의 해시 계산
        
        Args:
            file_list: 파일명 목록
        
        Returns:
            SHA256 해시 (16진수 문자열)
        """
        # 정렬하여 일관성 보장
        sorted_files = sorted(file_list)
        file_string = '|'.join(sorted_files)
        return hashlib.sha256(file_string.encode()).hexdigest()
    
    @staticmethod
    def start_analysis(
        emp_id: str,
        request: AnalysisStartRequest,
        db: Session
    ) -> AnalysisStartResponse:
        """
        분석 시작
        
        Args:
            emp_id: 사번
            request: 분석 요청
            db: DB 세션
        
        Returns:
            AnalysisStartResponse
        """
        try:
            # 사용자 검증
            employee = db.query(Employee).filter(
                Employee.emp_id == emp_id
            ).first()
            if not employee:
                raise ValueError("사용자를 찾을 수 없습니다")
            
            # 폴더 내 파일 확인
            files = db.query(FileUpload).filter(
                FileUpload.emp_id == emp_id,
                FileUpload.folder_path == request.folder_path
            ).all()
            
            if not files:
                raise ValueError("분석할 파일이 없습니다")
            
            # 파일 목록과 해시 계산 (중복 제거)
            file_list = list(set([f.filename for f in files]))  # 중복 제거
            current_hash = AnalysisService.calculate_files_hash(file_list)
            
            # 마지막 완료된 분석 찾기
            last_job = db.query(AnalysisJob).filter(
                AnalysisJob.emp_id == emp_id,
                AnalysisJob.folder_path == request.folder_path,
                AnalysisJob.status == "completed"
            ).order_by(AnalysisJob.created_at.desc()).first()
            
            # 형상 미변경 & 강제 재분석 아님
            if last_job and last_job.files_hash == current_hash and not request.force_reanalysis:
                return AnalysisStartResponse(
                    success=True,
                    job_id=last_job.job_id,
                    message="이미 분석이 완료되었습니다. 이력을 확인하시거나 강제 재분석을 요청하세요.",
                    status="unchanged",
                    analysis_available=False
                )
            
            # 작업 ID 생성
            job_id = f"job_{uuid.uuid4().hex[:12]}"
            
            # 파일 목록과 옵션 준비
            options = {
                "include_classification": request.include_classification,
                "include_validation": request.include_validation
            }
            
            # DB에 분석 작업 저장
            analysis_job = AnalysisJob(
                job_id=job_id,
                emp_id=emp_id,
                folder_path=request.folder_path,
                file_ids=file_list,
                files_hash=current_hash,
                options=options,
                status="pending",
                started_at=datetime.utcnow()
            )
            db.add(analysis_job)
            db.commit()
            
            # 메모리에 작업 추적
            AnalysisService._jobs[job_id] = {
                "emp_id": emp_id,
                "folder_path": request.folder_path,
                "files": [f.filename for f in files],
                "status": "pending",
                "progress": 0
            }
            
            return AnalysisStartResponse(
                success=True,
                job_id=job_id,
                message="분석이 시작되었습니다",
                status="started",
                analysis_available=True
            )
        
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"분석 시작 실패: {str(e)}")
    
    @staticmethod
    def get_progress(
        job_id: str,
        emp_id: str,
        db: Session
    ) -> AnalysisProgressResponse:
        """
        분석 진행률 조회
        
        Args:
            job_id: 분석 작업 ID
            emp_id: 사번
            db: DB 세션
        
        Returns:
            AnalysisProgressResponse
        """
        try:
            # DB에서 분석 작업 조회
            job = db.query(AnalysisJob).filter(
                AnalysisJob.job_id == job_id,
                AnalysisJob.emp_id == emp_id
            ).first()
            
            if not job:
                raise ValueError("작업을 찾을 수 없습니다")
            
            # 파일 목록과 총 파일 수
            file_ids = job.file_ids or []
            total_files = len(file_ids)
            
            # Get currently processing files (set) from in-memory tracker
            current_processing_files = AnalysisService._current_processing.get(job_id, set())
            
            # 분석 결과 조회
            results = db.query(AnalysisResult).filter(
                AnalysisResult.job_id == job_id
            ).all()
            
            # Count completed and processing files from DB status field
            completed_files = sum(1 for r in results if r.status == 'completed')
            processing_files = sum(1 for r in results if r.status == 'processing')
            processed_files = completed_files + processing_files
            
            # 현재 상태에 따라 진행률 계산
            if job.status == "pending":
                progress = 0
            elif job.status == "processing":
                # For processing jobs: calculate progress based on actual file statuses
                progress = int(((completed_files + processing_files * 0.5) / total_files * 100)) if total_files > 0 else 0
            elif job.status == "completed":
                progress = 100
            else:
                progress = int((processed_files / total_files * 100)) if total_files > 0 else 0
            
            # Build results dictionary for quick lookup
            results_dict = {result.file_id: result for result in results}
            
            # 결과 데이터 준비 - include ALL files with their statuses
            results_list = []
            suspicious_count = 0
            
            # Iterate through all files to show status for each
            for filename in file_ids:
                result = results_dict.get(filename)
                
                if result and result.status == 'completed':
                    # File has completed analysis results
                    file_status = result.status  # 'completed'
                    
                    # Get confidence from metadata
                    confidence = result.stt_metadata.get("confidence", 0.5) if result.stt_metadata else 0.5
                    
                    # Determine risk level based on detection results, NOT confidence
                    # Check improper_detection_results and incomplete_detection_results
                    risk_level = None
                    if result.improper_detection_results:
                        improper_detected = result.improper_detection_results.get("detected", False)
                        if improper_detected:
                            risk_level = "danger"  # 부당권유 발견
                    
                    if result.incomplete_detection_results and not risk_level:
                        incomplete_detected = result.incomplete_detection_results.get("detected", False)
                        if incomplete_detected:
                            risk_level = "warning"  # 불완전판매 발견
                    
                    # Default to safe if no issues detected
                    if not risk_level:
                        risk_level = "safe"
                    
                    result_dict = {
                        "filename": result.file_id,
                        "stt_text": result.stt_text,
                        "status": file_status,
                        "confidence": confidence,
                        "risk_level": risk_level
                    }
                else:
                    # File is pending, processing, or failed - no risk assessment yet
                    file_status = result.status if result else "pending"
                    
                    result_dict = {
                        "filename": filename,
                        "stt_text": None,
                        "status": file_status,
                        "confidence": None,
                        "risk_level": None
                    }
                
                results_list.append(result_dict)
            
            return AnalysisProgressResponse(
                job_id=job_id,
                folder_path=job.folder_path,
                status=job.status,
                progress=progress,
                current_file=list(current_processing_files) if current_processing_files else [],
                total_files=total_files,
                processed_files=completed_files,
                error_message=None,
                started_at=job.started_at,
                updated_at=job.completed_at or datetime.utcnow(),
                estimated_time_remaining=None,
                results=results_list
            )
        
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"진행률 조회 실패: {str(e)}")
    
    @staticmethod
    def get_results(
        job_id: str,
        emp_id: str,
        db: Session
    ) -> AnalysisResultListResponse:
        """
        분석 결과 조회
        
        Args:
            job_id: 분석 작업 ID
            emp_id: 사번
            db: DB 세션
        
        Returns:
            AnalysisResultListResponse
        """
        try:
            # 분석 작업 조회
            job = db.query(AnalysisJob).filter(
                AnalysisJob.job_id == job_id,
                AnalysisJob.emp_id == emp_id
            ).first()
            
            if not job:
                raise ValueError("작업을 찾을 수 없습니다")
            
            # 분석 결과 조회
            results = db.query(AnalysisResult).filter(
                AnalysisResult.job_id == job_id
            ).all()
            
            # 결과 변환
            result_list = []
            for r in results:
                transcription = None
                if r.transcription_text:
                    transcription = TranscriptionResult(
                        filename=r.filename,
                        text=r.transcription_text,
                        confidence=r.transcription_confidence or 0.0,
                        duration=r.audio_duration or 0.0
                    )
                
                classification = None
                if r.classification_category:
                    classification = ClassificationResult(
                        category=r.classification_category,
                        confidence=r.classification_confidence or 0.0,
                        keywords=r.classification_keywords or []
                    )
                
                validation = None
                if r.validation_risk_level:
                    validation = ValidationResult(
                        issues_found=r.validation_issues_found or False,
                        risk_level=r.validation_risk_level,
                        issues=r.validation_issues or []
                    )
                
                result_list.append({
                    "job_id": job_id,
                    "filename": r.filename,
                    "status": r.status,
                    "transcription": transcription,
                    "classification": classification,
                    "validation": validation,
                    "processed_at": r.processed_at,
                    "duration": r.processing_duration or 0.0
                })
            
            return AnalysisResultListResponse(
                job_id=job_id,
                folder_path=job.folder_path,
                status=job.status,
                total_files=job.total_files,
                completed_files=job.completed_files,
                failed_files=job.failed_files,
                results=result_list,
                started_at=job.started_at,
                completed_at=job.completed_at
            )
        
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"결과 조회 실패: {str(e)}")
    
    @staticmethod
    async def process_analysis_async(
        job_id: str,
        emp_id: str,
        folder_path: str,
        files: List[str],
        include_classification: bool,
        include_validation: bool,
        db: Session
    ):
        """
        백그라운드에서 분석 실행 (비동기)
        
        Args:
            job_id: 분석 작업 ID
            emp_id: 사번
            folder_path: 폴더 경로
            files: 파일 목록
            include_classification: 분류 포함
            include_validation: 검증 포함
            db: DB 세션
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"[process_analysis_async] 시작: job_id={job_id}")
            
            # 작업 상태 업데이트
            job = db.query(AnalysisJob).filter(
                AnalysisJob.job_id == job_id
            ).first()
            
            logger.info(f"[process_analysis_async] job 조회 완료: job={job}")
            
            if job:
                job.status = "processing"
                db.commit()
                logger.info(f"[process_analysis_async] job status를 processing으로 업데이트")
            
            total_files = len(files)
            logger.info(f"[process_analysis_async] 처리할 파일 수: {total_files}")
            
            # 각 파일에 대해 결과 생성 (더미 분석)
            for filename in files:
                try:
                    logger.info(f"[process_analysis_async] 파일 처리: {filename}")
                    
                    # 파일 경로
                    user_dir = get_user_upload_dir(emp_id)
                    file_path = user_dir / folder_path / filename
                    logger.info(f"[process_analysis_async] file_path: {file_path}")
                    
                    # 결과 저장
                    result = AnalysisResult(
                        job_id=job_id,
                        file_id=filename,
                        stt_text=f"[샘플 텍스트] {filename}의 음성 인식 결과",
                        stt_metadata={
                            "duration": 120.0,
                            "language": "ko",
                            "confidence": 0.95
                        }
                    )
                    db.add(result)
                    db.commit()
                    logger.info(f"[process_analysis_async] 결과 저장 완료: {filename}")
                
                except Exception as e:
                    logger.error(f"[process_analysis_async] 파일 처리 실패: {filename}, {str(e)}", exc_info=True)
                    # 파일 처리 중 에러
                    result = AnalysisResult(
                        job_id=job_id,
                        file_id=filename,
                        stt_text=None
                    )
                    db.add(result)
                    db.commit()
            
            # 작업 완료 표시
            if job:
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                db.commit()
                logger.info(f"[process_analysis_async] job status를 completed로 업데이트")
            
            logger.info(f"[process_analysis_async] 완료: job_id={job_id}")
        
        except Exception as e:
            logger.error(f"[process_analysis_async] 함수 에러: {str(e)}", exc_info=True)
            # 작업 실패
            job = db.query(AnalysisJob).filter(
                AnalysisJob.job_id == job_id
            ).first()
            if job:
                job.status = "failed"
                job.completed_at = datetime.utcnow()
                db.commit()
                logger.info(f"[process_analysis_async] job status를 failed로 업데이트 (exception 발생)")
    
    @staticmethod
    def get_analysis_history(
        emp_id: str,
        folder_path: Optional[str] = None,
        db: Session = None
    ) -> dict:
        """
        분석 이력 조회
        
        Args:
            emp_id: 사번
            folder_path: 폴더 경로 (선택사항)
            db: DB 세션
        
        Returns:
            분석 이력 목록
        """
        try:
            # 기본 쿼리
            query = db.query(AnalysisJob).filter(AnalysisJob.emp_id == emp_id)
            
            # 폴더 경로로 필터링
            if folder_path:
                query = query.filter(AnalysisJob.folder_path == folder_path)
            
            # 최신순 정렬
            jobs = query.order_by(AnalysisJob.created_at.desc()).all()
            
            # 결과 구성
            history_list = []
            for job in jobs:
                # 각 job별 결과 개수 조회
                result_count = db.query(AnalysisResult).filter(
                    AnalysisResult.job_id == job.job_id
                ).count()
                
                history_list.append({
                    "job_id": job.job_id,
                    "folder_path": job.folder_path,
                    "status": job.status,
                    "total_files": len(job.file_ids) if job.file_ids else 0,
                    "completed_files": result_count,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None
                })
            
            return {
                "success": True,
                "data": history_list,
                "count": len(history_list)
            }
        
        except Exception as e:
            raise Exception(f"분석 이력 조회 실패: {str(e)}")    
    @staticmethod
    def process_analysis_sync(
        job_id: str,
        emp_id: str,
        folder_path: str,
        files: List[str],
        include_classification: bool,
        include_validation: bool
    ):
        """
        백그라운드에서 분석 실행 (동기 함수)
        FastAPI의 BackgroundTasks에 의해 별도 스레드에서 실행됨
        동시(concurrent) 처리를 위해 asyncio.gather 사용
        
        Args:
            job_id: 분석 작업 ID
            emp_id: 사번
            folder_path: 폴더 경로
            files: 파일 목록
            include_classification: 분류 포함
            include_validation: 검증 포함
        """
        import logging
        from app.utils.db import SessionLocal
        
        logger = logging.getLogger(__name__)
        new_db = SessionLocal()
        
        try:
            logger.info(f"[process_analysis_sync] 분석 시작 (동시 처리): job_id={job_id}, files={files}")
            
            # 작업 상태 업데이트
            job = new_db.query(AnalysisJob).filter(
                AnalysisJob.job_id == job_id
            ).first()
            
            if job:
                job.status = "processing"
                new_db.commit()
                logger.info(f"[process_analysis_sync] job status: pending → processing")
            
            total_files = len(files)
            logger.info(f"[process_analysis_sync] 처리할 파일 수: {total_files} (동시 처리)")
            logger.info(f"[process_analysis_sync] 최대 동시 처리 개수: {MAX_CONCURRENT_ANALYSIS}")
            
            # === Create pending result rows upfront ===
            # 각 파일에 대해 pending 상태의 result row 미리 생성 (재실행 시는 이미 리셋됨)
            logger.info(f"[process_analysis_sync] pending result rows 확인 중...")
            for filename in files:
                existing = new_db.query(AnalysisResult).filter(
                    AnalysisResult.job_id == job_id,
                    AnalysisResult.file_id == filename
                ).first()
                
                if not existing:
                    # 새로운 파일인 경우에만 생성
                    pending_result = AnalysisResult(
                        job_id=job_id,
                        file_id=filename,
                        status='pending',
                        stt_text=None,
                        stt_metadata=None
                    )
                    new_db.add(pending_result)
                    logger.info(f"[process_analysis_sync] Created new result row for {filename}")
                else:
                    logger.info(f"[process_analysis_sync] Result row already exists for {filename} (status={existing.status})")
            
            new_db.commit()
            logger.info(f"[process_analysis_sync] Ready to process {total_files} files")
            
            # Cycle through confidence values to ensure all risk levels appear (for testing)
            test_confidence_values = [0.2, 0.45, 0.8]  # danger, warning, safe
            
            # 비동기 함수로 파일 처리 (결과는 즉시 DB에 저장)
            async def process_single_file(idx: int, filename: str, semaphore: asyncio.Semaphore):
                """개별 파일 처리 (세마포어로 동시성 제어, 결과 즉시 저장)"""
                import time
                start_wait = time.time()
                logger.info(f"[process_analysis_sync] 파일 대기 시작: {filename} (idx={idx}, semaphore_value={semaphore._value})")
                
                async with semaphore:  # 세마포어로 동시 실행 개수 제한
                    wait_time = time.time() - start_wait
                    logger.info(f"[process_analysis_sync] 파일 처리 시작: {filename} (idx={idx}, 대기시간={wait_time:.2f}s, semaphore_value={semaphore._value})")
                    
                    # === Update status to 'processing' in DB ===
                    from app.utils.db import SessionLocal as TempSessionLocal
                    temp_db = TempSessionLocal()
                    try:
                        result = temp_db.query(AnalysisResult).filter(
                            AnalysisResult.job_id == job_id,
                            AnalysisResult.file_id == filename
                        ).first()
                        
                        if result:
                            result.status = 'processing'
                            temp_db.commit()
                            logger.info(f"[process_analysis_sync] {filename} status: pending → processing")
                    finally:
                        temp_db.close()
                    
                    # in-memory tracking 업데이트 (set에 파일 추가)
                    if job_id not in AnalysisService._current_processing:
                        AnalysisService._current_processing[job_id] = set()
                    AnalysisService._current_processing[job_id].add(filename)
                    
                    db_session = None
                    start_time = time.time()
                    try:
                        # 파일 경로
                        user_dir = get_user_upload_dir(emp_id)
                        file_path = user_dir / folder_path / filename
                        
                        # STT API 호출 (순서: STT → privacy_removal → agent)
                        stt_result = await stt_service.transcribe_local_file(
                            file_path=str(file_path),
                            language="ko",
                            is_stream=False,
                            privacy_removal=True,  # privacy_removal 항상 수행
                            classification=False,
                            ai_agent=include_classification,  # agent는 선택에 따라
                            incomplete_elements_check=include_validation
                        )
                        
                        # === TEST MODE: Simulate failure on fallback (dummy response) ===
                        # STT 호출 실패 후 fallback(dummy)일 때만 TEST MODE 적용
                        if not stt_result.get('success') and TEST_FAILURE_RATE > 0 and random.random() < TEST_FAILURE_RATE:
                            logger.warning(f"[TEST MODE] Simulating failure on fallback for {filename} (failure_rate={TEST_FAILURE_RATE})")
                            stt_result = {
                                "success": False,
                                "error": "simulated_test_failure_on_fallback",
                                "message": f"테스트 모드 실패 - fallback에서 시뮬레이션 (failure_rate={TEST_FAILURE_RATE})"
                            }
                        
                        logger.info(f"[process_analysis_sync] STT 완료: {filename}, success={stt_result.get('success')}")
                        
                        # 결과를 즉시 DB에 저장 (동시성 제어 필요)
                        from app.utils.db import SessionLocal
                        db_session = SessionLocal()
                        
                        try:
                            # DB에서 기존 result를 조회 (pending 상태로 미리 생성되어 있어야 함)
                            existing_result = db_session.query(AnalysisResult).filter(
                                AnalysisResult.job_id == job_id,
                                AnalysisResult.file_id == filename
                            ).first()
                            
                            if stt_result.get('success'):
                                # STT 성공
                                confidence = test_confidence_values[idx % len(test_confidence_values)]
                                
                                if existing_result:
                                    # 기존 result 업데이트
                                    existing_result.status = 'completed'
                                    existing_result.stt_text = stt_result.get('text', '')
                                    existing_result.stt_metadata = {
                                        "duration": stt_result.get('duration_sec', 0),
                                        "language": stt_result.get('language', 'ko'),
                                        "backend": stt_result.get('backend', 'unknown'),
                                        "processing_steps": stt_result.get('processing_steps', {}),
                                        "confidence": confidence
                                    }
                                    result = existing_result
                                else:
                                    # 없으면 새로 생성
                                    result = AnalysisResult(
                                        job_id=job_id,
                                        file_id=filename,
                                        status='completed',
                                        stt_text=stt_result.get('text', ''),
                                        stt_metadata={
                                            "duration": stt_result.get('duration_sec', 0),
                                            "language": stt_result.get('language', 'ko'),
                                            "backend": stt_result.get('backend', 'unknown'),
                                            "processing_steps": stt_result.get('processing_steps', {}),
                                            "confidence": confidence
                                        }
                                    )
                                    db_session.add(result)
                            else:
                                # STT 실패
                                if existing_result:
                                    existing_result.status = 'failed'
                                    existing_result.stt_text = None
                                    existing_result.stt_metadata = {
                                        "error": stt_result.get('error', 'unknown'),
                                        "message": stt_result.get('message', '처리 실패')
                                    }
                                    result = existing_result
                                else:
                                    result = AnalysisResult(
                                        job_id=job_id,
                                        file_id=filename,
                                        status='failed',
                                        stt_text=None,
                                        stt_metadata={
                                            "error": stt_result.get('error', 'unknown'),
                                            "message": stt_result.get('message', '처리 실패')
                                        }
                                    )
                                    db_session.add(result)
                            
                            db_session.commit()
                            elapsed = time.time() - start_time
                            logger.info(f"[process_analysis_sync] 결과 즉시 저장 완료: {filename}, status={result.status} (총처리시간={elapsed:.2f}s)")
                        
                        except Exception as db_error:
                            db_session.rollback()
                            logger.error(f"[process_analysis_sync] DB 저장 실패: {filename}, {str(db_error)}", exc_info=True)
                            raise
                        finally:
                            db_session.close()
                            # in-memory tracking에서 파일 제거 (처리 완료)
                            if job_id in AnalysisService._current_processing:
                                AnalysisService._current_processing[job_id].discard(filename)
                        
                        return {
                            "idx": idx,
                            "filename": filename,
                            "stt_result": stt_result,
                            "error": None,
                            "saved": True
                        }
                    
                    except Exception as e:
                        logger.error(f"[process_analysis_sync] 파일 처리 중 에러: {filename}, {str(e)}", exc_info=True)
                        elapsed = time.time() - start_time
                        logger.error(f"[process_analysis_sync] 파일 처리 실패 시간: {filename} (처리시간={elapsed:.2f}s)")
                        
                        # 에러 결과도 DB에 저장
                        if db_session is None:
                            from app.utils.db import SessionLocal
                            db_session = SessionLocal()
                        
                        try:
                            result = AnalysisResult(
                                job_id=job_id,
                                file_id=filename,
                                stt_text=None,
                                stt_metadata={"error": str(e)}
                            )
                            db_session.add(result)
                            db_session.commit()
                            logger.info(f"[process_analysis_sync] 에러 결과 저장: {filename}")
                        
                        except Exception as db_error:
                            db_session.rollback()
                            logger.error(f"[process_analysis_sync] 에러 결과 저장 실패: {str(db_error)}", exc_info=True)
                        finally:
                            db_session.close()
                            # in-memory tracking에서 파일 제거 (처리 완료/실패)
                            if job_id in AnalysisService._current_processing:
                                AnalysisService._current_processing[job_id].discard(filename)
                        
                        return {
                            "idx": idx,
                            "filename": filename,
                            "stt_result": None,
                            "error": str(e),
                            "saved": False
                        }
            
            # 모든 파일을 동시에 처리 (동시성 제어)
            async def process_all_files():
                """모든 파일을 동시에 처리 (세마포어로 동시 개수 제한)"""
                # 세마포어 생성: 동시에 MAX_CONCURRENT_ANALYSIS개만 실행
                semaphore = asyncio.Semaphore(MAX_CONCURRENT_ANALYSIS)
                
                # 모든 파일을 처리할 task 생성
                tasks = [
                    process_single_file(idx, filename, semaphore)
                    for idx, filename in enumerate(files)
                ]
                
                # 모든 task를 동시에 실행 (세마포어로 동시 개수 제한)
                return await asyncio.gather(*tasks)
            
            # asyncio.run으로 동시 처리 실행
            import time as time_module
            batch_start = time_module.time()
            results = asyncio.run(process_all_files())
            batch_elapsed = time_module.time() - batch_start
            logger.info(f"[process_analysis_sync] 모든 파일 처리 완료: {len(results)}개 결과 (총소요시간={batch_elapsed:.2f}s)")
            
            # 결과는 이미 process_single_file에서 즉시 DB에 저장되었으므로 
            # 여기서는 최종 상태만 확인하고 로깅
            saved_count = sum(1 for r in results if r.get("saved", False))
            failed_count = len(results) - saved_count
            logger.info(f"[process_analysis_sync] 저장 완료: {saved_count}개, 실패: {failed_count}개")
            
            # 작업 완료 여부 확인 - 모든 파일이 완료되었는지 체크
            if job:
                # 전체 job의 모든 파일 결과 확인
                all_results = new_db.query(AnalysisResult).filter(
                    AnalysisResult.job_id == job_id
                ).all()
                
                total_count = len(all_results)
                completed_count = sum(1 for r in all_results if r.status in ['completed', 'failed'])
                pending_or_processing = total_count - completed_count
                
                logger.info(f"[process_analysis_sync] Job 전체 상태: {completed_count}/{total_count} 완료, {pending_or_processing} 진행중/대기중")
                
                # 모든 파일이 완료되었을 때만 job을 completed로 표시
                if pending_or_processing == 0:
                    job.status = "completed"
                    job.completed_at = datetime.utcnow()
                    new_db.commit()
                    logger.info(f"[process_analysis_sync] job status: processing → completed (모든 파일 완료)")
                else:
                    # 일부 파일만 완료된 경우 processing 상태 유지
                    logger.info(f"[process_analysis_sync] job status: processing 유지 (아직 {pending_or_processing}개 파일 남음)")

            
            logger.info(f"[process_analysis_sync] 분석 완료 (동시 처리): job_id={job_id}")
        
        except Exception as e:
            logger.error(f"[process_analysis_sync] 분석 중 에러: {str(e)}", exc_info=True)
            # 작업 실패 상태로 업데이트
            try:
                job = new_db.query(AnalysisJob).filter(
                    AnalysisJob.job_id == job_id
                ).first()
                if job:
                    job.status = "failed"
                    job.completed_at = datetime.utcnow()
                    new_db.commit()
                    logger.error(f"[process_analysis_sync] job status: failed")
            except Exception as db_error:
                logger.error(f"[process_analysis_sync] 상태 업데이트 실패: {str(db_error)}")
        
        finally:
            new_db.close()
            logger.info(f"[process_analysis_sync] DB 세션 종료")