"""
세션 기반 인증 서비스
Phase 1: 사번 검증 및 직원 정보 관리
"""

from sqlalchemy.orm import Session
from datetime import datetime
from app.models.database import Employee
from config import ALLOWED_EMPLOYEES


class AuthService:
    """인증 관련 비즈니스 로직"""
    
    @staticmethod
    def validate_employee(emp_id: str, db: Session) -> dict:
        """
        사번 검증 및 직원 정보 DB 기록
        
        Args:
            emp_id: 사번 (문자열)
            db: SQLAlchemy Session
        
        Returns:
            {
                "success": bool,
                "emp_id": str,
                "name": str,
                "dept": str,
                "error": str (실패 시만)
            }
        """
        # 1. 사번 형식 검증: 6자리 숫자만 허용
        if not emp_id or not emp_id.isdigit() or len(emp_id) != 6:
            return {
                "success": False,
                "error": "사번은 6자리 숫자여야 합니다."
            }
        
        # 2. DB에서 직원 정보 조회
        employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
        
        # 3. 없으면 새로 생성 (첫 로그인), 있으면 기존 정보 사용
        if not employee:
            # ALLOWED_EMPLOYEES에서 기본 정보 확인 (선택적)
            emp_info = ALLOWED_EMPLOYEES.get(emp_id, {})
            
            # 새 직원 레코드 생성
            employee = Employee(
                emp_id=emp_id,
                name=emp_info.get("name", f"사용자{emp_id}"),  # 기본 이름
                dept=emp_info.get("dept", "미분류")  # 기본 부서
            )
            db.add(employee)
        
        # 4. last_login 업데이트
        employee.last_login = datetime.utcnow()
        db.commit()
        db.refresh(employee)
        
        return {
            "success": True,
            "emp_id": emp_id,
            "name": employee.name,
            "dept": employee.dept
        }
    
    @staticmethod
    def get_current_employee(session: dict) -> dict:
        """
        세션에서 현재 로그인한 사용자 정보 조회
        
        Args:
            session: Starlette Request.session 딕셔너리
        
        Returns:
            {
                "emp_id": str,
                "name": str,
                "dept": str
            }
            또는 None (미인증 시)
        """
        if "emp_id" not in session:
            return None
        
        return {
            "emp_id": session.get("emp_id"),
            "name": session.get("name"),
            "dept": session.get("dept")
        }
    
    @staticmethod
    def is_authenticated(session: dict) -> bool:
        """
        세션 인증 여부 확인
        
        Args:
            session: Starlette Request.session 딕셔너리
        
        Returns:
            bool: 인증 여부
        """
        return "emp_id" in session and session.get("emp_id") is not None

# 전역 인스턴스 생성
auth_service = AuthService()