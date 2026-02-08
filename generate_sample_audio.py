#!/usr/bin/env python3
"""
STT Engine 샘플 오디오 파일 생성 스크립트

다양한 길이의 테스트용 오디오 파일을 생성합니다:
- 짧은 오디오 (0.5초)
- 중간 오디오 (3초)
- 긴 오디오 (10초)

참고: Whisper 모델은 정현파 신호보다는 음성에 최적화되어 있으므로,
여러 주파수의 조합으로 음성에 유사한 mel-spectrogram을 생성합니다.
"""

import numpy as np
import wave
from pathlib import Path

def create_audio_file(filepath, duration_seconds, sample_rate=16000):
    """
    음성 유사 신호로 wav 파일 생성
    
    여러 주파수의 조합으로 음성의 mel-spectrogram과 유사한 패턴을 생성합니다.
    
    Args:
        filepath: 저장할 파일 경로
        duration_seconds: 오디오 길이 (초)
        sample_rate: 샘플링 레이트 (Hz)
    """
    num_samples = int(sample_rate * duration_seconds)
    t = np.linspace(0, duration_seconds, num_samples)
    
    # 음성 유사 신호: 여러 주파수의 조합
    # 기본 주파수들 (음성 포먼트와 유사)
    f1 = 200 + 100 * np.sin(2 * np.pi * 0.5 * t)   # 변조된 저주파 (100-300Hz)
    f2 = 700 + 200 * np.sin(2 * np.pi * 1.0 * t)   # 변조된 중간주파 (500-900Hz)
    f3 = 2200 + 300 * np.sin(2 * np.pi * 1.5 * t)  # 변조된 고주파 (1900-2500Hz)
    
    # 주파수 변조된 신호 생성
    audio = (0.2 * np.sin(2 * np.pi * f1 * t) +
             0.15 * np.sin(2 * np.pi * f2 * t) +
             0.1 * np.sin(2 * np.pi * f3 * t))
    
    # 음성의 특성을 더 잘 반영하기 위해 envelope 추가
    # 음성은 시작과 끝이 약하고 중간이 강한 특성이 있음
    envelope = np.sin(np.pi * t / duration_seconds) ** 0.5
    audio = audio * envelope * 0.3
    
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
