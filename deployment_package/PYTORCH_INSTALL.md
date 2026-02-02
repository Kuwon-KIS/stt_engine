# PyTorch 설치 가이드

## 📌 현재 상황

**배포 패키지에 포함된 것:**
- ✅ 일반 패키지 44개 (wheels/ 디렉토리)
- ❌ PyTorch wheels (수동 다운로드 필요)

**필요한 것:**
- torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
- torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

---

## 🔧 설치 방법 3가지

### 방법 1️⃣: wheels에 PyTorch 포함 (권장 - 완전 오프라인)

**macOS에서 (인터넷 있는 곳):**

```bash
cd deployment_package/wheels

# PyTorch CUDA 12.1 wheels 다운로드
wget https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
wget https://download.pytorch.org/whl/cu121/torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

# 또는 curl 사용:
curl -O https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
curl -O https://download.pytorch.org/whl/cu121/torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

# wheels 디렉토리에 파일 확인
ls -lh | grep -E "(torch|audio)"
```

**Linux 서버에서:**

```bash
cd deployment_package

# 모든 wheels 일괄 설치 (PyTorch 포함)
pip install wheels/*.whl

# 또는 명시적으로:
pip install wheels/torch-2.2.0-cp311-*.whl \
            wheels/torchaudio-2.2.0-cp311-*.whl \
            wheels/transformers-*.whl \
            wheels/*.whl
```

---

### 방법 2️⃣: 온라인에서 PyTorch만 설치 (부분 오프라인)

**Linux 서버에서 (인터넷 필요):**

```bash
source venv/bin/activate

# Step 1: 기타 패키지 먼저 설치 (오프라인)
cd deployment_package
pip install wheels/*.whl --no-deps

cd ..

# Step 2: PyTorch 온라인 설치 (인터넷 필요)
pip install torch==2.2.0 torchaudio==2.2.0 \
    --index-url https://download.pytorch.org/whl/cu121
```

**주의:**
- 이 방법은 서버에 인터넷이 필요
- `--no-deps`로 wheels의 의존성 중복 설치 방지

---

### 방법 3️⃣: 별도 단계별 설치

**Linux 서버에서:**

```bash
source venv/bin/activate

# Step 1: 기타 패키지 설치
cd deployment_package
pip install \
    wheels/transformers-*.whl \
    wheels/librosa-*.whl \
    wheels/scipy-*.whl \
    wheels/numpy-*.whl \
    wheels/fastapi-*.whl \
    wheels/uvicorn-*.whl \
    wheels/pydantic-*.whl \
    wheels/*.whl \
    --no-index --find-links ./

cd ..

# Step 2: PyTorch 설치 (wheels 또는 온라인)

# 옵션 A: wheels에서 (wheels/에 PyTorch가 있으면)
pip install deployment_package/wheels/torch-*.whl \
            deployment_package/wheels/torchaudio-*.whl

# 옵션 B: 온라인 설치
pip install torch torchaudio \
    --index-url https://download.pytorch.org/whl/cu121
```

---

## 🎯 추천 설정 (완전 오프라인)

### 1. macOS에서 준비 (인터넷 있음)

```bash
cd deployment_package/wheels

# PyTorch 2개 파일 다운로드
wget https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
wget https://download.pytorch.org/whl/cu121/torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

# 확인
ls -lh | grep -E "(torch|audio)"
# 출력: 약 900MB 각각

# 압축 파일 생성
cd ../..
tar -czf stt_engine_deployment_slim_v2_pytorch.tar.gz stt_engine/
```

### 2. Linux 서버에서 설치

```bash
# 1. 파일 전송
scp stt_engine_deployment_slim_v2_pytorch.tar.gz user@server:/tmp/

# 2. 서버에서 압축 해제
cd /tmp
tar -xzf stt_engine_deployment_slim_v2_pytorch.tar.gz
cd stt_engine

# 3. 환경 설정
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# 4. 모든 wheels 설치 (PyTorch 포함)
cd deployment_package
pip install wheels/*.whl

cd ..

# 5. 모델 다운로드 (인터넷 필요)
python3 download_model.py

# 6. STT Engine 설치
pip install -e .

# 7. API 실행
python3 api_server.py
```

---

## ✅ 설치 확인

```bash
# PyTorch 설치 확인
python3 -c "import torch; print(f'PyTorch: {torch.__version__}')"
# 출력: PyTorch: 2.2.0

# CUDA 지원 확인
python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
# 출력: CUDA: True

# torchaudio 확인
python3 -c "import torchaudio; print(f'torchaudio: {torchaudio.__version__}')"
# 출력: torchaudio: 2.2.0

# 모든 패키지 확인
pip list | grep -E "(torch|transformers|librosa)"
```

---

## ⚠️ 주의사항

### Python 버전
```bash
# 반드시 Python 3.11 사용!
python3.11 --version
# PyTorch wheels는 cp311 (Python 3.11 호환)

# 틀린 예:
python download_model.py  # 기본 python이 3.x가 아니면 실패

# 올바른 예:
python3.11 download_model.py
# 또는 venv 활성화 후:
python download_model.py
```

### wheels 순서
```bash
# wheels 설치 시 순서는 자동 처리됨
pip install wheels/*.whl  # 모든 의존성 자동 처리

# 특정 순서 필요 없음 (pip가 의존성 자동 해결)
```

### CUDA 호환성
```bash
# CUDA 12.9 서버에서 CUDA 12.1 wheels 사용 가능
# (상위 호환성이 있음)

nvidia-smi
# Driver Version: 575.57.08
# CUDA Version: 12.9 ← 이 값이 12.1 이상이면 OK
```

---

## 🛠️ 문제 해결

### "No module named 'torch'"
```bash
# 해결:
pip install wheels/torch-*.whl wheels/torchaudio-*.whl --force-reinstall
```

### CUDA 오류
```bash
# 확인:
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"

# CPU 모드로 실행 (GPU 없을 때):
export CUDA_VISIBLE_DEVICES=""
python3 api_server.py
```

### Wheel 파일 찾을 수 없음
```bash
# wheels/ 디렉토리 확인
ls -lh deployment_package/wheels/

# PyTorch 파일이 없으면:
# → 다시 다운로드 필요
cd deployment_package/wheels
wget https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

---

## 📝 빠른 명령어

```bash
# 가장 간단한 방법:
# 1. wheels에 PyTorch 파일 있는지 확인
ls -lh deployment_package/wheels/ | grep torch

# 2. 있으면 한 줄로 설치
pip install deployment_package/wheels/*.whl

# 3. 확인
python -c "import torch; print('✅ PyTorch OK')"
```

---

**권장: 방법 1️⃣ (wheels에 PyTorch 포함) - 완전 오프라인 가능!**
