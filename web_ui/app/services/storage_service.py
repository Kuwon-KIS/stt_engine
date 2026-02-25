"""
Storage quota management service
Tracks and enforces user storage limits
"""
from sqlalchemy.orm import Session
from typing import Dict
from app.models.database import Employee, FileUpload
from sqlalchemy import func


class StorageService:
    """저장 용량 관리 서비스"""
    
    @staticmethod
    def check_quota_available(emp_id: str, file_size_bytes: int, db: Session) -> Dict[str, any]:
        """
        사용자의 저장 용량 할당량 확인
        
        Args:
            emp_id: 사원번호
            file_size_bytes: 업로드하려는 파일 크기 (bytes)
            db: Database session
            
        Returns:
            Dictionary with quota check result
        """
        employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
        
        if not employee:
            return {
                "available": False,
                "error": "사용자 정보를 찾을 수 없습니다"
            }
        
        # Calculate available space
        available_bytes = employee.storage_quota - employee.storage_used
        
        if file_size_bytes > available_bytes:
            return {
                "available": False,
                "error": f"저장 용량이 부족합니다. 사용 가능: {available_bytes / (1024**3):.2f}GB, 필요: {file_size_bytes / (1024**3):.2f}GB",
                "storage_used": employee.storage_used,
                "storage_quota": employee.storage_quota,
                "available_bytes": available_bytes
            }
        
        return {
            "available": True,
            "storage_used": employee.storage_used,
            "storage_quota": employee.storage_quota,
            "available_bytes": available_bytes
        }
    
    @staticmethod
    def add_usage(emp_id: str, file_size_bytes: int, db: Session) -> bool:
        """
        사용자의 저장 용량 사용량 증가
        
        Args:
            emp_id: 사원번호
            file_size_bytes: 추가할 파일 크기 (bytes)
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
            
            if not employee:
                return False
            
            employee.storage_used += file_size_bytes
            db.commit()
            return True
            
        except Exception:
            db.rollback()
            return False
    
    @staticmethod
    def subtract_usage(emp_id: str, file_size_bytes: int, db: Session) -> bool:
        """
        사용자의 저장 용량 사용량 감소
        
        Args:
            emp_id: 사원번호
            file_size_bytes: 감소할 파일 크기 (bytes)
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
            
            if not employee:
                return False
            
            # Prevent negative usage
            employee.storage_used = max(0, employee.storage_used - file_size_bytes)
            db.commit()
            return True
            
        except Exception:
            db.rollback()
            return False
    
    @staticmethod
    def get_storage_info(emp_id: str, db: Session) -> Dict[str, any]:
        """
        사용자의 저장 용량 정보 조회
        
        Args:
            emp_id: 사원번호
            db: Database session
            
        Returns:
            Dictionary with storage information
        """
        employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
        
        if not employee:
            return {
                "success": False,
                "error": "사용자 정보를 찾을 수 없습니다"
            }
        
        storage_used_gb = employee.storage_used / (1024**3)
        storage_quota_gb = employee.storage_quota / (1024**3)
        usage_percent = (employee.storage_used / employee.storage_quota * 100) if employee.storage_quota > 0 else 0
        available_gb = (employee.storage_quota - employee.storage_used) / (1024**3)
        
        return {
            "success": True,
            "storage_used": employee.storage_used,
            "storage_quota": employee.storage_quota,
            "storage_used_gb": round(storage_used_gb, 2),
            "storage_quota_gb": round(storage_quota_gb, 2),
            "available_gb": round(available_gb, 2),
            "usage_percent": round(usage_percent, 1)
        }
    
    @staticmethod
    def recalculate_usage(emp_id: str, db: Session) -> bool:
        """
        사용자의 실제 파일 사용량을 재계산하여 동기화
        
        Args:
            emp_id: 사원번호
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
            
            if not employee:
                return False
            
            # Calculate total file size from file_uploads table
            total_size = db.query(func.sum(FileUpload.file_size_mb)).filter(
                FileUpload.emp_id == emp_id
            ).scalar() or 0.0
            
            # Convert MB to bytes
            total_bytes = int(total_size * 1024 * 1024)
            
            employee.storage_used = total_bytes
            db.commit()
            return True
            
        except Exception:
            db.rollback()
            return False
