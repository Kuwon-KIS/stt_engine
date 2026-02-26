"""
Web UI 서버 설정
"""
import os
from pathlib import Path
from datetime import timedelta

# 기본 경로
BASE_DIR = Path(__file__).parent

# 데이터 디렉토리 설정
# 우선순위:
# 1. DATA_DIR 환경변수가 설정되어 있으면 사용
# 2. /app/data가 존재하면 (Docker 환경) 사용
# 3. 로컬 개발 환경: web_ui/data 폴더 사용
if os.getenv("DATA_DIR"):
    DATA_DIR = Path(os.getenv("DATA_DIR"))
elif Path("/app/data").exists():
    # Docker 환경 (마운트된 볼륨)
    DATA_DIR = Path("/app/data")
else:
    # 로컬 개발 환경: web_ui/data 폴더 사용
    DATA_DIR = BASE_DIR / "data"

UPLOAD_DIR = DATA_DIR / "uploads"
RESULT_DIR = DATA_DIR / "results"
BATCH_INPUT_DIR = DATA_DIR / "batch_input"
DB_PATH = DATA_DIR / "db.sqlite"

# === Phase 1: 데이터베이스 설정 ===
DATABASE_URL = f"sqlite:///{DATA_DIR / 'stt_web.db'}"

# === Phase 1: 세션 설정 ===
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "dev-secret-key-change-in-production")
SESSION_TIMEOUT = timedelta(hours=8)

# === 인증 방식 ===
# DB 기반 인증 사용: employees 테이블에서 사용자 정보 관리
# 새로운 사용자는 관리자 페이지에서 추가 가능
# 관리자 비밀번호: app/routes/admin.py의 ADMIN_PASSWORD_HASH 참조

# === Phase 1: AI Agent 설정 ===
AI_AGENTS = {
    "stt": {
        "url": os.getenv("STT_AGENT_URL", "http://localhost:8001"),
        "timeout": int(os.getenv("STT_AGENT_TIMEOUT", 300))
    },
    "classification": {
        "url": os.getenv("CLASSIFICATION_AGENT_URL", "http://localhost:8002"),
        "timeout": int(os.getenv("CLASSIFICATION_AGENT_TIMEOUT", 60))
    },
    "improper_detection": {
        "url": os.getenv("IMPROPER_DETECTION_AGENT_URL", "http://localhost:8003"),
        "timeout": int(os.getenv("IMPROPER_DETECTION_AGENT_TIMEOUT", 120))
    },
    "element_detection": {
        "url": os.getenv("ELEMENT_DETECTION_AGENT_URL", "http://localhost:8004"),
        "timeout": int(os.getenv("ELEMENT_DETECTION_AGENT_TIMEOUT", 120))
    }
}

# 디렉토리 생성
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)
BATCH_INPUT_DIR.mkdir(parents=True, exist_ok=True)

# 웹 서버 설정
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", 8100))

# STT API 서버 설정
STT_API_URL = os.getenv("STT_API_URL", "http://localhost:8003")
STT_API_TIMEOUT = int(os.getenv("STT_API_TIMEOUT", 300))

# 파일 업로드 설정
# MAX_UPLOAD_SIZE_MB: 무제한 (환경변수로 제한 설정 가능, 예: MAX_UPLOAD_SIZE_MB=5000)
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", 999999))  # 무제한 (약 1000TB)
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}

# 배치 처리 설정
BATCH_PARALLEL_COUNT = int(os.getenv("BATCH_PARALLEL_COUNT", 2))
BATCH_CHECK_INTERVAL = int(os.getenv("BATCH_CHECK_INTERVAL", 5))  # 초

# 분석 작업 동시 처리 설정
# 분석 중 동시에 처리할 최대 파일 개수 (기본값: 2)
# 환경변수: MAX_CONCURRENT_ANALYSIS (예: 1, 2, 3, 4)
MAX_CONCURRENT_ANALYSIS = int(os.getenv("MAX_CONCURRENT_ANALYSIS", 2))

# 로깅 설정
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"

# 데이터베이스 설정
DATABASE_URL = f"sqlite:///{DB_PATH}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# CORS 설정
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# 기본 언어
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ko")
