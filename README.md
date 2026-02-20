# 🎙️ STT Engine (Speech-to-Text)

**Language**: English | [한국어](README_KO.md)

OpenAI Whisper 기반 실시간 음성-텍스트 변환 엔진

## � 문서

**STT Engine 워크플로우 개선 (Phase 1-5)**: 
- **[docs/01_WORKFLOW_IMPLEMENTATION_PLAN.md](docs/01_WORKFLOW_IMPLEMENTATION_PLAN.md)** - 설계 및 계획
- **[docs/02_WORKFLOW_IMPLEMENTATION_COMPLETE.md](docs/02_WORKFLOW_IMPLEMENTATION_COMPLETE.md)** - 구현 완료
- **[docs/03_WORKFLOW_PROJECT_COMPLETION_REPORT.md](docs/03_WORKFLOW_PROJECT_COMPLETION_REPORT.md)** - 최종 보고서

**API 가이드**:
- **[QUICKSTART.md](QUICKSTART.md)** - 5분 안에 시작하기
- **[docs/API_USAGE_GUIDE.md](docs/API_USAGE_GUIDE.md)** - API 엔드포인트 상세 가이드 ⭐ NEW
- **[docs/API_SERVER_RESTRUCTURING_GUIDE.md](docs/API_SERVER_RESTRUCTURING_GUIDE.md)** - 서버 구조 설명

**배포 및 아키텍처**:
- **[docs/README_KO.md](docs/README_KO.md)** - 전체 문서 가이드
- **[docs/deployment/](docs/deployment/)** - 배포 및 설치 가이드
- **[docs/architecture/](docs/architecture/)** - 아키텍처 및 모델 정보

## �📋 빠른 시작

### 1️⃣ 로컬 개발 (macOS/Linux)

```bash
# 환경 설정
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# API 서버 시작
python3.11 api_server.py

# 테스트 (다른 터미널)
curl http://localhost:8003/health
```

### 2️⃣ Linux 서버 배포

```bash
# 로컬에서: 배포 패키지 전송
scp -r deployment_package/ user@server:/home/user/stt_engine/

# 서버에서: 배포 실행
ssh user@server
cd /home/user/stt_engine/deployment_package
./deploy.sh

# 서버: API 시작
python3.11 api_server.py
```

### 3️⃣ EC2 배포 (권장! ⭐)

EC2 인스턴스에서 한 번에 모델 준비 + 엔진 빌드:

```bash
# EC2 접속
ssh -i your-key.pem ec2-user@your-ec2-ip

# 1단계: 모델 다운로드 및 준비 (10-20분)
bash scripts/ec2_prepare_model.sh

# 2단계: Docker 이미지 빌드 (5-10분)
bash scripts/build-ec2-engine-image.sh

# 3단계: 실행
docker run -p 8003:8003 -v $(pwd)/models:/app/models stt-engine:latest
```

**특징:**
- ✅ 상대 경로 심링크로 Docker/운영 경로 모두 호환
- ✅ 자동 진단 및 복구 기능 포함
- ✅ model.bin 파일 자동 생성
- ✅ Python 3.11 검증

### 4️⃣ Docker 배포 (로컬 빌드)

```bash
# 로컬: Docker 이미지 빌드 (1.2GB)
bash scripts/build-ec2-engine-image.sh

# 로컬: tar 파일로 저장됨 (build/output/)

# 서버: 이미지 로드 및 실행
docker load -i stt-engine-linux-x86_64.tar
docker run -p 8003:8003 stt-engine:linux-x86_64
```
### 5️⃣ Web UI 대시보드 (독립 컨테이너) 

Web UI는 STT API와 별도의 Docker 컨테이너로 실행됩니다:

```bash
# 1단계: Docker 네트워크 생성 (처음 한 번만)
docker network create stt-network

# 2단계: Web UI 이미지 빌드 (EC2에서)
bash scripts/build-ec2-web-ui-image.sh v1.0

# 3단계: 두 서비스 동시 실행
# 터미널 1: STT API
docker run -d --name stt-api --network stt-network -p 8003:8003 \
  -e STT_DEVICE=cuda -e STT_COMPUTE_TYPE=int8 \
  -v $(pwd)/models:/app/models \
  stt-engine:cuda129-rhel89-v1.0

# 터미널 2: Web UI
docker run -d --name stt-web-ui --network stt-network -p 8100:8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -v $(pwd)/web_ui/data:/app/data \
  stt-web-ui:cuda129-rhel89-v1.0

# 4단계: 접속
# 🌐 Web UI: http://localhost:8100
# 📡 API: http://localhost:8003
```

**Docker 네트워크 통신:**
- Web UI와 STT API는 `stt-network` 브릿지 네트워크로 통신
- Web UI → API 내부 URL: `http://stt-api:8003` (DNS 자동 해석)
- 외부 접속: `http://localhost:8003` (API), `http://localhost:8100` (Web UI)

**또는 Docker Compose 사용:**

```bash
# web_ui/docker/docker-compose.yml 사용
cd web_ui/docker
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

📖 **자세한 가이드**: [web_ui/SETUP_WEB_UI.md](web_ui/SETUP_WEB_UI.md)
---

## � REST API 사용 가이드

### 빠른 예시

```bash
# 1️⃣ 로컬 파일 처리 (권장!)
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test.wav' \
  -F 'language=ko'

# 2️⃣ 파일 업로드
curl -X POST http://localhost:8003/transcribe_by_upload \
  -F 'file=@/Users/user/audio.wav' \
  -F 'language=ko'

# 3️⃣ 헬스 체크
curl http://localhost:8003/health | jq
```

### 응답 예시 (v1.1+)

```json
{
  "success": true,
  "text": "안녕하세요. 어떻게 도와드릴까요?",
  "language": "ko",
  "duration": 2.5,
  "backend": "faster-whisper",
  "file_size_mb": 0.015,
  "processing_time_seconds": 1.23,
  "processing_mode": "normal",
  "segments_processed": 1,
  "memory_info": {
    "available_mb": 14000,
    "used_percent": 10.5
  },
  "performance": {
    "cpu_percent_avg": 45.3,
    "cpu_percent_max": 78.2,
    "ram_mb_avg": 2048.5,
    "ram_mb_peak": 3072.0,
    "gpu_vram_mb_current": 4096.0,
    "gpu_vram_mb_peak": 5120.0,
    "gpu_percent": 89.5,
    "processing_time_sec": 1.23
  }
}
```

### 주요 기능

✅ **3가지 엔드포인트**
- `POST /transcribe` - 로컬 파일 경로 기반 (권장)
- `POST /transcribe_by_upload` - 파일 업로드 기반
- `GET /health` - 서버 상태 확인

✅ **2가지 처리 모드**
- **일반 모드**: 빠른 처리, 메모리 사용 (< 1GB 파일)
- **스트리밍 모드**: 메모리 효율적, 느린 처리 (무제한 파일)

✅ **언어 지원**
- 기본: 한국어 (ko)
- 지원: 영어(en), 일본어(ja), 중국어(zh) 등

✅ **성능 모니터링 (v1.1+)**
- **CPU 추적**: 평균/최대 사용률 (%)
- **메모리 추적**: 평균/최대 사용량 (MB)
- **GPU 추적**: VRAM 사용량, GPU 활용도 (%)
- **자동 로깅**: 처리 완료 후 자동 저장
- **웹 UI 시각화**: 대시보드 및 배치 작업 성능 지표 표시

📖 **자세한 가이드**: [docs/API_USAGE_GUIDE.md](docs/API_USAGE_GUIDE.md)

---

## �📂 프로젝트 구조

```
stt_engine/
├── 📖 docs/                          # 모든 문서
│   ├── INDEX.md                      # 📍 문서 시작점
│   ├── QUICKSTART.md                 # 5분 빠른 시작
│   ├── FINAL_STATUS.md               # 프로젝트 현황
│   ├── DEPLOYMENT_READY.md           # 배포 준비
│   ├── architecture/                 # 기술 문서
│   ├── deployment/                   # 배포 가이드
│   └── guides/                       # 각종 가이드
│
├── 📦 deployment_package/            # 배포용 패키지
│   ├── wheels/                       # 59개 wheel 파일 (413MB)
│   ├── deploy.sh                     # ⭐ 메인 배포 스크립트
│   ├── setup_offline.sh              # 수동 설치
│   ├── run_all.sh                    # 서비스 실행
│   ├── START_HERE.sh                 # 배포 시작 가이드
│   └── requirements.txt              # 패키지 목록
│
├── 🐳 docker/                        # Docker 설정
│   ├── Dockerfile.engine             # STT Engine 이미지
│   ├── Dockerfile.wheels-download    # Wheel 다운로드 이미지
│   ├── docker-compose.yml            # 다중 컨테이너 설정
│   └── ...                           # 기타 Dockerfile
│
├── 🛠️  scripts/                       # 개발/빌드 스크립트
│   ├── ec2_prepare_model.sh          # 🆕 EC2 모델 준비 (권장)
│   ├── build-ec2-engine-image.sh     # Docker 이미지 빌드 (EC2용)
│   ├── setup.sh                      # 초기 설정
│   ├── models/
│   │   ├── download/                 # 🆕 모델 다운로드 (4개 스크립트)
│   │   ├── convert/                  # 🆕 모델 변환 (5개 스크립트)
│   │   └── validate/                 # 🆕 모델 검증 (5개 스크립트)
│   └── analysis/                     # 🆕 분석/디버깅 (3개 스크립트)
│
├── 🏗️  build/                        # 빌드 산출물
│   └── output/                       # Docker tar 파일
│
├── ⚙️  모델 및 데이터
│   ├── models/                       # 다운로드된 모델
│   ├── audio/                        # 테스트 오디오
│   └── wheels/                       # 휠 캐시
│
├── 📄 서비스 (Production)
│   ├── main.py                       # ⭐ 애플리케이션 진입점
│   ├── stt_engine.py                 # ⭐ STT 엔진 코어
│   ├── api_server.py                 # ⭐ FastAPI 서버
│   ├── api_client.py                 # ⭐ API 클라이언트
│   ├── model_manager.py              # ⭐ 모델 관리 유틸
│   └── download_model_hf.py          # ⭐ 모델 다운로드 (메인)
│
└── ⚙️  설정 파일
    ├── requirements.txt              # 의존성
    ├── pyproject.toml                # 프로젝트 설정
    ├── README.md                     # 이 파일
    ├── README_KO.md                  # 한국어 버전
    └── .env                          # 환경변수 (선택사항)
```

---

## 🚀 배포 방법

| 방법 | 시간 | 권장 | 명령 |
|------|------|------|------|
| **EC2 (원클릭)** | 15-30분 | ⭐⭐⭐⭐⭐ | `bash scripts/ec2_prepare_model.sh && bash scripts/build-ec2-engine-image.sh` |
| **오프라인** | 5-10분 | ⭐⭐⭐⭐ | `cd deployment_package && ./deploy.sh` |
| **Docker** | 10-20분 | ⭐⭐⭐ | `bash scripts/build-ec2-engine-image.sh` |
| **개발 환경** | 5분 | ⭐⭐⭐⭐ | `pip install -r requirements.txt` |

---

## 📚 문서

### 🎯 시작하기
- **[docs/INDEX.md](docs/INDEX.md)** ← 📍 문서 시작점
- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - 5분 빠른 시작
- **[docs/FINAL_STATUS.md](docs/FINAL_STATUS.md)** - 현재 상태

### 📋 배포 가이드
- **[docs/DEPLOYMENT_READY.md](docs/DEPLOYMENT_READY.md)** - 배포 준비 사항
- **[docs/deployment/](docs/deployment/)** - 상세 배포 가이드
- **[deployment_package/START_HERE.sh](deployment_package/START_HERE.sh)** - 배포 시작

### 🔧 기술 문서
- **[docs/architecture/](docs/architecture/)** - 모델 구조 및 최적화
- **[docs/guides/](docs/guides/)** - 설정 및 마이그레이션

---

## 🎓 기술 스펙

| 항목 | 정보 |
|------|------|
| **모델** | OpenAI Whisper Large v3 Turbo |
| **프레임워크** | PyTorch 2.1.2 |
| **API** | FastAPI 0.109.0 |
| **Python** | 3.11.5 |
| **플랫폼** | Linux x86_64, macOS |
| **GPU 지원** | NVIDIA CUDA 12.1/12.9 |

---

## 📊 주요 기능

✅ **실시간 음성 인식**
- 44.1kHz 오디오 지원
- 다양한 오디오 포맷 (WAV, MP3, M4A 등)

✅ **API 서버**
- FastAPI 기반 REST API
- 헬스 체크 및 통계 엔드포인트
- 비동기 처리 지원

✅ **오프라인 배포**
- 인터넷 없이 Linux 서버에 배포 가능
- 사전 다운로드된 휠 파일 (413MB)

✅ **Docker 지원**
- Docker 이미지 자동 빌드
- 일관된 환경 보장

---

## ⚡ 성능

| 항목 | 사양 |
|------|------|
| **메모리 (CPU)** | 2-4GB |
| **메모리 (GPU)** | 6-8GB |
| **디스크** | 2GB+ |
| **추론 속도** | ~5-10초/분 |

---

## 🔧 설정

### 환경 변수

```bash
# .env 파일
HF_HOME=/path/to/models
LOG_LEVEL=INFO
API_PORT=8003
CUDA_VISIBLE_DEVICES=0  # GPU 선택 (선택사항)
```

### 시스템 요구사항

**최소 요구사항:**
- Python 3.11.5
- 2GB RAM
- 2GB Disk

**권장 사양:**
- Python 3.11.5
- 8GB RAM (4GB CPU, 8GB GPU)
- SSD 디스크

**GPU 사용 (선택사항):**
- NVIDIA GPU (CUDA Compute Capability 3.5+)
- NVIDIA Driver 575+
- CUDA 12.1 or 12.9
- cuDNN

---

## 📖 상세 가이드

### 로컬 개발

```bash
# 1. 저장소 클론
git clone <repo>
cd stt_engine

# 2. 가상 환경 생성
python3.11 -m venv venv
source venv/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. API 서버 시작
python3.11 api_server.py

# 5. 테스트 (다른 터미널)
curl http://localhost:8003/health
```

### Linux 서버 배포

[docs/DEPLOYMENT_READY.md](docs/DEPLOYMENT_READY.md) 참고

### Docker 배포

[docs/deployment/DEPLOYMENT_GUIDE.md](docs/deployment/DEPLOYMENT_GUIDE.md) 참고

---

## 🐛 문제 해결

| 문제 | 해결책 |
|------|--------|
| API 시작 안 됨 | 모델 다운로드 대기 (1-2분) 확인 |
| 메모리 부족 | CPU 모드 사용 또는 메모리 증설 |
| GPU 인식 안 됨 | `nvidia-smi` 명령으로 드라이버 확인 |
| 포트 충돌 | `API_PORT` 환경변수 변경 |

더 자세한 내용은 [docs/](docs/) 참고

---

## 📞 지원

- **문서**: [docs/INDEX.md](docs/INDEX.md)
- **이슈**: GitHub Issues
- **논의**: GitHub Discussions

---

## 📄 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 🙏 감사의 말

- OpenAI (Whisper 모델)
- Meta (PyTorch)
- Hugging Face (Transformers)

---

**버전**: 1.0.0  
**마지막 업데이트**: 2026-02-02  
**상태**: ✅ 배포 준비 완료
