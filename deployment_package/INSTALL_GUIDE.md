# STT Engine - Linux 서버 설치 가이드

## 📋 요구사항

- **OS**: RHEL 8.9 (또는 호환 Linux)
- **Python**: 3.11.5
- **GPU**: NVIDIA (CUDA 12.1/12.9)
- **Driver**: 575.57.08 이상

## 🔧 설치 절차

### 1️⃣ 사전 준비 (Linux 서버)

```bash
# Python 3.11 설치 확인
python3.11 --version
# Python 3.11.5

# CUDA/Driver 확인
nvidia-smi
# Driver Version: 575.57.08
# CUDA Version: 12.9
```

### 2️⃣ 배포 패키지 다운로드 및 전송

**macOS 환경에서:**

```bash
# 1. Python 3.11로 기본 패키지 준비 (인터넷 필요)
cd deployment_package

# 2. 수동으로 PyTorch wheels 다운로드
mkdir -p wheels
cd wheels

# PyTorch CUDA 12.1 wheels 다운로드 (2GB 이상)
# https://download.pytorch.org/whl/cu121 에서 다음 파일 다운로드:
# - torch-2.5.1-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
# - torchaudio-2.5.1-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

# 또는 wget 사용:
wget https://download.pytorch.org/whl/cu121/torch-2.5.1-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
wget https://download.pytorch.org/whl/cu121/torchaudio-2.5.1-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

# 기타 패키지 다운로드
pip download transformers huggingface-hub librosa scipy numpy python-dotenv pydantic fastapi uvicorn requests pyyaml --only-binary=:all: --platform manylinux_2_17_x86_64 --python-version 311

cd ..
```

**Linux 서버로 전송:**

```bash
# macOS에서
scp -r deployment_package user@your-server:/tmp/

# 또는 rsync 사용
rsync -avz deployment_package/ user@your-server:/tmp/stt_deployment/
```

### 3️⃣ Linux 서버에서 설치

```bash
cd /tmp/deployment_package
# 또는 전송된 경로

# Python 3.11 venv 생성 (선택사항)
python3.11 -m venv venv
source venv/bin/activate

# wheels 디렉토리에서 설치
pip install wheels/*.whl

# 또는 개별 설치
pip install \
    wheels/torch-2.5.1-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl \
    wheels/torchaudio-2.5.1-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl \
    wheels/*.whl
```

### 4️⃣ STT Engine 설치

```bash
# 패키지 최상위 디렉토리로 이동
cd /path/to/stt_engine

# 필요한 패키지 확인
pip list

# STT Engine 설치 (offline)
pip install -e .
```

### 5️⃣ 검증

```bash
# Python에서 import 테스트
python3.11 -c "import torch; print(f'PyTorch: {torch.__version__}')"
python3.11 -c "import transformers; print('✅ Transformers OK')"
python3.11 -c "import librosa; print('✅ Librosa OK')"

# API 서버 실행
python3.11 api_server.py
# 또는
uvicorn api_server:app --host 0.0.0.0 --port 8001
```

## ⚠️ 주의사항

1. **네트워크 없음**: wheels 디렉토리의 모든 파일이 필수
2. **Python 버전**: 반드시 3.11.5 사용 (3.10 이상에서도 작동하지만 권장)
3. **CUDA 버전**: CUDA 12.1 wheels는 CUDA 12.9와 호환
4. **디스크 공간**: 최소 50GB 이상 필요 (모델 포함)
5. **메모리**: Whisper Large 실행 시 12GB+ GPU 메모리 권장

## 🐛 문제 해결

### PyTorch 설치 실패
```bash
# NVIDIA 드라이버 확인
nvidia-smi

# CUDA 호환성 확인
python -c "import torch; print(torch.cuda.is_available())"
```

### Import 에러
```bash
# 경로 확인
python -c "import sys; print(sys.path)"

# 개별 패키지 설치
pip install --no-cache-dir wheels/package-name.whl
```

### 메모리 부족
```bash
# 모델 양자화 설정
export WHISPER_DEVICE=cuda
export WHISPER_DTYPE=float16
python api_server.py
```

## 📞 추가 지원

더 자세한 내용은 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) 참고
