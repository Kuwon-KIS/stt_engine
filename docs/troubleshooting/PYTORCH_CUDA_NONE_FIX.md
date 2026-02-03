# ⚠️ ❌ [2026-02-03 v1.0-DEPRECATED] PyTorch CUDA: None 문제 분석 (폐기됨)

**버전**: v1.0-DEPRECATED (폐기됨)  
**발견일**: 2026-02-03  
**상태**: ❌ **사용 금지** (Docker 이미지 내 수정 방식)

---

## 📋 문서 상태

| 버전 | 날짜 | 상태 | 설명 |
|------|------|------|------|
| v1.0-DEPRECATED | 2026-02-03 | ❌ **폐기** | Docker 이미지 내에서 CUDA 12.4 wheel 설치 시도 (불가능) |

### ⚠️ 이 문서를 사용하면 안 되는 이유
- ❌ Mac에서 CUDA wheel 다운로드 (아키텍처 불일치)
- ❌ Docker 이미지 내에서 수정 (이미지가 잘못되었으면 실패)
- ❌ CPU 버전 설치 가능성

### ✅ 대신 이 문서를 읽으세요
👉 **[CORRECT_FINAL_DEPLOYMENT.md](CORRECT_FINAL_DEPLOYMENT.md)**

---

# ❌ 이전 내용 (작동하지 않음)

## 🔴 중요: PyTorch CUDA: None 문제 분석 및 해결

---

## 🔍 무엇을 의미하는가?

### PyTorch CUDA 버전 확인 결과

```bash
$ docker run -it stt-engine:linux-x86_64 python3 -c \
  "import torch; print(f'PyTorch CUDA: {torch.version.cuda}')"

# 결과
PyTorch CUDA: None
```

### 해석

| 결과 | 의미 | GPU 사용 |
|------|------|---------|
| `PyTorch CUDA: 12.1` | CUDA 12.1 지원 PyTorch | ✅ 가능 |
| `PyTorch CUDA: None` | CPU 전용 PyTorch | ❌ 불가능 |

**현 상황**: 
- PyTorch는 설치되어 있음
- **하지만 CUDA 지원 없음**
- GPU 사용 불가능

---

## 🤔 왜 이런 일이 발생했을까?

### 가능성 1: wheels에 CPU 전용 PyTorch가 있었음 ✅ 확인됨

```bash
# deployment_package/wheels/ 에 있는 PyTorch wheel 확인
$ ls deployment_package/wheels/ | grep torch

# 실제 결과:
# torch-2.1.2+cpu-cp311-cp311-linux_x86_64.whl ← CPU 버전!
# torchaudio-2.1.2+cpu-cp311-cp311-linux_x86_64.whl ← CPU 버전!
```

**CPU vs CUDA wheel 이름 비교**:
```
CPU 버전:    torch-2.1.2+cpu-cp311-cp311-linux_x86_64.whl ← 현재!
CUDA 12.1:   torch-2.1.2-cp311-cp311-cu121-linux_x86_64.whl
CUDA 12.4:   torch-2.1.2-cp311-cp311-cu124-linux_x86_64.whl
             ↑ CUDA 버전이 명시됨 (없으면 CPU 버전)

현재: torch-2.1.2+cpu-cp311-cp311-linux_x86_64.whl
      → **CPU 전용** (이것이 문제!)
```

**확인**:
- `+cpu` 표기 = CPU 전용
- `cu124` 표기 = CUDA 12.4 지원
- 아무 표기 없으면 = CPU 또는 호환성 문제

### 가능성 2: 원래 다운로드할 때 --index-url을 지정하지 않아서

```bash
# 잘못된 명령어 (인덱스 지정 안 함)
pip wheel torch==2.1.2 -w deployment_package/wheels/
# → 최신 CPU 버전 다운로드

# 올바른 명령어
pip wheel torch==2.1.2 --index-url https://download.pytorch.org/whl/cu121 -w deployment_package/wheels/
# → CUDA 12.1 버전 다운로드
```

---

## ✅ 해결책

### 현재 상황에서 즉시 할 일

**현재 이미지는 GPU 사용 불가능하므로, CUDA 12.4 새 이미지 빌드가 필수입니다.**

```
CPU PyTorch (현재) → GPU 사용 불가능 ❌
       ↓
CUDA 12.4 PyTorch (새 빌드) → GPU 사용 가능 ✅
```

---

## 🚀 CUDA 12.4 이미지 빌드 (정확한 명령어)

### Step 1: wheels-cu124 폴더 생성

```bash
cd /Users/a113211/workspace/stt_engine
mkdir -p deployment_package/wheels-cu124
```

### Step 2: CUDA 12.4 PyTorch wheels 다운로드 (매우 중요!)

```bash
# ⚠️ 반드시 --index-url을 포함할 것!

python3 -m pip wheel torch==2.1.2 torchaudio==2.1.2 \
  --index-url https://download.pytorch.org/whl/cu124 \
  -w deployment_package/wheels-cu124/ \
  --no-deps

# 검증: 다운로드된 wheel 이름 확인
ls -lh deployment_package/wheels-cu124/ | grep torch

# 예상 (cu124가 포함되어야 함):
# torch-2.1.2-cp311-cp311-cu124-linux_x86_64.whl ✅
# torchaudio-2.1.2-cp311-cp311-cu124-linux_x86_64.whl ✅
```

**중요**: 
- ❌ `torch-2.1.2-cp311-cp311-linux_x86_64.whl` (cu124 없음 = CPU 버전)
- ✅ `torch-2.1.2-cp311-cp311-cu124-linux_x86_64.whl` (cu124 있음 = CUDA 버전)

### Step 3: 다른 의존성 다운로드

```bash
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

# 확인
ls -1 deployment_package/wheels-cu124/ | wc -l
# 예상: 60개 이상
```

### Step 4: Dockerfile.engine-cu124 생성 또는 확인

파일: `docker/Dockerfile.engine-cu124`

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

### Step 5: Docker 이미지 빌드

```bash
cd /Users/a113211/workspace/stt_engine

docker build \
  -t stt-engine:cu124 \
  -f docker/Dockerfile.engine-cu124 \
  .

# 빌드 완료 확인
docker images | grep cu124
```

### Step 6: CUDA 지원 확인 (중요!)

```bash
# 새 이미지에서 PyTorch CUDA 버전 확인
docker run -it stt-engine:cu124 python3 -c \
  "import torch; print(f'PyTorch CUDA: {torch.version.cuda}'); \
   print(f'CUDA Available: {torch.cuda.is_available()}')"

# 예상 출력:
# PyTorch CUDA: 12.4  ✅
# CUDA Available: False  (서버 GPU가 없으므로)
```

**중요**: 
- ❌ `PyTorch CUDA: None` → CPU 버전 (실패)
- ✅ `PyTorch CUDA: 12.4` → CUDA 버전 (성공)

### Step 7: 이미지를 tar.gz로 저장

```bash
mkdir -p build/output

docker save stt-engine:cu124 | gzip > build/output/stt-engine-cu124.tar.gz

# 크기 확인
ls -lh build/output/stt-engine-cu124.tar.gz
# 예상: ~1.0-1.1GB
```

---

## 🖥️ 서버에서 배포

### 이미지 전송 및 로드

```bash
# 로컬에서 서버로 전송
scp build/output/stt-engine-cu124.tar.gz ddpapp@dlddpgai1:/data/stt/

# 서버에 SSH 접속
ssh ddpapp@dlddpgai1

# 이미지 로드
docker load -i /data/stt/stt-engine-cu124.tar.gz

# 기존 컨테이너 정리
docker stop stt-engine 2>/dev/null || true
docker rm stt-engine 2>/dev/null || true

# 새 컨테이너 실행
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v /data/models:/app/models \
  -v /data/logs:/app/logs \
  --gpus all \
  stt-engine:cu124

# 로그에서 CUDA 확인
docker logs -f stt-engine

# 예상 로그:
# ✅ faster-whisper 모델 로드 완료 (Device: cuda, compute: float16)
```

### 검증

```bash
# CUDA 사용 확인
docker exec stt-engine python3 -c \
  "import torch; print(f'PyTorch CUDA: {torch.version.cuda}'); \
   print(f'CUDA Available: {torch.cuda.is_available()}'); \
   print(f'Device: {torch.cuda.current_device()}')"

# 예상 출력:
# PyTorch CUDA: 12.4  ✅
# CUDA Available: True  ✅
# Device: 0  ✅
```

---

## 🚨 현재 상황 정리

| 항목 | 상태 |
|------|------|
| 현재 이미지 (stt-engine:linux-x86_64) | CPU PyTorch (CUDA: None) ❌ |
| GPU 드라이버 (575.57.08) | ✅ 완벽 |
| CUDA Runtime (12.9) | ✅ 있음 |
| 필요한 것 | CUDA 12.4 PyTorch 새 이미지 빌드 |

---

## 📋 실행 체크리스트

```
로컬 빌드 (40분)
☑ deployment_package/wheels-cu124/ 폴더 생성
☑ pip wheel torch==2.1.2 --index-url https://download.pytorch.org/whl/cu124
  → cu124가 포함된 wheel 다운로드 확인 ✅
☑ 다른 의존성 wheels 다운로드
☑ Dockerfile.engine-cu124 생성/확인
☑ docker build -t stt-engine:cu124 실행
☑ docker run으로 CUDA 버전 확인: "PyTorch CUDA: 12.4" ✅
☑ docker save로 tar.gz 생성

서버 배포 (15분)
☑ scp로 이미지 전송
☑ docker load 실행
☑ docker run --gpus all 실행
☑ docker logs에서 "Device: cuda" 확인
☑ docker exec로 PyTorch CUDA 버전 재확인: "PyTorch CUDA: 12.4" ✅

최종 검증
☑ nvidia-smi에서 GPU 메모리 사용 보임
☑ curl /health → {"status":"healthy","device":"cuda"}
☑ 음성 파일 STT 테스트 (GPU 사용 확인)
```

---

## ⚠️ 중요 주의사항

### --index-url 반드시 포함!

```bash
# ❌ 잘못된 명령어 (CPU 버전 다운로드)
pip wheel torch==2.1.2 -w deployment_package/wheels-cu124/

# ✅ 올바른 명령어 (CUDA 12.4 버전 다운로드)
pip wheel torch==2.1.2 \
  --index-url https://download.pytorch.org/whl/cu124 \
  -w deployment_package/wheels-cu124/
```

**--index-url이 없으면**:
- PyPI 기본 인덱스에서 다운로드
- CPU 전용 최신 버전 (또는 CUDA 지원 안 하는 버전) 다운로드
- 같은 문제 반복!

### 다운로드 후 확인!

```bash
# 다운로드 후 반드시 확인
ls -lh deployment_package/wheels-cu124/ | grep torch

# ✅ 정확한 파일명:
# torch-2.1.2-cp311-cp311-cu124-linux_x86_64.whl
# torchaudio-2.1.2-cp311-cp311-cu124-linux_x86_64.whl
```

---

**결론**: CUDA 12.4 PyTorch 이미지를 정확히 빌드하면 GPU 지원 완벽하게 됩니다! 🎯
