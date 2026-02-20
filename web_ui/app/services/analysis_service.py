"""
분석 시스템 서비스
Phase 3: 분석 작업 관리 및 실행
"""

import asyncio
import uuid
import json
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
from config import STT_API_URL


class AnalysisService:
    """분석 서비스"""
    
    # 진행 중인 작업 추적
    _jobs: Dict[str, Dict] = {}
    
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
            
            # 작업 ID 생성
            job_id = f"job_{uuid.uuid4().hex[:12]}"
            
            # 파일 목록과 옵션 준비
            file_list = [f.filename for f in files]
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
                message="분석이 시작되었습니다"
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
            
            return AnalysisProgressResponse(
                job_id=job_id,
                status=job.status,
                progress=progress,
                current_file=None,
                total_files=total_files,
                processed_files=processed_files,
                error_message=None,
                started_at=job.started_at,
                updated_at=job.completed_at or datetime.utcnow(),
                estimated_time_remaining=None
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
        try:
            # 진행률 업데이트
            progress = db.query(AnalysisProgress).filter(
                AnalysisProgress.job_id == job_id
            ).first()
            
            if progress:
                progress.status = "processing"
                progress.updated_at = datetime.utcnow()
                db.commit()
            
            total_files = len(files)
            
            # 각 파일 분석
            async with aiohttp.ClientSession() as session:
                for idx, filename in enumerate(files):
                    try:
                        # 진행률 업데이트
                        current_progress = int((idx / total_files) * 100)
                        
                        if progress:
                            progress.processed_files = idx
                            progress.progress = current_progress
                            progress.current_filename = filename
                            progress.updated_at = datetime.utcnow()
                            db.commit()
                        
                        # 파일 경로
                        user_dir = get_user_upload_dir(emp_id)
                        file_path = user_dir / folder_path / filename
                        
                        if not file_path.exists():
                            # 파일 없음 처리
                            result = AnalysisResult(
                                job_id=job_id,
                                emp_id=emp_id,
                                filename=filename,
                                status="failed",
                                processed_at=datetime.utcnow(),
                                processing_duration=0.0
                            )
                            db.add(result)
                            db.commit()
                            continue
                        
                        # STT API 호출
                        try:
                            file_size = file_path.stat().st_size
                            
                            with open(file_path, 'rb') as f:
                                form_data = aiohttp.FormData()
                                form_data.add_field('audio', f, filename=filename)
                                
                                timeout = aiohttp.ClientTimeout(total=600)
                                async with session.post(
                                    f"{STT_API_URL}/transcribe",
                                    data=form_data,
                                    timeout=timeout
                                ) as resp:
                                    if resp.status == 200:
                                        stt_result = await resp.json()
                                        
                                        # 결과 저장
                                        result = AnalysisResult(
                                            job_id=job_id,
                                            emp_id=emp_id,
                                            filename=filename,
                                            status="completed",
                                            transcription_text=stt_result.get("text", ""),
                                            transcription_confidence=float(stt_result.get("confidence", 0.0)),
                                            audio_duration=float(stt_result.get("duration", 0.0)),
                                            processed_at=datetime.utcnow(),
                                            processing_duration=float(stt_result.get("duration", 0.0))
                                        )
                                        db.add(result)
                                        db.commit()
                                    else:
                                        error_text = await resp.text()
                                        result = AnalysisResult(
                                            job_id=job_id,
                                            emp_id=emp_id,
                                            filename=filename,
                                            status="failed",
                                            processed_at=datetime.utcnow(),
                                            processing_duration=0.0
                                        )
                                        db.add(result)
                                        db.commit()
                        except asyncio.TimeoutError:
                            # 타임아웃
                            result = AnalysisResult(
                                job_id=job_id,
                                emp_id=emp_id,
                                filename=filename,
                                status="failed",
                                processed_at=datetime.utcnow(),
                                processing_duration=0.0
                            )
                            db.add(result)
                            db.commit()
                    
                    except Exception as e:
                        # 파일 처리 중 에러
                        result = AnalysisResult(
                            job_id=job_id,
                            emp_id=emp_id,
                            filename=filename,
                            status="failed",
                            processed_at=datetime.utcnow(),
                            processing_duration=0.0
                        )
                        db.add(result)
                        db.commit()
            
            # 최종 진행률 업데이트
            if progress:
                progress.processed_files = total_files
                progress.progress = 100
                progress.status = "completed"
                progress.updated_at = datetime.utcnow()
                db.commit()
            
            # 작업 완료 표시
            job = db.query(AnalysisJob).filter(
                AnalysisJob.job_id == job_id
            ).first()
            if job:
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                
                # 통계 계산
                results = db.query(AnalysisResult).filter(
                    AnalysisResult.job_id == job_id
                ).all()
                job.completed_files = sum(1 for r in results if r.status == "completed")
                job.failed_files = sum(1 for r in results if r.status == "failed")
                db.commit()
        
        except Exception as e:
            # 작업 실패
            if progress:
                progress.status = "failed"
                progress.error_message = str(e)
                progress.updated_at = datetime.utcnow()
                db.commit()
            
            job = db.query(AnalysisJob).filter(
                AnalysisJob.job_id == job_id
            ).first()
            if job:
                job.status = "failed"
                job.completed_at = datetime.utcnow()
                db.commit()
