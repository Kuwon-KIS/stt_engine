FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 라이브러리 설치
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 업그레이드
RUN pip install --upgrade pip setuptools wheel

# 요구사항 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 복사
COPY . .

# 모델 다운로드 (선택사항: 빌드 시 미리 다운로드)
# RUN python download_model.py

# 음성 파일 디렉토리 생성
RUN mkdir -p audio models logs

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "from stt_engine import WhisperSTT; print('OK')" || exit 1

# 기본 명령어
CMD ["python", "stt_engine.py"]
