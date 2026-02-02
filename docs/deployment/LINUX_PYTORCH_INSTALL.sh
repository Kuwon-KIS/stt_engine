#!/bin/bash

###############################################################################
# Linux RHEL 8.9 서버에서 PyTorch 설치 스크립트
# CUDA 12.9 환경에 최적화됨
# 작성: 2026-02-02
###############################################################################

set -e  # 에러 발생 시 중단

echo "🚀 ======================================"
echo "   PyTorch 설치 스크립트"
echo "   CUDA 12.9 (RHEL 8.9)"
echo "======================================"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# Step 1: 시스템 정보 확인
# ============================================================================
echo "📋 Step 1: 시스템 정보 확인"
echo "=================================="
echo ""

echo "🔍 Python 버전:"
python3 --version

echo ""
echo "🔍 CUDA 버전:"
nvidia-smi 2>/dev/null || echo "⚠️  nvidia-smi 없음 (나중에 확인 가능)"

echo ""
echo "🔍 디스크 용량:"
df -h / | tail -1

echo ""
echo "✅ 시스템 정보 확인 완료"
echo ""

# ============================================================================
# Step 2: 가상환경 확인 및 활성화
# ============================================================================
echo "📋 Step 2: 가상환경 확인"
echo "=================================="
echo ""

if [ -d "venv" ]; then
    echo "✅ venv 디렉토리 발견"
    source venv/bin/activate
    echo "✅ 가상환경 활성화됨"
else
    echo "❌ venv 디렉토리 없음"
    echo "   생성 중..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ 새 가상환경 생성 및 활성화됨"
fi

echo ""
echo "🔍 활성화된 Python:"
which python
python --version

echo ""

# ============================================================================
# Step 3: pip 업그레이드
# ============================================================================
echo "📋 Step 3: pip 업그레이드"
echo "=================================="
echo ""

echo "⬇️  pip 업그레이드 중..."
pip install --upgrade pip setuptools wheel -q
echo "✅ pip 업그레이드 완료"
echo ""

# ============================================================================
# Step 4: 기존 wheels 설치 (있으면)
# ============================================================================
echo "📋 Step 4: 기존 패키지 wheels 설치"
echo "=================================="
echo ""

WHEELS_DIR="deployment_package/wheels"
WHEEL_COUNT=$(ls -1 "$WHEELS_DIR"/*.whl 2>/dev/null | wc -l)

if [ "$WHEEL_COUNT" -gt 0 ]; then
    echo "📦 발견된 wheel 파일: $WHEEL_COUNT개"
    echo "⬇️  설치 중... (시간이 걸릴 수 있습니다)"
    
    # PyTorch wheels 제외 (별도로 설치)
    WHEEL_FILES=$(find "$WHEELS_DIR" -name "*.whl" ! -name "torch*" ! -name "torchaudio*" -type f)
    
    if [ -n "$WHEEL_FILES" ]; then
        pip install $WHEEL_FILES -q
        echo "✅ $(echo "$WHEEL_FILES" | wc -l) 개 패키지 설치 완료"
    else
        echo "⚠️  PyTorch 제외 wheel 파일 없음"
    fi
else
    echo "⚠️  wheels 디렉토리가 비어있습니다"
    echo "   PyTorch만 온라인으로 설치합니다"
fi

echo ""

# ============================================================================
# Step 5: PyTorch 설치 (CUDA 12.9 최적화)
# ============================================================================
echo "📋 Step 5: PyTorch 설치 (CUDA 12.9)"
echo "=================================="
echo ""

echo "🔥 PyTorch 최신 버전 설치 중... (약 10-20분 소요)"
echo ""

# 자동으로 CUDA 12.9와 호환되는 최신 버전 설치
pip install torch torchaudio torchvision

# 설치 실패 시 대체 방법
if ! python3 -c "import torch" 2>/dev/null; then
    echo "⚠️  기본 설치 실패, CUDA 12.4 명시 버전으로 재시도..."
    pip install torch torchaudio torchvision \
        --index-url https://download.pytorch.org/whl/cu124
fi

echo ""
echo "✅ PyTorch 설치 완료"
echo ""

# ============================================================================
# Step 6: 설치 검증
# ============================================================================
echo "📋 Step 6: 설치 검증"
echo "=================================="
echo ""

python3 << 'EOF'
import sys
print("🔍 설치 검증 중...")
print("")

try:
    import torch
    print(f"✅ PyTorch 버전: {torch.__version__}")
    print(f"✅ PyTorch 경로: {torch.__file__}")
    print("")
    
    import torchaudio
    print(f"✅ torchaudio 버전: {torchaudio.__version__}")
    print("")
    
    # CUDA 정보
    print("🔥 CUDA 정보:")
    cuda_available = torch.cuda.is_available()
    print(f"   CUDA Available: {cuda_available}")
    
    if cuda_available:
        print(f"   CUDA Version: {torch.version.cuda}")
        print(f"   GPU 개수: {torch.cuda.device_count()}")
        print(f"   현재 Device: {torch.cuda.current_device()}")
        print(f"   GPU 이름: {torch.cuda.get_device_name(0)}")
        
        # 메모리 확인
        props = torch.cuda.get_device_properties(0)
        total_memory = props.total_memory / 1024 / 1024 / 1024  # GB
        print(f"   GPU 메모리: {total_memory:.1f} GB")
    else:
        print("   ⚠️  CUDA 비활성화 (CPU 모드로 작동합니다)")
    
    print("")
    print("✅ 모든 검증 통과!")
    
except ImportError as e:
    print(f"❌ 설치 실패: {e}")
    sys.exit(1)
EOF

VALIDATION=$?

echo ""

# ============================================================================
# Step 7: 다음 단계
# ============================================================================
if [ $VALIDATION -eq 0 ]; then
    echo "📋 Step 7: 다음 단계"
    echo "=================================="
    echo ""
    echo "✅ PyTorch 설치 성공!"
    echo ""
    echo "다음으로 실행할 명령어:"
    echo ""
    echo "  # 나머지 설정 자동화"
    echo "  bash deployment_package/post_deploy_setup.sh"
    echo ""
    echo "또는 수동으로:"
    echo ""
    echo "  # 모델 다운로드"
    echo "  python3 download_model.py"
    echo ""
    echo "  # API 서버 실행"
    echo "  python3 api_server.py"
    echo ""
else
    echo "❌ 설치 검증 실패"
    echo "   로그를 확인하고 다시 시도해주세요"
    exit 1
fi

echo ""
echo "🎉 ======================================"
echo "   PyTorch 설치 완료!"
echo "======================================"
echo ""
