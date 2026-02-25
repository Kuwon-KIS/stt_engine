"""
Admin service for user management and administrative functions.
"""
import bcrypt
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.database import Employee
from app.constants import (
    ADMIN_PASSWORD_HASH,
    DEFAULT_STORAGE_QUOTA,
    EMPLOYEE_ID_LENGTH
)


def verify_admin_password(password: str) -> bool:
    """
    Verify admin password against stored hash.
    
    Args:
        password: Plain text password to verify
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            ADMIN_PASSWORD_HASH.encode('utf-8')
        )
    except Exception:
        return False


def create_user(
    emp_id: str,
    name: str,
    dept: str,
    db: Session
) -> Dict[str, any]:
    """
    Create a new user in the system.
    
    Args:
        emp_id: Employee ID (must be exactly 6 digits)
        name: Employee name
        dept: Department name
        db: Database session
        
    Returns:
        Dictionary with success status and message/error
    """
    # Validate employee ID format
    if not emp_id or len(emp_id) != EMPLOYEE_ID_LENGTH:
        return {
            "success": False,
            "error": f"사번은 정확히 {EMPLOYEE_ID_LENGTH}자리 숫자여야 합니다."
        }
    
    if not emp_id.isdigit():
        return {
            "success": False,
            "error": "사번은 숫자만 입력 가능합니다."
        }
    
    # Validate required fields
    if not name or not name.strip():
        return {
            "success": False,
            "error": "이름을 입력해주세요."
        }
    
    if not dept or not dept.strip():
        return {
            "success": False,
            "error": "부서를 입력해주세요."
        }
    
    try:
        # Create new employee with default quota
        new_employee = Employee(
            emp_id=emp_id,
            name=name.strip(),
            dept=dept.strip(),
            storage_quota=DEFAULT_STORAGE_QUOTA,
            storage_used=0,
            is_admin=0
        )
        
        db.add(new_employee)
        db.commit()
        db.refresh(new_employee)
        
        return {
            "success": True,
            "message": f"사용자 {name} (사번: {emp_id})가 생성되었습니다.",
            "user": {
                "emp_id": new_employee.emp_id,
                "name": new_employee.name,
                "dept": new_employee.dept,
                "storage_quota": new_employee.storage_quota,
                "storage_used": new_employee.storage_used,
                "is_admin": new_employee.is_admin
            }
        }
        
    except IntegrityError:
        db.rollback()
        return {
            "success": False,
            "error": f"이미 존재하는 사번입니다: {emp_id}"
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"사용자 생성 중 오류가 발생했습니다: {str(e)}"
        }


def list_users(db: Session) -> List[Dict[str, any]]:
    """
    Get list of all users with their storage information.
    
    Args:
        db: Database session
        
    Returns:
        List of user dictionaries with quota information
    """
    try:
        employees = db.query(Employee).order_by(Employee.emp_id).all()
        
        users = []
        for emp in employees:
            users.append({
                "emp_id": emp.emp_id,
                "name": emp.name,
                "dept": emp.dept,
                "storage_quota": emp.storage_quota,
                "storage_used": emp.storage_used,
                "storage_quota_gb": round(emp.storage_quota / (1024**3), 2),
                "storage_used_gb": round(emp.storage_used / (1024**3), 2),
                "is_admin": emp.is_admin,
                "created_at": emp.created_at.isoformat() if emp.created_at else None,
                "last_login": emp.last_login.isoformat() if emp.last_login else None
            })
        
        return users
        
    except Exception as e:
        return []


def update_user_quota(
    emp_id: str,
    quota_gb: float,
    db: Session
) -> Dict[str, any]:
    """
    Update user's storage quota.
    
    Args:
        emp_id: Employee ID
        quota_gb: New quota in GB
        db: Database session
        
    Returns:
        Dictionary with success status and message/error
    """
    # Validate quota
    if quota_gb <= 0:
        return {
            "success": False,
            "error": "용량은 0보다 커야 합니다."
        }
    
    if quota_gb > 1000:
        return {
            "success": False,
            "error": "용량은 1000GB를 초과할 수 없습니다."
        }
    
    try:
        employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
        
        if not employee:
            return {
                "success": False,
                "error": f"사용자를 찾을 수 없습니다: {emp_id}"
            }
        
        # Convert GB to bytes
        quota_bytes = int(quota_gb * 1024 * 1024 * 1024)
        
        # Check if new quota is less than current usage
        if quota_bytes < employee.storage_used:
            return {
                "success": False,
                "error": f"할당량은 현재 사용량({round(employee.storage_used / (1024**3), 2)}GB)보다 작을 수 없습니다."
            }
        
        employee.storage_quota = quota_bytes
        db.commit()
        
        return {
            "success": True,
            "message": f"{employee.name}의 할당량이 {quota_gb}GB로 변경되었습니다.",
            "storage_quota": quota_bytes,
            "storage_quota_gb": quota_gb
        }
        
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"할당량 변경 중 오류가 발생했습니다: {str(e)}"
        }
