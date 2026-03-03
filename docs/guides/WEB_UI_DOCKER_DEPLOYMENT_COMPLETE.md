# Web UI Docker 독립 배포 아키텍처 - 완료 보고서

## 📋 프로젝트 완료 요약

### ✅ 완료된 작업

#### 1️⃣ Web UI 포트 변경 (8001 → 8100)
**파일**: [web_ui/config.py](web_ui/config.py)
```python
WEB_PORT = int(os.getenv("WEB_PORT", 8100))  # 8001 → 8100
```
- ✅ 완료
- 영향: Web UI 접속 주소 변경 (localhost:8100)
- 환경변수 `WEB_PORT=8100`으로 오버라이드 가능

#### 2️⃣ 독립 Docker 컨테이너 아키텍처
**파일**: 
- [web_ui/docker/docker-compose.yml](web_ui/docker/docker-compose.yml)
- [docker/docker-compose.yml](docker/docker-compose.yml)

**핵심 변경사항**:
- ✅ Docker 브릿지 네트워크 `stt-network` 구성
- ✅ 사전 빌드된 이미지 기반 (build → image 변경)
- ✅ 서비스 간 DNS 기반 통신 (`http://stt-api:8003`)

**아키텍처**:
```
┌─────────────────────────────────────────┐
│    Docker Bridge Network (stt-network)  │
├─────────────────────────────────────────┤
│                                         │
│  stt-web-ui ←→ stt-api (DNS 해석)      │
│   :8100           :8003                 │
│    ↕               ↕                    │
│  port 8100      port 8003              │
│  (외부 접속)    (외부 접속)             │
│                                         │
└─────────────────────────────────────────┘
```

#### 3️⃣ Web UI 빌드 스크립트
**파일**: [scripts/build-ec2-web-ui-image.sh](scripts/build-ec2-web-ui-image.sh)
- ✅ 완료
- 기능: EC2 RHEL 8.9 환경에서 Web UI Docker 이미지 빌드
- 패턴: STT Engine 빌드 스크립트와 동일
- 버전 관리: `stt-web-ui:cuda129-rhel89-vX.X` 형식

**사용법**:
```bash
# 기본 (latest)
bash scripts/build-ec2-web-ui-image.sh

# 특정 버전
bash scripts/build-ec2-web-ui-image.sh v1.0

# 결과
# ✅ stt-web-ui:cuda129-rhel89-v1.0
# 📊 빌드로그: /tmp/build-web-ui-YYYYMMDD-HHMMSS.log
```

**포함된 기능**:
- 자동 전제 조건 검사 (Docker 설치, 디렉토리 확인)
- 이전 이미지 자동 정리 (선택)
- 자세한 로깅 및 진행 상황 표시
- 빌드 정보 저장 (build/output/web_ui_build_info.txt)
- 실행 명령어 자동 제시

#### 4️⃣ 포괄적인 설정 및 배포 문서

**새로운 문서**:
- ✅ [web_ui/SETUP_WEB_UI.md](web_ui/SETUP_WEB_UI.md) - 환경별 완전 가이드

**업데이트된 문서**:
- ✅ [README.md](README.md) - Web UI 독립 배포 섹션 추가
- ✅ [web_ui/README.md](web_ui/README.md) - 포트 8100, Docker 네트워크 설명
- ✅ [docker/README.md](docker/README.md) - 배포 흐름도 및 Docker Compose 사용법

---

## 🚀 배포 환경별 실행 방법

### 로컬 개발 (MacBook)

```bash
# 1. 의존성 설치
pip install -r web_ui/requirements.txt

# 2. 환경 변수 설정 (선택)
export STT_API_URL=http://localhost:8003
export WEB_PORT=8100

# 3. 개발 서버 시작
cd web_ui
python -m uvicorn main:app --host 0.0.0.0 --port 8100 --reload

# 또는 Docker Compose 사용
docker-compose -f docker/docker-compose.yml up

# 접속: http://localhost:8100
```

### EC2 빌드 환경

```bash
# 1. SSH 접속
ssh -i your-key.pem ec2-user@your-ec2-ip
cd /home/ec2-user/stt_engine

# 2. Web UI 이미지 빌드
bash scripts/build-ec2-web-ui-image.sh v1.0

# 3. STT Engine 이미지도 빌드 (필요시)
bash scripts/build-ec2-engine-image.sh v1.0

# 4. 이미지 확인
docker images | grep stt-
# stt-engine:cuda129-rhel89-v1.0
# stt-web-ui:cuda129-rhel89-v1.0
```

### RHEL 배포 환경

#### 방법 A: Docker Compose 사용 (권장)

```bash
# 1. Docker 네트워크 생성
docker network create stt-network

# 2. docker-compose.yml 준비
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  stt-api:
    image: stt-engine:cuda129-rhel89-v1.0
    container_name: stt-api
    ports: ["8003:8003"]
    environment:
      - STT_DEVICE=cuda
      - STT_COMPUTE_TYPE=int8
    volumes:
      - /home/stt_engine/models:/app/models
    networks: [stt-network]
    restart: unless-stopped

  stt-web-ui:
    image: stt-web-ui:cuda129-rhel89-v1.0
    container_name: stt-web-ui
    ports: ["8100:8100"]
    environment:
      - STT_API_URL=http://stt-api:8003
    volumes:
      - /home/stt_engine/web_ui/data:/app/data
      - /home/stt_engine/web_ui/logs:/app/logs
    networks: [stt-network]
    depends_on:
      - stt-api
    restart: unless-stopped

networks:
  stt-network:
    driver: bridge
EOF

# 3. 서비스 시작
docker-compose up -d

# 4. 상태 확인
docker-compose ps

# 5. 로그 확인
docker-compose logs -f
```

#### 방법 B: 독립 Docker 명령어 사용

```bash
# 1. Docker 네트워크 생성
docker network create stt-network

# 2. STT API 실행
docker run -d --name stt-api --network stt-network -p 8003:8003 \
  -e STT_DEVICE=cuda -e STT_COMPUTE_TYPE=int8 \
  -v /home/stt_engine/models:/app/models \
  --gpus all \
  stt-engine:cuda129-rhel89-v1.0

# 3. Web UI 실행
docker run -d --name stt-web-ui --network stt-network -p 8100:8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -v /home/stt_engine/web_ui/data:/app/data \
  -v /home/stt_engine/web_ui/logs:/app/logs \
  stt-web-ui:cuda129-rhel89-v1.0

# 4. 상태 확인
docker ps | grep stt-
```

### 접속 및 테스트

```bash
# Web UI 접속
# 브라우저: http://localhost:8100

# STT API 헬스 체크
curl http://localhost:8003/health

# 컨테이너 간 통신 테스트
docker exec stt-web-ui curl http://stt-api:8003/health
```

---

## 📊 파일 변경 요약

### 신규 파일
| 파일 | 설명 |
|------|------|
| `scripts/build-ec2-web-ui-image.sh` | Web UI 빌드 스크립트 (EC2용) |
| `web_ui/SETUP_WEB_UI.md` | 환경별 설정 및 배포 가이드 |
| `SETUP_WEB_UI.md` | 최상위 설정 문서 (참고용) |

### 수정된 파일
| 파일 | 변경사항 |
|------|----------|
| `web_ui/config.py` | WEB_PORT: 8001 → 8100 |
| `web_ui/docker/docker-compose.yml` | 독립 이미지 기반, 포트 8100 |
| `docker/docker-compose.yml` | Web UI 서비스 추가 |
| `README.md` | Web UI 섹션 추가 |
| `web_ui/README.md` | 포트 8100, Docker 네트워크 설명 |
| `docker/README.md` | Docker Compose 및 배포 흐름도 |

---

## 🔧 기술 세부사항

### Docker 네트워크 통신 방식

**내부 통신 (Docker 네트워크)**:
```
Web UI 코드:
  response = requests.get('http://stt-api:8003/health')
  
Docker 네트워크 처리:
  stt-api (호스트명)
    ↓
  Docker 내장 DNS 해석
    ↓
  172.20.0.2 (STT API 컨테이너 IP)
    ↓
  STT API 서버 (포트 8003)
```

**외부 접속**:
```
클라이언트:
  http://localhost:8100  →  Web UI 컨테이너
  http://localhost:8003  →  STT API 컨테이너
```

### 버전 관리 형식

```
이미지명: {서비스}:{CUDA}_{RHEL}_{버전}
예시: stt-web-ui:cuda129-rhel89-v1.0

구성 요소:
- stt-web-ui: 서비스명
- cuda129: CUDA 12.9
- rhel89: RHEL 8.9
- v1.0: 버전
```

### 환경 변수

**Web UI**:
| 변수 | 기본값 | 설명 |
|------|--------|------|
| `STT_API_URL` | `http://localhost:8003` | STT API 주소 |
| `WEB_PORT` | `8100` | Web UI 포트 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |

**STT API**:
| 변수 | 기본값 | 설명 |
|------|--------|------|
| `STT_DEVICE` | `cpu` | 디바이스 (cpu/cuda) |
| `STT_COMPUTE_TYPE` | `default` | 컴퓨트 타입 |
| `API_PORT` | `8003` | API 포트 |

---

## 📚 참고 문서

### 메인 문서
- [README.md](README.md) - 프로젝트 개요 및 Web UI 배포
- [web_ui/README.md](web_ui/README.md) - Web UI 기능 및 빠른 시작
- [web_ui/SETUP_WEB_UI.md](web_ui/SETUP_WEB_UI.md) - **상세 설정 가이드** (MacBook/EC2/RHEL)

### Docker 관련
- [docker/README.md](docker/README.md) - Docker 설정 및 배포 흐름
- [docker/docker-compose.yml](docker/docker-compose.yml) - 로컬 개발 설정
- [web_ui/docker/docker-compose.yml](web_ui/docker/docker-compose.yml) - 프로덕션 참고용

### 빌드 스크립트
- [scripts/build-ec2-web-ui-image.sh](scripts/build-ec2-web-ui-image.sh) - Web UI 빌드
- [scripts/build-ec2-engine-image.sh](scripts/build-ec2-engine-image.sh) - STT Engine 빌드

---

## ✨ 주요 특징

### 1. 환경별 최적화
- **MacBook**: 빠른 개발 + 즉시 테스트
- **EC2**: 프로덕션 환경과 동일한 빌드
- **RHEL**: 안정적인 배포

### 2. Docker 네트워크 활용
- 브릿지 네트워크로 컨테이너 자동 연결
- DNS 기반 서비스 디스커버리
- 포트 충돌 방지

### 3. 버전 관리
- 동일한 버전 스키마 사용
- 쉬운 롤백 및 업데이트
- 명확한 배포 추적

### 4. 완전한 문서화
- 환경별 실행 방법
- 트러블슈팅 가이드
- 네트워크 통신 설명

---

## 🎯 다음 단계 (선택사항)

### 즉시 테스트
```bash
# 로컬에서 docker-compose 테스트
cd /Users/a113211/workspace/stt_engine
docker-compose up

# 접속 확인
curl http://localhost:8100/health
```

### EC2 빌드 준비
```bash
# EC2 인스턴스에서 실행
bash scripts/build-ec2-web-ui-image.sh v1.0

# 빌드 확인
docker images | grep stt-web-ui
```

### RHEL 배포 준비
```bash
# docker-compose.yml 수정하여 배포
# 또는 독립 docker run 명령어 사용
```

---

## ✅ 검증 체크리스트

- [x] Web UI 포트 변경 (8001 → 8100)
- [x] 독립 Docker 컨테이너 아키텍처
- [x] Docker 브릿지 네트워크 구성
- [x] Web UI 빌드 스크립트 생성
- [x] 환경별 설정 가이드 작성
- [x] README 업데이트
- [x] Docker Compose 구성

---

## 📞 문제 해결

### Web UI가 API에 연결되지 않음
```bash
# 1. 네트워크 확인
docker network inspect stt-network

# 2. DNS 해석 확인
docker exec stt-web-ui nslookup stt-api

# 3. 통신 테스트
docker exec stt-web-ui curl http://stt-api:8003/health
```

### 포트 충돌
```bash
# 포트 확인
lsof -i :8100
lsof -i :8003

# 환경변수로 포트 변경
export WEB_PORT=8101
```

### 빌드 실패
```bash
# 빌드 로그 확인
cat /tmp/build-web-ui-*.log

# Docker 디스크 공간 확인
docker system df
```

---

**완료 일시**: 2026-02-02  
**상태**: ✅ 완료 및 배포 준비 완료  
**다음 단계**: EC2에서 빌드 테스트 → RHEL 배포
