#!/usr/bin/env python3
"""
Whisper Large-V3-Turbo 모델을 ctranslate2 포맷으로 변환
"""
import sys
from pathlib import Path

print("🔄 Whisper 모델을 ctranslate2 포맷으로 변환")
print("=" * 60)

models_dir = Path("/Users/a113211/workspace/stt_engine/models")
output_dir = models_dir / "openai_whisper-large-v3-turbo"

print(f"📁 입력 경로: {models_dir}")
print(f"📁 출력 경로: {output_dir}")
print()

try:
    from faster_whisper.vad import get_speech_timestamps
    import torch
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
    import ctranslate2
    
    print("1️⃣ HuggingFace 모델 로드 중...")
    
    # HuggingFace에서 모델 로드
    model_name = "openai/whisper-large-v3-turbo"
    processor = WhisperProcessor.from_pretrained(model_name, cache_dir=str(models_dir), local_files_only=True)
    hf_model = WhisperForConditionalGeneration.from_pretrained(model_name, cache_dir=str(models_dir), local_files_only=True)
    
    print("✅ HuggingFace 모델 로드 완료")
    
    print("\n2️⃣ ctranslate2 포맷으로 변환 중...")
    
    # ctranslate2로 변환
    converter = ctranslate2.converters.TransformersConverter(
        model_name,
        copy_files=["*.json", "*.txt", "*.md"],
        quantization="int8",
    )
    converter.convert(str(output_dir))
    
    print("✅ ctranslate2 포맷 변환 완료")
    
    print(f"\n📁 변환된 모델 파일:")
    for f in sorted(output_dir.glob("**/*")):
        if f.is_file():
            size = f.stat().st_size
            print(f"   - {f.relative_to(output_dir)}: {size / (1024**2):.1f} MB")
    
    print("\n✅ 모델 변환 완료!")
    
except ImportError as e:
    print(f"❌ 필요한 패키지 미설치: {e}")
    print("\nctranslate2를 설치해야 합니다:")
    print("  pip install ctranslate2")
    sys.exit(1)
except Exception as e:
    print(f"❌ 변환 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
