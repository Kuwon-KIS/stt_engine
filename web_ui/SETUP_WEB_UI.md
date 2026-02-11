# Web UI 설정 및 배포 가이드

STT Web UI를 개발 환경, EC2 빌드 환경, RHEL 배포 환경에 맞춰 설정하고 배포하는 방법을 설명합니다.

## 📋 목차

1. [로컬 개발 (MacBook)](#로컬-개발-macbook)
2. [EC2 빌드 환경](#ec2-빌드-환경)
3. [RHEL 배포 환경](#rhel-배포-환경)
4. [Docker 네트워크 통신](#docker-네트워크-통신)
5. [트러블슈팅](#트러블슈팅)

---

## 로컬 개발 (MacBook)

### 1️⃣ 환경 설정

```bash
# 저장소 디렉토리로 이동
cd /Users/a113211/workspace/stt_engine

# Python 가상 환경 생성
python3.11 -m venv venv_web_ui
source venv_web_ui/bin/activate

# Web UI 의존성 설치
pip install -r web_ui/requirements.txt
```

### 2️⃣ 환경 변수 설정

```bash
# MacBook에서 STT API 실행 (다른 터미널)
python3.11 api_server.py

# Web UI 환경 변수 설정
export STT_API_URL=http://localhost:8003
export WEB_PORT=8100
export LOG_LEVEL=DEBUG

# 또는 .env 파일 생성 (web_ui/.env)
cat > web_ui/.env << EOF
STT_API_URL=http://localhost:8003
WEB_PORT=8100
LOG_LEVEL=DEBUG
EOF
```

### 3️⃣ 로컬 개발 서버 시작

```bash
# Web UI 디렉토리로 이동
cd web_ui

# 개발 서버 시작 (자동 재로드)
python -m uvicorn main:app --host 0.0.0.0 --port 8100 --reload

# 또는 run.sh 사용
bash run.sh
```

### 4️⃣ 접속 및 테스트

```bash
# 브라우저에서 접속
# http://localhost:8100

# 또는 curl로 테스트
curl http://localhost:8100/health
```

**개발 중 유용한 명령어:**
```bash
# API 헬스 체크
curl http://localhost:8003/health

# 설정 확인
python -c "from web_ui import config; print('Port:', config.WEB_PORT)"

# 로그 레벨 변경
export LOG_LEVEL=INFO
```

---

## EC2 빌드 환경

### 1️⃣ EC2 인스턴스 준비

**요구사항:**
- RHEL 8.9 기반 Amazon Linux 2
- 30GB 이상 스토리지
- Docker 설치 완료

**EC2 접속:**
```bash
ssh -i your-key.pem ec2-user@your-ec2-ip
cd /home/ec2-user/stt_engine
```

### 2️⃣ Web UI 이미지 빌드

```bash
# Web UI 이미지 빌드 (Dockerfile.web_ui 기반)
bash scripts/build-ec2-web-ui-image.sh v1.0

# 결과:
# ✅ 빌드 완료: stt-web-ui:cuda129-rhel89-v1.0
# 📊 빌드로그: /tmp/build-web-ui-YYYYMMDD-HHMMSS.log

# 이미지 확인
docker images | grep stt-web-ui
```

**빌드 스크립트 옵션:**
```bash
# 기본값 (latest)
bash scripts/build-ec2-web-ui-image.sh

# 특정 버전
bash scripts/build-ec2-web-ui-image.sh v1.0
bash scripts/build-ec2-web-ui-image.sh v1.1

# 버전 확인
cat build/output/web_ui_build_info.txt
```

### 3️⃣ STT Engine 이미지도 함께 빌드

```bash
# 이미 빌드되어 있으면 생략, 없으면 빌드
bash scripts/build-ec2-engine-image.sh v1.0

# 두 이미지 모두 확인
docker images | grep "stt-"
```

**출력 예시:**
```
REPOSITORY                 TAG                    IMAGE ID
stt-engine                 cuda129-rhel89-v1.0    abc123...
stt-web-ui                 cuda129-rhel89-v1.0    def456...
```

### 4️⃣ 빌드 산출물 확인

```bash
# 빌드 정보 저장 위치
ls -la build/output/

# Web UI 빌드 로그 확인
tail -f /tmp/build-web-ui-*.log
```

---

## RHEL 배포 환경

### 1️⃣ 배포 준비

**온-프레미스 RHEL 8.9 서버에서:**

```bash
# 필수 조건 확인
docker --version    # Docker 설치 필수
docker ps          # Docker daemon 실행 중 확인

# 디렉토리 구조 생성
mkdir -p /home/stt_engine/{models,web_ui/data,web_ui/logs,docker}
cd /home/stt_engine
```

### 2️⃣ Docker 이미지 로드 (EC2에서 빌드한 경우)

```bash
# EC2에서 이미지를 tar로 저장 (선택)
docker save stt-engine:cuda129-rhel89-v1.0 | gzip > stt-engine-v1.0.tar.gz
docker save stt-web-ui:cuda129-rhel89-v1.0 | gzip > stt-web-ui-v1.0.tar.gz

# RHEL 서버로 전송
scp stt-*.tar.gz user@rhel-server:/home/stt_engine/

# RHEL 서버에서 로드
docker load -i stt-engine-v1.0.tar.gz
docker load -i stt-web-ui-v1.0.tar.gz

# 이미지 확인
docker images | grep "stt-"
```

### 3️⃣ Docker 네트워크 생성

```bash
# 브릿지 네트워크 생성 (처음 한 번만)
docker network create stt-network

# 네트워크 확인
docker network ls | grep stt-network
docker network inspect stt-network
```

### 4️⃣ 서비스 실행

#### 방법 A: 독립 Docker 명령어 사용

**터미널 1: STT API**
```bash
docker run -d \
  --name stt-api \
  --network stt-network \
  -p 8003:8003 \
  -e STT_DEVICE=cuda \
  -e STT_COMPUTE_TYPE=int8 \
  -v /home/stt_engine/models:/app/models \
  -v /home/stt_engine/logs:/app/logs \
  --gpus all \
  stt-engine:cuda129-rhel89-v1.0

# 실행 확인
docker logs stt-api
```

**터미널 2: Web UI**
```bash
docker run -d \
  --name stt-web-ui \
  --network stt-network \
  -p 8100:8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -v /home/stt_engine/web_ui/data:/app/data \
  -v /home/stt_engine/web_ui/logs:/app/logs \
  stt-web-ui:cuda129-rhel89-v1.0

# 실행 확인
docker logs stt-web-ui
```

#### 방법 B: Docker Compose 사용 (권장)

```bash
# docker-compose.yml 파일 위치
cat > /home/stt_engine/docker-compose.yml << 'EOF'
version: '3.8'

services:
  stt-api:
    image: stt-engine:cuda129-rhel89-v1.0
    container_name: stt-api
    ports:
      - "8003:8003"
    environment:
      - STT_DEVICE=cuda
      - STT_COMPUTE_TYPE=int8
    volumes:
      - /home/stt_engine/models:/app/models
      - /home/stt_engine/logs:/app/logs
    networks:
      - stt-network
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  stt-web-ui:
    image: stt-web-ui:cuda129-rhel89-v1.0
    container_name: stt-web-ui
    ports:
      - "8100:8100"
    environment:
      - STT_API_URL=http://stt-api:8003
    volumes:
      - /home/stt_engine/web_ui/data:/app/data
      - /home/stt_engine/web_ui/logs:/app/logs
    networks:
      - stt-network
    depends_on:
      - stt-api
    restart: unless-stopped

networks:
  stt-network:
    driver: bridge
EOF

# Docker Compose 실행
cd /home/stt_engine
docker-compose up -d

# 상태 확인
docker-compose ps
docker-compose logs -f
```

### 5️⃣ 접속 및 테스트

```bash
# STT API 헬스 체크
curl http://localhost:8003/health

# Web UI 접속
# 브라우저: http://RHEL서버IP:8100

# 또는 curl로 테스트
curl http://localhost:8100/health

# 컨테이너 로그 확인
docker logs stt-api -f
docker logs stt-web-ui -f
```

### 6️⃣ 서비스 관리

```bash
# 상태 확인
docker ps | grep stt-

# 로그 확인
docker logs stt-web-ui --tail 50
docker logs stt-api --tail 50

# 중지
docker-compose stop
# 또는
docker stop stt-web-ui stt-api

# 시작
docker-compose start
# 또는
docker start stt-api stt-web-ui

# 삭제
docker-compose down
# 또는
docker rm stt-web-ui stt-api
docker network rm stt-network

# 재시작
docker-compose restart
# 또는
docker restart stt-api stt-web-ui
```

---

## Docker 네트워크 통신

### 아키텍처

```
┌─────────────────────────────────────────────────┐
│           Docker Bridge Network                 │
│            (stt-network)                        │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────┐     DNS 해석      ┌─────────┐ │
│  │  stt-web-ui ├─────────────────→ │ stt-api │ │
│  │  :8100      │  stt-api:8003    │ :8003   │ │
│  └─────────────┘                   └─────────┘ │
│        ↕                                  ↕    │
│   Port 8100                          Port 8003 │
│  (외부 접속)                       (외부 접속)  │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 통신 원리

**내부 통신 (Docker 네트워크):**
```
Web UI → http://stt-api:8003
         ↓
    Docker DNS 해석
         ↓
    stt-api 컨테이너 IP (예: 172.20.0.2)
         ↓
    STT API 서버 (포트 8003)
```

**외부 접속:**
```
Client → http://localhost:8100
         ↓
    포트 매핑 (8100:8100)
         ↓
    stt-web-ui 컨테이너 (포트 8100)

Client → http://localhost:8003
         ↓
    포트 매핑 (8003:8003)
         ↓
    stt-api 컨테이너 (포트 8003)
```

### 네트워크 확인

```bash
# 네트워크 상태 확인
docker network inspect stt-network

# 컨테이너 IP 확인
docker inspect stt-api | grep "IPAddress"
docker inspect stt-web-ui | grep "IPAddress"

# 컨테이너 간 통신 테스트
docker exec stt-web-ui curl http://stt-api:8003/health

# DNS 해석 확인
docker exec stt-web-ui nslookup stt-api
```

---

## 환경 변수

### Web UI 설정

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `STT_API_URL` | `http://localhost:8003` | STT API 서버 URL |
| `WEB_PORT` | `8100` | Web UI 서버 포트 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 (DEBUG/INFO/WARNING) |
| `UPLOAD_MAX_SIZE_MB` | `100` | 최대 업로드 크기 (MB) |
| `BATCH_MAX_WORKERS` | `4` | 배치 처리 병렬 수 |

### STT API 설정

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `STT_DEVICE` | `cpu` | 사용 디바이스 (cpu/cuda) |
| `STT_COMPUTE_TYPE` | `default` | 컴퓨트 타입 (default/int8/float16) |
| `API_PORT` | `8003` | API 서버 포트 |

### 환경변수 설정 방법

**Docker 실행 시:**
```bash
docker run -e STT_API_URL=http://stt-api:8003 \
           -e WEB_PORT=8100 \
           stt-web-ui:cuda129-rhel89-v1.0
```

**Docker Compose:**
```yaml
services:
  stt-web-ui:
    environment:
      - STT_API_URL=http://stt-api:8003
      - WEB_PORT=8100
      - LOG_LEVEL=DEBUG
```

**.env 파일:**
```bash
# web_ui/.env
STT_API_URL=http://stt-api:8003
WEB_PORT=8100
LOG_LEVEL=INFO
BATCH_MAX_WORKERS=4
```

---

## 트러블슈팅

### Web UI가 시작되지 않음

```bash
# 로그 확인
docker logs stt-web-ui

# 포트 충돌 확인
lsof -i :8100
# 또는
netstat -tuln | grep 8100

# 포트 변경 (환경변수)
docker run -e WEB_PORT=8101 ...
```

### STT API와 통신 안 됨

```bash
# 네트워크 확인
docker network inspect stt-network

# 컨테이너 간 통신 테스트
docker exec stt-web-ui curl http://stt-api:8003/health

# DNS 해석 확인
docker exec stt-web-ui ping stt-api

# API 서버 상태 확인
docker logs stt-api
```

### 성능 저하

```bash
# 리소스 사용 확인
docker stats stt-web-ui stt-api

# GPU 사용 확인
docker exec stt-api nvidia-smi

# 로그 레벨 확인
docker logs stt-web-ui | grep ERROR
```

### 파일 업로드 문제

```bash
# 디렉토리 권한 확인
ls -la web_ui/data/
ls -la web_ui/logs/

# 권한 변경
chmod 755 web_ui/data
chmod 755 web_ui/logs

# 컨테이너 내부 경로 확인
docker exec stt-web-ui ls -la /app/data
```

---

## 참고 문서

- [README.md](README.md) - Web UI 개요
- [WEB_UI_ARCHITECTURE.md](WEB_UI_ARCHITECTURE.md) - 아키텍처 상세
- [../scripts/build-ec2-web-ui-image.sh](../scripts/build-ec2-web-ui-image.sh) - 빌드 스크립트
- [../docker/docker-compose.yml](../docker/docker-compose.yml) - Docker Compose 설정
