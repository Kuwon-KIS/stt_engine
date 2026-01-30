# STT Engine 프로젝트 구조

```
stt_engine/
│
├── 📖 핵심 문서 (루트)
│   ├── README.md                 ← 프로젝트 개요 (먼저 읽기)
│   ├── QUICKSTART.md             ← 빠른 시작 (5분)
│   └── .env.example              ← 환경 변수 템플릿
│
├── 📁 docs/                      ← 모든 문서
│   ├── guides/                   ← 사용 가이드
│   │   ├── QUICKSTART_LOCAL.md   ← 로컬 실행 (개발)
│   │   ├── QUICKSTART_DOCKER.md  ← Docker 실행
│   │   └── API_USAGE.md          ← API 사용법
│   │
│   ├── architecture/             ← 기술 문서
│   │   ├── ARCHITECTURE.md       ← 전체 아키텍처
│   │   ├── MODEL_STRUCTURE.md    ← 모델 구조
│   │   ├── API_SPEC.md           ← API 명세
│   │   └── PERFORMANCE.md        ← 성능 분석
│   │
│   └── deployment/               ← 배포 가이드
│       ├── LINUX_DEPLOYMENT.md   ← Linux 서버 배포
│       ├── DOCKER_DEPLOYMENT.md  ← Docker 배포
│       └── VLLM_SETUP.md         ← vLLM 설정
│
├── 📁 deployment_package/        ← 오프라인 배포 패키지
│   ├── wheels/                   ← Python 라이브러리 (2-3GB)
│   ├── deploy.sh                 ← 배포 스크립트
│   ├── QUICKSTART.md             ← 배포 빠른 시작
│   └── DEPLOYMENT_GUIDE.md       ← 배포 상세 가이드
│
├── 📁 src/ (코드)
│   ├── stt_engine.py             ← STT 엔진
│   ├── api_server.py             ← REST API 서버
│   ├── api_client.py             ← API 클라이언트
│   ├── vllm_client.py            ← vLLM 클라이언트
│   ├── model_manager.py          ← 모델 관리
│   └── download_model.py         ← 모델 다운로드
│
├── 📁 scripts/                   ← 유틸리티 스크립트
│   ├── setup.sh                  ← 초기 설정
│   ├── download-model.sh         ← 모델 다운로드
│   └── migrate-to-gpu-server.sh  ← GPU 마이그레이션
│
├── 📁 docker/                    ← Docker 설정
│   ├── Dockerfile                ← 기본 이미지
│   ├── Dockerfile.gpu            ← GPU 이미지
│   ├── Dockerfile.compressed     ← 압축 이미지
│   ├── docker-compose.yml        ← Docker Compose
│   ├── docker-compose.vllm.yml   ← vLLM Compose
│   └── docker-compose.modes.txt  ← 모드 설명
│
├── 📁 models/                    ← 모델 저장소
│   └── openai_whisper-large-v3-turbo/
│
├── 📁 audio/                     ← 테스트 오디오 파일
│
├── 📁 logs/                      ← 실행 로그
│
├── 📋 설정 파일
│   ├── pyproject.toml            ← Python 프로젝트 설정
│   ├── requirements.txt          ← 의존성
│   ├── .python-version           ← Python 버전 명시
│   ├── .env.example              ← 환경 변수 템플릿
│   └── .gitignore                ← Git 제외 파일
│
└── 📌 참고 파일 (보관)
    ├── ARCHIVED/
    │   ├── CODE_FIXES_APPLIED.md
    │   ├── CODE_REVIEW.md
    │   ├── VLLM_ANSWER.md
    │   └── ... (과정 문서들)
    └── (README에서 참조하지 않음)
```

## 파일 설명

### 루트 문서 (반드시 읽기)
- **README.md** - 프로젝트 개요, 설치, 기본 사용법
- **QUICKSTART.md** - 5분만에 시작하기

### docs/ 하위 문서

#### guides/
- **QUICKSTART_LOCAL.md** - 로컬 개발 환경
- **QUICKSTART_DOCKER.md** - Docker로 실행
- **API_USAGE.md** - HTTP API 사용 방법

#### architecture/
- **ARCHITECTURE.md** - 전체 시스템 아키텍처
- **MODEL_STRUCTURE.md** - 모델 구조
- **API_SPEC.md** - API 엔드포인트 명세
- **PERFORMANCE.md** - 성능 최적화

#### deployment/
- **LINUX_DEPLOYMENT.md** - Linux 서버 배포
- **DOCKER_DEPLOYMENT.md** - Docker 배포
- **VLLM_SETUP.md** - vLLM 설정

### deployment_package/
오프라인 배포용 독립 패키지 (내부 문서 포함)

## 추천 읽기 순서

### 신규 사용자
1. README.md (5분)
2. QUICKSTART.md (5분)
3. docs/guides/QUICKSTART_LOCAL.md (10분)

### 운영자
1. README.md (5분)
2. docs/deployment/LINUX_DEPLOYMENT.md (20분)
3. docs/deployment/DOCKER_DEPLOYMENT.md (15분)

### 개발자
1. docs/architecture/ARCHITECTURE.md (20분)
2. docs/architecture/API_SPEC.md (15분)
3. 소스코드 읽기

## 파일 정책

✅ **루트에 유지**: README, QUICKSTART, .env.example  
✅ **docs/에 이동**: 모든 가이드 및 기술 문서  
✅ **deployment_package/에 유지**: 배포 관련 독립 패키지  
✅ **ARCHIVED/에 이동**: 과정 기록 (CODE_FIXES_APPLIED 등)  
✅ **src/에 이동**: 모든 Python 코드  
✅ **docker/에 이동**: 모든 Docker 파일  
✅ **scripts/에 이동**: 모든 쉘 스크립트
