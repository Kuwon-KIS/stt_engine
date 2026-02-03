# ✅ 수정된 배포 가이드 (오프라인 + CUDA 호환성)

**작성일**: 2026-02-03  
**목적**: python-multipart 추가 및 CUDA 문제 해결 후 안정적인 배포 절차

---

## 🎯 근본 문제 해결 완료

### ✅ 문제 1: python-multipart 누락 - FIXED
- **조치**: python_multipart-0.0.22-py3-none-any.whl (24KB) 추가
- **위치**: `deployment_package/wheels/`
- **확인**: `ls -lh deployment_package/wheels/ | grep multipart`
- **결과**: FastAPI File Upload 기능 정상 작동

### ✅ 문제 2: CUDA 하드코딩 - FIXED  
- **조치**: `api_server.py`에서 환경변수 기반 device 선택
- **변경**: `device="cuda"` → `device=os.getenv("STT_DEVICE", "cpu")`
- **효과**: CPU 기본값, CUDA는 환경변수로 옵션 선택 가능
- **결과**: 모든 서버 환경에서 배포 가능

### ❌ 문제 3: Exited 컨테이너의 docker exec 불가능
- **이유**: 컨테이너가 시작 실패로 종료됨
- **해결**: 새 이미지(python-multipart 포함)로 재시작 필요
- **방법**: 아래 "Step 4: 서버 배포" 참고

---

## 📦 배포 아티팩트 준비 상태

| 항목 | 파일명 | 크기 | 상태 |
|------|--------|------|------|
| Docker Image | stt-engine-linux-x86_64.tar | 1.1GB | ✅ 이미 존재 |
| Wheels (압축) | build/output/wheels.tar.gz | 400MB | ✅ **재생성됨** (python-multipart 포함) |
| Wheels (디렉토리) | deployment_package/wheels/ | 406MB | ✅ **업데이트됨** (62개 파일) |
| 모델 | whisper-model.tar.gz | 1.4GB | ✅ 이미 존재 |

---

## 🚀 새로운 배포 절차

### Step 0: 로컬 이미지 빌드 (업데이트된 Dockerfile 사용)

```bash
cd /Users/a113211/workspace/stt_engine

# Docker 이미지 빌드 (python-multipart 포함, STT_DEVICE=cpu 설정)
bash scripts/build-engine-image.sh
# 또는
docker build -t stt-engine:linux-x86_64 -f docker/Dockerfile.engine .

# 이미지를 tar로 저장 (이미 존재하면 덮어쓰기)
docker save stt-engine:linux-x86_64 | gzip > build/output/stt-engine-linux-x86_64.tar.gz

# 크기 확인
ls -lh build/output/stt-engine-linux-x86_64.tar.gz
```

### Step 1: 서버에 아티팩트 전송

```bash
# 로컬 머신에서 실행
scp build/output/stt-engine-linux-x86_64.tar.gz user@server:/path/to/deployment/
scp build/output/wheels.tar.gz user@server:/path/to/deployment/  # (필요 시)
scp models/whisper-model.tar.gz user@server:/path/to/deployment/  # (필요 시)

# 예: server IP가 192.168.1.100인 경우
scp build/output/stt-engine-linux-x86_64.tar.gz ddpapp@dlddpgai1:/data/stt/
```

### Step 2: 서버에서 이미지 로드

```bash
# 서버에 SSH 접속
ssh user@server

# 도커 이미지 로드
docker load -i /data/stt/stt-engine-linux-x86_64.tar.gz

# 또는 gz가 아닌 경우
docker load -i /data/stt/stt-engine-linux-x86_64.tar

# 이미지 확인
docker images | grep stt-engine
```

### Step 3: 기존 컨테이너 정리

```bash
# 현재 컨테이너 상태 확인
docker ps -a | grep stt-engine

# 실행 중인 컨테이너 중지
docker stop stt-engine 2>/dev/null || true

# 컨테이너 제거
docker rm stt-engine 2>/dev/null || true

# 확인: 완전히 제거되었는지 확인
docker ps -a | grep stt-engine
# (아무것도 출력되지 않아야 함)
```

### Step 4: 새 컨테이너 실행

#### 옵션 A: CPU 모드 (권장 - 호환성 최고)

```bash
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v /data/models:/app/models \
  -v /data/logs:/app/logs \
  -e STT_DEVICE=cpu \
  stt-engine:linux-x86_64

# 로그 확인
docker logs -f stt-engine

# 헬스 체크 (성공할 때까지 반복)
curl -X GET http://localhost:8003/health
```

#### 옵션 B: CUDA 모드 (서버 GPU 드라이버가 충분한 경우)

```bash
docker run -d \
  --name stt-engine \
  --gpus all \
  -p 8003:8003 \
  -v /data/models:/app/models \
  -v /data/logs:/app/logs \
  -e STT_DEVICE=cuda \
  stt-engine:linux-x86_64

# 로그 확인 (CUDA 초기화 확인)
docker logs -f stt-engine
```

#### 옵션 C: Auto 모드 (faster-whisper 자동 감지)

```bash
docker run -d \
  --name stt-engine \
  --gpus all \
  -p 8003:8003 \
  -v /data/models:/app/models \
  -v /data/logs:/app/logs \
  -e STT_DEVICE=auto \
  stt-engine:linux-x86_64
```

---

## ✅ 배포 후 검증

### 1. 컨테이너 상태 확인

```bash
# 컨테이너 running 상태 확인
docker ps | grep stt-engine

# 예상 출력:
# CONTAINER ID  IMAGE               COMMAND            STATUS          PORTS
# abc123...     stt-engine:...      "python3.11 api..." Up 5 minutes    0.0.0.0:8003->8003/tcp
```

### 2. 헬스 체크 (API 응답 확인)

```bash
# 헬스 체크 엔드포인트 호출
curl -X GET http://localhost:8003/health

# 예상 응답: 200 OK
# {"status": "healthy", "device": "cpu"}
```

### 3. 음성 파일 테스트 (실제 STT 기능)

```bash
# 테스트 음성 파일 준비 (WAV 또는 MP3)
# 예: /data/test_audio.wav

# API 호출 (File Upload 사용)
curl -X POST http://localhost:8003/transcribe \
  -F "file=@/data/test_audio.wav"

# 예상 응답 (json):
# {
#   "text": "recognizedtext...",
#   "duration_seconds": 5.2,
#   "processing_time_seconds": 0.8,
#   "model": "whisper-large-v3-turbo",
#   "device": "cpu"
# }
```

### 4. 로그 모니터링

```bash
# 실시간 로그 확인
docker logs -f stt-engine

# 마지막 100줄 확인
docker logs --tail 100 stt-engine

# 에러 확인
docker logs stt-engine 2>&1 | grep -i "error\|warn\|fail"
```

---

## 🔧 배포 중 문제 해결

### 문제: "Form data requires python-multipart"

**원인**: python-multipart가 이미지에 없음  
**해결**: 새 이미지 빌드 (python-multipart 포함)

```bash
# Step 0부터 다시 시작
docker build -t stt-engine:linux-x86_64 -f docker/Dockerfile.engine .
docker save stt-engine:linux-x86_64 | gzip > build/output/stt-engine-linux-x86_64.tar.gz
# 서버로 전송 및 배포 진행
```

### 문제: "CUDA driver version is insufficient"

**원인**: 서버 GPU 드라이버 버전이 낮음  
**해결**:

```bash
# 옵션 1: CPU 모드로 실행 (권장)
docker run -d --name stt-engine -p 8003:8003 -e STT_DEVICE=cpu stt-engine:linux-x86_64

# 옵션 2: GPU 드라이버 업그레이드 (시스템 관리자 작업)
# nvidia-driver 업그레이드 후 CUDA 모드 사용 가능
```

### 문제: "컨테이너가 Exited 상태에서 시작 안 됨"

**원인**: 이미지에 문제 있거나 의존성 누락  
**진단**:

```bash
# 디버그 모드로 실행
docker run -it --name stt-engine-debug stt-engine:linux-x86_64 /bin/bash

# 컨테이너 내부에서 검증
python3 -c "import fastapi; print('fastapi OK')"
python3 -c "import faster_whisper; print('faster_whisper OK')"
python3 -c "import python_multipart; print('python_multipart OK')"

# 로그 확인
python3 api_server.py
```

### 문제: "모델 파일을 찾을 수 없음"

**원인**: 모델 마운트 경로 불일치  
**해결**:

```bash
# 1. 서버에 모델 존재 확인
ls -la /data/models/openai_whisper-large-v3-turbo/

# 2. 마운트 재확인 (-v 옵션 확인)
docker inspect stt-engine | grep -A 5 "Mounts"

# 3. 컨테이너 재시작 (경로 수정 후)
docker stop stt-engine
docker rm stt-engine
docker run -d -p 8003:8003 -v /data/models:/app/models stt-engine:linux-x86_64
```

---

## 📊 배포 체크리스트

```
사전 준비 (로컬)
☑ Dockerfile.engine 확인: python-multipart 포함 (라인 22)
☑ api_server.py 확인: os.getenv('STT_DEVICE', 'cpu') 사용 (라인 23)
☑ Docker 이미지 빌드 완료
☑ stt-engine-linux-x86_64.tar.gz 준비
☑ wheels.tar.gz 준비 (python-multipart 포함)

배포 (서버)
☑ 이미지 파일 서버로 전송
☑ 기존 컨테이너 중지/제거
☑ 새 이미지 로드
☑ 새 컨테이너 실행 (STT_DEVICE=cpu)
☑ 헬스 체크 통과 (http://localhost:8003/health)
☑ 음성 파일 테스트 성공

운영
☑ 로그 모니터링 설정
☑ 자동 재시작 설정 (docker restart policy)
☑ 모니터링 알림 설정
```

---

## 🔗 참고 자료

- [ROOT_CAUSE_ANALYSIS.md](ROOT_CAUSE_ANALYSIS.md) - 근본 원인 분석
- [SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md) - 초기 배포 가이드
- [DOCKER_MODEL_MOUNT_GUIDE.md](DOCKER_MODEL_MOUNT_GUIDE.md) - 모델 마운트 방법
- [requirements.txt](/requirements.txt) - 전체 의존성 목록

---

## ⚠️ 중요 사항

1. **python-multipart 필수**: FastAPI File Upload 기능 사용 시 반드시 필요
2. **STT_DEVICE 환경변수**: CPU(안정적) vs CUDA(빠름) 선택 가능
3. **Offline-First Design**: 모든 의존성이 wheels에 포함되어야 함
4. **모델 마운트**: 로컬 경로 → 컨테이너 /app/models 마운트 필수

---

**상태**: 🟢 배포 준비 완료 ✅
