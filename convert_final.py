#!/usr/bin/env python3
"""
간단한 모델 변환: openai-whisper로 로드 후 CTranslate2 변환
"""

import sys
import json
import torch
from pathlib import Path

print("=" * 80)
print("🚀 모델 변환: OpenAI Whisper → CTranslate2")
print("=" * 80)
print()

try:
    import whisper
    from transformers import AutoConfig
    import ctranslate2
    
    print(f"✅ OpenAI Whisper: {whisper.__version__}")
    print(f"✅ CTranslate2: {ctranslate2.__version__}")
    print(f"✅ PyTorch: {torch.__version__}")
    print()
    
except ImportError as e:
    print(f"❌ 패키지 부족: {e}")
    sys.exit(1)

model_path = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"
model_safetensors = model_path / "model.safetensors"

print(f"📂 모델 경로: {model_path}")
print()

if not model_safetensors.exists():
    print(f"❌ model.safetensors 없음: {model_safetensors}")
    sys.exit(1)

size_gb = model_safetensors.stat().st_size / (1024 ** 3)
print(f"✅ 모델 파일 확인: {model_safetensors.name} ({size_gb:.2f}GB)")
print()

# Step 1: 모델을 PyTorch로 로드
print("1️⃣  모델 로드 중...")
print("-" * 80)

try:
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
    
    # 모델 로드
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        str(model_path),
        local_files_only=True,
        trust_remote_code=True
    )
    print("✅ PyTorch 모델 로드 완료")
    
    # state_dict 저장 (임시)
    temp_model_pt = model_path / "model.pt"
    torch.save(model.state_dict(), temp_model_pt)
    print(f"✅ 임시 PyTorch 모델 저장: {temp_model_pt.name}")
    
except Exception as e:
    print(f"❌ 로드 실패: {e}")
    sys.exit(1)

print()

# Step 2: CTranslate2 모델로 변환
print("2️⃣  CTranslate2로 변환 중...")
print("-" * 80)
print("   (이 과정은 2-5분 소요됩니다)")
print()

try:
    # 변환 메커니즘
    from ctranslate2.converters import TransformersConverter
    
    # Config 파일 읽기
    with open(model_path / "config.json") as f:
        config = json.load(f)
    
    print(f"   모델 타입: {config.get('model_type', 'unknown')}")
    print(f"   변환 시작...")
    
    # CTranslate2 변환 시도 (여러 방식)
    try:
        # 방식 1: 기본 변환
        converter = TransformersConverter(str(model_path))
        converter.convert(str(model_path), force=True)
        print("   ✅ 변환 완료 (방식1)")
        
    except TypeError as te:
        # 방식 2: 호환성 파라미터 제거
        print(f"   방식1 실패, 대체 방식 시도...")
        
        # 수동 변환: safetensors를 PyTorch 바이너리로 변환
        from safetensors.torch import load_file
        
        state_dict = load_file(str(model_safetensors))
        model_pt_file = model_path / "pytorch_model.bin"
        torch.save(state_dict, model_pt_file)
        print(f"   • safetensors → pytorch 변환: {model_pt_file.name}")
        
        # 이제 PyTorch 모델로 변환
        converter = TransformersConverter(str(model_path))
        converter.convert(str(model_path), force=True)
        print("   ✅ 변환 완료 (방식2)")

except Exception as e:
    print(f"❌ 변환 실패: {e}")
    print()
    print("   현재 상태 파일:")
    for f in sorted(model_path.glob("*")):
        if f.is_file() and f.suffix in [".bin", ".pt", ".safetensors"]:
            size = f.stat().st_size / (1024**3)
            print(f"   - {f.name}: {size:.2f}GB")
    sys.exit(1)

print()

# Step 3: 정리 및 확인
print("3️⃣  최종 확인...")
print("-" * 80)

# 임시 파일 정리
for temp_file in [model_path / "model.pt", model_path / "pytorch_model.bin"]:
    if temp_file.exists():
        temp_file.unlink()
        print(f"   • 임시 파일 삭제: {temp_file.name}")

print()
print("   📁 최종 파일 목록:")
for f in sorted(model_path.glob("*")):
    if f.is_file():
        size = f.stat().st_size
        if size > 1024 ** 3:
            size_str = f"{size / (1024**3):.2f}GB"
        elif size > 1024 ** 2:
            size_str = f"{size / (1024**2):.1f}MB"
        else:
            size_str = f"{size / 1024:.1f}KB"
        
        status = "✅" if f.name in ["model.bin", "model.safetensors"] else "  "
        print(f"   {status} {f.name:40s} {size_str:>10s}")

print()
model_bin = model_path / "model.bin"
if model_bin.exists():
    print("=" * 80)
    print("✅ 모델 변환 성공!")
    print("=" * 80)
else:
    print("=" * 80)
    print("⚠️  model.bin 생성 확인 필요")
    print("=" * 80)

print()
print("📝 다음 단계:")
print("   scp models/openai_whisper-large-v3-turbo/model.bin user@server:/path/models/")
print()
