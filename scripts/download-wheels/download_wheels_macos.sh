#!/bin/bash

###############################################################################
# STT Engine - Wheel 다운로드 매크로 스크립트
#
# 이 스크립트는 macOS에서 Linux (x86_64) 플랫폼용 wheel을 다운로드합니다.
# 플랫폼 간 호환성을 보장합니다.
#
# 사용법:
#   chmod +x download_wheels_macos.sh
#   ./download_wheels_macos.sh
###############################################################################

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WHEELS_DIR="${SCRIPT_DIR}/wheels"

echo "🔧 STT Engine - macOS에서 Linux용 Wheel 다운로드"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Python 버전 확인
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "🐍 현재 Python 버전: $PYTHON_VERSION"
echo "📍 목표 플랫폼: Linux x86_64"
echo ""

if [[ ! $PYTHON_VERSION =~ ^3\.11 ]]; then
    echo "⚠️  경고: Python 3.11.x를 권장합니다 (현재: $PYTHON_VERSION)"
fi

echo "📥 Linux (x86_64) 플랫폼용 Wheel 다운로드 중..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# PyTorch (CUDA 12.9)
echo "⬇️  1/2 PyTorch CUDA 12.9..."
python3 -m pip download \
    --python-version 311 \
    --only-binary=:all: \
    --platform manylinux_2_17_x86_64 \
    -d "$WHEELS_DIR" \
    --index-url https://download.pytorch.org/whl/cu129 \
    torch==2.1.2 \
    torchaudio==2.1.2 \
    2>&1 | tail -5

# 기타 패키지
echo ""
echo "⬇️  2/2 기타 패키지..."
python3 -m pip download \
    --python-version 311 \
    --only-binary=:all: \
    --platform manylinux_2_17_x86_64 \
    -d "$WHEELS_DIR" \
    transformers==4.37.2 \
    huggingface-hub==0.21.4 \
    librosa==0.10.0 \
    scipy==1.12.0 \
    numpy==1.24.3 \
    python-dotenv==1.0.0 \
    pydantic==2.5.3 \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    requests==2.31.0 \
    pyyaml==6.0.1 \
    2>&1 | tail -10

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 통계
WHEEL_COUNT=$(find "$WHEELS_DIR" -name "*.whl" | wc -l)
TOTAL_SIZE=$(du -sh "$WHEELS_DIR" 2>/dev/null | awk '{print $1}')

echo ""
echo "✅ 다운로드 완료"
echo ""
echo "📊 통계:"
echo "   • .whl 파일: $WHEEL_COUNT개"
echo "   • 총 크기: $TOTAL_SIZE"
echo ""

echo "✨ 다음 단계:"
echo "   1. deployment_package를 Linux 서버로 전송"
echo "   2. 서버에서: chmod +x deploy.sh && ./deploy.sh"
echo ""
