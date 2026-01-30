# 모델 압축 및 원격 로드 - 빠른 가이드

## ✅ 가능한 방식들

모든 방식이 **완전히 가능**합니다! 선택만 하시면 됩니다.

---

## 🎯 가장 쉬운 방법: TAR 압축 + 자동 해제

### Step 1️⃣: 모델 압축 (로컬)

```bash
# Python 스크립트 사용 (권장)
python model_manager.py compress

# 또는 직접 명령어
cd models
tar -czf whisper-model.tar.gz openai_whisper-large-v3-turbo/
cd ..
```

**결과:**
- `models/whisper-model.tar.gz` 생성 (~1.2GB)
- 원본 폴더는 그대로 유지

### Step 2️⃣: Docker에서 자동 해제

```bash
# 방법 1: 압축 Dockerfile 사용
docker build -t stt-engine:compressed -f Dockerfile.compressed .

# 방법 2: 기존 docker-compose 사용
docker-compose up -d
```

**장점:**
- ✅ 자동 해제 (빌드 시)
- ✅ 간단함
- ✅ 저장소 공간 절약 (1.5GB → 1.2GB)

---

## 📦 모델 매니저 CLI 사용법

```bash
# 상태 확인
python model_manager.py info

# 모델 압축
python model_manager.py compress

# 압축 후 원본 삭제
python model_manager.py compress --cleanup

# 압축 해제
python model_manager.py extract

# 자동 압축 해제 테스트
python model_manager.py test

# S3에서 다운로드 + 해제
python model_manager.py download-s3 --bucket my-bucket --key whisper-model.tar.gz
```

---

## ☁️ AWS S3 원격 로드 (프로덕션)

### 1단계: 모델 S3 업로드

```bash
# AWS CLI 설치
pip install boto3
aws configure  # AWS 자격증명 입력

# 모델 압축 파일 업로드
python model_manager.py compress
aws s3 cp models/whisper-model.tar.gz s3://my-bucket/whisper-model.tar.gz
```

### 2단계: Docker에서 S3 로드

```bash
# 환경 변수 설정
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export S3_BUCKET=my-bucket
export S3_MODEL_KEY=whisper-model.tar.gz

# Docker 실행
docker build -t stt-engine:s3 -f Dockerfile.s3 .
docker-compose up -d
```

---

## 🤖 Hugging Face Hub (최고 권장!)

### 1단계: Hugging Face에 업로드

```bash
# 로그인
huggingface-cli login

# 저장소 생성
huggingface-cli repo create --repo-type model my-whisper-model

# 모델 파일 업로드
git clone https://huggingface.co/your-username/my-whisper-model
cp -r models/openai_whisper-large-v3-turbo/* my-whisper-model/
cd my-whisper-model
git add .
git commit -m "Add Whisper model"
git push
```

### 2단계: Python에서 직접 사용

```python
from stt_engine import WhisperSTT

# Hugging Face에서 직접 로드 (캐시됨)
stt = WhisperSTT("your-username/my-whisper-model")

# 또는 로컬 경로 (변화 없음)
stt = WhisperSTT("models/openai_whisper-large-v3-turbo")
```

---

## 🚀 실제 사용 예제

### 예제 1: 로컬 압축 방식 (개발)

```bash
# 1. 로컬에서 준비
python model_manager.py compress --cleanup

# 2. Docker 빌드
docker build -t stt-engine:compressed -f Dockerfile.compressed .

# 3. 실행
docker-compose -f docker-compose.yml up -d
```

### 예제 2: S3 방식 (프로덕션)

```bash
# 1. S3에 업로드
python model_manager.py compress
aws s3 cp models/whisper-model.tar.gz s3://stt-models/

# 2. 서버에서 실행
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
export S3_BUCKET=stt-models
docker build -t stt-engine:s3 -f Dockerfile.s3 .
docker-compose up -d
```

### 예제 3: Hugging Face (팀 협업)

```bash
# 1. Hugging Face에 업로드 (한 번만)
# (위의 Hugging Face Hub 섹션 참고)

# 2. 모든 팀원이 사용
python -c "from stt_engine import WhisperSTT; stt = WhisperSTT('your-username/my-whisper-model')"
```

---

## 📊 방식별 비교

| 방식 | 준비 시간 | 네트워크 | 저장소 | 추천 |
|------|----------|---------|--------|------|
| TAR 압축 | 5분 | 불필요 | 최소 | ⭐⭐⭐⭐ 개발 |
| S3 | 10분 | 필수 | 중간 | ⭐⭐⭐⭐⭐ 프로덕션 |
| Hugging Face | 15분 | 필수 | 최소 | ⭐⭐⭐⭐⭐ 공유 |
| Google Drive | 5분 | 필수 | 중간 | ⭐⭐⭐ 소규모 |

---

## ❓ FAQ

**Q: 압축하면 품질이 떨어지나요?**  
A: 아니오! TAR.GZ는 무손실 압축입니다. 품질 손상 없음.

**Q: 압축 파일이 있으면 원본 폴더는 필요 없나요?**  
A: 네, 원본을 삭제하고 압축 파일만 유지해도 됩니다.

**Q: Docker 빌드 시간이 길어지나요?**  
A: 네, 압축 해제 때문에 1~2분 추가 소요.

**Q: 여러 서버에서 모델을 공유할 수 있나요?**  
A: S3 또는 Hugging Face 사용 시 가능합니다.

**Q: vLLM에서도 Whisper 모델을 로드할 수 있나요?**  
A: 아니오, vLLM은 LLM만 지원. STT 엔진에서만 사용.

---

## 📚 자세한 정보

더 자세한 정보는 [MODEL_COMPRESSION.md](MODEL_COMPRESSION.md) 참고

---

## 💡 추천 선택

```
┌─ 로컬 개발
│  └─ 압축 안 함 (기본)
│
├─ Docker 배포 (자체 서버)
│  └─ TAR 압축 + Dockerfile.compressed
│
├─ AWS 클라우드
│  └─ S3 + Dockerfile.s3
│
└─ 팀/공개 배포
   └─ Hugging Face Hub
```

선택하신 방식에 따라 위의 예제를 따라하시면 됩니다! 🚀
