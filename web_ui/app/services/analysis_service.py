"""
분석 시스템 서비스
Phase 3: 분석 작업 관리 및 실행
"""

import asyncio
import uuid
import json
import hashlib
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
from config import STT_API_URL


class AnalysisService:
    """분석 서비스"""
    
    # 진행 중인 작업 추적
    _jobs: Dict[str, Dict] = {}
    
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
            
            # 파일 목록과 해시 계산
            file_list = [f.filename for f in files]
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
            
            # 분석 결과 조회
            results = db.query(AnalysisResult).filter(
                AnalysisResult.job_id == job_id
            ).all()
            
            processed_files = len(results)
            progress = int((processed_files / total_files * 100)) if total_files > 0 else 0
            
            # 현재 상태에 따라 조정
            if job.status == "pending":
                progress = 0
            elif job.status == "completed":
                progress = 100
            
            # 결과 데이터 준비
            results_list = []
            suspicious_count = 0
            for result in results:
                result_dict = {
                    "filename": result.file_id,  # 프론트엔드에서는 filename을 기대함
                    "stt_text": result.stt_text,
                    "status": "completed",  # AnalysisResult에는 status 필드가 없으므로 항상 completed
                    "confidence": result.stt_metadata.get("confidence", 0) if result.stt_metadata else 0,
                    "risk_level": "safe"  # 기본값
                }
                results_list.append(result_dict)
            
            return AnalysisProgressResponse(
                job_id=job_id,
                folder_path=job.folder_path,
                status=job.status,
                progress=progress,
                current_file=None,
                total_files=total_files,
                processed_files=processed_files,
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
            logger.info(f"[process_analysis_sync] 분석 시작: job_id={job_id}, files={files}")
            
            # 작업 상태 업데이트
            job = new_db.query(AnalysisJob).filter(
                AnalysisJob.job_id == job_id
            ).first()
            
            if job:
                job.status = "processing"
                new_db.commit()
                logger.info(f"[process_analysis_sync] job status: pending → processing")
            
            total_files = len(files)
            logger.info(f"[process_analysis_sync] 처리할 파일 수: {total_files}")
            
            # 각 파일에 대해 STT 처리 및 결과 생성
            for filename in files:
                try:
                    logger.info(f"[process_analysis_sync] 파일 처리: {filename}")
                    
                    # 파일 경로
                    user_dir = get_user_upload_dir(emp_id)
                    file_path = user_dir / folder_path / filename
                    
                    # STT API 호출 (asyncio.run으로 비동기 함수 실행)
                    stt_result = asyncio.run(stt_service.transcribe_local_file(
                        file_path=str(file_path),
                        language="ko",
                        is_stream=False,
                        classification=include_classification,
                        ai_agent=include_classification,
                        incomplete_elements_check=include_validation
                    ))
                    
                    logger.info(f"[process_analysis_sync] STT 결과: {filename}, success={stt_result.get('success')}")
                    
                    # 결과 저장
                    if stt_result.get('success'):
                        result = AnalysisResult(
                            job_id=job_id,
                            file_id=filename,
                            stt_text=stt_result.get('text', ''),
                            stt_metadata={
                                "duration": stt_result.get('duration_sec', 0),
                                "language": stt_result.get('language', 'ko'),
                                "backend": stt_result.get('backend', 'unknown'),
                                "processing_steps": stt_result.get('processing_steps', {})
                            }
                        )
                    else:
                        # STT 실패 시에도 에러 정보 저장
                        result = AnalysisResult(
                            job_id=job_id,
                            file_id=filename,
                            stt_text=None,
                            stt_metadata={
                                "error": stt_result.get('error', 'unknown'),
                                "message": stt_result.get('message', '처리 실패'),
                                "backend": stt_result.get('backend', 'unknown')
                            }
                        )
                    
                    new_db.add(result)
                    new_db.commit()
                    logger.info(f"[process_analysis_sync] 결과 저장: {filename}")
                
                except Exception as e:
                    logger.error(f"[process_analysis_sync] 파일 처리 실패: {filename}, {str(e)}", exc_info=True)
                    # 파일 처리 중 에러도 기록
                    result = AnalysisResult(
                        job_id=job_id,
                        file_id=filename,
                        stt_text=None,
                        stt_metadata={"error": str(e)}
                    )
                    new_db.add(result)
                    new_db.commit()
            
            # 작업 완료 표시
            if job:
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                new_db.commit()
                logger.info(f"[process_analysis_sync] job status: processing → completed")
            
            logger.info(f"[process_analysis_sync] 분석 완료: job_id={job_id}")
        
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