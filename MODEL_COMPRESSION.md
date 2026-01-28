# Whisper 모델 압축 및 원격 로드 방식

## 📌 먼저 명확히 하기

**vLLM과 Whisper는 다른 모델입니다:**
- **vLLM**: LLM (대규모 언어 모델) 추론 엔진 (예: Llama, Mistral)
- **Whisper**: STT (음성→텍스트) 모델

따라서 vLLM에서 직접 Whisper를 호출할 수 없습니다. 하지만 **STT 엔진**에서 압축된 모델을 사용하거나, 원격으로 로드하는 것은 충분히 가능합니다!

---

## 🎯 가능한 4가지 방식

### 1️⃣ **TAR 압축 후 해제 방식** (저장소 공간 절약)

#### 로컬에서 압축
```bash
# 1. 모델 폴더 압축 (약 1.5GB → 1.2GB)
cd models/
tar -czf whisper-model.tar.gz openai_whisper-large-v3-turbo/

# 2. 압축 파일 크기 확인
ls -lh whisper-model.tar.gz  # ~1.2GB

# 3. 원본 폴더 삭제 (선택사항)
rm -rf openai_whisper-large-v3-turbo/
```

#### 서버에서 자동 해제 (Docker 빌드 시)
```dockerfile
# Dockerfile에 추가
FROM python:3.11-slim
WORKDIR /app

# 압축 파일 복사
COPY models/whisper-model.tar.gz /app/

# 모델 해제
RUN tar -xzf /app/whisper-model.tar.gz -C /app/models/
RUN rm /app/whisper-model.tar.gz

# ... 나머지 설정
CMD ["python", "api_server.py"]
```

#### 또는 시작시 자동 해제 (Python)
```python
import tarfile
import os
from pathlib import Path

def extract_model_if_needed():
    model_path = Path("models/openai_whisper-large-v3-turbo")
    tar_path = Path("models/whisper-model.tar.gz")
    
    if tar_path.exists() and not model_path.exists():
        print("📦 모델 압축 해제 중...")
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path="models/")
        print("✅ 해제 완료")
    
    return model_path

# 서버 시작 전에 호출
model_path = extract_model_if_needed()
stt = WhisperSTT(str(model_path))
```

**장점:** 저장소 공간 15% 절약, Git에 용이  
**단점:** 해제 시간 필요 (~1분), 추가 코드

---

### 2️⃣ **AWS S3 또는 GCS에서 원격 로드** (권장, 서버 환경에서)

#### S3에 모델 업로드
```bash
# 1. AWS CLI 설치
pip install boto3

# 2. S3 버킷 생성
aws s3 mb s3://stt-models-bucket

# 3. 모델 업로드
aws s3 cp models/whisper-model.tar.gz \
    s3://stt-models-bucket/whisper-model.tar.gz

# 4. 진행률 보기
aws s3 cp models/whisper-model.tar.gz \
    s3://stt-models-bucket/whisper-model.tar.gz \
    --sse AES256
```

#### Python에서 S3에서 로드
```python
import boto3
import tarfile
from pathlib import Path
import tempfile

def download_model_from_s3(
    bucket_name: str = "stt-models-bucket",
    model_key: str = "whisper-model.tar.gz",
    local_path: str = "models"
):
    """S3에서 모델 다운로드 및 추출"""
    
    s3 = boto3.client('s3')
    tar_file = Path(local_path) / "whisper-model.tar.gz"
    model_dir = Path(local_path) / "openai_whisper-large-v3-turbo"
    
    # 이미 존재하면 스킵
    if model_dir.exists():
        print("✅ 모델이 이미 존재합니다")
        return model_dir
    
    print(f"📥 S3에서 모델 다운로드 중... ({bucket_name}/{model_key})")
    
    # 다운로드
    s3.download_file(bucket_name, model_key, str(tar_file))
    print("✅ 다운로드 완료")
    
    # 추출
    print("📦 모델 압축 해제 중...")
    with tarfile.open(tar_file, "r:gz") as tar:
        tar.extractall(path=local_path)
    print("✅ 해제 완료")
    
    # 압축 파일 삭제
    tar_file.unlink()
    
    return model_dir

# Docker에서 사용
from stt_engine import WhisperSTT

model_path = download_model_from_s3()
stt = WhisperSTT(str(model_path))
```

#### Docker Compose에 환경 변수 추가
```yaml
services:
  stt-engine:
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - S3_BUCKET_NAME=stt-models-bucket
      - S3_MODEL_KEY=whisper-model.tar.gz
```

**장점:** 여러 서버에서 공유 가능, 버전 관리 용이, 자동 백업  
**단점:** AWS 비용 발생, 초기 다운로드 시간, 네트워크 의존

---

### 3️⃣ **Google Drive에서 원격 로드** (개인/소규모 프로젝트용)

```python
from google.colab import drive
from googleapiclient.discovery import build
import tarfile

def download_from_google_drive(file_id: str, destination: str):
    """Google Drive에서 파일 다운로드"""
    
    import urllib.request
    
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    print(f"📥 Google Drive에서 다운로드 중...")
    urllib.request.urlretrieve(url, destination)
    print("✅ 다운로드 완료")
    
    # 압축 해제
    print("📦 압축 해제 중...")
    with tarfile.open(destination, "r:gz") as tar:
        tar.extractall(path="models/")
    print("✅ 완료")

# 사용법
# 1. Google Drive에 whisper-model.tar.gz 업로드
# 2. 파일 ID 복사 (URL: https://drive.google.com/file/d/{FILE_ID}/view)
# 3. 다음 코드 실행

download_from_google_drive(
    file_id="YOUR_FILE_ID_HERE",
    destination="models/whisper-model.tar.gz"
)
```

**장점:** 무료, 간단  
**단점:** 느림, 대역폭 제한, 신뢰성 낮음

---

### 4️⃣ **Hugging Face Hub에 직접 업로드** (최고 권장! 🌟)

이미 Hugging Face에서 모델을 다운로드 중이므로, 직접 Hub에 올려서 사용하면 가장 깔끔합니다!

#### 자신의 Hugging Face 모델 저장소 생성
```bash
# 1. Hugging Face 계정 생성 (https://huggingface.co)

# 2. 토큰 설정
huggingface-cli login
# → token 입력

# 3. 저장소 생성 (웹에서 또는 CLI)
huggingface-cli repo create --repo-type=model \
    --private stt-whisper-custom

# 4. 로컬에 클론
git clone https://huggingface.co/your-username/stt-whisper-custom
cd stt-whisper-custom

# 5. 모델 파일 복사
cp -r ../models/openai_whisper-large-v3-turbo/* .

# 6. 푸시
git add .
git commit -m "Add Whisper model"
git push
```

#### Python에서 직접 로드
```python
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq

# Hugging Face에서 직접 로드 (캐시됨)
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    "your-username/stt-whisper-custom"
)
processor = AutoProcessor.from_pretrained(
    "your-username/stt-whisper-custom"
)

# 또는 로컬 경로 지정
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    "./models/openai_whisper-large-v3-turbo"
)
```

**장점:** 최고의 통합성, 버전 관리, 자동 캐싱, 커뮤니티 공유  
**단점:** 인터넷 필요 (초기에만)

---

## 📊 방식별 비교

| 방식 | 저장소 | 속도 | 관리 | 추천 |
|------|--------|------|------|------|
| TAR 압축 | 최소 (1.2GB) | 빠름 | 보통 | 로컬 개발 |
| AWS S3 | 중간 | 보통 | 최고 | 프로덕션 |
| Google Drive | 중간 | 느림 | 보통 | 소규모 |
| Hugging Face | 최소 | 빠름 | 최고 | 최우수 |

---

## 🚀 실전 예제: TAR 압축 + Docker 자동 해제

### 1단계: 로컬에서 압축
```bash
cd /Users/a113211/workspace/stt_engine
tar -czf models/whisper-model.tar.gz -C models openai_whisper-large-v3-turbo/
```

### 2단계: Dockerfile 수정
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg libsndfile1 git tar gzip \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 모델 압축 파일이 있으면 자동 해제
RUN if [ -f models/whisper-model.tar.gz ]; then \
        echo "📦 모델 압축 해제 중..."; \
        tar -xzf models/whisper-model.tar.gz -C models/; \
        rm models/whisper-model.tar.gz; \
        echo "✅ 완료"; \
    fi

RUN mkdir -p audio logs

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "api_server.py"]
```

### 3단계: Docker Compose 실행
```bash
# 압축된 모델로 이미지 빌드
docker build -t stt-engine:compressed .

# 실행
docker-compose up -d
```

**결과:**
- ✅ 이미지 크기 약간 감소
- ✅ 빌드 시간 약간 증가 (압축 해제)
- ✅ 런타임 시간 동일

---

## 💾 Git에 TAR 파일 추가 (큰 파일 관리)

### Git LFS 사용 (권장)
```bash
# 1. Git LFS 설치
brew install git-lfs  # macOS
apt-get install git-lfs  # Ubuntu

# 2. Git LFS 초기화
git lfs install

# 3. TAR 파일을 LFS로 추적
git lfs track "models/whisper-model.tar.gz"

# 4. .gitattributes 커밋
git add .gitattributes
git commit -m "Add git-lfs tracking for model"

# 5. 모델 파일 추가
git add models/whisper-model.tar.gz
git commit -m "Add compressed Whisper model"

# 6. 푸시 (자동으로 LFS로 업로드)
git push
```

---

## 🎯 권장 선택

### 📍 상황별 추천

**로컬 개발 (macOS/Linux):**
```bash
# 현재 상태 유지 (압축 안 함)
# → 빠름, 간편
```

**Docker 배포 (자체 서버):**
```bash
# TAR 압축 방식
# → 저장소 공간 절약, 빌드 자동화
```

**클라우드 배포 (AWS/GCP):**
```bash
# S3/GCS에서 로드
# → 유연함, 확장성, 버전 관리
```

**공개 배포 또는 팀 협업:**
```bash
# Hugging Face Hub
# → 최고의 통합성, 커뮤니티 활용
```

---

## 📝 간단한 구현: 압축 후 자동 해제

### 한 줄 명령어로 설정
```bash
# 1. 압축
tar -czf models/whisper-model.tar.gz -C models openai_whisper-large-v3-turbo/

# 2. Dockerfile 자동 생성 (압축 해제 포함)
cat > Dockerfile.compressed << 'EOF'
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg libsndfile1 git && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip setuptools wheel
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p audio logs && \
    test -f models/whisper-model.tar.gz && \
    tar -xzf models/whisper-model.tar.gz -C models/ && \
    rm models/whisper-model.tar.gz || true
EXPOSE 8001
CMD ["python", "api_server.py"]
EOF

# 3. 빌드
docker build -t stt-engine:compressed -f Dockerfile.compressed .

# 4. 실행
docker run -p 8001:8001 stt-engine:compressed
```

---

## 결론

| 방식 | 가능 여부 | 난이도 | 추천도 |
|------|---------|--------|--------|
| TAR 압축 자동 해제 | ✅ 가능 | 쉬움 | ⭐⭐⭐⭐ |
| S3 원격 로드 | ✅ 가능 | 중간 | ⭐⭐⭐⭐ |
| Hugging Face 로드 | ✅ 가능 | 쉬움 | ⭐⭐⭐⭐⭐ |
| Google Drive 로드 | ✅ 가능 | 쉬움 | ⭐⭐⭐ |

**vLLM과는 별개이지만, STT 엔진에서는 모두 가능합니다!** 🚀
