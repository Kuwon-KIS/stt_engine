#!/usr/bin/env python3
from faster_whisper import WhisperModel
import numpy as np

print("\n" + "="*60)
print("🔍 STT Engine 모델 검증")
print("="*60 + "\n")

print("📌 Step 1: 모델 로드 테스트\n")
print("⏳ faster-whisper로 모델 로드 중...")
print("   (이 단계는 1-5분 걸릴 수 있습니다)\n")

try:
    from pathlib import Path
    
    # 다운로드된 모델 경로
    model_path = str(Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo")
    
    model = WhisperModel(
        model_size_or_path=model_path,
        device="cpu",
        compute_type="int8"
    )
    print("✅ faster-whisper 모델 로드 성공!\n")
    
    print("📋 모델 정보:")
    print("   ✓ 모델 타입: Whisper Large-v3-Turbo")
    print("   ✓ 디바이스: CPU")
    print("   ✓ 양자화: INT8\n")
    
    print("📌 Step 2: 추론 테스트\n")
    print("⏳ 더미 오디오로 추론 테스트 중...\n")
    
    dummy_audio = np.zeros((16000,), dtype=np.float32)
    segments, info = model.transcribe(dummy_audio, language="ko")
    
    print("✅ 추론 테스트 성공!\n")
    
    print("📊 추론 결과:")
    print(f"   ✓ 감지된 언어: {info.language}")
    print(f"   ✓ 언어 신뢰도: {info.language_probability:.2%}")
    print(f"   ✓ 처리된 오디오 시간: {info.duration:.2f}초\n")
    
    segment_list = list(segments)
    print(f"   ✓ 감지된 세그먼트: {len(segment_list)}개\n")
    
    print("="*60)
    print("✅ 모델 검증 완료!")
    print("="*60)
    print("\n🎉 모델이 정상적으로 작동합니다!\n")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}\n")
    import traceback
    traceback.print_exc()
