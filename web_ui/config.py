"""
Web UI 서버 설정
"""
import os
from pathlib import Path

# 기본 경로
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
RESULT_DIR = DATA_DIR / "results"
BATCH_INPUT_DIR = DATA_DIR / "batch_input"
DB_PATH = DATA_DIR / "db.sqlite"

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
