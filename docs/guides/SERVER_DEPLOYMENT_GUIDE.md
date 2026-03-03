# 🚀 Linux 서버 배포 실행 가이드

**대상**: tar 파일 서버 전송 후 단계  
**소요 시간**: ~10분  

---

## 📋 사전 확인사항

서버에 다음이 있는지 확인:

```bash
# 1. Docker 설치 확인
docker --version
# 예상 출력: Docker version 20.10 이상

# 2. Python 설치 확인
python3.11 --version
# 예상 출력: Python 3.11.x

# 3. 디스크 공간 확인 (최소 5GB)
df -h / | tail -1
```

---

## 🔧 Step 1: Docker 이미지 로드

```bash
# 1-1. 이미지 파일이 있는 디렉토리로 이동
cd /path/to/deployment_files

# 1-2. 이미지 로드
docker load -i stt-engine-linux-x86_64.tar

# ✅ 예상 출력
# Loaded image: stt-engine:linux-x86_64

# 1-3. 이미지 확인
docker images | grep stt-engine
# stt-engine              linux-x86_64   <id>  <date>   1.1GB
```

---

## 📦 Step 2: Wheel 파일 준비 (2가지 방법)

### 방법 A: 별도 wheels.tar.gz 사용 (권장)

```bash
# 2A-1. 압축 해제
tar -xzf wheels.tar.gz
# 생성: wheels/ 디렉토리

# 2A-2. 확인
ls -1 wheels/ | head -10
# 61개 파일이 보이면 정상
```

### 방법 B: 온라인에서 직접 설치

```bash
# wheel 파일 없이 PyPI에서 다운로드
# (인터넷 연결 필요)
docker run --rm stt-engine:linux-x86_64 \
  pip install torch torchaudio faster-whisper fastapi uvicorn
```

---

## 🎯 Step 3: 모델 파일 준비 (3가지 선택)

### 방법 A: 압축된 모델 사용 (추천 - 가장 빠름)

```bash
# 3A-1. 로컬에서 모델 전송
scp models/whisper-model.tar.gz user@server:/path/to/deployment/

# 3A-2. 서버에서 압축 해제
tar -xzf whisper-model.tar.gz -C ./

# 생성: openai_whisper-large-v3-turbo/ 디렉토리
# 이 디렉토리를 Docker에 마운트
```

### 방법 B: 처음부터 다운로드 (온라인 필요)

```bash
# Docker 실행 시 자동으로 첫 사용 때 다운로드됨
# (약 5-10분 소요, 모델 크기에 따라)
# 이후 디스크에 캐시되어 재사용 가능
```

### 방법 C: NFS 공유 스토리지 사용

```bash
# 중앙 저장소에 모델 저장
/mnt/shared_models/openai_whisper-large-v3-turbo/

# 각 서버에서는 마운트만
```

---

## 🐳 Step 4: Docker 컨테이너 실행

### 방법 1: 단순 Docker run (권장 for 테스트)

```bash
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v /path/to/models:/app/models \
  -v /path/to/logs:/app/logs \
  stt-engine:linux-x86_64

# 실행 결과 확인
docker ps | grep stt-engine
```

**경로 설명**:
- `/path/to/models` → 로컬 모델 경로 (절대경로 권장)
- `/path/to/logs` → 로그 저장 경로 (선택사항)
- `8003` → API 포트

**구체적 예시**:
```bash
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v /home/user/deployment/openai_whisper-large-v3-turbo:/app/models/openai_whisper-large-v3-turbo \
  -v /home/user/logs:/app/logs \
  stt-engine:linux-x86_64
```

---

### 방법 2: Docker Compose (권장 for 프로덕션)

**docker-compose.yml** 작성:
```yaml
version: '3.8'

services:
  stt-engine:
    image: stt-engine:linux-x86_64
    container_name: stt-engine
    
    ports:
      - "8003:8003"
    
    volumes:
      - /path/to/models:/app/models
      - /path/to/logs:/app/logs
    
    environment:
      - HF_HOME=/app/models
      - PYTHONUNBUFFERED=1
    
    restart: unless-stopped
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

**실행**:
```bash
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

**중지/시작**:
```bash
docker-compose stop
docker-compose start
docker-compose down  # 완전 제거
```

---

## ✅ Step 5: 서비스 검증

### 5-1. 컨테이너 상태 확인

```bash
# 실행 중인지 확인
docker ps | grep stt-engine

# 로그 확인
docker logs stt-engine

# 예상 로그:
# ✅ faster-whisper 모델 로드 완료 (Device: cuda, compute: float16)
# INFO:     Uvicorn running on http://0.0.0.0:8003
```

### 5-2. API 헬스 체크

```bash
# 헬스 체크 엔드포인트
curl http://localhost:8003/health

# 예상 응답:
# {"status":"ok","version":"1.0.0","engine":"faster-whisper"}
```

### 5-3. 실제 음성 인식 테스트

```bash
# 테스트 음성 파일 준비
curl -X POST -F "file=@test_audio.wav" \
  http://localhost:8003/transcribe

# 예상 응답:
# {
#   "success": true,
#   "text": "인식된 텍스트",
#   "language": "ko",
#   "duration": 5.2
# }
```

---

## 🔗 Step 6: 방화벽 및 네트워크 설정

### 포트 개방 (Linux 방화벽)

```bash
# firewalld 사용
sudo firewall-cmd --permanent --add-port=8003/tcp
sudo firewall-cmd --reload

# ufw 사용 (Ubuntu)
sudo ufw allow 8003/tcp

# 확인
sudo firewall-cmd --list-ports
```

### 외부 접근 설정

```bash
# 로컬만 접근 (기본)
docker run -p 127.0.0.1:8003:8003 ...

# 외부 접근 허용
docker run -p 0.0.0.0:8003:8003 ...

# 또는 리버스 프록시 (Nginx 권장)
```

---

## 📊 Step 7: 성능 모니터링

### 리소스 사용량 확인

```bash
# 실시간 모니터링
docker stats stt-engine

# 예상 출력:
# CONTAINER   CPU %   MEM USAGE / LIMIT   NET I/O
# stt-engine  2.5%    2.1G / 8G          125MB / 89MB
```

### 로그 모니터링

```bash
# 마지막 100줄 보기
docker logs --tail 100 stt-engine

# 실시간 로그
docker logs -f stt-engine

# 타임스탬프 포함
docker logs -f --timestamps stt-engine
```

---

## 🛠️ Step 8: 문제 해결

### 문제 1: 이미지 로드 실패

```bash
# 원인: tar 파일 손상 또는 경로 오류
# 해결
docker load -i /full/path/to/stt-engine-linux-x86_64.tar

# 로드 진행률 확인
docker load -i stt-engine-linux-x86_64.tar 2>&1 | tail -20
```

### 문제 2: 컨테이너 시작 실패

```bash
# 로그 확인
docker logs stt-engine

# 공통 원인:
# - 모델 경로 잘못됨 → -v 경로 확인
# - 포트 이미 사용 중 → docker ps 확인
# - 메모리 부족 → free -h 확인
```

### 문제 3: 모델 로드 실패

```bash
# 모델 파일이 존재하는지 확인
docker exec stt-engine ls -lh /app/models/

# 권한 확인
ls -la /path/to/models/

# 해결
chmod -R 755 /path/to/models/
docker restart stt-engine
```

### 문제 4: CUDA/GPU 인식 실패

```bash
# GPU 드라이버 확인
nvidia-smi

# NVIDIA Docker 설치 확인
docker run --rm --gpus all nvidia/cuda:12.1 nvidia-smi

# GPU 사용하는 Docker 실행
docker run -d \
  --gpus all \
  -p 8003:8003 \
  -v /path/to/models:/app/models \
  stt-engine:linux-x86_64
```

---

## 📋 완전 배포 체크리스트

```
✅ 사전 확인
  □ Docker 설치 (v20.10+)
  □ Python 3.11 설치
  □ 디스크 공간 5GB 이상
  □ 네트워크 연결 (첫 모델 다운로드 시)

✅ Step 1: 이미지 로드
  □ docker load -i stt-engine-linux-x86_64.tar
  □ docker images | grep stt-engine 확인

✅ Step 2: Wheel 준비
  □ tar -xzf wheels.tar.gz 또는 PyPI 설치
  □ wheel 파일 61개 확인

✅ Step 3: 모델 준비
  □ tar -xzf whisper-model.tar.gz
  □ openai_whisper-large-v3-turbo/ 확인

✅ Step 4: 컨테이너 실행
  □ docker run 또는 docker-compose up
  □ docker ps 에서 stt-engine 보임

✅ Step 5: 검증
  □ curl http://localhost:8003/health
  □ 응답: {"status":"ok",...}
  □ 음성 파일 테스트 (선택)

✅ Step 6: 네트워크
  □ 방화벽 포트 8003 개방
  □ 보안 그룹 설정 확인

✅ Step 7: 모니터링
  □ docker stats 정상
  □ docker logs 에러 없음

✅ Step 8: 백업
  □ 설정 파일 백업
  □ 모델 경로 기록
```

---

## 🎯 Quick Start (완전 자동)

위 단계를 자동화한 스크립트:

```bash
#!/bin/bash
set -e

# 설정
IMAGE_FILE="stt-engine-linux-x86_64.tar"
WHEELS_FILE="wheels.tar.gz"
MODEL_FILE="whisper-model.tar.gz"
MODELS_PATH="/home/user/deployment/models"
LOGS_PATH="/home/user/deployment/logs"

echo "🚀 STT Engine 배포 시작..."

# 1. 이미지 로드
echo "📦 Docker 이미지 로드 중..."
docker load -i "$IMAGE_FILE"

# 2. 모델 준비
echo "🎯 모델 파일 준비 중..."
mkdir -p "$MODELS_PATH"
tar -xzf "$MODEL_FILE" -C "$MODELS_PATH/.."

# 3. 컨테이너 실행
echo "🐳 컨테이너 실행 중..."
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v "$MODELS_PATH":/app/models \
  -v "$LOGS_PATH":/app/logs \
  stt-engine:linux-x86_64

# 4. 검증
echo "✅ 서비스 검증 중..."
sleep 3
curl http://localhost:8003/health

echo "🎉 배포 완료!"
echo "📍 API: http://localhost:8003"
echo "📊 로그: docker logs -f stt-engine"
```

---

## 📞 지원 및 다음 단계

**배포 후**:
1. ✅ 헬스 체크 확인
2. ✅ 테스트 음성 파일로 인식 테스트
3. ✅ 모니터링 설정 (docker stats, 로그 수집)
4. ✅ 백업 정책 수립
5. ✅ 자동 재시작 설정 (systemd 또는 docker restart policy)

**보안 권장사항**:
- 방화벽으로 포트 8003 제한
- HTTPS/SSL 인증서 추가 (리버스 프록시)
- 인증 추가 (API 키, JWT 토큰)
- 정기 모니터링 및 로그 수집

---

**상태**: 🟢 서버 배포 완벽 준비 ✅
