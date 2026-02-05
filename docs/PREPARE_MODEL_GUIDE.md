# STT Engine - Whisper 모델 준비 가이드

## 📋 목표

- 기존 모델 파일 정리 (손상된 파일 제거)
- Huggingface에서 올바른 모델 다운로드
- CTranslate2 포맷 변환 (faster-whisper 호환)
- 압축하여 운영 서버로 전송

---

## 🚀 빠른 시작

### 옵션 1: Python 간단한 버전 (권장)

```bash
# Mac에서 실행
cd /Users/a113211/workspace/stt_engine
python3 prepare_model_simple.py

# 또는 변환 건너뛰기 (PyTorch 포맷만)
python3 prepare_model_simple.py --no-convert
```

**소요 시간**: 5-10분
**결과**: `models/whisper-large-v3-turbo-model.tar.gz`

---

### 옵션 2: Bash 스크립트

```bash
cd /Users/a113211/workspace/stt_engine
bash prepare_model.sh
```

**소요 시간**: 5-10분
**결과**: `models/whisper-large-v3-turbo-model.tar.gz`

---

### 옵션 3: Python 상세 버전

```bash
python3 prepare_model.py
```

---

## 📊 각 단계 설명

### Step 1: 기존 모델 정리 (~30초)
- 기존 `models/openai_whisper-large-v3-turbo/` 백업 생성
- 기존 디렉토리 삭제
- 새 디렉토리 생성

**결과**: 깨끗한 상태에서 다시 시작

### Step 2: Huggingface 다운로드 (2-5분)
- `openai/whisper-large-v3-turbo` 모델 다운로드
- 필수 파일:
  - `pytorch_model.bin` (1.3GB)
  - `config.json`
  - `preprocessor_config.json`
  - `tokenizer.json`
  - 기타 메타데이터 파일

**결과**: 모든 모델 파일이 로컬에 저장

### Step 3: CTranslate2 변환 (3-10분, 선택사항)
- PyTorch 모델을 CTranslate2 바이너리 포맷으로 변환
- 결과: `model.bin` 생성
- 용도: faster-whisper 최적화 백엔드

**결과**: `model.bin` (1.5GB, CTranslate2 포맷)

**참고**:
- 변환이 실패해도 `pytorch_model.bin`이 있으면 openai-whisper 사용 가능
- `--no-convert` 옵션으로 건너뛸 수 있음

### Step 4: 검증 (~10초)
- 필수 파일 존재 확인
- 파일 무결성 검증

### Step 5: 압축 (1-3분)
- 모든 모델 파일을 `tar.gz`으로 압축
- 결과: `whisper-large-v3-turbo-model.tar.gz` (~500MB)

---

## 📁 최종 구조

```
models/
├── openai_whisper-large-v3-turbo/
│   ├── pytorch_model.bin           (1.3GB)
│   ├── model.bin                   (1.5GB, CTranslate2 - 선택사항)
│   ├── config.json
│   ├── preprocessor_config.json
│   ├── tokenizer.json
│   ├── generation_config.json
│   └── ...
├── whisper-large-v3-turbo-model.tar.gz  (500MB)
└── .backup/
    └── backup_20260205_1234567/    (이전 버전 백업)
```

---

## 🚀 운영 서버로 배포

### 1단계: Mac에서 전송
```bash
# 준비된 tar 파일 다운로드 확인
ls -lh models/whisper-large-v3-turbo-model.tar.gz

# RHEL 서버로 전송
scp models/whisper-large-v3-turbo-model.tar.gz user@rhel_server:/tmp/
```

### 2단계: RHEL 서버에서 설치
```bash
# 접속
ssh user@rhel_server

# 압축 해제
cd /tmp
tar -xzf whisper-large-v3-turbo-model.tar.gz

# 모델 디렉토리로 이동
mv openai_whisper-large-v3-turbo /path/to/stt_engine/models/

# 확인
ls -la /path/to/stt_engine/models/openai_whisper-large-v3-turbo/
```

### 3단계: Docker에 마운트
```bash
# 모델 디렉토리를 Docker 컨테이너에 마운트
docker run -d \
  --name stt-api \
  -v /path/to/models/openai_whisper-large-v3-turbo:/app/models/openai_whisper-large-v3-turbo \
  -p 8003:8003 \
  stt-engine:cuda129-v1.2
```

---

## ✅ 검증

### 다운로드 후 확인
```bash
# 파일 목록 확인
ls -la /path/to/models/openai_whisper-large-v3-turbo/

# 파일 크기 확인
du -sh /path/to/models/openai_whisper-large-v3-turbo/

# 필수 파일 확인
ls -1 /path/to/models/openai_whisper-large-v3-turbo/ | grep -E "pytorch_model|config|tokenizer"
```

### Docker에서 테스트
```bash
# 모델 로드 테스트
docker run --rm \
  -v /path/to/models/openai_whisper-large-v3-turbo:/app/models/openai_whisper-large-v3-turbo \
  stt-engine:cuda129-v1.2 \
  python3.11 -c "
import whisper
print('✅ PyTorch 모델 로드 성공')
"

# faster-whisper 테스트
docker run --rm \
  -v /path/to/models/openai_whisper-large-v3-turbo:/app/models/openai_whisper-large-v3-turbo \
  stt-engine:cuda129-v1.2 \
  python3.11 -c "
from faster_whisper import WhisperModel
print('✅ faster-whisper 로드 성공')
"
```

---

## 🔧 문제 해결

### "Huggingface 로그인 필요" 오류
```bash
# 토큰 설정
huggingface-cli login
# 또는
export HF_TOKEN="your_token_here"
```

### "다운로드 중단됨" 오류
```bash
# 재실행하면 자동으로 이어서 다운로드
python3 prepare_model_simple.py
```

### "디스크 공간 부족" 오류
```bash
# 필요 공간: ~5GB (다운로드 중), ~3GB (최종)
df -h

# 백업 정리 (선택)
rm -rf models/.backup/*
```

### "CTranslate2 변환 실패" 오류
```bash
# 변환 건너뛰고 PyTorch만 사용
python3 prepare_model_simple.py --no-convert

# 또는 나중에 수동 변환
cd models/openai_whisper-large-v3-turbo
ct2-transformers-converter --model_name_or_path . --output_dir . --quantization float32
```

---

## 📊 예상 시간 및 크기

| 항목 | 소요 시간 | 크기 |
|------|---------|------|
| 정리 | 30초 | - |
| 다운로드 | 2-5분 | 1.3GB |
| 변환 | 3-10분 | +1.5GB |
| 검증 | 10초 | - |
| 압축 | 1-3분 | 500MB |
| **총합** | **7-20분** | **5GB (임시) → 500MB (최종)** |

---

## 💡 팁

### 네트워크가 느린 경우
- 야간에 실행하기
- 로컬 와이파이 사용
- `--no-convert` 옵션으로 변환 건너뛰기

### 디스크 공간이 부족한 경우
```bash
# 작은 모델 먼저 다운로드 후 확인
python3 prepare_model_simple.py --no-convert

# 나중에 필요시 변환
cd models/openai_whisper-large-v3-turbo
python3 -c "from faster_whisper import WhisperModel; WhisperModel('.')"
```

### 백업 복원
```bash
# 이전 모델로 롤백
rm -rf models/openai_whisper-large-v3-turbo
cp -r models/.backup/backup_20260205_123456 models/openai_whisper-large-v3-turbo
```

---

## 🎯 다음 단계

1. **모델 준비 완료** ✅
   ```bash
   python3 prepare_model_simple.py
   ```

2. **EC2에서 Docker 이미지 빌드** (별도)
   ```bash
   bash scripts/build-stt-engine-ec2.sh
   ```

3. **모델 + 이미지 함께 RHEL 서버로 배포**
   ```bash
   scp models/whisper-large-v3-turbo-model.tar.gz user@rhel_server:/tmp/
   scp build/output/stt-engine-cuda129-v1.2.tar.gz user@rhel_server:/tmp/
   ```

---

## 📞 지원

- 문제 발생 시: 로그 확인 및 다시 실행
- `--help` 옵션으로 사용 방법 확인 (일부)
- Python 스크립트는 자세한 오류 메시지 제공

