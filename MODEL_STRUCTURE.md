# Whisper 모델 폴더 구조 및 GPU 서버 이관 가이드

## 📂 두 폴더의 역할

### 1️⃣ `models--openai--whisper-large-v3-turbo` 폴더
**용도**: Hugging Face 캐시 메타데이터  
**크기**: ~100KB (거의 비어있음)  
**파일**: 1개 (`refs/main`)  

```
models--openai--whisper-large-v3-turbo/
└── refs/
    └── main  (모델 버전 정보)
```

**설명**:
- Hugging Face Hub의 **캐시 시스템**이 생성
- 다운로드한 모델의 **버전 정보, 메타데이터** 저장
- 모델 업데이트 확인 등에 사용
- **삭제해도 괜찮음** (다시 다운로드 시 자동 생성)

---

### 2️⃣ `openai_whisper-large-v3-turbo` 폴더 ⭐ (중요!)
**용도**: 실제 Whisper 모델 파일  
**크기**: **~1.5GB**  
**파일**: 41개 (모델 가중치, 설정, 토크나이저 등)  

```
openai_whisper-large-v3-turbo/
├── model.safetensors           # 모델 가중치 (1.5GB)
├── config.json                 # 모델 설정
├── preprocessor_config.json    # 음성 전처리 설정
├── tokenizer.json              # 토크나이저
├── tokenizer_config.json       # 토크나이저 설정
├── vocab.json                  # 어휘집
├── merges.txt                  # BPE 머지 규칙
├── generation_config.json      # 생성 설정
├── special_tokens_map.json     # 특수 토큰
├── added_tokens.json           # 추가 토큰
├── normalizer.json             # 음성 정규화
├── .gitattributes              # Git 속성
├── README.md                   # 모델 문서
└── .cache/                     # 캐시 디렉토리
```

**설명**:
- **실제 STT 추론에 필요한 모든 파일**
- `model.safetensors`: 모델의 신경망 가중치 (1.5GB, 가장 중요)
- 설정 파일들: 음성 전처리, 토크나이저 등 필요한 모든 설정
- **이 폴더가 없으면 STT를 사용할 수 없음**

---

## 🔄 GPU 서버로 이관하기

### 📋 준비 사항
```
Linux GPU 서버:
├── Docker 및 NVIDIA Docker
├── 충분한 디스크 공간 (최소 2GB)
└── 인터넷 연결 (초기 모델 다운로드 시)
```

---

## 🚀 방법 1️⃣: 폴더 통째로 복사 (권장) ⭐

**가장 빠르고 간단한 방법** - 이미 다운로드된 모델을 그대로 가져감

### 로컬 macOS → Linux 서버로 복사

#### 옵션 A: SCP로 복사 (권장)
```bash
# 로컬 macOS 터미널에서 실행
scp -r /Users/a113211/workspace/stt_engine/models/openai_whisper-large-v3-turbo \
    username@linux-server:/opt/stt_engine/models/

# 예시
scp -r /Users/a113211/workspace/stt_engine/models/openai_whisper-large-v3-turbo \
    user@192.168.1.100:/opt/stt_engine/models/
```

#### 옵션 B: 압축해서 복사 (빠름)
```bash
# 로컬 macOS에서 압축
cd /Users/a113211/workspace/stt_engine/models/
tar -czf whisper-model.tar.gz openai_whisper-large-v3-turbo/

# 서버로 전송
scp whisper-model.tar.gz username@linux-server:/tmp/

# 서버에서 압축 해제
ssh username@linux-server
cd /opt/stt_engine/models/
tar -xzf /tmp/whisper-model.tar.gz
rm /tmp/whisper-model.tar.gz
```

#### 옵션 C: USB 또는 외장 드라이브 (빠른 인터넷 없을 때)
```bash
# 1. USB에 복사
cp -r /Users/a113211/workspace/stt_engine/models/openai_whisper-large-v3-turbo \
    /Volumes/USB_Drive/

# 2. Linux 서버에 연결 후
cp -r /mnt/usb/openai_whisper-large-v3-turbo \
    /opt/stt_engine/models/
```

---

## 🔧 방법 2️⃣: 서버에서 직접 다운로드

**인터넷 속도가 빠를 때 권장** - 더 간단하고 검증 자동화

### Linux 서버에서 다운로드

```bash
# 1. 프로젝트 클론
git clone https://github.com/Kuwon-KIS/stt_engine.git
cd stt_engine

# 2. Docker로 모델 다운로드 (권장)
docker build -t stt-engine:with-model -f Dockerfile.gpu .

# 또는 로컬에서 다운로드
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python download_model.py
```

**장점**:
- 자동으로 올바른 경로에 저장
- 체크섬 검증 포함
- 파일 무결성 보장

**단점**:
- 인터넷 속도에 따라 15-30분 소요
- 서버 리소스 사용

---

## ✅ 최적의 방식 (권장)

### 😊 상황 1: 이미 로컬에서 다운로드 완료
```bash
# 로컬에서 선택적으로 필요한 폴더만 복사
scp -r /Users/a113211/workspace/stt_engine/models/openai_whisper-large-v3-turbo \
    user@server:/opt/stt_engine/models/

# (openai_whisper-large-v3-turbo 폴더만 필요!)
```

### 😊 상황 2: GPU 서버에서 처음 설정
```bash
# 서버에서 한 번에 설정
git clone https://github.com/Kuwon-KIS/stt_engine.git
cd stt_engine
docker-compose up -d  # 자동으로 모델 다운로드 (Dockerfile.gpu 사용 시)
```

---

## 📊 파일 구조 비교

| 항목 | `models--openai...` | `openai_whisper...` |
|------|-------------------|-------------------|
| **용도** | 캐시 메타데이터 | **실제 모델 파일** ⭐ |
| **크기** | ~100KB | ~1.5GB |
| **파일 수** | 1 | 41 |
| **필수 여부** | ❌ No (선택) | ✅ Yes (필수) |
| **이관 필요** | ❌ No | ✅ Yes |
| **서버 설정 후** | 자동 생성 | 미리 준비 필요 |

---

## 🐳 Docker를 사용한 완벽한 이관 방법

### 이미 다운로드된 모델 사용

#### 1단계: 로컬에서 모델만 복사
```bash
# 로컬에서
scp -r /Users/a113211/workspace/stt_engine/models/openai_whisper-large-v3-turbo \
    user@server:/opt/stt_engine/models/
```

#### 2단계: 서버에서 Docker Compose 시작
```bash
# 서버에서
cd /opt/stt_engine
docker-compose up -d

# 확인
docker-compose logs -f stt-engine
curl http://localhost:8001/health
```

### 또는 모델 포함 이미지 빌드

```bash
# 로컬 macOS에서 모델 포함 이미지 빌드
docker build -t stt-engine:with-model -f Dockerfile.gpu .

# Docker Hub에 푸시 (선택사항)
docker tag stt-engine:with-model username/stt-engine:latest
docker push username/stt-engine:latest

# 서버에서 풀
docker pull username/stt-engine:latest
docker-compose up -d
```

---

## 🛡️ 검증 및 문제 해결

### 모델 다운로드 완료 확인
```bash
# 로컬에서
ls -lah /Users/a113211/workspace/stt_engine/models/openai_whisper-large-v3-turbo/
# → model.safetensors가 1.5GB 크기여야 함
```

### 서버에서 모델 준비 확인
```bash
# Linux 서버에서
ls -lah /opt/stt_engine/models/openai_whisper-large-v3-turbo/
# → model.safetensors가 있는지 확인

# 또는 Docker 컨테이너 내에서
docker-compose exec stt-engine ls -lah /app/models/
```

### 모델 파일 무결성 확인
```bash
# 로컬과 서버의 파일 크기 비교
du -sh /Users/a113211/workspace/stt_engine/models/openai_whisper-large-v3-turbo/
# 로컬: ~1.5GB

# 서버에서
du -sh /opt/stt_engine/models/openai_whisper-large-v3-turbo/
# 서버: ~1.5GB (같아야 함)

# 또는 체크섬 비교
md5sum /Users/a113211/workspace/stt_engine/models/openai_whisper-large-v3-turbo/model.safetensors
md5sum /opt/stt_engine/models/openai_whisper-large-v3-turbo/model.safetensors
# 같아야 함
```

### STT 기능 테스트
```bash
# 서버에서 API 테스트
curl http://localhost:8001/health

# 음성 파일로 테스트
curl -X POST -F "file=@test_audio.wav" \
    http://localhost:8001/transcribe
```

---

## 📋 체크리스트: GPU 서버 이관

### 준비 단계
- [ ] GPU 서버 Docker 환경 확인
- [ ] 디스크 공간 확인 (최소 2GB)
- [ ] 인터넷 연결 확인

### 이관 단계
- [ ] 로컬에서 모델 다운로드 확인
  ```bash
  ls -lah /Users/a113211/workspace/stt_engine/models/openai_whisper-large-v3-turbo/model.safetensors
  ```
- [ ] 모델 폴더만 서버로 복사 (openai_whisper-large-v3-turbo만!)
  ```bash
  scp -r /Users/a113211/workspace/stt_engine/models/openai_whisper-large-v3-turbo \
      user@server:/opt/stt_engine/models/
  ```
- [ ] 프로젝트 코드 서버에 클론
  ```bash
  git clone https://github.com/Kuwon-KIS/stt_engine.git /opt/stt_engine
  ```
- [ ] docker-compose.yml에서 WHISPER_DEVICE를 cuda로 설정
  ```bash
  nano /opt/stt_engine/docker-compose.yml
  # WHISPER_DEVICE=cuda로 변경
  ```
- [ ] Docker Compose 시작
  ```bash
  cd /opt/stt_engine
  docker-compose up -d
  ```
- [ ] 헬스 체크
  ```bash
  curl http://localhost:8001/health
  curl http://localhost:8000/health  # vLLM
  ```

### 검증 단계
- [ ] 음성 파일 준비
- [ ] STT 기능 테스트
- [ ] vLLM 통합 테스트
- [ ] 로그 확인

---

## 💡 팁

### 모델 폴더 정리
```bash
# 첫번째 폴더는 삭제해도 괜찮음
rm -rf /Users/a113211/workspace/stt_engine/models/models--openai--whisper-large-v3-turbo

# 또는 최적화: 두 폴더를 하나로 정리
# (고급 사용자용)
```

### 모델 업데이트
```bash
# 새 버전 다운로드 필요할 때
rm -rf /Users/a113211/workspace/stt_engine/models/openai_whisper-large-v3-turbo
python download_model.py

# 캐시 정리 (선택사항)
rm -rf /Users/a113211/workspace/stt_engine/models/models--openai--whisper-large-v3-turbo
```

### 네트워크 속도가 느릴 때
```bash
# 로컬에서 먼저 다운로드 완료 후 이관 권장
# USB 또는 클라우드 스토리지(Google Drive, S3 등) 사용 고려
```

---

## 🎯 최종 정리

| 항목 | 설명 |
|------|------|
| **즉시 삭제 가능** | `models--openai--whisper-large-v3-turbo` |
| **반드시 이관** | `openai_whisper-large-v3-turbo` (1.5GB) |
| **권장 방법** | SCP로 폴더 복사 후 서버에서 docker-compose up |
| **소요 시간** | 복사: 5-10분, 서버 설정: 5분 |
| **주의사항** | model.safetensors 파일 크기(1.5GB) 확인 필수 |
