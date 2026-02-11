"""
파일 관리 서비스
"""
import os
import shutil
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from config import UPLOAD_DIR, RESULT_DIR, BATCH_INPUT_DIR, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB

logger = logging.getLogger(__name__)


class FileService:
    """파일 관리 클래스"""
    
    @staticmethod
    def validate_file(filename: str, file_size: int) -> tuple[bool, Optional[str]]:
        """
        파일 유효성 검증
        
        Returns:
            (성공 여부, 에러 메시지)
        """
        # 확장자 검증
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"지원하지 않는 파일 형식: {ext}. 지원: {ALLOWED_EXTENSIONS}"
        
        # 크기 검증
        size_mb = file_size / (1024 * 1024)
        if size_mb > MAX_UPLOAD_SIZE_MB:
            return False, f"파일이 너무 큽니다. 최대: {MAX_UPLOAD_SIZE_MB}MB, 입력: {size_mb:.2f}MB"
        
        return True, None
    
    @staticmethod
    def save_upload_file(file_data: bytes, original_filename: str) -> tuple[str, str]:
        """
        업로드 파일 저장
        
        Args:
            file_data: 파일 데이터
            original_filename: 원본 파일명
        
        Returns:
            (파일_ID, 저장_경로)
        """
        try:
            # 파일 ID 생성
            file_id = str(uuid.uuid4())
            ext = Path(original_filename).suffix.lower()
            
            # 저장 경로
            saved_filename = f"{file_id}{ext}"
            saved_path = UPLOAD_DIR / saved_filename
            
            # 파일 저장
            with open(saved_path, "wb") as f:
                f.write(file_data)
            
            logger.info(f"[File Service] 파일 저장: {saved_path}")
            return file_id, str(saved_path)
        
        except Exception as e:
            logger.error(f"[File Service] 파일 저장 실패: {e}")
            raise
    
    @staticmethod
    def save_result(file_id: str, text: str, metadata: dict) -> str:
        """
        처리 결과 저장
        
        Args:
            file_id: 파일 ID
            text: 변환된 텍스트
            metadata: 메타데이터
        
        Returns:
            저장된 결과 파일 경로
        """
        try:
            result_path = RESULT_DIR / f"{file_id}.txt"
            
            # 결과 저장
            with open(result_path, "w", encoding="utf-8") as f:
                f.write(f"=== STT 처리 결과 ===\n\n")
                f.write(f"파일: {metadata.get('filename', 'N/A')}\n")
                f.write(f"언어: {metadata.get('language', 'N/A')}\n")
                f.write(f"지속시간: {metadata.get('duration_sec', 0):.2f}초\n")
                f.write(f"처리시간: {metadata.get('processing_time_sec', 0):.2f}초\n")
                f.write(f"백엔드: {metadata.get('backend', 'N/A')}\n")
                f.write(f"생성시간: {datetime.now().isoformat()}\n\n")
                f.write(f"--- 텍스트 ---\n\n")
                f.write(text)
            
            logger.info(f"[File Service] 결과 저장: {result_path}")
            return str(result_path)
        
        except Exception as e:
            logger.error(f"[File Service] 결과 저장 실패: {e}")
            raise
    
    @staticmethod
    def get_file_size_mb(file_path: str) -> float:
        """파일 크기를 MB 단위로 반환"""
        return os.path.getsize(file_path) / (1024 * 1024)
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """파일 삭제"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"[File Service] 파일 삭제: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"[File Service] 파일 삭제 실패: {e}")
            return False
    
    @staticmethod
    def list_batch_files(
        input_dir: str = str(BATCH_INPUT_DIR),
        extension: str = ".wav"
    ) -> list[dict]:
        """
        배치 입력 디렉토리의 파일 목록
        
        Args:
            input_dir: 입력 디렉토리
            extension: 파일 확장자
        
        Returns:
            파일 정보 딕셔너리 리스트
        """
        try:
            input_path = Path(input_dir)
            files = []
            
            for file_path in input_path.glob(f"*{extension}"):
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        "name": file_path.name,
                        "path": str(file_path),
                        "size_mb": stat.st_size / (1024 * 1024),
                        "modified": datetime.fromtimestamp(stat.st_mtime),
                        "status": "pending"
                    })
            
            logger.info(f"[File Service] 배치 파일 목록: {len(files)}개")
            return files
        
        except Exception as e:
            logger.error(f"[File Service] 배치 파일 목록 조회 실패: {e}")
            return []


# 싱글톤 인스턴스
file_service = FileService()
