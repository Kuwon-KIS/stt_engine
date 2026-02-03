# 🚀 CUDA 12.4 PyTorch 이미지 빌드 실행 가이드

**작성일**: 2026-02-03  
**목표**: CUDA 12.9 서버와 호환되는 이미지 빌드  
**소요 시간**: 40-50분

---

## 1️⃣ 사전 검증 (서버에서 먼저 확인)

```bash
# SSH로 서버 접속 후

# 1. GPU 드라이버 버전 확인
nvidia-smi

# 출력 예:
# NVIDIA-SMI 555.42.02
# CUDA Version: 12.9
# ...

# 드라이버가 555.xx 이상이면 → CUDA 12.4 호환 ✅
# 드라이버가 550.xx 이하이면 → 업그레이드 필요 ❌

# 2. CUDA Toolkit 확인
nvcc --version

# 출력 예:
# nvcc: NVIDIA (R) Cuda compiler driver
# release 12.9, V12.9.1
```

**조건 확인**:
- ☑ GPU 드라이버: 555.xx 이상
- ☑ CUDA Toolkit: 12.9 설치됨

---

## 2️⃣ 로컬에서 CUDA 12.4 Wheel 준비

### Step 1: 새 wheels 디렉토리 생성

```bash
cd /Users/a113211/workspace/stt_engine

# 기존 wheels는 유지하고 새로 만들기
mkdir -p deployment_package/wheels-cu124

cd deployment_package/wheels-cu124
```

### Step 2: CUDA 12.4용 PyTorch wheels 다운로드

```bash
# 현재 위치: deployment_package/wheels-cu124/

# PyTorch CUDA 12.4 버전 다운로드
python3 -m pip wheel torch==2.1.2 torchaudio==2.1.2 \
  --index-url https://download.pytorch.org/whl/cu124 \
  -w . \
  --no-deps

# 다른 의존성 (이전과 동일)
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
  -w . \
  --no-deps

# 확인: wheels 파일 개수
ls -1 | wc -l
# 예상: 60개 이상

# 크기 확인
du -sh .
# 예상: 400MB 정도
```

**다운로드 완료 확인**:
```bash
$ ls -lh | grep -E "torch|cuda|pytorch"
# 다음 파일들이 있어야 함:
# torch-2.1.2-cp311-cp311-linux_x86_64.whl
# torchaudio-2.1.2-cp311-cp311-linux_x86_64.whl
```

---

## 3️⃣ CUDA 12.4용 Dockerfile 생성

```bash
# 로컬 workspace에서

cd /Users/a113211/workspace/stt_engine
```

`docker/Dockerfile.engine-cu124` 파일을 생성:

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

---

## 4️⃣ CUDA 12.4 이미지 빌드

```bash
cd /Users/a113211/workspace/stt_engine

# 빌드 시작 (30-40분 소요)
docker build \
  -t stt-engine:cu124 \
  -f docker/Dockerfile.engine-cu124 \
  . \
  2>&1 | tee /tmp/build-cu124.log

# 또는 백그라운드에서
nohup docker build \
  -t stt-engine:cu124 \
  -f docker/Dockerfile.engine-cu124 \
  . > /tmp/build-cu124.log 2>&1 &

# 빌드 진행 상황 확인
tail -f /tmp/build-cu124.log
```

**빌드 확인**:
```bash
# 완료 후
docker images | grep cu124

# 예상 출력
# stt-engine           cu124          abc123...     1.1GB
```

---

## 5️⃣ 이미지를 tar.gz로 저장

```bash
# 빌드 완료 후

mkdir -p build/output

# 이미지를 압축 파일로 저장
docker save stt-engine:cu124 | gzip > build/output/stt-engine-cu124.tar.gz

# 크기 확인
ls -lh build/output/stt-engine-cu124.tar.gz

# 예상: 1.0-1.1GB
```

---

## 6️⃣ 서버로 이미지 전송

```bash
# 로컬에서 서버로 전송
scp build/output/stt-engine-cu124.tar.gz ddpapp@dlddpgai1:/data/stt/

# 또는
scp build/output/stt-engine-cu124.tar.gz user@server:/path/to/

# 전송 진행 상황 확인
# (약 5-10분 소요, 네트워크 속도에 따라)
```

---

## 7️⃣ 서버에서 배포

```bash
# 서버에 SSH 접속
ssh user@server

# 또는
ssh ddpapp@dlddpgai1

# 이미지 로드
cd /data/stt
docker load -i stt-engine-cu124.tar.gz

# 로드 확인
docker images | grep cu124
```

### 기존 컨테이너 정리

```bash
# 실행 중인 컨테이너 중지
docker stop stt-engine 2>/dev/null || true

# 컨테이너 제거
docker rm stt-engine 2>/dev/null || true

# 확인
docker ps -a | grep stt-engine
# (아무것도 나오지 않아야 함)
```

### 새 컨테이너 실행

```bash
# CUDA 12.4 이미지로 실행
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v /data/models:/app/models \
  -v /data/logs:/app/logs \
  --gpus all \
  -e STT_DEVICE=auto \
  stt-engine:cu124

# 또는 CUDA 자동 선택
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v /data/models:/app/models \
  -v /data/logs:/app/logs \
  --gpus all \
  stt-engine:cu124
```

**참고**: 
- `--gpus all`: GPU 모든 CUDA 기능 활성화
- `STT_DEVICE=auto`: 자동 감지 (더 안전)

### 배포 검증

```bash
# 컨테이너 상태 확인
docker ps | grep stt-engine

# 예상: stt-engine ... Up ... 0.0.0.0:8003->8003/tcp

# 로그 확인 (CUDA 초기화 메시지 확인)
docker logs -f stt-engine

# 예상 로그:
# ✅ faster-whisper 모델 로드 완료 (Device: cuda, compute: float16)
# INFO:     Started server process
# INFO:     Uvicorn running on http://0.0.0.0:8003
```

### 헬스 체크

```bash
# API 응답 확인
curl -X GET http://localhost:8003/health

# 예상 응답:
# {"status": "healthy", "device": "cuda"}
```

### 음성 파일 테스트

```bash
# 테스트 음성 파일이 있으면
curl -X POST http://localhost:8003/transcribe \
  -F "file=@/data/test_audio.wav"

# 예상 응답:
# {
#   "text": "recognized text...",
#   "duration_seconds": 5.2,
#   "processing_time_seconds": 0.8,
#   "model": "whisper-large-v3-turbo",
#   "device": "cuda"
# }
```

---

## 📊 빌드 체크리스트

```
로컬 준비 (40분)
☑ CUDA 12.4 wheels 다운로드 (deployment_package/wheels-cu124/)
☑ Dockerfile.engine-cu124 생성
☑ Docker 이미지 빌드 (docker build ...)
☑ 이미지 tar.gz 저장 (docker save ...)
☑ 파일 크기 확인 (~1.1GB)

서버 전송 (10분)
☑ scp로 이미지 파일 전송 (build/output/stt-engine-cu124.tar.gz)
☑ 전송 완료 확인 (/data/stt/stt-engine-cu124.tar.gz)

서버 배포 (5분)
☑ docker load -i stt-engine-cu124.tar.gz
☑ 기존 컨테이너 중지/제거
☑ 새 컨테이너 실행 (--gpus all)
☑ docker logs 확인 (Device: cuda)
☑ curl /health 헬스 체크
☑ 음성 파일 STT 테스트

최종 검증
☑ GPU 사용 확인 (nvidia-smi)
☑ 로그 모니터링 (에러 없음)
☑ STT 성능 확인 (처리 시간)
```

---

## 🔄 만약 CUDA 12.4가 아닌 다른 버전이 필요하면?

### PyTorch CUDA 버전 변경

```bash
# CUDA 12.4 대신:
# - CUDA 11.8: --index-url https://download.pytorch.org/whl/cu118
# - CUDA 12.1: --index-url https://download.pytorch.org/whl/cu121
# - CUDA 12.5: --index-url https://download.pytorch.org/whl/cu125

# 예: CUDA 11.8용
pip wheel torch==2.1.2 torchaudio==2.1.2 \
  --index-url https://download.pytorch.org/whl/cu118 \
  -w deployment_package/wheels-cu118/
```

---

## ⏱️ 소요 시간 예측

| 단계 | 예상 시간 |
|------|----------|
| wheels 다운로드 | 10-15분 |
| Docker 빌드 | 20-30분 |
| tar.gz 저장 | 2-3분 |
| scp 전송 | 5-10분 (네트워크) |
| 서버 로드 | 2-3분 |
| 컨테이너 실행 | 1-2분 |
| **총계** | **40-60분** |

---

## 🎯 최종 권장사항

**CUDA 12.9 서버에는 CUDA 12.4 이미지가 정답입니다!**

```bash
# 1단계: 서버 확인 (드라이버 555.xx 이상)
nvidia-smi

# 2단계: 로컬에서 빌드 (40분)
python3 -m pip wheel torch==2.1.2 --index-url https://download.pytorch.org/whl/cu124 -w deployment_package/wheels-cu124/
docker build -t stt-engine:cu124 -f docker/Dockerfile.engine-cu124 .

# 3단계: 서버 배포 (10분)
scp build/output/stt-engine-cu124.tar.gz server:/data/
ssh server "docker load -i /data/stt-engine-cu124.tar.gz && \
  docker run -d --gpus all -p 8003:8003 stt-engine:cu124"

# 4단계: 검증 (5분)
curl http://server:8003/health
```

---

**상태**: 🟢 CUDA 12.9 환경 완벽 지원 ✅
