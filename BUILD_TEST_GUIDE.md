# STT Engine - 빌드 및 모델 테스트 완벽 가이드

## 📋 개요

운영 서버 배포 전 빌드 서버에서 **Docker 이미지 재빌드 + 모델 다운로드 + 통합 테스트**를 수행하는 완벽한 가이드입니다.

**이 가이드로 완성되는 것:**
- ✅ RHEL 8.9 호환 Docker 이미지 (`stt-engine:cuda129-rhel89-v1.2`)
- ✅ OpenAI Whisper Large-v3-turbo 모델 (원본 + CTranslate2 변환)
- ✅ 엔진과 모델의 통합 테스트
- ✅ 운영 서버 배포 준비 완료

---

## 🔄 Phase 1: 빌드 서버 환경 준비 (5~10분)

### 1-1. 빌드 서버 접속 및 사전 체크

```bash
# 빌드 서버 SSH 접속
ssh -i your-key.pem ec2-user@build-server-ip

# Docker 상태 확인
docker --version
docker ps

# 디스크 공간 확인 (최소 100GB 필요: Docker 이미지 7GB + 모델 2.5GB)
df -h /

# 인터넷 연결 확인
ping -c 3 8.8.8.8
```

### 1-2. 소스 코드 업데이트

```bash
cd /path/to/stt_engine

# 최신 코드 가져오기
git fetch origin main
git reset --hard origin/main

# 변경 사항 확인
git log --oneline -5
# 최신 커밋에 "fix: Update CTranslate2 model validation..." 있는지 확인
```

### 1-3. 기존 이미지 및 모델 정리

```bash
# 기존 이미지 제거 (선택사항)
docker rmi stt-engine:cuda129-rhel89-v1.2 2>/dev/null || true

# 미사용 이미지 정리
docker image prune -a --force --filter "until=24h"

# 디스크 정리
docker system prune -a --force

# 기존 모델 제거 (옵션)
rm -rf /path/to/stt_engine/models
```

---

## 🔨 Phase 2: Docker 이미지 빌드 (20~40분)

### 2-1. 빌드 실행

```bash
cd /path/to/stt_engine

# 방법 1: RHEL 8.9 전용 빌드 스크립트 사용 (권장)
bash scripts/build-stt-engine-rhel89.sh

# 또는 방법 2: 직접 docker build 실행
docker build \
  --platform linux/amd64 \
  -t stt-engine:cuda129-rhel89-v1.2 \
  -f docker/Dockerfile.engine.rhel89 \
  . 2>&1 | tee /tmp/build.log
```

### 2-2. 빌드 진행 상황 모니터링

```bash
# 별도 터미널에서 로그 모니터링
tail -f /tmp/build.log

# Docker 빌드 상태 확인
docker ps -a
```

### 2-3. 빌드 완료 확인

```bash
# 이미지 확인
docker images | grep stt-engine

# 예상 출력:
# stt-engine   cuda129-rhel89-v1.2   HASH   7.3GB   1 minute ago

# 이미지 상세 정보 확인
docker inspect stt-engine:cuda129-rhel89-v1.2 | jq '.Config.Env[] | select(startswith("LD_"))'

# 예상 출력에 LD_LIBRARY_PATH가 포함되어야 함
```

### 2-4. 빌드 오류 처리

```bash
# 오류가 발생한 경우 로그 확인
grep -i "error\|failed\|not found" /tmp/build.log | tail -20
```

---

## 📦 Phase 3: 모델 다운로드 및 변환 (25~45분)

**중요**: 빌드 서버의 **로컬 환경**에서 모델을 다운로드합니다.

### 3-1. 모델 다운로드 및 CTranslate2 변환

```bash
cd /path/to/stt_engine

# 필수 패키지 설치 (필요시)
pip install --upgrade huggingface-hub transformers ctranslate2

# 모델 다운로드 및 변환 실행 (자동으로 모두 처리)
python3 download_model_hf.py 2>&1 | tee /tmp/model_download.log

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
# ✅ 모델 다운로드 완료 (약 3-5분 소요)
#
# 📌 Step 3: 모델 파일 검증
# ✅ config.json 검증 완료
# ✅ pytorch_model.bin 검증 완료
# ✅ tokenizer.json 검증 완료
#
# 📌 Step 4: CTranslate2 포맷 변환
# ⏳ CTranslate2 변환 중... (약 5-10분 소요)
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

### 3-2. 모델 디렉토리 구조 확인

```bash
# 모델 디렉토리 구조 확인
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

### 3-3. 모델 파일 검증 (Python)

```bash
python3 << 'PYTHON_TEST'
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

## 🧪 Phase 4: 기본 환경 검증 (10~15분)

### 4-1. 컨테이너 시작 (모델 마운트)

```bash
cd /path/to/stt_engine

# 컨테이너 실행 (모델 디렉토리 마운트)
docker run -it \
  --name stt-test-engine \
  -v $(pwd)/models:/app/models \
  -e CUDA_VISIBLE_DEVICES=0 \
  stt-engine:cuda129-rhel89-v1.2 \
  /bin/bash
```

### 4-2. 컨테이너 내 마운트된 모델 확인

컨테이너 내부에서:

```bash
# 마운트 확인
ls -lh /app/models/
du -sh /app/models/*
```

### 4-3. CUDA 및 PyTorch 검증

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

### 4-4. 권한 및 캐시 검증

컨테이너 내부에서:

```bash
# 현재 사용자
whoami

# 캐시 권한 테스트
touch /opt/app-root/src/.cache/test.txt && rm /opt/app-root/src/.cache/test.txt && echo "✅ 캐시 디렉토리 쓰기 가능"
```

---

## 📦 Phase 5: 모델 로드 테스트 (20~30분)

### 5-1. CTranslate2 모델 진단

컨테이너 내부에서:

```bash
python3 << 'PYTHON_TEST'
import sys
sys.path.insert(0, '/app')

from stt_engine import diagnose_faster_whisper_model

print("=" * 70)
print("🔍 CTranslate2 모델 진단")
print("=" * 70)

result = diagnose_faster_whisper_model("/app/models/ctranslate2_model")

if not result.get('errors'):
    print("\n✅ 모델 구조 정상!")
else:
    print(f"\n❌ 오류 발생: {result.get('errors')}")

PYTHON_TEST
```

### 5-2. Faster-Whisper 로드 테스트

컨테이너 내부에서:

```bash
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
```

### 5-3. OpenAI Whisper 로드 테스트

컨테이너 내부에서:

```bash
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

### 5-4. 오디오 처리 테스트

컨테이너 내부에서:

```bash
python3 << 'PYTHON_TEST'
import torch
import torchaudio

print("=" * 70)
print("🎵 오디오 처리 테스트")
print("=" * 70)

try:
    # 테스트 오디오 생성
    sample_rate = 16000
    duration_sec = 1
    
    print(f"\n🔊 테스트 오디오 생성 중...")
    
    waveform = torch.randn(1, sample_rate * duration_sec)
    if torch.cuda.is_available():
        waveform = waveform.cuda()
    
    print(f"   샘플 레이트: {sample_rate} Hz")
    print(f"   지속 시간: {duration_sec} 초")
    print(f"   웨이브폼: {waveform.shape}, 디바이스: {waveform.device}")
    print("✅ 오디오 처리 성공!")
    
except Exception as e:
    print(f"❌ 오류: {type(e).__name__}: {e}")

PYTHON_TEST
```

---

## ✅ Phase 6: 최종 검증 (5분)

컨테이너에서 `exit` 실행:

```bash
exit
```

그 후 최종 정리:

```bash
# 컨테이너 제거
docker rm stt-test-engine

# 빌드 결과 저장
docker images | grep stt-engine
ls -lh models/

# 로그 저장
cp /tmp/build.log build-success-$(date +%Y%m%d).log
cp /tmp/model_download.log model-success-$(date +%Y%m%d).log
```

---

## 📊 최종 체크리스트

모든 항목이 ✅ 상태여야 합니다:

```
Phase 1: 환경 준비
  ✅ git fetch & reset 완료
  ✅ 기존 이미지/모델 정리

Phase 2: Docker 이미지 빌드
  ✅ 이미지 빌드 성공 (7.3GB)
  ✅ LD_LIBRARY_PATH 설정됨

Phase 3: 모델 다운로드
  ✅ Whisper 모델 다운로드 (1.6GB)
  ✅ CTranslate2 변환 (0.9GB)
  ✅ 모델 파일 검증 완료

Phase 4: 기본 환경 검증
  ✅ 모델 마운트 성공
  ✅ PyTorch 설치 확인
  ✅ CUDA 사용 가능
  ✅ 캐시 디렉토리 권한 OK

Phase 5: 모델 로드 테스트
  ✅ CTranslate2 구조 정상
  ✅ Faster-Whisper 로드 성공
  ✅ OpenAI Whisper 로드 성공
  ✅ 오디오 처리 성공

Phase 6: 최종 정리
  ✅ 빌드 결과 정리 완료
  ✅ 로그 저장 완료
```

---

## ⏱️ 전체 소요 시간

| Phase | 시간 | 합계 |
|-------|------|------|
| 1. 환경 준비 | 5~10분 | 5~10분 |
| 2. Docker 빌드 | 20~40분 | 25~50분 |
| 3. 모델 다운로드 | 25~45분 | 50~95분 |
| 4. 기본 검증 | 10~15분 | 60~110분 |
| 5. 모델 테스트 | 20~30분 | 80~140분 |
| 6. 최종 검증 | 5분 | 85~145분 |
| **총합** | - | **90~150분 (1.5~2.5시간)** |

---

## 🎯 성공 기준

이 모든 항목이 통과하면 운영 서버 배포 준비 완료:

✅ Docker 이미지 빌드 성공 (7.3GB)  
✅ 모델 완벽 다운로드 (2.5GB)  
✅ CTranslate2 변환 성공 (model.bin 생성)  
✅ 컨테이너 정상 시작  
✅ CUDA 라이브러리 모두 로드  
✅ PyTorch/torchaudio 정상  
✅ Faster-Whisper 모델 로드 성공  
✅ OpenAI Whisper 모델 로드 성공  
✅ 모든 파일 권한 정상  
✅ CUDA 계산 테스트 성공  

**이 모든 항목 통과 → 운영 배포 안전!** 🚀
