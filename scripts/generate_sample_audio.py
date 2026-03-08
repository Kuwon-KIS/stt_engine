#!/usr/bin/env python3
"""
STT Engine 샘플 오디오 파일 생성 스크립트

다양한 길이의 테스트용 오디오 파일을 생성합니다:
- 짧은 오디오 (0.5초)
- 중간 오디오 (3초)
- 긴 오디오 (10초)
- 텍스트를 음성 유사 신호로 변환한 오디오

참고: 순수 numpy + wave로 표준 WAV 파일 생성 (외부 의존성 최소)
"""

import numpy as np
import wave
from pathlib import Path
import sys
import os
import struct




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

def create_speech_audio(filepath, text, language='ko'):
    """
    텍스트를 음성 유사 신호로 변환하여 wav 파일 생성
    
    Args:
        filepath: 저장할 파일 경로
        text: 음성으로 변환할 텍스트
        language: 언어 ('ko' = 한국어)
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"📝 음성 신호 생성 중... ({len(text)}자)")
    
    # 오디오 파라미터
    sample_rate = 44100  # 44.1kHz
    duration = max(3, len(text) / 3)  # 텍스트 길이에 따라 (평균 3자/초)
    num_samples = int(sample_rate * duration)
    
    # 시간 배열
    t = np.linspace(0, duration, num_samples, dtype=np.float64)
    
    # ===== 1. 기본 피치 생성 (100-200Hz) =====
    # 자연스러운 음성 피치 변조
    base_pitch = 150 + 40 * np.sin(2 * np.pi * 0.3 * t)
    pitch_signal = np.sin(2 * np.pi * base_pitch * t)
    
    # ===== 2. 포먼트 신호 (음성의 특성) =====
    # F1 (저주파, 모음 결정) - 500-800Hz
    f1_freq = 650 + 100 * np.sin(2 * np.pi * 0.5 * t)
    f1_signal = np.sin(2 * np.pi * f1_freq * t)
    
    # F2 (중주파) - 1500-2500Hz
    f2_freq = 2000 + 300 * np.sin(2 * np.pi * 0.7 * t)
    f2_signal = np.sin(2 * np.pi * f2_freq * t)
    
    # F3 (고주파) - 2500-3500Hz
    f3_freq = 3000 + 400 * np.sin(2 * np.pi * 1.0 * t)
    f3_signal = np.sin(2 * np.pi * f3_freq * t)
    
    # ===== 3. 음절 구조 추가 (자음/모음 리듬) =====
    # 초당 음절 수 (텍스트 길이 기반)
    syllable_rate = 3 + len(text) / duration / 5  # 대략 3-8 음절/초
    
    # 음절 온/오프 패턴
    syllable_wave = np.sin(2 * np.pi * syllable_rate * t)
    syllable_envelope = np.where(syllable_wave > 0, 1.0, 0.3)  # 음절 강조/약화
    
    # ===== 4. 최종 신호 합성 =====
    # 포먼트 신호 혼합 (음성 품질)
    voice = (0.4 * f1_signal + 0.3 * f2_signal + 0.2 * f3_signal)
    
    # 음절 구조 적용
    voice = voice * syllable_envelope
    
    # 피치 정보 추가
    voice = voice + 0.1 * pitch_signal * syllable_envelope
    
    # ===== 5. 에너지 엔벨로프 (시작/끝 약화) =====
    energy_envelope = np.sin(np.pi * t / duration) ** 0.6
    voice = voice * energy_envelope
    
    # ===== 6. 화자 특성 추가 (약간의 거친 음질) =====
    # 저주파 노이즈 추가 (거친 음성)
    noise = np.random.RandomState(42).normal(0, 0.01, num_samples)
    voice = voice + noise
    
    # ===== 7. 정규화 및 클리핑 방지 =====
    # 최대값으로 정규화
    max_val = np.max(np.abs(voice))
    if max_val > 0:
        voice = voice / max_val
    
    # 볼륨 조정 (0.8로 설정하여 클리핑 방지)
    voice = voice * 0.8
    
    # 클리핑 방지
    voice = np.clip(voice, -0.99, 0.99)
    
    # ===== 8. int16 변환 =====
    audio_int16 = np.int16(voice * 32767)
    
    # ===== 9. WAV 파일로 저장 =====
    try:
        with wave.open(str(filepath), 'wb') as wav_file:
            # WAV 포맷 설정
            n_channels = 1  # 모노
            sample_width = 2  # 16-bit (2bytes)
            
            wav_file.setnchannels(n_channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        # 파일 확인
        if filepath.exists():
            file_size = filepath.stat().st_size
            if file_size > 0:
                print(f"✅ 생성: {filepath.name}")
                print(f"   - 길이: {len(text)}자 → {duration:.1f}초")
                print(f"   - 크기: {file_size} bytes ({file_size/1024:.1f} KB)")
                print(f"   - 포맷: WAV, 44100Hz, 16-bit, Mono")
                return True
            else:
                print(f"❌ 오류: {filepath.name} (파일 크기 0)")
                return False
        else:
            print(f"❌ 오류: {filepath.name} (파일 생성 실패)")
            return False
    
    except Exception as e:
        print(f"❌ 오류: {filepath.name} - {str(e)}")
        return False



# 메인 로직
BASE_DIR = Path(__file__).parent.absolute()
audio_dir = BASE_DIR / "audio" / "samples"

print("🎵 STT Engine 샘플 오디오 파일 생성\n")

# 1. 기본 샘플 오디오 생성
print("📝 [1단계] 기본 샘플 오디오 생성")
print("-" * 50)
samples = [
    ("short_0.5s.wav", 0.5),
    ("medium_3s.wav", 3.0),
    ("long_10s.wav", 10.0),
]

for filename, duration in samples:
    filepath = audio_dir / filename
    create_audio_file(filepath, duration)

# 2. 텍스트 음성 변환
print("\n📝 [2단계] 텍스트를 음성으로 변환")
print("-" * 50)

# 명령줄 인자로 텍스트 받기
if len(sys.argv) > 1:
    custom_text = " ".join(sys.argv[1:])
else:
    # 기본 부당권유 판매 샘플
    custom_text = "고객님의 상황과 상관없이 이 상품은 무조건 가입해야해. 완전 대박이야. 수익 완전 보장하니까 동의 없이 내가 고객님 비번으로 임의로 가입할께"

print(f"📢 텍스트: {custom_text}\n")

speech_file = audio_dir / "improper_sales_example.wav"
success = create_speech_audio(speech_file, custom_text, language='ko')

if success:
    # 파일 정보 출력
    file_size = speech_file.stat().st_size
    print(f"\n📊 파일 정보:")
    print(f"   - 경로: {speech_file}")
    print(f"   - 크기: {file_size} bytes ({file_size/1024:.2f} KB)")
    print(f"   - 텍스트 길이: {len(custom_text)}자")

print(f"\n📁 저장 위치: {audio_dir}")
print(f"\n✨ 샘플 오디오 생성 완료!")
print("\n💡 사용 방법:")
print("   docker run -v $(pwd)/audio/samples:/app/audio/samples stt-engine:latest")
print("   curl -X POST http://localhost:8003/transcribe -F \"file=@audio/samples/improper_sales_example.wav\"")


# ============================================================================
# 테스트 모드
# ============================================================================
if "--test" in sys.argv:
    print("\n" + "=" * 50)
    print("🧪 테스트 모드 시작")
    print("=" * 50)
    
    # 생성된 파일들 검증
    test_files = [
        ("short_0.5s.wav", 0),
        ("medium_3s.wav", 0),
        ("long_10s.wav", 0),
        ("improper_sales_example.wav", 1000),  # 최소 1KB
    ]
    
    print("\n📋 파일 검증:")
    all_passed = True
    
    for filename, min_size in test_files:
        filepath = audio_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            if size >= min_size:
                print(f"✅ {filename:30s} {size:8d} bytes")
            else:
                print(f"❌ {filename:30s} {size:8d} bytes (최소: {min_size} bytes)")
                all_passed = False
        else:
            print(f"❌ {filename:30s} (파일 없음)")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    print("=" * 50)


