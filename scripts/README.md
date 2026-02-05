# 🛠️ Scripts 디렉토리 가이드

## 📁 디렉토리 구조

```
scripts/
├── README.md                    # 이 파일
├── models/                      # 🆕 모델 관리 스크립트
│   ├── download/               # 모델 다운로드
│   │   ├── download_model.py
│   │   ├── download_model_simple.py
│   │   ├── download_model_direct.py
│   │   └── download_hf_model.py
│   ├── convert/                # 모델 포맷 변환
│   │   ├── convert_model_ctranslate2.py
│   │   ├── convert_model_direct.py
│   │   ├── convert_final.py
│   │   ├── simple_model_convert.py
│   │   └── setup_and_convert.py
│   └── validate/               # 모델 검증
│       ├── validate_model.py
│       ├── validate_model_detailed.py
│       ├── test_model.py
│       ├── test_model_transformers.py
│       └── check_model_structure.py
│
├── analysis/                    # 🆕 분석 및 디버깅
│   ├── analyze_model_compatibility.py
│   ├── docker_model_fix_analysis.py
│   └── compress_model.py
│
├── build-engine-image.sh        # ⭐ Docker 이미지 빌드 (메인)
├── setup.sh                     # 초기 설정 스크립트
├── download-model.sh            # 모델 다운로드 (레거시)
├── migrate-to-gpu-server.sh     # GPU 서버 마이그레이션
├── download_pytorch_wheels.py   # PyTorch wheel 다운로드 (Python)
│
└── download-wheels/             # 로컬 wheel 다운로드 스크립트
    ├── download_wheels.sh
    ├── download-wheels.sh
    ├── download_wheels_macos.sh
    ├── download_wheels_3.11.sh
    ├── download_pytorch.sh
    ├── download_pytorch_manual.sh
    ├── download_all_wheels.sh
    ├── download-wheels-docker.sh
    └── download-wheels-docker-rhel89.sh
```

## 메인 스크립트

### ⭐ build-engine-image.sh (필수)
**목적**: STT Engine Docker 이미지 빌드  
**사용처**: macOS/Linux에서 Docker 이미지 생성

```bash
bash scripts/build-engine-image.sh
```

**기능**:
- Wheel 자동 감지
- 온/오프라인 Dockerfile 조건부 생성
- Docker 이미지 빌드
- tar 파일로 저장 (build/output/)

**결과**:
- `build/output/stt-engine-linux-x86_64.tar` (1.2GB)

---

### setup.sh (선택)
**목적**: 초기 개발 환경 설정

```bash
bash scripts/setup.sh
```

---

### download-model.sh (선택)
**목적**: Whisper 모델 사전 다운로드

```bash
bash scripts/download-model.sh
```

**결과**:
- `models/openai_whisper-large-v3-turbo/` 생성

---

### migrate-to-gpu-server.sh (선택)
**목적**: GPU 서버로 마이그레이션

```bash
bash scripts/migrate-to-gpu-server.sh
```

---

### download_pytorch_wheels.py (참고)
**목적**: PyTorch wheel을 Python으로 다운로드

```bash
python3.11 scripts/download_pytorch_wheels.py
```

---

## download-wheels/ (로컬 전용)

**목적**: macOS에서 Linux용 wheel 파일을 다양한 방법으로 다운로드

### 사용 가능한 스크립트

| 스크립트 | 설명 | 장점 | 단점 |
|---------|------|------|------|
| download_wheels.sh | 기본 다운로드 | 간단 | 느림 |
| download-wheels.sh | 분할 압축 다운로드 | 빠름 | 복잡 |
| download_wheels_macos.sh | macOS 최적화 | macOS 호환 | macOS만 |
| download_wheels_3.11.sh | Python 3.11 최적화 | 안정적 | 느림 |
| download_pytorch.sh | PyTorch만 | 빠름 | 불완전 |
| download_all_wheels.sh | 모든 의존성 | 완전 | 매우 느림 |
| download-wheels-docker.sh | Docker 기반 | 자동화 | Docker 필요 |
| download-wheels-docker-rhel89.sh | RHEL 8.9 최적화 | RHEL 호환 | RHEL 필요 |

### 사용 예

```bash
# 기본 방법
bash scripts/download-wheels/download_wheels.sh

# 또는 macOS에서
bash scripts/download-wheels/download_wheels_macos.sh

# 또는 Docker로 (권장)
bash scripts/download-wheels/download-wheels-docker.sh
```

**결과**:
- `deployment_package/wheels/` 에 wheel 파일 생성

---

## 권장 사용 흐름

### 1️⃣ 새 프로젝트 시작

```bash
# 1. 초기 설정
bash scripts/setup.sh

# 2. 모델 다운로드 (선택)
bash scripts/download-model.sh

# 3. 개발 환경 구성
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2️⃣ Linux 배포 준비

```bash
# 1. Docker 이미지 빌드
bash scripts/build-engine-image.sh

# 2. 결과 확인
ls -lh build/output/stt-engine-linux-x86_64.tar

# 3. 서버로 전송
scp build/output/stt-engine-linux-x86_64.tar user@server:/tmp/
scp -r deployment_package/ user@server:/home/user/
```

### 3️⃣ 서버에서 배포

```bash
# 1. tar 파일 로드
docker load -i /tmp/stt-engine-linux-x86_64.tar

# 2. 또는 직접 배포
cd deployment_package
./deploy.sh

# 3. 실행
python3.11 api_server.py
```

---

## 환경 변수

### 다운로드 스크립트에서
```bash
PYTHON_BIN=/opt/homebrew/bin/python3.11
PYTHON_VERSION=311
WHEELS_DIR=./deployment_package/wheels
```

### build-engine-image.sh에서
```bash
WORKSPACE=/Users/a113211/workspace/stt_engine
WHEELS_DIR=$WORKSPACE/deployment_package/wheels
BUILD_DIR=/tmp/stt_engine_docker
OUTPUT_DIR=$WORKSPACE
```

---

## 문제 해결

| 문제 | 해결책 |
|------|--------|
| 스크립트 실행 권한 없음 | `chmod +x scripts/*.sh` |
| Python 버전 오류 | `python3.11 --version` 확인 |
| 네트워크 오류 | Docker 다운로드 사용 |
| 디스크 부족 | wheel 파일 정리 후 재시도 |

---

## 정리 후 구조

✅ **정리된 상태**
- `build-engine-image.sh` - 메인 빌드 스크립트
- `download-wheels/` - 로컬 다운로드 옵션들
- 기본 설정 스크립트들

📝 **참고**
- 각 스크립트는 독립적으로 실행 가능
- deployment_package의 스크립트와는 다른 목적
- download-wheels는 사용 환경에 맞게 선택

---

**버전**: 1.0  
**마지막 업데이트**: 2026-02-02
