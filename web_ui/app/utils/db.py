"""
데이터베이스 세션 관리 및 초기화
Phase 1: SQLAlchemy ORM 기반 DB 관리
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from app.models.database import Base
from config import DATABASE_URL
import logging
import time

# 성능 측정 로거 설정
perf_logger = logging.getLogger("performance")

# 데이터베이스 엔진 생성
# SQLite 사용 시 check_same_thread=False 필수 (멀티스레드 환경에서)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False  # 기본값: SQL 로깅 비활성화, 아래에서 선택적으로 활성화
)

# 쿼리 성능 측정 (echo 활성화 시 모든 SQL 로깅)
@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """쿼리 실행 전 타이밍 기록"""
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """쿼리 실행 후 소요 시간 기록"""
    total_time = time.time() - conn.info['query_start_time'].pop(-1)
    perf_logger.debug(f"Query execution time: {total_time:.3f}s")

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
