FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 라이브러리 설치
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 업그레이드
RUN pip install --upgrade pip setuptools wheel

# 요구사항 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 복사
COPY main.py api_server.py stt_engine.py stt_utils.py ./
COPY api_server/ ./api_server/
COPY utils/ ./utils/

# Privacy Remover 모듈 복사 (LLM 기반 개인정보 제거)
COPY scratch/prompt_test_all/ ./prompt_test_all/

# 모델, 오디오, 로그 디렉토리 생성
RUN mkdir -p audio models logs

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/models
ENV STT_DEVICE=cpu

# 헬스체크 추가
HEALTHCHECK --interval=60s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# API 포트
EXPOSE 8003

# 시작 명령어
CMD ["python3.11", "main.py"]
