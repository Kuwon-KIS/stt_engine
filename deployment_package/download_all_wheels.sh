#!/bin/bash

PYTHON="/opt/homebrew/bin/python3.11"
WHEELS_DIR="./wheels"

echo "🚀 STT Engine - 전체 wheels 다운로드 시작"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. PyTorch 다운로드 (최신 안정 버전 2.2.0 CUDA 12.1)
echo "⬇️  1/2 PyTorch 2.2.0 + torchaudio CUDA 12.1..."
$PYTHON -m pip download \
    torch==2.2.0 torchaudio==2.2.0 \
    --only-binary=:all: \
    --platform manylinux_2_17_x86_64 \
    --python-version 311 \
    --index-url https://download.pytorch.org/whl/cu121 \
    -d "$WHEELS_DIR" 2>&1 | grep -E "(Successfully|Collecting|ERROR)" | tail -5

echo ""
echo "⬇️  2/2 기타 패키지들..."
$PYTHON -m pip download \
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
    --only-binary=:all: \
    --platform manylinux_2_17_x86_64 \
    --python-version 311 \
    -d "$WHEELS_DIR" 2>&1 | grep -E "(Successfully|Collecting|ERROR)" | tail -10

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ 다운로드 완료!"
echo ""
echo "📊 다운로드된 파일:"
ls -1 "$WHEELS_DIR"/*.whl 2>/dev/null | wc -l | awk '{print "  • .whl 파일: " $1 "개"}'
du -sh "$WHEELS_DIR" | awk '{print "  • 총 크기: " $1}'
echo ""
echo "✨ 다음 단계:"
echo "  1. deployment_package를 Linux 서버로 전송"
echo "  2. 서버에서: pip install wheels/*.whl"

