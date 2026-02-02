# 🎯 Docker 모델 마운트 가이드

**현재 상태**: ✅ 마운트 완벽 지원

---

## 📊 현재 모델 상태

### 로컬 모델 (1.4GB)
```
models/
├── models--openai--whisper-large-v3-turbo/    # HuggingFace 캐시 형식
├── openai_whisper-large-v3-turbo/             # Faster-Whisper 사용 경로 ⭐
└── whisper-model.tar.gz                       # 압축본 (1.4GB)
```

**상태**:
- ✅ 로컬에서 이미 다운로드됨
- ✅ Docker 이미지에 **포함되지 않음** (이미지 크기 최소화)
- ✅ 마운트를 통해 주입 가능

---

## 🐳 Docker 마운트 방법

### 방법 1: 로컬 모델 마운트 (권장)

```bash
docker run -p 8003:8003 \
  -v /path/to/local/models:/app/models \
  stt-engine:linux-x86_64
```

**예시** (실제 경로):
```bash
docker run -p 8003:8003 \
  -v ~/workspace/stt_engine/models:/app/models \
  stt-engine:linux-x86_64
```

---

### 방법 2: Docker Compose 사용

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  stt-engine:
    image: stt-engine:linux-x86_64
    ports:
      - "8003:8003"
    volumes:
      - ./models:/app/models          # 로컬 models → 컨테이너 /app/models
      - ./logs:/app/logs              # 로그 저장
    environment:
      - HF_HOME=/app/models           # Hugging Face 캐시 경로
    restart: unless-stopped
```

**실행**:
```bash
docker-compose up -d
```

---

### 방법 3: 압축본 사용 (온라인 환경)

서버에 `models/whisper-model.tar.gz` 를 전송 후:

```bash
# 1. 압축 해제
cd /path/to/deployment_package
tar -xzf models/whisper-model.tar.gz

# 2. Docker 실행
docker run -p 8003:8003 \
  -v ./openai_whisper-large-v3-turbo:/app/models/openai_whisper-large-v3-turbo \
  stt-engine:linux-x86_64
```

---

## ⚙️ 모델 경로 설정

### Docker 이미지 내부 구조

```dockerfile
ENV HF_HOME=/app/models

# 애플리케이션이 찾는 경로
models/
└── openai_whisper-large-v3-turbo/
    ├── config.json
    ├── model.bin (또는 safetensors)
    ├── preprocessor_config.json
    ├── tokenizer.json
    └── ...
```

### 소스 코드에서의 설정

**api_server.py** (현재):
```python
model_path = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"
stt = WhisperSTT(str(model_path), device="cuda")
```

**환경변수로 변경 가능** (권장):
```python
import os

model_path = os.getenv(
    "MODEL_PATH",
    Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"
)
stt = WhisperSTT(str(model_path), device="cuda")
```

**실행할 때**:
```bash
# 커스텀 경로 사용
MODEL_PATH=/custom/path/to/model python3.11 api_server.py

# 또는 Docker에서
docker run -e MODEL_PATH=/app/models/custom_model \
  -v /path/to/model:/app/models/custom_model \
  stt-engine:linux-x86_64
```

---

## 📦 배포 시나리오별 가이드

### 시나리오 1: 로컬에서 개발 중

```bash
# 모델이 이미 로컬에 있으므로 직접 사용
python3.11 api_server.py

# 또는 Docker로 테스트
docker run -p 8003:8003 \
  -v $(pwd)/models:/app/models \
  stt-engine:linux-x86_64
```

---

### 시나리오 2: Linux 서버 배포 (처음)

```bash
# 1. 모델 파일 전송 (로컬 → 서버)
scp models/whisper-model.tar.gz user@server:/home/user/deployment/

# 2. 서버에서 압축 해제
ssh user@server
cd /home/user/deployment
tar -xzf whisper-model.tar.gz

# 3. Docker 실행
docker run -p 8003:8003 \
  -v /home/user/deployment/openai_whisper-large-v3-turbo:/app/models/openai_whisper-large-v3-turbo \
  stt-engine:linux-x86_64
```

---

### 시나리오 3: 다중 서버 배포 (모델 공유)

```bash
# 중앙 NFS/공유 스토리지에 모델 저장
/mnt/shared_models/openai_whisper-large-v3-turbo/

# 각 서버에서 마운트
docker run -p 8003:8003 \
  -v /mnt/shared_models/openai_whisper-large-v3-turbo:/app/models/openai_whisper-large-v3-turbo \
  stt-engine:linux-x86_64
```

---

## 🔍 모델 경로 검증

Docker 실행 후 모델이 제대로 로드되었는지 확인:

```bash
# 1. 헬스 체크
curl http://localhost:8003/health

# 예상 결과:
# {"status": "ok", "version": "1.0.0", "engine": "faster-whisper"}

# 2. 로그 확인
docker logs <container_id> | grep "faster-whisper 모델"

# 3. 모델 경로 검증
docker exec <container_id> ls -lh /app/models/openai_whisper-large-v3-turbo/
```

---

## 💾 모델 다운로드가 필요한 경우

마운트할 모델이 없다면, Docker 컨테이너 실행 시 자동으로 다운로드:

```bash
docker run -p 8003:8003 \
  -v /path/to/local/models:/app/models \
  stt-engine:linux-x86_64

# 첫 실행 시:
# 1. /app/models이 비어있음
# 2. Hugging Face에서 자동 다운로드
# 3. /app/models에 캐시됨
# 4. 이후 재사용 가능
```

**주의**: 온라인 연결 필요하며, 모델 다운로드에 시간 소요 (모델 크기에 따라)

---

## 🎯 권장 배포 구성

### 완전 오프라인 배포 (추천)

```bash
# 전송 파일
build/output/stt-engine-linux-x86_64.tar     # 1.1GB
deployment_package/wheels.tar.gz              # 400MB
models/whisper-model.tar.gz                   # 1.4GB

# 서버에서 설치
docker load -i stt-engine-linux-x86_64.tar
tar -xzf wheels.tar.gz
tar -xzf whisper-model.tar.gz -C ./models

# 실행
docker run -p 8003:8003 \
  -v $(pwd)/openai_whisper-large-v3-turbo:/app/models/openai_whisper-large-v3-turbo \
  stt-engine:linux-x86_64
```

---

## 📋 체크리스트

마운트 설정 전 확인사항:

- [ ] 로컬 모델 경로 확인: `models/openai_whisper-large-v3-turbo/` 존재?
- [ ] Docker 이미지 로드됨: `docker images | grep stt-engine`
- [ ] 마운트 경로 권한: `-v` 플래그 경로에 읽기 권한?
- [ ] 디스크 공간: 모델 크기(~2GB) + 임시 파일 공간 확인?

---

**결론**: 현재 상태는 마운트를 위해 완벽하게 준비되어 있습니다! 🎉
