# ⚠️ ❌ [2026-02-03 v1.0-DEPRECATED] 이 문서는 작동하지 않습니다 (아키텍처 불일치)

**버전**: v1.0-DEPRECATED (폐기됨)  
**날짜**: 2026-02-03  
**상태**: ❌ **사용 금지** (아키텍처 불일치)  
**우선순위**: 읽지 마세요 (참고용으로만)

---

## 📋 문서 상태

| 버전 | 날짜 | 상태 | 설명 |
|------|------|------|------|
| v1.0-DEPRECATED | 2026-02-03 | ❌ **폐기** | Mac 아키텍처에서 Linux 바이너리 받으려고 시도 (불가능) |

### ⚠️ 이 문서를 사용하면 안 되는 이유
- ❌ Mac에서 Linux용 wheel 다운로드 시도 (아키텍처 불일치)
- ❌ Docker 이미지 빌드 (실패 경험 있음)
- ❌ CPU 버전 설치 가능성 높음

### ✅ 대신 이 문서를 읽으세요
👉 **[CORRECT_FINAL_DEPLOYMENT.md](CORRECT_FINAL_DEPLOYMENT.md)**

---

## 왜 이 방식이 작동하지 않는가?

```
❌ 문제: Mac에서 Linux용 PyTorch wheel을 다운로드하려고 함

Mac (darwin 아키텍처)
  ↓
pip wheel torch (← Mac용 wheel 다운로드)
  ↓
torch-2.1.2-cp311-cp311-macosx_11_0_arm64.whl ← Mac용!
  ↓
Linux 서버로 전송
  ↓
설치 시도 → ❌ 호환되지 않음 (아키텍처 불일치)
```

**해결책**: Linux 서버에서 직접 `pip install torch` (아래 링크 참고)

---

## ✅ 정정된 최종 방법

👉 **[CORRECT_FINAL_DEPLOYMENT.md](CORRECT_FINAL_DEPLOYMENT.md)를 읽으세요!**

이 문서에서:
1. Mac에서는 tar.gz만 준비
2. Linux 서버에서 직접 `pip install torch`
3. 100% 성공률

---

# ❌ 이전 내용 (참고용, 실제로는 작동 안 함)

### Step 1: wheels-cu124 폴더 생성

```bash
cd /Users/a113211/workspace/stt_engine
mkdir -p deployment_package/wheels-cu124
```

### Step 2: CUDA 12.4 PyTorch 다운로드 (⚠️ --index-url 필수!)

```bash
# ⚠️ 반드시 --index-url 포함할 것! 
# 없으면 CPU 버전 다운로드됨

python3 -m pip wheel torch==2.1.2 torchaudio==2.1.2 \
  --index-url https://download.pytorch.org/whl/cu124 \
  -w deployment_package/wheels-cu124/ \
  --no-deps
```

### Step 3: 다운로드 확인 (매우 중요!)

```bash
# cu124가 포함되어야 함!
ls -lh deployment_package/wheels-cu124/ | grep torch

# ✅ 정확한 파일명:
# torch-2.1.2-cp311-cp311-cu124-linux_x86_64.whl
# torchaudio-2.1.2-cp311-cp311-cu124-linux_x86_64.whl

# ❌ 잘못된 파일명 (이러면 삭제하고 다시):
# torch-2.1.2+cpu-cp311-cp311-linux_x86_64.whl (CPU 버전)
# torch-2.1.2-cp311-cp311-linux_x86_64.whl (cu124 없음)
```

**다시 다운로드하려면** (cu124 파일이 없으면):
```bash
rm -rf deployment_package/wheels-cu124
mkdir -p deployment_package/wheels-cu124

# 다시 시도 (--index-url 확인)
python3 -m pip wheel torch==2.1.2 torchaudio==2.1.2 \
  --index-url https://download.pytorch.org/whl/cu124 \
  -w deployment_package/wheels-cu124/ \
  --no-deps
```

### Step 4: 다른 의존성 다운로드

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
```

### Step 5: Dockerfile.engine-cu124 생성

파일 `docker/Dockerfile.engine-cu124` 생성:

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libsndfile1 ffmpeg curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY deployment_package/wheels-cu124/ /wheels/

RUN python3.11 -m pip install --no-index --find-links=/wheels/ \
    torch torchaudio faster-whisper \
    librosa scipy numpy \
    fastapi uvicorn requests pydantic \
    huggingface-hub python-dotenv pyyaml \
    python-multipart && \
    rm -rf /wheels/

COPY stt_engine.py api_server.py requirements.txt /app/

RUN mkdir -p /app/models /app/logs /app/audio

ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/models
ENV STT_DEVICE=auto

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

CMD ["python3.11", "api_server.py"]
```

### Step 6: Docker 이미지 빌드 (20-25분)

```bash
cd /Users/a113211/workspace/stt_engine

docker build \
  -t stt-engine:cu124 \
  -f docker/Dockerfile.engine-cu124 \
  .
```

### Step 7: CUDA 지원 확인 (⚠️ 반드시 확인!)

```bash
# 새 이미지에서 PyTorch CUDA 버전 확인
docker run -it stt-engine:cu124 python3 -c \
  "import torch; print(f'PyTorch CUDA: {torch.version.cuda}')"

# ✅ 정확한 출력 (이렇게 나와야 함):
# PyTorch CUDA: 12.4

# ❌ 잘못된 출력 (이러면 Step 2부터 다시):
# PyTorch CUDA: None
```

**이 단계를 반드시 확인하세요!** 만약 `None`이 나오면 --index-url 문제입니다.

### Step 8: 이미지 저장

```bash
mkdir -p build/output

docker save stt-engine:cu124 | gzip > build/output/stt-engine-cu124.tar.gz

ls -lh build/output/stt-engine-cu124.tar.gz
# 예상: ~1.0-1.1GB
```

---

## 🖥️ 서버 배포 (10분)

### 1. 이미지 전송

```bash
# 로컬에서
scp build/output/stt-engine-cu124.tar.gz ddpapp@dlddpgai1:/data/stt/
```

### 2. 서버에서 로드 및 실행

```bash
# 서버에 SSH
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

# 로그 확인 (Ctrl+C로 종료)
docker logs -f stt-engine
```

### 3. GPU 사용 확인 (매우 중요!)

```bash
# 컨테이너에서 PyTorch CUDA 확인
docker exec stt-engine python3 -c \
  "import torch; print(f'PyTorch CUDA: {torch.version.cuda}'); \
   print(f'CUDA Available: {torch.cuda.is_available()}')"

# ✅ 정확한 출력:
# PyTorch CUDA: 12.4
# CUDA Available: True

# ❌ 잘못된 출력 (이러면 Step 2부터 다시):
# PyTorch CUDA: None
# CUDA Available: False
```

### 4. API 테스트

```bash
# 헬스 체크
curl -X GET http://localhost:8003/health

# 예상 응답:
# {"status":"healthy","device":"cuda"}

# GPU 메모리 확인
nvidia-smi

# 예상: 1.1GB GPU 메모리 사용 중
```

---

## 🚨 주의사항

### --index-url 절대 빠뜨리면 안 됨!

```bash
# ❌ 이렇게 하면 CPU 버전 다운로드됨:
pip wheel torch==2.1.2 -w deployment_package/wheels-cu124/

# ✅ 반드시 이렇게:
pip wheel torch==2.1.2 \
  --index-url https://download.pytorch.org/whl/cu124 \
  -w deployment_package/wheels-cu124/
```

### 다운로드 후 파일명 반드시 확인!

```bash
# torch 파일 확인
ls deployment_package/wheels-cu124/ | grep torch

# ✅ cu124가 있어야 함:
# torch-2.1.2-cp311-cp311-cu124-linux_x86_64.whl

# ❌ cu124가 없으면 다시 다운로드:
# torch-2.1.2+cpu-cp311-cp311-linux_x86_64.whl (이건 CPU!)
```

### Docker 빌드 후 CUDA 테스트 반드시 할 것!

```bash
# Step 7에서 반드시 확인:
docker run -it stt-engine:cu124 python3 -c \
  "import torch; print(torch.version.cuda)"

# None이 나오면 Step 2부터 다시!
```

---

## 📊 진행 상황 체크리스트

```
로컬 (40분)
☑ wheels-cu124 폴더 생성
☑ --index-url https://download.pytorch.org/whl/cu124 로 torch 다운로드
☑ ls로 cu124 파일 확인 (cu124가 파일명에 있는지!)
☑ 다른 의존성 다운로드
☑ Dockerfile.engine-cu124 생성
☑ docker build 실행
☑ docker run으로 PyTorch CUDA 확인: "PyTorch CUDA: 12.4" ✅
☑ docker save로 tar.gz 생성

서버 (10분)
☑ scp로 이미지 전송
☑ docker load
☑ docker run --gpus all
☑ docker exec로 CUDA 재확인: "PyTorch CUDA: 12.4" ✅
☑ curl /health → "device":"cuda"
```

---

**시작하세요!** Step 1부터 Step 7까지 순서대로 따라가면 됩니다. 특히 Step 3과 Step 7에서 CUDA 버전을 반드시 확인하세요! ✅
