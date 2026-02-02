# 🚀 PyTorch 설치 - 3가지 방법

## 📌 상황별 설치 방법

### 상황 1️⃣: wheels에 PyTorch 포함 (완전 오프라인) ⭐ 권장

**준비 (macOS):**
```bash
cd deployment_package/wheels
wget https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
wget https://download.pytorch.org/whl/cu121/torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

**설치 (Linux):**
```bash
pip install deployment_package/wheels/*.whl
```

**장점:**
- ✅ 완전 오프라인 설치 가능
- ✅ 가장 빠름
- ✅ 의존성 자동 처리

---

### 상황 2️⃣: 기타 패키지는 오프라인, PyTorch는 온라인

**설치 (Linux - 인터넷 필요):**
```bash
# Phase 1: 기타 패키지 (오프라인)
pip install deployment_package/wheels/*.whl --no-index

# Phase 2: PyTorch (온라인)
pip install torch==2.2.0 torchaudio==2.2.0 \
    --index-url https://download.pytorch.org/whl/cu121
```

**사용 경우:**
- 서버에 인터넷 연결 있음
- wheels에 PyTorch 파일 없음

---

### 상황 3️⃣: 모든 것 온라인 설치 (최단 시간)

**설치 (Linux - 인터넷 필요):**
```bash
pip install -r requirements.txt \
    --index-url https://download.pytorch.org/whl/cu121 \
    --platform manylinux_2_17_x86_64 \
    --only-binary=:all:
```

**사용 경우:**
- 서버에 인터넷 연결 있음
- wheels 다운로드 못 함

---

## ⚡ 가장 간단한 방법

```bash
# Step 1: wheels 확인
ls -lh deployment_package/wheels/ | head -10

# Step 2: 한 줄 설치
pip install deployment_package/wheels/*.whl

# Step 3: 확인
python -c "import torch; print(torch.__version__)"
```

**자동 설정 스크립트가 알아서 처리합니다:**
```bash
bash deployment_package/post_deploy_setup.sh
```

---

## 🎯 권장 순서

### macOS (인터넷 있음)에서 준비:

1. **PyTorch wheels 다운로드** (2분)
```bash
cd /Users/a113211/workspace/stt_engine/deployment_package/wheels
wget https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
wget https://download.pytorch.org/whl/cu121/torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

2. **tar.gz 다시 생성** (1분)
```bash
cd /Users/a113211/workspace
tar -czf stt_engine_deployment_with_pytorch.tar.gz stt_engine/
```

3. **서버로 전송** (5-10분)
```bash
scp stt_engine_deployment_with_pytorch.tar.gz user@server:/tmp/
```

### Linux 서버에서:

1. **압축 해제** (1분)
```bash
cd /tmp
tar -xzf stt_engine_deployment_with_pytorch.tar.gz
cd stt_engine
```

2. **자동 설정** (30-40분)
```bash
bash deployment_package/post_deploy_setup.sh
```

3. **완료!** 모든 것이 자동으로 설치됨

---

## ✅ PyTorch 설치 확인

```bash
# 버전 확인
python -c "import torch; print(torch.__version__)"
# 출력: 2.2.0

# CUDA 지원 확인
python -c "import torch; print(torch.cuda.is_available())"
# 출력: True

# GPU 정보
python -c "import torch; print(torch.cuda.get_device_name(0))"
# 출력: NVIDIA A100 (또는 해당 GPU 이름)
```

---

## 🆘 문제 해결

### PyTorch 설치 실패
```bash
# 해결 방법 1: 강제 재설치
pip install torch==2.2.0 torchaudio==2.2.0 \
    --index-url https://download.pytorch.org/whl/cu121 \
    --force-reinstall --no-cache-dir

# 해결 방법 2: wheels에서 직접 설치
pip install /path/to/torch-2.2.0-*.whl \
            /path/to/torchaudio-2.2.0-*.whl
```

### CUDA 호환성 오류
```bash
# NVIDIA 드라이버 확인
nvidia-smi

# CUDA 버전 확인
nvidia-smi | grep "CUDA Version"

# PyTorch CUDA 지원 확인
python -c "import torch; print(torch.cuda.is_available())"
```

### wheels 파일 찾을 수 없음
```bash
# PyTorch wheels 다시 다운로드
cd deployment_package/wheels
wget https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
wget https://download.pytorch.org/whl/cu121/torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

---

**결론: wheels에 PyTorch 포함 → 한 줄 설치로 완료!** 🎯
