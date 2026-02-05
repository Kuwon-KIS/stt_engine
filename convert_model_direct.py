#!/usr/bin/env python3
"""
CTranslate2 모델 변환 - transformers 직접 활용
"""

import sys
import json
from pathlib import Path

print("=" * 80)
print("🚀 CTranslate2 모델 변환 (Direct Conversion)")
print("=" * 80)
print()

# 필요한 패키지 설치 확인
try:
    import torch
    import ctranslate2
    from transformers import AutoModelForCausalLM, WhisperForConditionalGeneration, AutoProcessor
    import safetensors
    
    print(f"✅ PyTorch: {torch.__version__}")
    print(f"✅ CTranslate2: {ctranslate2.__version__}")
    print(f"✅ Transformers: ready")
    print()
    
except ImportError as e:
    print(f"❌ 패키지 import 실패: {e}")
    sys.exit(1)

model_path = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"

print(f"📂 모델 경로: {model_path}")
print()

# Step 1: 모델 파일 확인
print("1️⃣  모델 파일 확인...")
print("-" * 80)

model_safetensors = model_path / "model.safetensors"
config_file = model_path / "config.json"

if not model_safetensors.exists():
    print(f"❌ model.safetensors를 찾을 수 없습니다: {model_safetensors}")
    sys.exit(1)

if not config_file.exists():
    print(f"❌ config.json을 찾을 수 없습니다: {config_file}")
    sys.exit(1)

size_gb = model_safetensors.stat().st_size / (1024 ** 3)
print(f"✅ 모델 파일: {model_safetensors.name} ({size_gb:.2f}GB)")
print(f"✅ 설정 파일: {config_file.name}")
print()

# Step 2: 모델 로드 및 변환
print("2️⃣  모델 로드 중...")
print("-" * 80)
print("   (이 과정은 1-3분 소요될 수 있습니다)")
print()

try:
    # 모델 로드
    print("   • PyTorch 모델 로드 중...")
    model = WhisperForConditionalGeneration.from_pretrained(
        str(model_path),
        trust_remote_code=True,
        local_files_only=True,
    )
    print("   ✅ PyTorch 모델 로드 완료")
    
except Exception as e:
    print(f"   ⚠️  PyTorch 로드 실패: {e}")
    print()
    print("   대체 방법: safetensors 직접 변환...")
    print()
    
    try:
        # safetensors를 PyTorch로 직접 변환
        from safetensors.torch import load_file
        
        state_dict = load_file(str(model_safetensors))
        print(f"   ✅ safetensors 로드: {len(state_dict)} 개 파라미터")
        
        # 모델 구조 생성
        with open(config_file) as f:
            config = json.load(f)
        
        print(f"   ✅ 설정 로드: {config.get('model_type', 'unknown')} 모델")
        
        # CTranslate2 변환
        print()
        print("   • CTranslate2 변환 중...")
        
        from ctranslate2.converters.converter import Converter
        
        # 임시 PyTorch 모델 저장
        temp_dir = model_path / "temp_pytorch"
        temp_dir.mkdir(exist_ok=True)
        
        # state_dict 저장
        torch.save(state_dict, temp_dir / "pytorch_model.bin")
        
        # config 저장
        with open(temp_dir / "config.json", "w") as f:
            json.dump(config, f)
        
        # 변환 실행
        converter = Converter(
            "models/Whisper",
            str(temp_dir),
            str(model_path),
            force=True,
        )
        converter.convert()
        
        print("   ✅ CTranslate2 변환 완료")
        
        # 임시 파일 정리
        import shutil
        shutil.rmtree(temp_dir)
        
    except Exception as e2:
        print(f"   ❌ 변환 실패: {e2}")
        sys.exit(1)

print()

# Step 3: model.bin 확인
print("3️⃣  변환 결과 확인...")
print("-" * 80)

model_bin = model_path / "model.bin"
if model_bin.exists():
    size_gb = model_bin.stat().st_size / (1024 ** 3)
    print(f"✅ model.bin 생성됨: {size_gb:.2f}GB")
else:
    print(f"⚠️  model.bin이 아직 생성되지 않음")
    print()
    print("   현재 파일 목록:")
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
print("✅ 작업 완료!")
print("=" * 80)
print()
