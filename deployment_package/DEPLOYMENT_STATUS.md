# 🚀 STT Engine - RHEL 8.9 오프라인 배포 가이드 (최종)

## 📋 현재 배포 준비 상태

### ✅ 완료된 항목
- **faster-whisper 의존성**: 52개 wheel 파일 다운로드 완료
- **압축 파일**: `wheels-all.tar.gz` (212MB) 생성 완료
- **배포 구조**: 모든 필요한 스크립트 및 가이드 준비 완료

### ⏳ 나중에 추가할 항목
- **PyTorch 2.x + torchaudio**: 다른 네트워크 환경에서 다운로드 예정

---

## 📦 배포 파일 위치 및 구조

```
stt_engine/
└── deployment_package/
    ├── wheels/                          # Wheels 저장 디렉토리
    │   ├── *.whl                        # 52개 패키지 wheel 파일
    │   ├── wheels-all.tar.gz            # 모든 wheel 압축 파일 (212MB)
    │   └── [PyTorch wheels 추가 예정]   # 나중에 추가될 위치
    │
    ├── INSTALL_GUIDE.md                 # 설치 방법 상세 가이드
    ├── SPLIT_WHEELS_README.md           # 분할 압축 파일 안내
    ├── requirements.txt                 # Python 패키지 목록
    ├── download-wheels.sh               # 모든 wheels 다운로드 스크립트
    ├── Dockerfile.wheels-download       # Docker 기반 wheels 다운로드 Dockerfile
    └── [기타 보조 스크립트들]
```

---

## 🔧 PyTorch 별도 다운로드 절차

### Step 1: PyTorch 다운로드 (다른 네트워크에서)

다음 스크립트를 실행하여 PyTorch wheels를 다운로드합니다:

```bash
# 다른 네트워크가 가능한 환경에서:
cd deployment_package/wheels

# PyTorch 2.4.1 + torchaudio (CUDA 12.4, 권장)
python3.11 -m pip download \
    torch==2.4.1 \
    torchaudio==2.4.1 \
    --only-binary=:all: \
    --platform manylinux_2_17_x86_64 \
    --python-version 311 \
    --index-url https://download.pytorch.org/whl/cu124 \
    -d .

# 또는 PyTorch 2.1.2 + torchaudio (CUDA 12.1)
python3.11 -m pip download \
    torch==2.1.2 \
    torchaudio==2.1.2 \
    --only-binary=:all: \
    --platform manylinux_2_17_x86_64 \
    --python-version 311 \
    --index-url https://download.pytorch.org/whl/cu121 \
    -d .
```

### Step 2: 전체 wheels 재압축 (PyTorch 포함)

```bash
cd deployment_package/wheels

# 기존 압축 파일 제거
rm -f wheels-all.tar.gz

# 모든 wheel 파일 재압축 (PyTorch 포함)
tar -czf wheels-all.tar.gz *.whl

# 분할 압축 필요시 (>900MB)
split -b 900m wheels-all.tar.gz "wheels-part-"
i=1
for file in $(ls -1 wheels-part-* 2>/dev/null | sort); do
    mv "$file" "wheels-part$(printf %02d $i).tar.gz"
    ((i++))
done
```

---

## 🚚 RHEL 8.9 서버에 배포하는 방법

### 전송 (macOS → RHEL 서버)

```bash
# 전체 deployment_package 디렉토리 전송
scp -r deployment_package/ user@rhel-server:/opt/stt/

# 또는 tar로 압축 후 전송 (더 빠름)
tar -czf stt_deployment.tar.gz deployment_package/
scp stt_deployment.tar.gz user@rhel-server:/opt/
ssh user@rhel-server "cd /opt && tar -xzf stt_deployment.tar.gz"
```

### 서버에서 설치

#### 1단계: wheels 압축 해제

```bash
cd /opt/stt/deployment_package/wheels

# 단일 파일인 경우
tar -xzf wheels-all.tar.gz

# 분할 파일인 경우
cat wheels-part*.tar.gz | tar -xzf -
```

#### 2단계: Python 3.11 환경 준비

```bash
# RHEL 8.9에 Python 3.11 설치 (필요한 경우)
sudo yum install python3.11 python3.11-devel python3.11-pip

# pip 업그레이드
python3.11 -m pip install --upgrade pip
```

#### 3단계: wheels 설치

```bash
cd /opt/stt/deployment_package/wheels

# 오프라인 모드로 설치 (인터넷 불필요)
python3.11 -m pip install --no-index --find-links=. *.whl

# 또는 requirements.txt 기반 설치
python3.11 -m pip install --no-index --find-links=. -r ../requirements.txt
```

---

## ✅ 설치 검증

```bash
# Python 패키지 확인
python3.11 -c "import faster_whisper; print('✅ faster-whisper 설치됨')"
python3.11 -c "import torch; print(f'✅ PyTorch {torch.__version__} 설치됨')"
python3.11 -c "import fastapi; print('✅ FastAPI 설치됨')"

# 전체 의존성 확인
python3.11 -m pip list | grep -E "torch|faster-whisper|fastapi"
```

---

## 📊 현재 wheels 파일 목록 (52개)

### 다운로드된 패키지
- **faster-whisper**: 1.0.3
- **librosa**: 0.10.0 + 의존성
- **numpy**: 1.24.3
- **scipy**: 1.12.0
- **fastapi**: 0.109.0
- **uvicorn**: 0.27.0
- **huggingface-hub**: 0.21.4
- **pydantic**: 2.5.3
- **requests**: 2.31.0
- **python-dotenv**: 1.0.0
- **pyyaml**: 6.0.1
- **기타 의존성**: ctranslate2, onnxruntime, 등 27개

### 추가될 패키지 (다운로드 예정)
- **torch**: 2.4.1 또는 2.1.2
- **torchaudio**: 2.4.1 또는 2.1.2

---

## 🔗 사용 가능한 Docker 이미지

Docker 환경에서 wheels를 다시 다운로드해야 하는 경우:

```bash
# Dockerfile.wheels-download를 사용한 빌드
docker build -f deployment_package/Dockerfile.wheels-download \
             -t stt-wheels-downloader:latest \
             -C deployment_package .

# 컨테이너 실행으로 wheels 다운로드
docker run --rm \
    -v /Users/a113211/workspace/stt_engine/deployment_package/wheels:/wheels \
    stt-wheels-downloader:latest
```

---

## 📝 체크리스트

### 현재 단계
- [x] faster-whisper + 의존성 wheels 다운로드 완료 (52개)
- [x] 압축 파일 생성 완료 (wheels-all.tar.gz, 212MB)
- [x] 배포 가이드 작성 완료
- [ ] **PyTorch wheels 다운로드** (다른 네트워크에서 진행)
- [ ] 전체 wheels 재압축 (PyTorch 포함)
- [ ] RHEL 8.9 서버로 전송
- [ ] 서버에서 설치 및 검증

### 완료 후
- [ ] `python3.11 -c "import faster_whisper"` 정상 실행
- [ ] `python3.11 -c "import torch"` 정상 실행
- [ ] API 서버 시작 확인: `python api_server.py`
- [ ] curl로 health check 확인: `curl http://localhost:8003/health`

---

## 🆘 문제 해결

### PyTorch 다운로드 실패 시

```bash
# 사용 가능한 버전 확인
python3.11 -m pip index versions torch --index-url https://download.pytorch.org/whl/cu124

# 또는 CUDA 12.9 호환 버전 사용
python3.11 -m pip download \
    torch==2.4.1 \
    torchaudio==2.4.1 \
    --index-url https://download.pytorch.org/whl/cu124
```

### wheels 설치 시 충돌 발생

```bash
# 기존 pip 캐시 제거
python3.11 -m pip cache purge

# 의존성 재분석하여 설치
python3.11 -m pip install --no-index --find-links=. \
    --no-deps \
    torch torchaudio faster-whisper fastapi uvicorn
```

---

## 📚 관련 가이드

- [INSTALL_GUIDE.md](./INSTALL_GUIDE.md) - 상세 설치 가이드
- [SPLIT_WHEELS_README.md](./SPLIT_WHEELS_README.md) - 분할 압축 파일 안내
- [requirements.txt](./requirements.txt) - 전체 패키지 목록

