# EC2 STT 엔진 모델 문제 진단 및 해결

## 🚨 현재 문제

Docker 컨테이너에서 모델을 로드할 수 없습니다:
```
❌ RuntimeError: Unable to open file 'model.bin' in model '/app/models/openai_whisper-large-v3-turbo'
```

**원인**: CTranslate2 모델 변환이 올바르게 완료되지 않았거나, 파일이 손상됨

---

## ✅ 해결 방법 (3단계)

### Step 1️⃣: EC2에서 모델 상태 진단

```bash
# EC2에 접속
ssh -i your-key.pem ec2-user@your-ec2-ip

# 모델 디렉토리 이동
cd /home/ec2-user/stt_engine

# 진단 스크립트 실행
python ec2_diagnose_and_fix.py
```

**출력 예시:**
```
=======================================================================
🔍 EC2 STT 엔진 모델 진단 (RHEL 8.9)
=======================================================================

📌 Step 1: 디렉토리 경로 확인
--------

  ✅ STT 디렉토리 존재
  ✅ 모델 디렉토리 존재
  ✅ 모델 폴더 존재

📌 Step 2: 모델 파일 구조 진단
--------

  ✅ ctranslate2_model 폴더 존재
  ❌ model.bin 너무 작음: 45.25MB (최소 1000MB 필요)
  ❌ model.bin 파일이 손상되었을 가능성 높음
```

---

### Step 2️⃣: 모델 파일 빠른 확인

진단 스크립트 없이 빠르게 확인:

```bash
# 모델 디렉토리 확인
ls -lh /home/ec2-user/stt_engine/models/openai_whisper-large-v3-turbo/

# CTranslate2 모델 파일 확인
ls -lh /home/ec2-user/stt_engine/models/openai_whisper-large-v3-turbo/ctranslate2_model/

# config.json 크기 확인 (2.2KB 미만이면 손상)
stat /home/ec2-user/stt_engine/models/openai_whisper-large-v3-turbo/ctranslate2_model/config.json

# model.bin 크기 확인 (1.5GB 이상 필요)
du -h /home/ec2-user/stt_engine/models/openai_whisper-large-v3-turbo/ctranslate2_model/model.bin
```

**정상 상태:**
```
-rw-r--r-- model.bin         (1.5GB 이상)
-rw-r--r-- config.json       (5KB 이상)
-rw-r--r-- vocabulary.json   (1MB 이상)
```

---

### Step 3️⃣: 모델 재구축 (자동 또는 수동)

#### 옵션 A: 자동 수정 (권장)

```bash
# 진단 + 자동 수정
python ec2_diagnose_and_fix.py --fix

# 또는 강제 재구축
python ec2_diagnose_and_fix.py --rebuild
```

이 명령은:
1. 기존 모델 백업
2. 새 모델 다운로드 및 변환
3. 재진단으로 성공 확인

---

#### 옵션 B: 수동 재구축

```bash
# 1. 기존 모델 삭제
rm -rf /home/ec2-user/stt_engine/models/openai_whisper-large-v3-turbo

# 2. 모델 재다운로드 및 변환 (10-20분 소요)
cd /home/ec2-user/stt_engine
python download_model_hf.py

# 3. 완료 확인
ls -lh models/openai_whisper-large-v3-turbo/ctranslate2_model/

# 4. 모델 로드 테스트
python -c "from faster_whisper import WhisperModel; m = WhisperModel('/home/ec2-user/stt_engine/models/openai_whisper-large-v3-turbo/ctranslate2_model', device='cpu'); print('✅ 모델 로드 성공')"
```

---

## 📊 상세 파일 구조

**정상적인 모델 구조:**
```
models/openai_whisper-large-v3-turbo/
├── config.json
├── generation_config.json
├── model.safetensors (3GB+)
├── preprocessor_config.json
├── tokenizer.json
└── ctranslate2_model/              ⭐ 중요
    ├── model.bin (1.5GB+)          ← 이 파일이 가장 중요
    ├── config.json (5KB+)
    └── vocabulary.json (1MB+)
```

**문제 상황 1**: model.bin 손상 또는 너무 작음
```
❌ model.bin: 45.25MB  (❌ 너무 작음, 최소 1.5GB 필요)
```
→ **해결**: 모델 재다운로드 필수

**문제 상황 2**: ctranslate2_model 폴더 없음
```
❌ ctranslate2_model/ 폴더 없음
```
→ **해결**: 모델 변환 스크립트 재실행

---

## 🧪 모델 로드 테스트 (수동)

```bash
cd /home/ec2-user/stt_engine

# Python 대화형 모드에서 테스트
python3 << 'EOF'
from pathlib import Path
from faster_whisper import WhisperModel

model_path = Path("/home/ec2-user/stt_engine/models/openai_whisper-large-v3-turbo/ctranslate2_model")

print(f"📂 모델 경로: {model_path}")
print(f"✅ 경로 존재: {model_path.exists()}")

# 파일 확인
print("\n📋 파일 확인:")
for f in sorted(model_path.glob("*")):
    if f.is_file():
        size = f.stat().st_size / (1024**2)
        print(f"  - {f.name}: {size:.2f}MB")

# 모델 로드
print("\n🔄 모델 로드 중...")
try:
    model = WhisperModel(str(model_path), device="cpu", compute_type="int8")
    print("✅ 모델 로드 성공!")
except Exception as e:
    print(f"❌ 모델 로드 실패: {e}")
EOF
```

---

## 🐳 Docker 에서 다시 테스트

모델을 재구축한 후:

```bash
# Docker 이미지 재빌드 (권장)
cd /home/ec2-user/stt_engine
docker build --platform linux/amd64 -t stt-engine:cuda129-rhel89-v1.5 -f docker/Dockerfile.engine.rhel89 .

# 또는 기존 이미지로 테스트 (모델만 마운트)
docker run -it \
  --name stt-api-test \
  -p 8003:8003 \
  -v /home/ec2-user/stt_engine/models:/app/models \
  -e CUDA_VISIBLE_DEVICES=0 \
  stt-engine:cuda129-rhel89-v1.5

# 또는 python api_server.py 직접 실행
docker run -it \
  --name stt-api-test \
  -p 8003:8003 \
  -v /home/ec2-user/stt_engine/models:/app/models \
  stt-engine:cuda129-rhel89-v1.5 \
  python3.11 api_server.py
```

---

## 🔍 추가 문제 해결

### 문제: download_model_hf.py 실행 실패

```bash
# 패키지 버전 확인
python -c "import ctranslate2, faster_whisper, transformers; print(f'ctranslate2: {ctranslate2.__version__}, faster-whisper 설치됨, transformers: {transformers.__version__}')"

# 문제 패키지 재설치
pip install --upgrade ctranslate2==4.7.1
pip install --upgrade faster-whisper==1.2.1
```

### 문제: 디스크 공간 부족

```bash
# 디스크 사용량 확인
df -h /home/ec2-user

# 불필요한 파일 정리
rm -rf ~/.cache/huggingface/hub/*
docker system prune -a
```

### 문제: 메모리 부족 (16GB 이상 권장)

```bash
# 메모리 확인
free -h

# swap 생성 (필요시)
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 💡 예상 소요 시간

| 단계 | 시간 | 설명 |
|------|------|------|
| 모델 다운로드 | 5-10분 | Hugging Face에서 1.5GB 다운로드 |
| CTranslate2 변환 | 5-15분 | PyTorch → CTranslate2 포맷 변환 |
| 압축 | 2-5분 | tar.gz 압축 (선택사항) |
| **총소요시간** | **15-30분** | 네트워크 속도에 따라 변함 |

---

## ✅ 성공 확인

모든 단계 완료 후:

```bash
# 1. 모델 파일 확인
ls -lh models/openai_whisper-large-v3-turbo/ctranslate2_model/

# 2. Docker 컨테이너 시작
docker run -it -p 8003:8003 -v $(pwd)/models:/app/models stt-engine:cuda129-rhel89-v1.5

# 3. API 건강 확인 (다른 터미널)
curl http://localhost:8003/health

# 4. 기대되는 응답:
# {"status":"ok","version":"1.0.0","backend":"faster-whisper"}
```

---

## 🔄 최신 개선사항 (2025년 2월)

### 상대 경로 심링크 적용

**문제**: 이전에는 model.bin 심링크가 절대 경로로 생성되어서, Docker (`/app/models`)와 운영 서버 (`/data/models`)에서 경로가 다르면 작동하지 않음

**해결**: 상대 경로 심링크로 변경
```
# 이전 (절대 경로)
model.bin → /home/ec2-user/stt_engine/models/openai_whisper-large-v3-turbo/ctranslate2_model/model-0001.bin
❌ Docker에서 작동 안함

# 현재 (상대 경로) ✅
model.bin → ./ctranslate2_model/model-0001.bin
✅ Docker (/app/models) & 운영 서버 (/data/models) 모두 작동
```

### 자동 진단 및 복구 도구

모델 문제 시 자동으로 진단하고 수정하는 스크립트 추가:

```bash
# EC2에서 모델 진단
python diagnose_model.py

# 또는 특정 경로 진단
python diagnose_model.py /data/models/openai_whisper-large-v3-turbo
```

**기능:**
1. 모델 디렉토리 구조 상세 진단
2. model.bin 파일 위치 자동 파악
3. 상대 경로 심링크 자동 생성 (또는 파일 복사)
4. faster-whisper 로드 테스트

**출력 예시:**
```
======================================================================
🔍 모델 디렉토리 진단
======================================================================

📁 모델 디렉토리: /data/models/openai_whisper-large-v3-turbo

📂 최상위 파일:
   🔗 model.bin (1.50GB)
      → ctranslate2_model/model-0001.bin
   📁 ctranslate2_model/ (3 items)

🔎 model.bin 파일 검색:
   ✅ 1개 발견:
      - ctranslate2_model/model-0001.bin (1.50GB)

======================================================================
✅ faster-whisper 모델 로드 테스트
======================================================================

✅ 모델 로드 성공!

📋 모델 정보:
   타입: Whisper Large-v3-Turbo (CTranslate2)
   디바이스: CPU
   Compute Type: FP32
```

### 모델 준비 스크립트 (EC2용)

EC2에서 모델을 처음부터 준비하는 쉘 스크립트:

```bash
# 스크립트 실행
bash ec2_prepare_model.sh

# 또는 옵션과 함께
bash ec2_prepare_model.sh --skip-test        # 테스트 스킵
bash ec2_prepare_model.sh --skip-compress    # 압축 스킵
bash ec2_prepare_model.sh --no-convert       # 변환 스킵 (PyTorch만)
```

**포함 기능:**
- Python 3.11 환경 확인
- 필수 패키지 검증 (huggingface-hub, faster-whisper, ctranslate2)
- 모델 다운로드 & CTranslate2 변환
- 자동 진행 상황 보고

### 심링크 호환성 확인

Docker와 운영 서버 모두에서 작동하는지 검증:

```bash
# 심링크 확인
ls -l models/openai_whisper-large-v3-turbo/model.bin

# 정상 출력 (상대 경로)
lrwxr-xr-x  user  group  ctranslate2_model/model-0001.bin → model.bin
```

**호환 경로:**

| 환경 | 경로 | 작동 |
|------|------|------|
| Docker | `/app/models/openai_whisper-large-v3-turbo` | ✅ |
| EC2 (/data) | `/data/models/openai_whisper-large-v3-turbo` | ✅ |
| EC2 (/home) | `/home/ec2-user/stt_engine/models/...` | ✅ |

모든 경로에서 상대 경로를 사용하므로 문제없이 작동합니다! ✨

**질문이나 추가 도움이 필요하면 알려주세요!**
