#!/bin/bash
# Docker 환경에서 모델을 미리 다운로드하는 빌드 스크립트

set -e

echo "📥 Whisper 모델 다운로드를 시작합니다..."

# Python 패키지 설치
pip install --no-cache-dir \
    transformers==4.37.2 \
    torch==2.1.2 \
    huggingface-hub==0.21.4

# 모델 다운로드
python << 'PYTHON_SCRIPT'
import os
from pathlib import Path
from huggingface_hub import snapshot_download
from transformers import AutoProcessor

model_id = "openai/whisper-large-v3-turbo"
cache_dir = Path("/app/models")

print(f"📥 모델 다운로드: {model_id}")
print(f"💾 저장 경로: {cache_dir}")

# 모델 다운로드
model_path = snapshot_download(
    repo_id=model_id,
    cache_dir=str(cache_dir),
    resume_download=True,
    local_dir=str(cache_dir / model_id.replace("/", "_"))
)

# Processor 저장
processor = AutoProcessor.from_pretrained(model_id)
processor.save_pretrained(model_path)

print("✅ 모델 다운로드 완료!")
print(f"📁 저장 위치: {model_path}")
PYTHON_SCRIPT

echo "✨ 모든 모델 다운로드가 완료되었습니다!"
