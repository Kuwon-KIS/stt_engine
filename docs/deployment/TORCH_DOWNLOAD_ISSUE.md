# PyTorch Wheel 다운로드 이슈 및 해결책

## 🚨 문제 상황

PyTorch 공식 CDN (download.pytorch.org)이 다음과 같은 문제를 나타내고 있습니다:
- `curl`, `wget`: HTML 에러 페이지 반환 (약 885B)
- `pip download`: "No matching distribution found" 에러
- `pip index versions`: CDN 연결 불가

**원인**: PyTorch CDN 접근 제한 또는 네트워크 문제

---

## ✅ 해결책 3가지

### 방법 1️⃣: Linux 서버에서 직접 설치 (권장 - 가장 안정적)

**Linux 서버에서 실행:**
```bash
# 1. 프로젝트 추출 및 이동
tar -xzf stt_engine_deployment_slim_v2.tar.gz
cd stt_engine

# 2. 가상환경 활성화
source venv/bin/activate

# 3. PyPI 기본 인덱스에서 직접 설치
pip install --upgrade pip setuptools wheel
pip install torch==2.0.1 torchaudio==2.0.2

# 또는 CUDA 12.1 버전 명시:
pip install torch==2.0.1 torchaudio==2.0.2 \
    --index-url https://download.pytorch.org/whl/cu121

# 4. 기타 패키지 설치
pip install deployment_package/wheels/*.whl

# 5. 설치 검증
python3 -c "import torch; print(f'PyTorch {torch.__version__} installed')"
```

**장점:**
- 가장 안정적 (서버에서 CDN 접근 가능할 가능성 높음)
- 자동으로 최적 버전 선택
- 네트워크 상태가 좋으면 빠름

**단점:**
- 서버에 인터넷 연결 필요

---

### 방법 2️⃣: 대체 PyTorch 버전 사용

CUDA 12.1과 호환되는 다른 버전들:
```bash
# PyTorch 2.0.1 (더 안정적)
pip install torch==2.0.1 torchaudio==2.0.2 \
    --index-url https://download.pytorch.org/whl/cu121

# PyTorch 2.1.0
pip install torch==2.1.0 torchaudio==2.1.0 \
    --index-url https://download.pytorch.org/whl/cu121

# 최신 버전 (온라인에서만)
pip install torch torchaudio
```

---

### 방법 3️⃣: Conda로 설치 (Linux 서버에서)

```bash
# conda 있는 경우:
conda install pytorch::pytorch torchaudio pytorch-cuda=12.1 -c pytorch

# 또는 pip로 conda 패키지 설치
pip install conda-forge::pytorch
```

---

## 🎯 현재 상황 해결 방안

### **Step 1: post_deploy_setup.sh 업데이트**

현재 스크립트를 온라인 설치로 자동 변경:

```bash
# Linux 서버에서:
cd /path/to/stt_engine

# post_deploy_setup.sh의 Phase 3를 다음으로 수정:
# ============================================
# Phase 3: Python 패키지 설치
# ============================================
echo "📦 Phase 3: Python 패키지 설치"
echo "=================================="

# 기본 패키지 먼저 설치
pip install --upgrade pip setuptools wheel

# 기타 패키지 설치
if ls deployment_package/wheels/*.whl 1> /dev/null 2>&1; then
    pip install deployment_package/wheels/*.whl
else
    echo "⚠️  wheels 디렉토리가 비어 있습니다. PyPI에서 설치합니다."
fi

# PyTorch 온라인 설치 (CUDA 12.1 최적화)
echo ""
echo "🔥 PyTorch 설치 중... (약 5-10분)"
pip install torch==2.0.1 torchaudio==2.0.2 \
    --index-url https://download.pytorch.org/whl/cu121

echo "✅ PyTorch 설치 완료"
```

### **Step 2: 검증**

```bash
# Python에서 PyTorch 버전 확인
python3 -c "
import torch
import torchaudio
print(f'✅ PyTorch: {torch.__version__}')
print(f'✅ CUDA Available: {torch.cuda.is_available()}')
print(f'✅ CUDA Version: {torch.version.cuda}')
"
```

---

## 📋 예상 시간 소요

| 방법 | 소요시간 | 요구사항 |
|------|---------|---------|
| Linux 온라인 설치 | 10-15분 | 서버 인터넷 필요 |
| Conda (있는 경우) | 5-10분 | conda 설치 필요 |
| 로컬 wheel (지금) | 불가능 | PyTorch CDN 문제 |

---

## 🚀 최종 권장안

```bash
# 1. tar.gz 파일은 현재 상태로 배포
# 2. Linux 서버에서:

tar -xzf stt_engine_deployment_slim_v2.tar.gz
cd stt_engine

# 3. 수동 설치:
source venv/bin/activate
pip install --upgrade pip
pip install torch==2.0.1 torchaudio==2.0.2 \
    --index-url https://download.pytorch.org/whl/cu121
pip install deployment_package/wheels/*.whl
bash deployment_package/post_deploy_setup.sh

# 4. 검증
python3 -c "import torch; print(f'PyTorch {torch.__version__} ✅')"
```

---

## 🔍 문제 조사

실제 문제를 확인하려면:

```bash
# CDN 직접 테스트
curl -I https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

# 대역폭 테스트
curl -w "\n%{http_code}\n" https://download.pytorch.org/whl/cu121/ | head -1
```

---

**현재 권장:**
✅ **Linux 서버에서 온라인 설치** (가장 확실하고 빠름)
❌ macOS에서 wheel 파일 수집 (CDN 문제로 불가능)
