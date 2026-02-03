# ⚠️ ❌ [2026-02-03 v1.0-DEPRECATED] CUDA 12.4 배포 (폐기됨)

**버전**: v1.0-DEPRECATED (폐기됨)  
**날짜**: 2026-02-03  
**상태**: ❌ **사용 금지** (Docker 이미지 빌드 방식)

---

## 📋 문서 상태

| 버전 | 날짜 | 상태 | 설명 |
|------|------|------|------|
| v1.0-DEPRECATED | 2026-02-03 | ❌ **폐기** | Mac에서 wheel 받아 Docker 빌드 (CPU 버전 위험) |

### ⚠️ 이 문서를 사용하면 안 되는 이유
- ❌ Mac에서 Linux용 wheel 수집 시도 (아키텍처 불일치)
- ❌ Docker 빌드 중 네트워크 불안정
- ❌ CPU 버전 다운로드 가능성

### ✅ 대신 이 문서를 읽으세요
👉 **[CORRECT_FINAL_DEPLOYMENT.md](CORRECT_FINAL_DEPLOYMENT.md)**

---

# ❌ 이전 내용 (작동하지 않음)

## 🏠 로컬 머신에서 (40분)

### 1️⃣ 폴더 및 파일 준비

```bash
cd /Users/a113211/workspace/stt_engine

# CUDA 12.4용 wheels 폴더 생성
mkdir -p deployment_package/wheels-cu124
```

### 2️⃣ CUDA 12.4 PyTorch wheels 다운로드 (10-15분)

```bash
python3 -m pip wheel torch==2.1.2 torchaudio==2.1.2 \
  --index-url https://download.pytorch.org/whl/cu124 \
  -w deployment_package/wheels-cu124/ \
  --no-deps

# 다른 의존성 다운로드
python3 -m pip wheel \
  faster-whisper==1.0.3 \
  librosa==0.10.0 \
  numpy==1.24.3 \
  scipy==1.12.0 \
  huggingface-hub==0.21.4 \
  python-dotenv==1.0.0 \
  pydantic==2.5.3 \
  fastapi==0.109.0 \
  uvicorn==0.27.0 \
  requests==2.31.0 \
  pyyaml==6.0.1 \
  python-multipart==0.0.22 \
  -w deployment_package/wheels-cu124/ \
  --no-deps

# 다운로드 확인
ls -1 deployment_package/wheels-cu124/ | wc -l
# 예상: 60개 이상
```

### 3️⃣ Dockerfile.engine-cu124 생성

다음 내용을 `docker/Dockerfile.engine-cu124` 파일로 저장:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy CUDA 12.4 wheels
COPY deployment_package/wheels-cu124/ /wheels/

# Install packages from wheels (offline)
RUN python3.11 -m pip install --no-index --find-links=/wheels/ \
    torch torchaudio faster-whisper \
    librosa scipy numpy \
    fastapi uvicorn requests pydantic \
    huggingface-hub python-dotenv pyyaml \
    python-multipart && \
    rm -rf /wheels/

# Copy application files
COPY stt_engine.py /app/
COPY api_server.py /app/
COPY requirements.txt /app/

# Create directories for models and logs
RUN mkdir -p /app/models /app/logs /app/audio

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/models
ENV STT_DEVICE=auto

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run API server
CMD ["python3.11", "api_server.py"]
```

### 4️⃣ Docker 이미지 빌드 (20-25분)

```bash
cd /Users/a113211/workspace/stt_engine

docker build \
  -t stt-engine:cu124 \
  -f docker/Dockerfile.engine-cu124 \
  .

# 빌드 완료 확인
docker images | grep cu124
```

### 5️⃣ 이미지를 tar.gz로 저장 (2-3분)

```bash
mkdir -p build/output

docker save stt-engine:cu124 | gzip > build/output/stt-engine-cu124.tar.gz

# 크기 확인
ls -lh build/output/stt-engine-cu124.tar.gz
# 예상: ~1.0-1.1GB
```

---

## 🖥️ 서버에서 (10-15분)

### 1️⃣ 로컬에서 서버로 이미지 전송 (5-10분)

```bash
# 로컬 머신에서 실행

scp build/output/stt-engine-cu124.tar.gz ddpapp@dlddpgai1:/data/stt/

# 또는 다른 서버 주소면:
# scp build/output/stt-engine-cu124.tar.gz user@server-ip:/path/to/
```

### 2️⃣ 서버에 SSH 접속 후 이미지 로드 (2-3분)

```bash
# 서버에 접속
ssh ddpapp@dlddpgai1

# 이미지 로드
docker load -i /data/stt/stt-engine-cu124.tar.gz

# 로드 확인
docker images | grep cu124
# 출력: stt-engine  cu124  ... 1.1GB
```

### 3️⃣ 기존 컨테이너 정리 (1분)

```bash
# 실행 중인 컨테이너 중지
docker stop stt-engine 2>/dev/null || true

# 컨테이너 제거
docker rm stt-engine 2>/dev/null || true

# 확인
docker ps -a | grep stt-engine
# (아무것도 나오지 않아야 함)
```

### 4️⃣ 새 컨테이너 실행 (1-2분)

```bash
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v /data/models:/app/models \
  -v /data/logs:/app/logs \
  --gpus all \
  stt-engine:cu124

# 컨테이너 상태 확인
docker ps | grep stt-engine
# 출력: stt-engine ... Up ... 0.0.0.0:8003->8003/tcp
```

### 5️⃣ 로그 확인 (CUDA 초기화 확인)

```bash
docker logs -f stt-engine

# 예상 출력:
# ✅ faster-whisper 모델 로드 완료 (Device: cuda, compute: float16)
# INFO:     Started server process
# INFO:     Uvicorn running on http://0.0.0.0:8003

# Ctrl+C로 빠져나오기
```

### 6️⃣ 헬스 체크 (API 응답 확인)

```bash
curl -X GET http://localhost:8003/health

# 예상 응답:
# {"status":"healthy","device":"cuda"}
```

---

## 🎬 음성 파일 테스트

### 1️⃣ 테스트 음성 파일 준비

```bash
# 서버에 테스트 파일이 있으면
ls /data/test_audio.wav

# 없으면 로컬에서 다운로드하여 서버로 전송
scp /path/to/test_audio.wav ddpapp@dlddpgai1:/data/
```

### 2️⃣ API 호출로 STT 테스트

```bash
# 서버에서

curl -X POST http://localhost:8003/transcribe \
  -F "file=@/data/test_audio.wav"

# 예상 응답 (JSON):
# {
#   "text": "recognized text here...",
#   "duration_seconds": 5.2,
#   "processing_time_seconds": 1.2,
#   "model": "whisper-large-v3-turbo",
#   "device": "cuda"
# }
```

---

## 📊 진행 상황 모니터링

### 빌드 진행 중 (로컬)

```bash
# 별도 터미널에서 Docker 빌드 상황 보기
docker stats
```

### 배포 후 (서버)

```bash
# 실시간 로그 모니터링
docker logs -f stt-engine

# 또는 마지막 100줄만 보기
docker logs --tail 100 stt-engine

# GPU 사용률 확인
nvidia-smi

# 또는 실시간 모니터링
watch -n 1 nvidia-smi
```

---

## 🆘 문제 발생 시

### 컨테이너가 Exited 상태면

```bash
# 로그 확인
docker logs stt-engine

# 에러 메시지 찾기
docker logs stt-engine 2>&1 | tail -50

# 컨테이너 상세 정보
docker inspect stt-engine
```

### CUDA 에러면

```bash
# nvidia-smi 확인
nvidia-smi

# GPU 드라이버와 CUDA Runtime 호환성 확인
nvidia-smi | grep -E "Driver|CUDA"
# 예상: Driver 575.57, CUDA 12.9
```

### 포트 8003이 이미 사용 중이면

```bash
# 포트 확인
lsof -i :8003

# 기존 프로세스 종료
kill -9 <PID>

# 또는 다른 포트 사용
docker run -d --name stt-engine -p 8004:8003 --gpus all stt-engine:cu124
```

---

## ✅ 최종 체크리스트

```
로컬 빌드 (50분 총소요 시간 중 40분)
☑ deployment_package/wheels-cu124/ 폴더 생성
☑ PyTorch CUDA 12.4 wheels 다운로드 (10-15분)
☑ 다른 의존성 wheels 다운로드
☑ Dockerfile.engine-cu124 생성
☑ docker build 시작 (20-25분)
☑ docker save로 tar.gz 생성 (~1.1GB)

서버 배포 (10-15분)
☑ scp로 이미지 전송 (5-10분)
☑ docker load 실행 (2-3분)
☑ 기존 컨테이너 제거
☑ docker run으로 새 컨테이너 실행
☑ docker logs에서 cuda 확인
☑ curl /health로 API 응답 확인

검증
☑ nvidia-smi에서 GPU 메모리 사용 확인
☑ 음성 파일로 STT 테스트
☑ 처리 시간 확인 (GPU: 1-2초, CPU: 5-10초)
```

---

**상태**: 🟢 준비 완료! 지금 바로 시작 가능 ✅
