# 프로젝트 구조 정리 가이드

## 📊 점검 결과

### ✅ 완료된 작업

1. **문서 디렉토리 구조 생성**
   - `docs/guides/` - 사용 가이드
   - `docs/architecture/` - 기술 문서
   - `docs/deployment/` - 배포 가이드

2. **README.md 개선**
   - 명확한 구조 안내
   - 빠른 시작 가이드 포함
   - 문서 계층화

3. **PROJECT_STRUCTURE.md 생성**
   - 전체 프로젝트 맵
   - 파일별 설명
   - 정책 명시

---

## 🗂️ 권장 정리 작업

### 현재 상태 (문제점)
```
루트 디렉토리:
├── CODE_FIXES_APPLIED.md     ← 과정 기록
├── CODE_REVIEW.md            ← 과정 기록
├── DEPLOYMENT.md             ← 배포 문서
├── MODEL_COMPRESSION.md      ← 모델 관련
├── MODEL_COMPRESSION_QUICKSTART.md
├── MODEL_MIGRATION_SUMMARY.md
├── MODEL_STRUCTURE.md
├── VLLM_ANSWER.md           ← 과정 기록
├── VLLM_CONFIG_SIMPLE.md
├── VLLM_QUICKSTART.md
├── VLLM_SETUP.md
├── SETUP_COMPLETE.md        ← 과정 기록
└── Dockerfile*              ← Docker 파일들
```

**문제:** 마크다운 파일이 너무 많고 비체계적임

### 목표 상태 (정리 후)
```
루트 디렉토리:
├── README.md                 ✅ (핵심 진입점)
├── QUICKSTART.md             ✅ (5분 시작)
├── PROJECT_STRUCTURE.md      ✅ (구조 설명)
├── .env.example              ✅ (설정 템플릿)
│
├── docs/                     📚 (모든 문서)
│   ├── guides/
│   │   ├── QUICKSTART_LOCAL.md
│   │   ├── QUICKSTART_DOCKER.md
│   │   └── API_USAGE.md
│   ├── architecture/
│   │   ├── ARCHITECTURE.md
│   │   ├── MODEL_STRUCTURE.md
│   │   ├── API_SPEC.md
│   │   └── PERFORMANCE.md
│   └── deployment/
│       ├── LINUX_DEPLOYMENT.md
│       ├── DOCKER_DEPLOYMENT.md
│       └── VLLM_SETUP.md
│
├── docker/                   🐳 (Docker 파일)
│   ├── Dockerfile
│   ├── Dockerfile.gpu
│   ├── Dockerfile.compressed
│   ├── docker-compose.yml
│   ├── docker-compose.vllm.yml
│   └── docker-compose.modes.txt
│
├── scripts/                  🔧 (유틸리티 스크립트)
│   ├── setup.sh
│   ├── download-model.sh
│   └── migrate-to-gpu-server.sh
│
├── 코드 파일 (루트)
│   ├── stt_engine.py
│   ├── api_server.py
│   ├── api_client.py
│   └── ... (기타 .py)
│
├── deployment_package/       🚀 (배포 패키지)
│
├── models/                   🤖
├── audio/                    🔊
├── logs/                     📝
│
├── 설정 파일
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── .gitignore
│
└── ARCHIVE/                  📦 (과정 기록)
    ├── CODE_FIXES_APPLIED.md
    ├── CODE_REVIEW.md
    ├── SETUP_COMPLETE.md
    └── ... (참고용만)
```

---

## 🎯 이동/정리 계획

### 1단계: 과정 기록 파일 ARCHIVE화

**이동할 파일:**
- `CODE_FIXES_APPLIED.md` → `ARCHIVE/`
- `CODE_REVIEW.md` → `ARCHIVE/`
- `SETUP_COMPLETE.md` → `ARCHIVE/`
- `VLLM_ANSWER.md` → `ARCHIVE/`

**이유:** 프로젝트 진행 기록일 뿐, 사용자가 봐야 할 내용이 아님

### 2단계: 기술 문서를 docs/로 이동

**이동할 파일:**
- `MODEL_STRUCTURE.md` → `docs/architecture/MODEL_STRUCTURE.md`
- `DEPLOYMENT.md` → `docs/deployment/LINUX_DEPLOYMENT.md` (수정 후)
- `VLLM_SETUP.md` → `docs/deployment/VLLM_SETUP.md` (수정 후)
- `VLLM_QUICKSTART.md` → `docs/deployment/` (통합)
- `VLLM_CONFIG_SIMPLE.md` → `docs/deployment/` (통합)
- `MODEL_COMPRESSION_QUICKSTART.md` → `docs/deployment/` (참고)
- `MODEL_MIGRATION_SUMMARY.md` → `docs/deployment/` (참고)
- `MODEL_COMPRESSION.md` → `docs/architecture/` (참고)

### 3단계: Docker 파일을 docker/로 이동

**이동할 파일:**
- `Dockerfile` → `docker/`
- `Dockerfile.gpu` → `docker/`
- `Dockerfile.compressed` → `docker/`
- `docker-compose.yml` → `docker/`
- `docker-compose.vllm.yml` → `docker/`
- `docker-compose.modes.txt` → `docker/`

### 4단계: 스크립트를 scripts/로 이동

**이동할 파일:**
- `setup.sh` → `scripts/`
- `download-model.sh` → `scripts/`
- `migrate-to-gpu-server.sh` → `scripts/`
- `download_model.py` → scripts/또는 루트 유지 (선택)

---

## 📋 파일 정책

### 루트에 유지 (5-7개만)
✅ **README.md** - 프로젝트 소개, 빠른 시작, 진입점
✅ **QUICKSTART.md** - 5분 시작 가이드
✅ **PROJECT_STRUCTURE.md** - 전체 구조 설명
✅ **.env.example** - 환경 변수 템플릿
✅ **requirements.txt** - 패키지 의존성
✅ **pyproject.toml** - 프로젝트 설정
✅ **.gitignore** - Git 제외 파일

### docs/에 이동 (모든 기술 문서)
📖 **guides/** - 사용 방법
📖 **architecture/** - 설계 문서
📖 **deployment/** - 배포 가이드

### docker/에 이동
🐳 모든 Docker 관련 파일

### scripts/에 이동
🔧 모든 쉘 스크립트, 유틸리티

### ARCHIVE/에 이동
📦 과정 기록, 참고용만 사용

### deployment_package/에 유지
🚀 오프라인 배포용 독립 패키지 (내부 문서 포함)

---

## 💡 장점

1. **명확한 구조**
   - 사용자는 루트에서 필요한 파일만 봄
   - 개발자는 docs/에서 상세 정보 찾음

2. **유지보수 용이**
   - 파일들이 논리적으로 그룹화
   - 관련 파일들이 함께 위치

3. **확장성**
   - 새로운 문서/기능 추가 용이
   - 명확한 위치 가이드라인

4. **문서 네비게이션**
   - README.md에서 시작
   - QUICKSTART.md로 빠른 시작
   - PROJECT_STRUCTURE.md에서 전체 맵 확인
   - docs/에서 상세 정보

---

## 📌 다음 단계

1. `ARCHIVE/` 디렉토리 생성
2. 과정 기록 파일들 이동
3. `docker/` 디렉토리에 파일들 이동
4. `scripts/` 디렉토리에 파일들 이동
5. `docs/` 디렉토리에 기술 문서 이동
6. 각 파일의 참조 링크 업데이트
7. `.gitignore` 업데이트

---

## 📄 작성 시간

- 작성: 2026-01-30
- 상태: 계획 수립 완료
- 다음: 구조 정리 실행
