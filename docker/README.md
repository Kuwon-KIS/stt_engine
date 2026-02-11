# 🐳 Docker 설정 가이드

## 디렉토리 구조

```
docker/
├── README.md                 ← 여기서 시작
├── docker-compose.yml        # 다중 컨테이너 설정
│
├── 📄 핵심 Dockerfile
│   ├── Dockerfile            # 기본 설정 (개발용)
│   ├── Dockerfile.engine     # STT Engine 이미지
│   └── Dockerfile.wheels-download  # Wheel 다운로드
│
└── 📦 참고용 Dockerfile (실제 사용 안 함)
    ├── Dockerfile.compressed     # 압축 버전
    ├── Dockerfile.gpu           # GPU 지원
    ├── Dockerfile.pytorch       # PyTorch 전용
    └── ...                      # 기타 실험용
```

## 각 Dockerfile 설명

### 1. **Dockerfile.engine** (권장)
- **목적**: STT Engine 최종 프로덕션 이미지
- **크기**: ~1.2GB
- **사용처**: Linux 서버 배포
- **특징**:
  - Wheel 오프라인 설치 또는 온라인 설치 지원
  - 최소 의존성
  - 빠른 빌드 시간

```bash
docker build -t stt-engine:linux-x86_64 -f Dockerfile.engine .
```

### 2. **Dockerfile.wheels-download**
- **목적**: PyTorch wheel 파일 다운로드
- **크기**: ~2GB (이미지), 413MB (wheel 산출물)
- **사용처**: 로컬 개발 환경에서 Linux용 wheel 준비
- **특징**:
  - 네트워크 문제 해결을 위한 별도 이미지
  - 다운로드된 wheel을 호스트로 추출

```bash
docker build -t stt-wheels:latest -f Dockerfile.wheels-download .
docker create --name stt-wheels-temp stt-wheels:latest
docker cp stt-wheels-temp:/wheels/ ./deployment_package/
docker rm stt-wheels-temp
```

### 3. **Dockerfile** (기본)
- **목적**: 일반적인 개발/테스트용
- **사용처**: Docker Compose에서 사용

### 4. 기타 Dockerfile (참고용)
- `Dockerfile.gpu` - GPU 지원 버전
- `Dockerfile.pytorch` - PyTorch 최적화
- `Dockerfile.compressed` - 압축된 크기
- 등 - 실험용, 실제 배포에는 사용 안 함

---

## 빌드 스크립트

### scripts/build-engine-image.sh
- **목적**: STT Engine Docker 이미지 자동 빌드
- **기능**:
  - Wheel 자동 감지
  - 온/오프라인 설치 자동 선택
  - 이미지를 tar 파일로 저장
- **사용법**:
  ```bash
  bash scripts/build-engine-image.sh
  # → build/output/stt-engine-linux-x86_64.tar 생성
  ```

---

## Docker Compose

### 로컬 개발 (MacBook)

docker-compose.yml로 STT API와 Web UI를 한 번에 실행:

```bash
# 로컬에서 이미지 빌드하고 실행
docker-compose up

# 또는 백그라운드 실행
docker-compose up -d

# 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f stt-engine-api
docker-compose logs -f stt-web-ui

# 중지
docker-compose down
```

**접속 주소:**
- 🌐 Web UI: http://localhost:8100
- 📡 STT API: http://localhost:8003

### 프로덕션 배포 (RHEL)

프로덕션 환경에서는 **사전 빌드된 이미지**를 사용하는 것이 권장됩니다:

```bash
# 1단계: EC2에서 이미지 빌드
bash scripts/build-ec2-engine-image.sh v1.0
bash scripts/build-ec2-web-ui-image.sh v1.0

# 2단계: 이미지 로드
docker load -i stt-engine-v1.0.tar.gz
docker load -i stt-web-ui-v1.0.tar.gz

# 3단계: docker-compose.yml 수정 (이미지 지정)
version: '3.8'
services:
  stt-engine-api:
    image: stt-engine:cuda129-rhel89-v1.0  # 미리 빌드된 이미지
    ...
  stt-web-ui:
    image: stt-web-ui:cuda129-rhel89-v1.0  # 미리 빌드된 이미지
    ...

# 4단계: docker-compose로 실행
docker-compose up -d
```

**또는 독립 Docker 명령어 사용:**

```bash
# Docker 네트워크 생성
docker network create stt-network

# STT API 실행
docker run -d --name stt-api --network stt-network -p 8003:8003 \
  -e STT_DEVICE=cuda -e STT_COMPUTE_TYPE=int8 \
  -v $(pwd)/models:/app/models \
  stt-engine:cuda129-rhel89-v1.0

# Web UI 실행
docker run -d --name stt-web-ui --network stt-network -p 8100:8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -v $(pwd)/web_ui/data:/app/data \
  stt-web-ui:cuda129-rhel89-v1.0
```

더 자세한 내용은 [../web_ui/SETUP_WEB_UI.md](../web_ui/SETUP_WEB_UI.md) 참고

---

## 정리 후 권장사항

✅ **사용할 파일**
- Dockerfile.engine (STT Engine 프로덕션)
- Dockerfile.web_ui (Web UI - web_ui/docker/ 디렉토리)
- docker-compose.yml (로컬 개발)
- scripts/build-ec2-engine-image.sh (EC2 빌드)
- scripts/build-ec2-web-ui-image.sh (EC2 빌드)

⚠️ **참고만 하는 파일**
- Dockerfile.gpu
- Dockerfile.pytorch
- Dockerfile.compressed
- 기타 실험용 파일

---

## 빌드 및 배포 흐름

### 로컬 개발 (MacBook)

```
MacBook (로컬 개발)
    ↓
docker-compose up  (Dockerfile 기반 빌드)
    ↓
STT API + Web UI 실행
    ↓
http://localhost:8003 (API)
http://localhost:8100 (Web UI)
```

### 프로덕션 배포 (EC2 → RHEL)

```
MacBook (코드 개발)
    ↓
    scp → EC2
    ↓
EC2 (빌드 환경)
    ↓
bash scripts/build-ec2-engine-image.sh v1.0
bash scripts/build-ec2-web-ui-image.sh v1.0
    ↓
stt-engine:cuda129-rhel89-v1.0
stt-web-ui:cuda129-rhel89-v1.0
    ↓
    (Docker Compose 설정 또는 독립 docker run)
    ↓
RHEL 서버 (프로덕션)
    ↓
docker network create stt-network
docker run -d ... stt-api
docker run -d ... stt-web-ui
    ↓
http://server:8003 (API)
http://server:8100 (Web UI)
```

**핵심: 빌드 환경과 배포 환경 분리**
- 로컬: 빠른 개발 테스트
- EC2: 프로덕션 환경과 동일한 빌드
- RHEL: 실제 배포

---

**버전**: 1.0  
**마지막 업데이트**: 2026-02-02

