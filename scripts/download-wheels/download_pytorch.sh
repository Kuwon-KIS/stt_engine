#!/bin/bash

WHEELS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/wheels"
PYTHON="/opt/homebrew/bin/python3.11"

echo "📥 PyTorch CUDA 12.1 wheels 다운로드 중..."
$PYTHON -m pip download torch==2.1.2 torchaudio==2.1.2 \
    --only-binary=:all: \
    --platform manylinux_2_17_x86_64 \
    --python-version 311 \
    --index-url https://download.pytorch.org/whl/cu121 \
    -d "$WHEELS_DIR" \
    2>&1 | tail -10

echo "✅ PyTorch wheels 다운로드 완료"
