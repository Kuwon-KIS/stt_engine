#!/usr/bin/env python3
"""
faster-whisper 모델 호환성 상세 분석

문제: Docker에서 model.bin을 찾을 수 없다는 에러
원인: faster-whisper가 사용하는 백엔드가 다름
"""

import sys
from pathlib import Path

print("=" * 80)
print("🔍 faster-whisper 모델 형식 호환성 상세 분석")
print("=" * 80)

# 1단계: faster-whisper 백엔드 확인
print("\n1️⃣  faster-whisper 백엔드 분석")
print("-" * 80)

try:
    import torch
    print(f"✓ PyTorch 버전: {torch.__version__}")
    
    # PyTorch 버전에 따른 faster-whisper 동작 방식
    pytorch_version = tuple(map(int, torch.__version__.split('.')[:2]))
    
    if pytorch_version >= (2, 2):
        print("  → PyTorch >= 2.2: PyTorch 백엔드 사용")
        print("    ✓ model.safetensors 지원")
    else:
        print(f"  → PyTorch < 2.2 ({pytorch_version}): CTranslate2 백엔드 사용")
        print("    ✗ model.safetensors 미지원")
        print("    ✓ model.bin 필요")
    
except ImportError:
    print("⚠️  PyTorch 정보 확인 불가")

# 2단계: faster-whisper 백엔드 확인
print("\n2️⃣  faster-whisper 내부 백엔드 확인")
print("-" * 80)

try:
    import faster_whisper
    print(f"✓ faster-whisper 설치됨")
    
    # 사용 중인 백엔드 확인
    try:
        import ctranslate2
        print("✓ CTranslate2 설치됨")
        print(f"  버전: {ctranslate2.__version__}")
        print("  → faster-whisper가 CTranslate2를 우선적으로 사용할 수 있음")
        print("  ✗ CTranslate2 모드: model.bin 형식 필요")
    except ImportError:
        print("✗ CTranslate2 미설치")
        print("  → PyTorch 백엔드만 사용 가능")
    
except ImportError:
    print("⚠️  faster-whisper 미설치")

# 3단계: 모델 파일 형식 확인
print("\n3️⃣  현재 모델 파일 형식")
print("-" * 80)

BASE_DIR = Path(__file__).parent.absolute()
models_dir = BASE_DIR / "models"

if (models_dir / "model.safetensors").exists():
    print("✓ model.safetensors 발견 (HuggingFace PyTorch 형식)")
    size_gb = (models_dir / "model.safetensors").stat().st_size / (1024**3)
    print(f"  크기: {size_gb:.2f}GB")
    print("  호환성:")
    print("    ✓ PyTorch >= 2.2")
    print("    ✗ CTranslate2")
elif (models_dir / "model.bin").exists():
    print("✓ model.bin 발견 (CTranslate2 형식)")
    size_gb = (models_dir / "model.bin").stat().st_size / (1024**3)
    print(f"  크기: {size_gb:.2f}GB")
    print("  호환성:")
    print("    ✓ CTranslate2")
    print("    ✓ PyTorch (변환 가능)")
else:
    print("✗ 모델 파일 미발견")

# 4단계: 문제 진단
print("\n4️⃣  문제 분석")
print("=" * 80)

print("""
발견된 문제:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✗ Docker 컨테이너의 PyTorch 버전이 < 2.2일 가능성
  → faster-whisper가 CTranslate2 백엔드를 사용하려고 시도
  → model.bin을 찾으려고 함
  → model.safetensors는 무시됨

✗ CTranslate2가 설치되었을 가능성
  → CTranslate2는 model.bin만 지원
  → model.safetensors 미지원

해결 방법:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

옵션 1️⃣  PyTorch 버전 업그레이드 (Docker)
  • PyTorch를 2.2 이상으로 업그레이드
  • 모든 환경에서 model.safetensors 사용 가능
  • 권장: ✓

옵션 2️⃣  모델 형식 변환 (현재 모델)
  • model.safetensors → model.bin (CTranslate2 형식) 변환
  • 약 400MB로 감소
  • CTranslate2가 필요한 경우 사용

옵션 3️⃣  CTranslate2 제거/비활성화
  • CTranslate2를 제거하면 PyTorch 백엔드 사용
  • model.safetensors 사용 가능
  • 추가 최적화 불가

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

print("\n권장 해결 방법:")
print("-" * 80)
print("""
🟢 권장: Dockerfile에서 PyTorch 버전을 2.6.0 이상으로 유지

현재 Dockerfile:
  FROM python:3.11-slim
  RUN pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124

이미 2.6.0이므로 다른 문제가 있을 수 있습니다.

확인 사항:
1. Docker 이미지 내부 PyTorch 버전 확인
2. CTranslate2 설치 여부 확인
3. stt_engine.py의 모델 로드 방식 확인
""")

print("\n=" * 80)
