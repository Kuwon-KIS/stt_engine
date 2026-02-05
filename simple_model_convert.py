#!/usr/bin/env python3
"""
Simpler CTranslate2 모델 변환 (faster-whisper 내장 방식)
"""

import sys
import shutil
from pathlib import Path

print("=" * 80)
print("🚀 간단한 모델 변환 (faster-whisper 캐시 활용)")
print("=" * 80)
print()

try:
    from faster_whisper import WhisperModel
    import ctranslate2
    
    print(f"✅ faster-whisper 버전: {WhisperModel.__module__}")
    print(f"✅ CTranslate2 버전: {ctranslate2.__version__}")
    print()
    
except ImportError as e:
    print(f"❌ 패키지 import 실패: {e}")
    print()
    print("📦 설치 필요: pip install faster-whisper ctranslate2 torch")
    sys.exit(1)

model_path = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"

print(f"📂 모델 경로: {model_path}")
print()

# Step 1: 모델 파일 확인
print("1️⃣  모델 파일 확인...")
print("-" * 80)

model_safetensors = model_path / "model.safetensors"
if not model_safetensors.exists():
    print(f"❌ model.safetensors를 찾을 수 없습니다: {model_safetensors}")
    sys.exit(1)

size_gb = model_safetensors.stat().st_size / (1024 ** 3)
print(f"✅ 모델 파일: {model_safetensors.name} ({size_gb:.2f}GB)")
print()

# Step 2: faster-whisper로 모델 로드 (자동 변환)
print("2️⃣  faster-whisper로 모델 로드 중...")
print("-" * 80)
print("   (이 과정은 2-5분 소요될 수 있습니다)")
print()

try:
    print("   모델 로딩 중...")
    model = WhisperModel(
        str(model_path),
        device="cpu",
        compute_type="default",
        local_files_only=True,
    )
    print("   ✅ 모델 로드 완료")
    
    # 모델이 로드되면 CTranslate2가 자동으로 model.bin을 생성
    
except Exception as e:
    print(f"❌ 모델 로드 실패: {e}")
    print()
    print("   원인 분석:")
    print("   - model.safetensors 포맷이 다를 수 있음")
    print("   - faster-whisper 버전 호환성 문제")
    sys.exit(1)

print()

# Step 3: model.bin 확인
print("3️⃣  변환된 모델 파일 확인...")
print("-" * 80)

model_bin = model_path / "model.bin"
if model_bin.exists():
    size_gb = model_bin.stat().st_size / (1024 ** 3)
    print(f"✅ model.bin 생성됨: {size_gb:.2f}GB")
else:
    # CTranslate2 캐시 위치 확인
    cache_dir = Path.home() / ".cache" / "ct2models"
    if cache_dir.exists():
        print(f"⚠️  모델이 캐시에 저장됨: {cache_dir}")
        print()
        print("   캐시된 모델을 프로젝트로 복사 중...")
        
        # 캐시에서 모델 찾기
        for cached_model in cache_dir.glob("whisper-*"):
            if (cached_model / "model.bin").exists():
                print(f"   찾은 캐시 모델: {cached_model.name}")
                shutil.copy2(cached_model / "model.bin", model_bin)
                print(f"   ✅ 복사 완료: {model_bin}")
                break
    else:
        print(f"❌ model.bin을 찾을 수 없습니다")
        sys.exit(1)

print()

# Step 4: 최종 확인
print("4️⃣  최종 파일 목록...")
print("-" * 80)

for f in sorted(model_path.glob("*")):
    if f.is_file():
        size = f.stat().st_size
        if size > 1024 ** 3:
            size_str = f"{size / (1024**3):.2f}GB"
        elif size > 1024 ** 2:
            size_str = f"{size / (1024**2):.1f}MB"
        else:
            size_str = f"{size / 1024:.1f}KB"
        print(f"   - {f.name:40s} {size_str:>10s}")

print()
print("=" * 80)
print("✅ 모델 변환 완료!")
print("=" * 80)
print()
print("📝 다음 단계: Linux 서버로 model.bin 전송")
print()
