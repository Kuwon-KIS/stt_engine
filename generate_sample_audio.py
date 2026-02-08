#!/usr/bin/env python3
"""
STT Engine 샘플 오디오 파일 생성 스크립트

다양한 길이의 테스트용 오디오 파일을 생성합니다:
- 짧은 오디오 (0.5초)
- 중간 오디오 (3초)
- 긴 오디오 (10초)
"""

import numpy as np
import wave
from pathlib import Path

def create_audio_file(filepath, duration_seconds, sample_rate=16000):
    """
    정현파 신호로 wav 파일 생성
    
    Args:
        filepath: 저장할 파일 경로
        duration_seconds: 오디오 길이 (초)
        sample_rate: 샘플링 레이트 (Hz)
    """
    # 1000Hz 정현파 생성
    num_samples = int(sample_rate * duration_seconds)
    frequency = 1000  # Hz
    t = np.linspace(0, duration_seconds, num_samples)
    audio = np.sin(2 * np.pi * frequency * t) * 0.3  # 0.3은 진폭
    
    # int16으로 변환
    audio_int16 = np.int16(audio * 32767)
    
    # WAV 파일 저장
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with wave.open(str(filepath), 'w') as wav_file:
        wav_file.setnchannels(1)  # 모노
        wav_file.setsampwidth(2)   # 16비트
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())
    
    print(f"✅ 생성: {filepath.name} ({duration_seconds}초)")

# 메인 로직
BASE_DIR = Path(__file__).parent.absolute()
audio_dir = BASE_DIR / "audio" / "samples"

print("🎵 STT Engine 샘플 오디오 파일 생성\n")

# 샘플 오디오 생성
samples = [
    ("short_0.5s.wav", 0.5),
    ("medium_3s.wav", 3.0),
    ("long_10s.wav", 10.0),
]

for filename, duration in samples:
    filepath = audio_dir / filename
    create_audio_file(filepath, duration)

print(f"\n📁 저장 위치: {audio_dir}")
print(f"\n✨ 샘플 오디오 생성 완료!")
print("\n💡 사용 방법:")
print("   docker run -v $(pwd)/audio/samples:/app/audio/samples stt-engine:latest")
print("   curl -X POST http://localhost:8003/transcribe -F \"file=@audio/samples/short_0.5s.wav\"")
