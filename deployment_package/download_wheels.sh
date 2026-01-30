#!/bin/bash

###############################################################################
# STT Engine - 오프라인 배포용 .whl 파일 다운로드 스크립트
# 
# 사용법:
#   chmod +x download_wheels.sh
#   ./download_wheels.sh
#
# 주의사항:
#   - Python 3.11.5 환경에서 실행
#   - 약 5GB 이상의 여유 공간 필요
#   - CUDA 12.1/12.9 호환 버전 다운로드
###############################################################################

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WHEELS_DIR="${SCRIPT_DIR}/wheels"

echo "🔧 STT Engine 오프라인 배포 패키지 생성"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 구성:"
echo "   • Python 버전: 3.11"
echo "   • CUDA 버전: 12.1/12.9 호환"
echo "   • Target OS: Linux"
echo ""

# wheels 디렉토리 확인
if [ ! -d "$WHEELS_DIR" ]; then
    echo "❌ wheels 디렉토리를 찾을 수 없습니다: $WHEELS_DIR"
    exit 1
fi

echo "📁 다운로드 위치: $WHEELS_DIR"
echo ""

# Python 버전 확인
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "🐍 현재 Python 버전: $PYTHON_VERSION"

if [[ ! $PYTHON_VERSION =~ ^3\.11 ]]; then
    echo "⚠️  경고: Python 3.11.x에서 실행하는 것을 권장합니다"
    echo "   현재: $PYTHON_VERSION"
    read -p "계속하시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "📦 의존성 패키지 다운로드 중..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# PyTorch와 torchaudio (CUDA 12.1 호환)
echo "⬇️  1/2 PyTorch ecosystem 다운로드 중..."
python3 -m pip download \
    --python-version 311 \
    --only-binary=:all: \
    --platform manylinux_2_17_x86_64 \
    -d "$WHEELS_DIR" \
    'torch==2.1.2' \
    'torchaudio==2.1.2' \
    --index-url https://download.pytorch.org/whl/cu121 \
    2>&1 | grep -E "(Downloading|Collecting|Successfully)" || true

echo ""
echo "⬇️  2/2 기타 의존성 다운로드 중..."
python3 -m pip download \
    --python-version 311 \
    --only-binary=:all: \
    --platform manylinux_2_17_x86_64 \
    -d "$WHEELS_DIR" \
    'transformers==4.37.2' \
    'huggingface-hub==0.21.4' \
    'librosa==0.10.0' \
    'scipy==1.12.0' \
    'numpy==1.24.3' \
    'python-dotenv==1.0.0' \
    'pydantic==2.5.3' \
    'fastapi==0.109.0' \
    'uvicorn==0.27.0' \
    'requests==2.31.0' \
    'pyyaml==6.0.1' \
    2>&1 | grep -E "(Downloading|Collecting|Successfully)" || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 다운로드된 파일 통계
WHEEL_COUNT=$(find "$WHEELS_DIR" -name "*.whl" | wc -l)
TOTAL_SIZE=$(du -sh "$WHEELS_DIR" | awk '{print $1}')

echo "✅ 다운로드 완료"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 통계:"
echo "   • .whl 파일 개수: $WHEEL_COUNT개"
echo "   • 총 크기: $TOTAL_SIZE"
echo ""

echo "📁 다운로드된 파일:"
ls -lh "$WHEELS_DIR" | grep "\.whl$" | awk '{printf "   • %s (%s)\n", $9, $5}'

echo ""
echo "✨ 배포 준비 완료!"
echo ""
echo "다음 단계:"
echo "  1. deployment_package 디렉토리를 Linux 서버로 복사"
echo "  2. 서버에서 deploy.sh 실행"
echo "  3. bash deploy.sh"
echo ""
