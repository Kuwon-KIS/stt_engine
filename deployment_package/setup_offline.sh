#!/bin/bash

###############################################################################
# STT Engine - 완전 오프라인 설치 스크립트
#
# 인터넷이 없는 환경에서 사용합니다.
# 모든 의존성이 wheels/ 디렉토리에 포함되어야 합니다.
#
# 사용법:
#   chmod +x setup_offline.sh
#   ./setup_offline.sh /path/to/venv
###############################################################################

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WHEELS_DIR="${SCRIPT_DIR}/wheels"
VENV_PATH="${1:-${HOME}/.venv/stt_engine}"

echo "🔧 STT Engine 완전 오프라인 설치"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Python 3.11 확인
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if [[ ! $PYTHON_VERSION =~ ^3\.11 ]]; then
    echo "❌ Python 3.11.x 필요 (현재: $PYTHON_VERSION)"
    exit 1
fi
echo "✅ Python 3.11.x 확인됨: $PYTHON_VERSION"
echo ""

# wheels 디렉토리 확인
if [ ! -d "$WHEELS_DIR" ]; then
    echo "❌ wheels 디렉토리 없음: $WHEELS_DIR"
    exit 1
fi

WHEEL_COUNT=$(find "$WHEELS_DIR" -name "*.whl" -o -name "*.tar.gz" | wc -l)
echo "✅ $WHEEL_COUNT개 패키지 발견"
echo ""

# 가상환경 생성
echo "📦 가상환경 생성 중: $VENV_PATH"
if [ -d "$VENV_PATH" ]; then
    echo "   기존 환경 삭제..."
    rm -rf "$VENV_PATH"
fi

python3 -m venv "$VENV_PATH"
source "${VENV_PATH}/bin/activate"
echo "✅ 가상환경 생성 완료"
echo ""

# pip 업그레이드
echo "🔄 pip 업그레이드 중..."
pip install --upgrade pip setuptools wheel --no-index --find-links="$WHEELS_DIR" -q
echo "✅ pip 업그레이드 완료"
echo ""

# 모든 패키지 설치
echo "📥 패키지 설치 중..."
pip install --no-index --find-links="$WHEELS_DIR" "$WHEELS_DIR"/*.whl -q
echo "✅ 패키지 설치 완료"
echo ""

# 설치 확인
echo "🔍 설치 확인 중..."
python3 -c "
import torch
import transformers
import fastapi
print('✅ 주요 패키지 확인됨:')
print(f'   • torch: {torch.__version__}')
print(f'   • transformers: {transformers.__version__}')
print(f'   • fastapi: {fastapi.__version__}')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✨ 설치 완료!"
    echo ""
    echo "가상환경 경로: $VENV_PATH"
    echo ""
    echo "사용법:"
    echo "  source $VENV_PATH/bin/activate"
    echo "  python3 api_server.py"
else
    echo "❌ 설치 검증 실패"
    exit 1
fi

deactivate 2>/dev/null || true
