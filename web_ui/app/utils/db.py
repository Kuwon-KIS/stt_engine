"""
데이터베이스 세션 관리 및 초기화
Phase 1: SQLAlchemy ORM 기반 DB 관리
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.database import Base
from config import DATABASE_URL

# 데이터베이스 엔진 생성
# SQLite 사용 시 check_same_thread=False 필수 (멀티스레드 환경에서)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    데이터베이스 초기화
    - 모든 테이블 생성 (존재하지 않을 경우)
    - 서버 시작 시 호출됨
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully")


def get_db():
    """
    FastAPI 의존성 함수
    라우트에서 DB 세션을 주입받을 때 사용
    
    Usage:
        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            # db 사용
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
