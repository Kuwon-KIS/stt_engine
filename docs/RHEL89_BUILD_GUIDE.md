# RHEL 8.9 환경에 최적화된 STT Engine 빌드 & 배포 가이드

## 📊 대상 환경 정보

```
운영 서버 (RHEL 8.9):
├─ OS: RHEL 8.9 (Ootpa)
├─ glibc: 2.28
├─ Python: 3.11.5
├─ CUDA: 12.9
├─ NVIDIA Driver: 575.57.08
└─ Status: ✅ 모든 정보 확인됨
```

---

## 🎯 빌드 전략

### 선택 사항

| 방식 | 장점 | 단점 | 호환성 |
|------|------|------|--------|
| **RHEL 8.9 EC2** 🔴 | glibc 완벽 일치 | 약간 비쌈 | ✅ 100% |
| **Ubuntu 22.04 EC2** | 저렴 | glibc 불일치 | ⚠️ 90% |
| **운영 서버 직접 빌드** | 비용 절감 | 다운타임 | ✅ 100% |

### 🔴 **권장: RHEL 8.9 EC2 빌드**
```
이유:
1. 타겟 서버와 동일한 glibc 2.28
2. 라이브러리 호환성 100%
3. 안전성 최우선
```

---

## 📋 Step 1: AWS EC2 생성 (RHEL 8.9)

### 1-1. AMI 선택
```bash
# AWS Console에서:
1. EC2 > Instances > Launch Instance
2. "RHEL" 검색
3. "Red Hat Enterprise Linux 8 (HVM)" 선택
4. Version: 8.9
```

### 1-2. 인스턴스 타입
```
t3.large (4GB RAM, 2 vCPU)
또는 t3.xlarge (8GB RAM, 4 vCPU - 권장)
```

### 1-3. Storage
```
EBS: 50GB 이상 (gp3 권장)
```

### 1-4. Security Group
```
Inbound:
- SSH (Port 22) from your-ip
- Optional: HTTP (80), HTTPS (443)
```

---

## 🚀 Step 2: EC2에 연결 및 환경 설정

### 2-1. SSH 연결
```bash
ssh -i your-key.pem ec2-user@<ec2-ip>
```

### 2-2. 필수 패키지 설치

#### 방법 A: Docker 설치 (권장 - 실제 Docker 사용)

```bash
# RHEL 8.9 기본 업데이트
sudo yum update -y

# Development Tools 설치
sudo yum groupinstall -y "Development Tools"

# Git 설치
sudo yum install -y git

# Docker 저장소 추가
sudo yum-config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo

# Docker CE 설치 (Podman 대신 실제 Docker)
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Docker 데몬 시작 및 자동 시작 활성화
sudo systemctl start docker
sudo systemctl enable docker

# 현재 사용자에게 Docker 권한 부여
sudo usermod -aG docker ec2-user
newgrp docker

# 버전 확인
docker --version
docker ps
git --version
```

**💡 팁**: `newgrp docker` 후 새 터미널에서 `sudo` 없이 docker 명령 사용 가능

---

#### 방법 B: Podman 사용 (기본 제공 - Docker 명령 호환)

만약 Docker 설치가 실패하면 Podman을 사용할 수 있습니다:

```bash
# Podman은 이미 설치됨 (위의 docker 설치 건너뜀)
# 동일한 명령으로 작동:
docker --version   # Podman으로 실행됨
docker ps
```

---

## ⚠️ RHEL 8.9 특수 사항: Docker vs Podman

### 상황
위의 **방법 A**로 Docker를 성공적으로 설치했다면 실제 Docker를 사용하고 있습니다.

```bash
# 확인 방법
docker --version
# 출력: Docker version 25.x.x, build xxxxx  ← 실제 Docker
```

### Docker 설치 실패 시

만약 Docker 저장소 추가가 실패하면 (네트워크 이슈 등):

```bash
# Podman으로 대체 가능 (기본 제공)
# docker 명령이 Podman으로 실행됨
docker --version
# 출력: Emulate Docker CLI using podman. podman version 4.9.4-rhel

# 이 경우에도 모든 docker 명령 동일하게 작동:
docker run ...    # ✅ 작동
docker ps         # ✅ 작동
docker build ...  # ✅ 작동
```

---

## 🚀 Step 3: 레포지토리 클론

```bash
# 방법 A: Git 클론 (권장)
cd ~
git clone https://github.com/Kuwon-KIS/stt_engine.git
cd stt_engine

# 방법 B: scp로 로컬 파일 전송
# Mac에서:
scp -i your-key.pem -r ~/workspace/stt_engine ec2-user@<ec2-ip>:~/
```

---

## 🏗️ Step 4: Docker 이미지 빌드 (20~40분)

### 4-1. 빌드 실행

```bash
cd ~/stt_engine

# 방법 1: RHEL 8.9 전용 빌드 스크립트 사용 (권장)
bash scripts/build-stt-engine-rhel89.sh

# 또는 방법 2: 직접 docker build 실행
docker build \
  --platform linux/amd64 \
  -t stt-engine:cuda129-rhel89-v1.2 \
  -f docker/Dockerfile.engine.rhel89 \
  . 2>&1 | tee /tmp/build.log
```

### 4-2. 빌드 진행 상황 모니터링

```bash
# 다른 터미널에서:
ssh -i your-key.pem ec2-user@<ec2-ip>
watch -n 10 'docker ps -a && echo "---" && df -h'

# 또는 로그 모니터링
tail -f /tmp/build.log
```

### 4-3. 빌드 완료 확인

```bash
# 이미지 확인
docker images | grep stt-engine

# 예상 출력:
# stt-engine   cuda129-rhel89-v1.2   HASH   7.3GB   1 minute ago

# 이미지 상세 정보 확인
docker inspect stt-engine:cuda129-rhel89-v1.2 | jq '.Config.Env[] | select(startswith("LD_"))'

# 예상 출력에 LD_LIBRARY_PATH가 포함되어야 함
```

### 4-4. 빌드 오류 처리

```bash
# 오류가 발생한 경우 로그 확인
grep -i "error\|failed\|not found" /tmp/build.log | tail -20
```

---

## 📦 Step 5: 모델 다운로드 및 준비 (25~45분)

**중요**: EC2 빌드 서버의 **로컬 환경**에서 모델을 다운로드합니다 (Docker가 아님).

### 5-0. RHEL 8.9 Python 환경 설정 (필수!)

```bash
cd ~/stt_engine

# 1️⃣ Python 3.11 및 pip 설치 (RHEL 8.9 특수)
sudo yum install -y python3.11-pip python3.11-devel

# 또는 pip가 없으면 ensurepip로 설치
python3.11 -m ensurepip --upgrade

# 2️⃣ pip 업그레이드
python3.11 -m pip install --upgrade pip setuptools wheel

# 3️⃣ 모델 다운로드/변환에 필요한 핵심 패키지 설치
# (이미지 내부에는 이미 설치되어 있지만, 호스트에서도 필요)
python3.11 -m pip install --upgrade \
    torch==2.6.0 \
    torchaudio==2.6.0 \
    transformers \
    ctranslate2 \
    huggingface-hub \
    scipy \
    numpy \
    librosa \
    pydantic \
    urllib3

# 설치 확인
python3.11 -c "import torch, transformers, ctranslate2; print('✅ 모든 패키지 설치됨')"
```

**주의**: 이 단계에서 패키지 설치는 5~15분 정도 소요됩니다.

### 5-1. 모델 다운로드 및 CTranslate2 변환

```bash
cd ~/stt_engine

# 모델 다운로드 및 변환 실행
# 이 스크립트는 자동으로:
#   1. openai/whisper-large-v3-turbo 다운로드 (Hugging Face)
#   2. CTranslate2 포맷 변환 (model.bin 생성)
#   3. 모델 구조 검증
python3.11 download_model_hf.py 2>&1 | tee /tmp/model_download.log

# 예상 출력:
# ========================================================
# 🚀 STT Engine 모델 준비
# ========================================================
# 
# 📌 Step 1: 기존 모델 파일 정리
# ✅ 기존 모델 파일 삭제 완료
#
# 📌 Step 2: Hugging Face에서 모델 다운로드
# ⏳ openai/whisper-large-v3-turbo 다운로드 중...
# ✅ 모델 다운로드 완료 (약 10-15분 소요)
#
# 📌 Step 3: 모델 파일 검증
# ✅ config.json 검증 완료
# ✅ pytorch_model.bin 검증 완료
# ✅ tokenizer.json 검증 완료
#
# 📌 Step 4: CTranslate2 포맷 변환
# ⏳ CTranslate2 변환 중... (약 5~10분 소요)
# ✅ CTranslate2 변환 완료
#
# 📌 Step 5: 모델 구조 검증
# ✅ ctranslate2_model 구조 확인
#    - config.json ✓
#    - model.bin ✓
#    - vocabulary.json ✓
#
# ✅ 모든 단계 완료!
```

**예상 소요시간**: 25~45분 (모델 크기 다운로드: 10~15분 + CTranslate2 변환: 5~10분)

### 5-2. 모델 디렉토리 구조 확인

```bash
# 모델 디렉토리 크기 확인
du -sh models/
du -sh models/openai_whisper-large-v3-turbo/
du -sh models/ctranslate2_model/

# 예상:
# 2.5G  models/
# 1.6G  models/openai_whisper-large-v3-turbo/
# 0.9G  models/ctranslate2_model/

# 파일 확인
find models/ -type f -name "*.json" -o -name "*.bin"
```

### 5-3. 모델 파일 검증 (Python)

```bash
python3.11 << 'PYTHON_TEST'
from pathlib import Path

models_base = Path("models")
print("=" * 70)
print("🔍 모델 구조 세부 검증")
print("=" * 70)

# CTranslate2 모델 확인
print("\n📂 CTranslate2 모델")
ct2_model = models_base / "ctranslate2_model"
required_files = {
    "config.json": "설정 파일",
    "model.bin": "모델 가중치",
    "vocabulary.json": "토크나이저 어휘"
}

for fname, desc in required_files.items():
    fpath = ct2_model / fname
    if fpath.exists():
        size = fpath.stat().st_size / (1024 * 1024)
        print(f"   ✅ {fname:20} ({size:6.1f} MB) - {desc}")
    else:
        print(f"   ❌ {fname:20} NOT FOUND")

# OpenAI Whisper 모델 확인
print("\n📂 OpenAI Whisper 모델")
whisper_model = models_base / "openai_whisper-large-v3-turbo"
required_whisper_files = {
    "config.json": "설정 파일",
    "pytorch_model.bin": "모델 가중치",
    "tokenizer.json": "토크나이저"
}

for fname, desc in required_whisper_files.items():
    fpath = whisper_model / fname
    if fpath.exists():
        size = fpath.stat().st_size / (1024 * 1024)
        print(f"   ✅ {fname:25} ({size:6.1f} MB) - {desc}")
    else:
        print(f"   ❌ {fname:25} NOT FOUND")

print("\n" + "=" * 70)
PYTHON_TEST
```

---

## 🧪 Step 6: 빌드 서버에서 모델 로드 테스트 (20~30분)

### 6-1. 테스트용 컨테이너 시작 (모델 마운트)

```bash
cd ~/stt_engine

# 컨테이너 실행 (모델 디렉토리 마운트)
docker run -it \
  --name stt-test-engine \
  -v $(pwd)/models:/app/models \
  -e CUDA_VISIBLE_DEVICES=0 \
  stt-engine:cuda129-rhel89-v1.2 \
  /bin/bash
```

### 6-2. 컨테이너 내 마운트된 모델 확인

컨테이너 내부에서:

```bash
# 마운트 확인
ls -lh /app/models/
du -sh /app/models/*
```

### 6-3. CUDA 및 PyTorch 검증

컨테이너 내부에서:

```bash
python3 << 'PYTHON_TEST'
import torch
import torchaudio
import os

print("=" * 70)
print("🔍 CUDA & PyTorch 검증")
print("=" * 70)

print(f"\n✅ PyTorch: {torch.__version__}")
print(f"✅ torchaudio: {torchaudio.__version__}")
print(f"✅ CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"✅ CUDA Device: {torch.cuda.get_device_name(0)}")
    x = torch.randn(1000, 1000).cuda()
    y = torch.randn(1000, 1000).cuda()
    z = torch.matmul(x, y)
    print(f"✅ CUDA Matrix Multiplication: Success")

print(f"✅ LD_LIBRARY_PATH: {bool(os.environ.get('LD_LIBRARY_PATH'))}")
print("=" * 70)

PYTHON_TEST
```

### 6-4. 모델 로드 테스트

컨테이너 내부에서:

```bash
# Faster-Whisper (CTranslate2 모델)
python3 << 'PYTHON_TEST'
import sys
sys.path.insert(0, '/app')

print("=" * 70)
print("🎯 Faster-Whisper 모델 로드 테스트")
print("=" * 70)

try:
    from faster_whisper import WhisperModel
    
    print("\n⏳ 모델 로드 중...")
    model = WhisperModel(
        "/app/models/ctranslate2_model",
        device="auto",
        compute_type="float32",
        download_root="/opt/app-root/src/.cache",
        local_files_only=True
    )
    
    print("✅ Faster-Whisper 모델 로드 성공!")
    
except Exception as e:
    print(f"❌ 오류: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

PYTHON_TEST

# OpenAI Whisper (원본 모델)
python3 << 'PYTHON_TEST'
import sys
sys.path.insert(0, '/app')

print("=" * 70)
print("🎯 OpenAI Whisper 모델 로드 테스트")
print("=" * 70)

try:
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
    
    print("\n⏳ Processor 로드 중...")
    processor = AutoProcessor.from_pretrained(
        "/app/models/openai_whisper-large-v3-turbo",
        local_files_only=True,
        cache_dir="/opt/app-root/src/.cache"
    )
    
    print("⏳ Model 로드 중...")
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        "/app/models/openai_whisper-large-v3-turbo",
        local_files_only=True,
        cache_dir="/opt/app-root/src/.cache"
    )
    
    print("✅ OpenAI Whisper 모델 로드 성공!")
    
except Exception as e:
    print(f"❌ 오류: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

PYTHON_TEST
```

### 6-5. 컨테이너 종료

```bash
# 컨테이너에서 exit 실행
exit

# 또는 다른 터미널에서
docker rm stt-test-engine
```

---

## 💾 Step 7: 이미지 및 모델 저장 (5~10분)

### 7-1. EC2에서 이미지와 모델 저장

```bash
cd ~/stt_engine

# Docker 이미지 저장
mkdir -p ~/build/output
docker save stt-engine:cuda129-rhel89-v1.2 | gzip > ~/build/output/stt-engine-cuda129-rhel89-v1.2.tar.gz

# 모델 디렉토리 확인
ls -lh models/
du -sh models/

# 빌드 로그 저장
cp /tmp/build.log ~/build/output/build-$(date +%Y%m%d-%H%M%S).log
cp /tmp/model_download.log ~/build/output/model-$(date +%Y%m%d-%H%M%S).log

# 최종 파일 확인
ls -lh ~/build/output/
```

**소요 시간: 5~10분**

---

## 🚢 Step 8: 운영 서버에 배포

### 8-1. Mac으로 파일 다운로드 (선택사항 - 로컬 검증용)

```bash
# Mac 로컬 터미널:
scp -i your-key.pem ec2-user@<ec2-ip>:~/build/output/stt-engine-cuda129-rhel89-v1.2.tar.gz \
    ~/Downloads/

# 파일 확인
ls -lh ~/Downloads/stt-engine-cuda129-rhel89-v1.2.tar.gz
```

**소요 시간: 2~5분 (네트워크에 따라)**

### 8-2. EC2 빌드 서버에서 운영 서버로 직접 전송 (권장)

```bash
# EC2 빌드 서버에서:
# 1. Docker 이미지 로드
scp -i your-key.pem \
  ~/build/output/stt-engine-cuda129-rhel89-v1.2.tar.gz \
  deploy-user@production-server:/tmp/

# 2. 모델 디렉토리 전송 (대용량이므로 시간이 걸림)
scp -r -i your-key.pem \
  ~/stt_engine/models \
  deploy-user@production-server:/path/to/deployment/
```

### 8-3. 운영 서버에서 로드

```bash
# RHEL 8.9 운영 서버:
cd /tmp

# 1. Docker 이미지 로드
docker load < stt-engine-cuda129-rhel89-v1.2.tar.gz

# 2. 이미지 확인
docker images | grep stt-engine
# 출력: stt-engine  cuda129-rhel89-v1.2  <image-id>  7.3GB
```

---

## ✅ Step 9: 이미지 검증 (운영 서버)

### 9-1. PyTorch/CUDA 검증
```bash
docker run --rm stt-engine:cuda129-rhel89-v1.2 python3.11 -c "
import torch
print(f'✅ PyTorch: {torch.__version__}')
print(f'✅ CUDA Available: {torch.cuda.is_available()}')
print(f'✅ cuDNN: OK')
"

# 예상 출력:
# ✅ PyTorch: 2.6.0
# ✅ CUDA Available: True
# ✅ cuDNN: OK
```

### 9-2. Whisper 검증
```bash
docker run --rm stt-engine:cuda129-rhel89-v1.2 python3.11 -c "
try:
    import faster_whisper
    print('✅ faster-whisper: 로드됨')
except:
    print('⚠️  faster-whisper: 미사용')
    
try:
    from transformers import AutoModelForSpeechSeq2Seq
    print('✅ transformers: 로드됨')
except:
    print('⚠️  transformers: 미사용')
"
```

### 9-3. 모델 마운트 및 통합 테스트

```bash
# 모델 디렉토리 마운트하여 컨테이너 실행
docker run -it \
  --name stt-final-test \
  -v /path/to/models:/app/models \
  -e CUDA_VISIBLE_DEVICES=0 \
  stt-engine:cuda129-rhel89-v1.2 \
  /bin/bash

# 컨테이너 내부에서:
python3 << 'PYTHON_TEST'
import sys
sys.path.insert(0, '/app')

print("=" * 70)
print("✅ 최종 통합 검증")
print("=" * 70)

# Faster-Whisper 로드 확인
try:
    from faster_whisper import WhisperModel
    model = WhisperModel(
        "/app/models/ctranslate2_model",
        device="auto",
        compute_type="float32",
        local_files_only=True
    )
    print("\n✅ Faster-Whisper 모델 로드 성공")
except Exception as e:
    print(f"\n❌ Faster-Whisper 오류: {e}")

# OpenAI Whisper 로드 확인
try:
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
    processor = AutoProcessor.from_pretrained(
        "/app/models/openai_whisper-large-v3-turbo",
        local_files_only=True
    )
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        "/app/models/openai_whisper-large-v3-turbo",
        local_files_only=True
    )
    print("✅ OpenAI Whisper 모델 로드 성공")
except Exception as e:
    print(f"❌ OpenAI Whisper 오류: {e}")

print("\n" + "=" * 70)
print("🎉 모든 검증 완료!")
print("=" * 70)
PYTHON_TEST

# 컨테이너 종료
exit
```

---

## 📊 예상 소요 시간 (전체)

| 단계 | 예상 시간 |
|------|----------|
| Step 1: EC2 생성 | 2분 |
| Step 2: 환경 설정 | 5분 |
| Step 3: 레포지토리 클론 | 2분 |
| Step 4: Docker 이미지 빌드 | 20~40분 |
| **Step 5-0: Python 환경 설정 (NEW)** | **5~15분** |
| Step 5: 모델 다운로드 + 변환 | 20~30분 |
| Step 6: 모델 로드 테스트 | 20~30분 |
| Step 7: 이미지/모델 저장 | 5~10분 |
| Step 8: 운영 서버 배포 | 5~15분 |
| Step 9: 이미지 검증 | 5분 |
| **총 소요 시간** | **95~170분 (1.6~2.8시간)** |

**주요 변경**: Step 5-0에서 Python 환경 설정 추가 (pip, PyTorch 등)

---

## ✅ 최종 검증 체크리스트

모든 항목이 ✅ 상태여야 합니다:

```
Build 서버 (EC2):
  ✅ Docker 이미지 빌드 성공 (7.3GB)
  ✅ 모델 다운로드 완료 (2.5GB)
  ✅ CTranslate2 변환 완료 (model.bin 생성)
  ✅ 모든 모델 파일 검증 완료
  ✅ 테스트 컨테이너 모델 로드 성공

Production 서버 (RHEL 8.9):
  ✅ Docker 이미지 로드 완료
  ✅ 모델 디렉토리 마운트 가능
  ✅ PyTorch/CUDA 정상 작동
  ✅ Faster-Whisper 모델 로드 성공
  ✅ OpenAI Whisper 모델 로드 성공
  ✅ 최종 통합 검증 통과
```

---

## 🎯 다음 단계 (운영 서버)

빌드 및 검증 완료 후:

1. **STT API 서버 실행**
   ```bash
   docker run -d \
     --name stt-api \
     --gpus all \
     -p 5000:5000 \
     -v /path/to/models:/app/models \
     -e CUDA_VISIBLE_DEVICES=0 \
     stt-engine:cuda129-rhel89-v1.2
   ```

2. **헬스 체크**
   ```bash
   sleep 10
   curl http://localhost:5000/health
   # 예상: {"status":"ok","backend":"faster-whisper"}
   ```

3. **STT 서비스 테스트**
   ```bash
   curl -X POST http://localhost:5000/transcribe \
     -F "file=@/path/to/audio.wav"
   ```

---

## 📞 트러블슈팅

| 문제 | 해결책 |
|------|--------|
| `/usr/bin/python3.11: No module named pip` | `sudo yum install -y python3.11-pip` 또는 `python3.11 -m ensurepip --upgrade` |
| `ModuleNotFoundError: No module named 'urllib3'` | Step 5-0 의 Python 패키지 설치 완료 확인 |
| `ModuleNotFoundError: torch` | PyTorch 2.6.0 설치 확인: `python3.11 -m pip install torch==2.6.0` |
| `ModuleNotFoundError: transformers` | `python3.11 -m pip install transformers` |
| `ModuleNotFoundError: ctranslate2` | `python3.11 -m pip install ctranslate2` |
| Docker 빌드 실패 | 인터넷 연결 확인, `grep -i error /tmp/build.log` 확인 |
| 모델 다운로드 실패 | HuggingFace 접근성 확인, VPN 사용, 프록시 설정 |
| CUDA 인식 안됨 | 운영 서버의 `nvidia-smi` 확인 |
| 모델 로드 실패 | 모델 파일 경로 확인, `/app/models` 마운트 확인 |
| 디스크 부족 | EC2: `df -h` 확인, 운영 서버: 충분한 스토리지 확보 |

---

## 📝 체크리스트 (완전 버전)

```
[ ] RHEL 8.9 정보 수집 완료
    - OS: 8.9
    - glibc: 2.28
    - Python: 3.11.5
    - CUDA: 12.9
    - NVIDIA Driver: 575.57.08

[ ] AWS EC2 RHEL 8.9 생성
    - t3.large 이상 (또는 t3.xlarge 권장)
    - 100GB 이상 스토리지 (Docker 7GB + 모델 2.5GB + 여유)
    - Security Group 설정

[ ] EC2 환경 설정
    - Docker 설치 및 실행
    - Git 설치
    - 사용자 권한 설정

[ ] Step 3: 레포지토리 클론
    - git clone 완료
    - 코드 최신화 확인

[ ] Step 4: Docker 이미지 빌드
    - 빌드 스크립트 실행
    - 빌드 완료 (7.3GB)
    - LD_LIBRARY_PATH 설정 확인

[ ] Step 5: 모델 다운로드 및 준비
    - download_model_hf.py 실행 완료
    - models/ 디렉토리 (2.5GB) 생성
    - CTranslate2 변환 완료
    - 모델 파일 검증 완료

[ ] Step 6: 빌드 서버에서 모델 로드 테스트
    - 테스트 컨테이너 실행
    - CUDA 및 PyTorch 검증
    - Faster-Whisper 로드 성공
    - OpenAI Whisper 로드 성공

[ ] Step 7: 이미지 및 모델 저장
    - Docker 이미지 저장 (tar.gz)
    - 빌드 로그 저장
    - 모델 디렉토리 확인

[ ] Step 8: 운영 서버 배포
    - 이미지 및 모델 전송 완료
    - 운영 서버 로드 완료

[ ] Step 9: 이미지 검증
    - PyTorch/CUDA 검증
    - Whisper 검증
    - 모델 마운트 테스트
    - 통합 검증 완료
```

---

## 🎯 주요 포인트 정리

### Build 서버 (AWS EC2 RHEL 8.9)에서:

1. **Step 1~3**: AWS EC2 준비 및 레포지토리 클론
   - ✅ 약 10분

2. **Step 4**: Docker 이미지 빌드
   - ✅ 약 20~40분
   - 결과: `stt-engine:cuda129-rhel89-v1.2` (7.3GB)

3. **Step 5**: 모델 다운로드 + CTranslate2 변환 (NEW)
   - ✅ 약 25~45분
   - 결과: `models/` 디렉토리 (2.5GB)
     - `openai_whisper-large-v3-turbo/` (1.6GB)
     - `ctranslate2_model/` (0.9GB)

4. **Step 6**: 모델 로드 테스트 (NEW)
   - ✅ 약 20~30분
   - Faster-Whisper + OpenAI Whisper 모두 테스트

5. **Step 7**: 이미지 및 모델 저장
   - ✅ 약 5~10분

6. **Step 8~9**: 운영 서버 배포 및 검증
   - ✅ 약 15~25분

### 최종 결과:
- ✅ Production Ready Docker 이미지
- ✅ 완벽하게 검증된 모델 세트
- ✅ RHEL 8.9 100% 호환성 보장

---

**마지막 업데이트**: 2026년 2월 7일
