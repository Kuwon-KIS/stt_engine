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

**docker-compose.yml**: 다중 컨테이너 설정

```yaml
version: '3.8'

services:
  stt-engine:
    build:
      context: .
      dockerfile: Dockerfile.engine
    ports:
      - "8003:8003"
    environment:
      - HF_HOME=/app/models
    volumes:
      - ./models:/app/models
    restart: unless-stopped
```

---

## 정리 후 권장사항

✅ **사용할 파일**
- Dockerfile.engine (프로덕션)
- Dockerfile.wheels-download (wheel 준비)
- docker-compose.yml (테스트)

⚠️ **참고만 하는 파일**
- Dockerfile.gpu
- Dockerfile.pytorch
- Dockerfile.compressed
- 기타 실험용 파일

---

## 빌드 및 배포 흐름

```
로컬 (macOS)
  ↓
scripts/build-engine-image.sh
  ↓
docker build -f Dockerfile.engine
  ↓
build/output/stt-engine-linux-x86_64.tar (1.2GB)
  ↓
scp → Linux 서버
  ↓
docker load -i stt-engine-linux-x86_64.tar
  ↓
docker run -p 8003:8003 stt-engine:linux-x86_64
```

---

**버전**: 1.0  
**마지막 업데이트**: 2026-02-02
