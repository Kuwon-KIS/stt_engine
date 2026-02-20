"""
SQLAlchemy ORM 모델 정의
Phase 1: 인증, 파일 관리, 분석 시스템을 위한 5개 테이블
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Employee(Base):
    """직원 정보 테이블"""
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True)
    emp_id = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    dept = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # 관계 설정
    file_uploads = relationship("FileUpload", back_populates="employee")
    analysis_jobs = relationship("AnalysisJob", back_populates="employee")
    
    def __repr__(self):
        return f"<Employee(emp_id='{self.emp_id}', name='{self.name}', dept='{self.dept}')>"


class FileUpload(Base):
    """업로드된 파일 정보 테이블"""
    __tablename__ = "file_uploads"
    
    id = Column(Integer, primary_key=True)
    emp_id = Column(String(10), ForeignKey("employees.emp_id"), nullable=False, index=True)
    folder_path = Column(String(500), nullable=False)
    # 예: "2026-02-20" (날짜 폴더) 또는 "부당권유_검토" (커스텀 폴더)
    filename = Column(String(500), nullable=False)
    file_size_mb = Column(Float)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    employee = relationship("Employee", back_populates="file_uploads")
    
    def __repr__(self):
        return f"<FileUpload(emp_id='{self.emp_id}', filename='{self.filename}', folder='{self.folder_path}')>"


class AnalysisJob(Base):
    """분석 작업 정보 테이블"""
    __tablename__ = "analysis_jobs"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(50), unique=True, nullable=False, index=True)
    # 작업 ID: UUID 또는 타임스탐프 기반 고유 ID
    emp_id = Column(String(10), ForeignKey("employees.emp_id"), nullable=False, index=True)
    folder_path = Column(String(500), nullable=False)
    # 분석할 폴더 경로
    file_ids = Column(JSON)
    # JSON 형식: ["file1.wav", "file2.wav", ...]
    status = Column(String(20), default="pending")
    # "pending", "processing", "completed", "failed"
    options = Column(JSON)
    # 분석 옵션: {"improper_solicitation": true, "incomplete_sales": true}
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # 관계 설정
    employee = relationship("Employee", back_populates="analysis_jobs")
    results = relationship("AnalysisResult", back_populates="job")
    progress = relationship("AnalysisProgress", back_populates="job")
    
    def __repr__(self):
        return f"<AnalysisJob(job_id='{self.job_id}', emp_id='{self.emp_id}', status='{self.status}')>"


class AnalysisResult(Base):
    """분석 결과 테이블"""
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(50), ForeignKey("analysis_jobs.job_id"), nullable=False, index=True)
    file_id = Column(String(500), nullable=False)
    # 파일명 또는 경로
    
    # === STT 결과 ===
    stt_text = Column(Text)
    # 음성→텍스트 변환 결과
    stt_metadata = Column(JSON)
    # {"duration": 60.5, "language": "ko", "confidence": 0.95}
    
    # === 분류 결과 ===
    classification_code = Column(String(20))
    # 분류 코드: "100-100", "100-200", "200-100" 등
    classification_category = Column(String(100))
    # 분류 카테고리: "적정", "주의", "위험" 등
    classification_confidence = Column(Float)
    # 신뢰도: 0.0-1.0
    
    # === 탐지 결과 ===
    improper_detection_results = Column(JSON)
    # 부당권유 탐지 결과
    # {
    #   "detected": true,
    #   "score": 0.85,
    #   "segments": [
    #     {"start": 10, "end": 15, "text": "...", "confidence": 0.9}
    #   ]
    # }
    incomplete_detection_results = Column(JSON)
    # 불완전판매 탐지 결과 (위와 동일한 구조)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    job = relationship("AnalysisJob", back_populates="results")
    
    def __repr__(self):
        return f"<AnalysisResult(job_id='{self.job_id}', file_id='{self.file_id}')>"


class AnalysisProgress(Base):
    """분석 진행 상황 테이블 (WebSocket/polling용)"""
    __tablename__ = "analysis_progress"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(50), ForeignKey("analysis_jobs.job_id"), nullable=False, index=True)
    file_id = Column(String(500), nullable=False)
    
    # 진행 단계
    step = Column(String(50))
    # "stt", "classification", "improper_detection", "incomplete_detection"
    
    progress_percent = Column(Integer, default=0)
    # 0-100
    status = Column(String(20))
    # "pending", "processing", "completed", "failed"
    message = Column(String(500))
    # 상태 메시지: "STT 진행 중...", "완료" 등
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    job = relationship("AnalysisJob", back_populates="progress")
    
    def __repr__(self):
        return f"<AnalysisProgress(job_id='{self.job_id}', file_id='{self.file_id}', step='{self.step}')>"
