#!/usr/bin/env python3
"""
transformers를 사용해 모델을 로드하고 검증
"""
import sys
from pathlib import Path

print("🔍 transformers를 사용한 모델 검증")
print("=" * 60)

models_dir = Path("/Users/a113211/workspace/stt_engine/models")

try:
    from transformers import WhisperForConditionalGeneration, WhisperProcessor
    import torch
    
    print(f"📁 모델 경로: {models_dir}")
    print()
    
    print("1️⃣ WhisperProcessor 로드 중...")
    processor = WhisperProcessor.from_pretrained(
        "openai/whisper-large-v3-turbo",
        cache_dir=str(models_dir),
        local_files_only=True
    )
    print("✅ Processor 로드 완료")
    print(f"   - Sample Rate: {processor.feature_extractor.sampling_rate}")
    
    print("\n2️⃣ WhisperForConditionalGeneration 모델 로드 중...")
    model = WhisperForConditionalGeneration.from_pretrained(
        "openai/whisper-large-v3-turbo",
        cache_dir=str(models_dir),
        local_files_only=True,
        torch_dtype=torch.float16,
        device_map="cpu"
    )
    print("✅ 모델 로드 완료")
    print(f"   - Model Type: {type(model).__name__}")
    print(f"   - Device: CPU")
    print(f"   - Dtype: float16")
    
    print("\n3️⃣ 모델 정보")
    print("-" * 60)
    print(f"   - 모델 크기: {sum(p.numel() for p in model.parameters()) / 1e6:.0f}M parameters")
    print(f"   - 학습 가능한 파라미터: {sum(p.numel() for p in model.parameters() if p.requires_grad) / 1e6:.0f}M")
    
    print("\n✅ 모델 검증 완료!")
    print("🚀 HuggingFace 모델 형식으로 정상 작동합니다!")
    
    # 모델 summary
    print("\n4️⃣ 모델 구조")
    print("-" * 60)
    print(f"   Encoder: {model.encoder}")
    print(f"   Decoder: {model.decoder}")
    
except ImportError as e:
    print(f"❌ 필수 패키지 미설치: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 모델 로드 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
