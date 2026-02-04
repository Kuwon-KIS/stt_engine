#!/usr/bin/env python3
"""
STT Engine 모델 다운로드 스크립트 (로컬 및 오프라인 배포용)

목적: 
  - Hugging Face에서 openai/whisper-large-v3-turbo 모델 다운로드
  - 오프라인 환경에서도 사용 가능하도록 로컬 저장
  - 외부 인터넷이 없는 Linux 서버로 이동 가능하게 준비

사용:
  python download_model_simple.py
"""

import os
import sys
import ssl
from pathlib import Path

# SSL 인증서 검증 비활성화 (네트워크 문제 해결용)
ssl._create_default_https_context = ssl._create_unverified_context

print("🔄 Whisper Large-V3-Turbo 모델 다운로드 중...")
print("=" * 60)

# 모델 저장 경로 설정
BASE_DIR = Path(__file__).parent.absolute()
models_dir = BASE_DIR / "models"
models_dir.mkdir(parents=True, exist_ok=True)

# HuggingFace 환경 변수 설정 (로컬 캐시 사용)
os.environ["HF_HOME"] = str(models_dir / ".cache")
os.environ["HF_HUB_CACHE"] = str(models_dir / ".cache" / "hub")
os.environ["TRANSFORMERS_CACHE"] = str(models_dir / ".cache")

print(f"📁 모델 저장 경로: {models_dir}")
print(f"🗂️  캐시 경로: {models_dir / '.cache'}")
print()

try:
    from faster_whisper import WhisperModel
    
    print(f"� 모델명: openai/whisper-large-v3-turbo")
    print(f"⏳ faster_whisper로 다운로드 중 (약 1.3GB)...")
    print()
    
    # faster_whisper에서 Hugging Face repo ID 직접 사용
    # download_root를 지정하면 models/ 폴더 직접 사용
    model = WhisperModel(
        "openai/whisper-large-v3-turbo",
        device="cpu",
        compute_type="int8",
        download_root=str(models_dir),
        local_files_only=False  # 온라인 다운로드
    )
    
    print()
    print("=" * 60)
    print("✅ 모델 다운로드 및 로드 완료!")
    print("=" * 60)
    # 파일 검증 및 통계
    import subprocess
    
    result = subprocess.run(f"find {models_dir} -type f ! -path '*/.*' ! -name '.DS_Store'", 
                          shell=True, capture_output=True, text=True)
    files = [f for f in result.stdout.strip().split('\n') if f and not f.startswith('.')]
    
    print(f"📊 다운로드된 파일 수: {len(files)}")
    
    # 필수 파일 확인
    REQUIRED_FILES = [
        "config.json",
        "model.safetensors",
        "generation_config.json",
        "preprocessor_config.json",
        "tokenizer.json",
    ]
    
    print("\n✓ 필수 파일 확인:")
    all_found = True
    for req_file in REQUIRED_FILES:
        if (models_dir / req_file).exists():
            size = (models_dir / req_file).stat().st_size / (1024**3)
            print(f"  ✓ {req_file} ({size:.2f}GB)")
        else:
            print(f"  ✗ {req_file} (MISSING)")
            all_found = False
    
    if not all_found:
        print("\n⚠️  일부 필수 파일이 누락되었습니다!")
        sys.exit(1)
    
    result = subprocess.run(f"du -sh {models_dir}", 
                          shell=True, capture_output=True, text=True)
    print(f"\n📏 총 크기: {result.stdout.strip()}")
    
    print("\n📁 디렉토리 구조:")
    result = subprocess.run(f"ls -lh {models_dir}/", 
                          shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    print("\n✅ faster_whisper 모델 준비 완료!")
    print("\n📋 다음 단계:")
    print("  1. 모델 검증: python validate_model.py")
    print("  2. 모델 압축: bash scripts/compress-model.sh")
    print("  3. 서버 전송: scp whisper-large-v3-turbo-models.tar.gz user@server:/path/")
    print("  4. 서버에서 압축 풀기: tar -xzf whisper-large-v3-turbo-models.tar.gz")
    print("\n💡 오프라인 환경에서 모델 사용:")
    print(f"  - 로컬 파일만 사용: local_files_only=True")
    print(f"  - 환경변수: HF_HOME={models_dir / '.cache'}")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
