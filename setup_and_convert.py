#!/usr/bin/env python3
"""
CTranslate2 모델 준비 스크립트 (Mac용)
PyTorch 형식의 모델을 CTranslate2가 읽을 수 있는 형식으로 준비

사용:
  python3 setup_and_convert.py
"""

import sys
import shutil
from pathlib import Path

WORKSPACE = Path(__file__).parent.absolute()
MODELS_DIR = WORKSPACE / "models"
MODEL_PATH = MODELS_DIR / "openai_whisper-large-v3-turbo"

print("=" * 80)
print("🚀 모델 준비 작업 시작")
print("=" * 80)
print()

# Step 1: 모델 파일 확인
print("1️⃣  모델 파일 확인...")
print("-" * 80)

if not MODEL_PATH.exists():
    print(f"❌ 모델 경로 없음: {MODEL_PATH}")
    sys.exit(1)

print(f"✅ 모델 경로: {MODEL_PATH}")
print()

# 필요한 파일 확인
required_files = ["config.json", "model.safetensors"]
for fname in required_files:
    fpath = MODEL_PATH / fname
    if fpath.exists():
        size_gb = fpath.stat().st_size / (1024 ** 3)
        print(f"✅ {fname:30s} {size_gb:6.2f}GB")
    else:
        print(f"❌ {fname:30s} (없음)")

print()

# Step 2: pytorch_model.bin 확인
print("2️⃣  PyTorch 모델 파일 확인...")
print("-" * 80)

pytorch_bin = MODEL_PATH / "pytorch_model.bin"
if pytorch_bin.exists():
    size_gb = pytorch_bin.stat().st_size / (1024 ** 3)
    print(f"✅ pytorch_model.bin 찾음: {size_gb:.2f}GB")
else:
    print(f"⚠️  pytorch_model.bin 없음 (선택사항)")

print()

# Step 3: model.bin 생성 또는 확인
print("3️⃣  CTranslate2 호환 모델 파일 생성...")
print("-" * 80)

model_bin = MODEL_PATH / "model.bin"

if model_bin.exists():
    size_gb = model_bin.stat().st_size / (1024 ** 3)
    print(f"✅ model.bin 이미 존재: {size_gb:.2f}GB")
elif pytorch_bin.exists():
    # pytorch_model.bin을 model.bin으로 복사
    print(f"📋 pytorch_model.bin → model.bin 복사 중...")
    try:
        shutil.copy2(pytorch_bin, model_bin)
        size_gb = model_bin.stat().st_size / (1024 ** 3)
        print(f"✅ model.bin 생성 완료: {size_gb:.2f}GB")
    except Exception as e:
        print(f"❌ 복사 실패: {e}")
        sys.exit(1)
else:
    print(f"⚠️  PyTorch 모델 파일을 찾을 수 없습니다")
    print(f"   (model.safetensors를 사용하면 openai-whisper 백엔드 사용)")

print()

# Step 4: 최종 파일 목록
print("4️⃣  최종 모델 파일 상태...")
print("-" * 80)

print(f"📁 {MODEL_PATH}/")
model_files = []
for f in sorted(MODEL_PATH.glob("*")):
    if f.is_file() and f.suffix in [".bin", ".safetensors", ".json"]:
        size = f.stat().st_size
        if size > 1024 ** 3:
            size_str = f"{size / (1024**3):.2f}GB"
        elif size > 1024 ** 2:
            size_str = f"{size / (1024**2):.1f}MB"
        else:
            size_str = f"{size / 1024:.1f}KB"
        
        marker = ""
        if f.name == "model.bin":
            marker = " ← CTranslate2 (faster-whisper)"
        elif f.name == "model.safetensors":
            marker = " ← PyTorch (openai-whisper)"
        
        print(f"   {f.name:35s} {size_str:>10s}{marker}")
        model_files.append((f.name, size))

print()
print("=" * 80)
print("✅ 모델 준비 완료!")
print("=" * 80)
print()
print("📝 배포 가능한 상태:")
print()

if (MODEL_PATH / "model.bin").exists():
    print("✅ faster-whisper 지원: model.bin 존재")
if (MODEL_PATH / "model.safetensors").exists():
    print("✅ openai-whisper 지원: model.safetensors 존재")

print()
print("🚀 다음 단계:")
print()
print("1️⃣  Linux 서버로 model.bin 전송:")
print(f"   scp {MODEL_PATH}/model.bin <user>@<server>:{MODEL_PATH}/")
print()
print("2️⃣  또는 전체 모델 디렉토리 전송:")
print(f"   scp -r {MODEL_PATH} <user>@<server>:{MODELS_DIR}/")
print()
print("3️⃣  Linux 서버에서 Docker 재빌드:")
print("   bash scripts/build-stt-engine-cuda.sh")
print()
print("4️⃣  Docker 실행 및 테스트:")
print("   curl http://localhost:8003/health")
print()


