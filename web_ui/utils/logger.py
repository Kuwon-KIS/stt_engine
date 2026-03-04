"""
로깅 설정
"""
import logging
import logging.handlers
from pathlib import Path
from config import LOG_LEVEL, LOG_FORMAT

# 로그 디렉토리 생성
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 기본 로거 설정
def setup_logging():
    """로깅 초기화"""
    
    # 루트 로거
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # 포매터
    formatter = logging.Formatter(LOG_FORMAT)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "web_ui.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 성능 모니터링 로거 (별도 파일)
    perf_logger = logging.getLogger("performance")
    perf_logger.setLevel(logging.INFO)
    
    perf_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "performance.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    perf_formatter = logging.Formatter("%(asctime)s - %(message)s")
    perf_handler.setFormatter(perf_formatter)
    perf_logger.addHandler(perf_handler)
    
    # 콘솔에도 성능 로그 출력
    perf_console = logging.StreamHandler()
    perf_console.setFormatter(perf_formatter)
    perf_logger.addHandler(perf_console)
    
    return root_logger


# 초기화
setup_logging()


def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 반환"""
    return logging.getLogger(name)

