#!/usr/bin/env python3
"""
STT Engine 모델 다운로드 스크립트 (huggingface-hub 직접 사용)

목적: 
  - Hugging Face에서 openai/whisper-large-v3-turbo 모델 다운로드
  - 심링크 없이 실제 파일로 저장 (오프라인 배포용)
  - 안정적인 다운로드 (재시도 지원)

사용:
  conda activate stt-py311
  python download_model_hf.py
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

print(f"📁 모델 저장 경로: {models_dir}")
print()

try:
    from huggingface_hub import snapshot_download
    
    MODEL_REPO = "openai/whisper-large-v3-turbo"
    
    print(f"📦 모델: {MODEL_REPO}")
    print(f"⏳ Hugging Face Hub에서 다운로드 중 (약 1.3GB)...")
    print()
    
    # snapshot_download를 사용하여 실제 파일로 저장
    # local_dir_use_symlinks=False: 심링크 대신 실제 파일 복사
    model_path = snapshot_download(
        repo_id=MODEL_REPO,
        cache_dir=str(models_dir),
        local_dir=str(models_dir / "model"),  # 실제 모델 경로
        local_dir_use_symlinks=False,         # 🔑 심링크 사용 안 함
        resume_download=True,                 # 중단된 다운로드 재개
        force_download=False                  # 이미 있으면 스킵
    )
    
    print()
    print("=" * 60)
    print("✅ 모델 다운로드 완료!")
    print("=" * 60)
    print()
    
    # 다운로드된 파일 검증
    import subprocess
    
    # 모델 폴더 구조 확인
    print("📁 다운로드된 파일:")
    result = subprocess.run(
        f"find {models_dir / 'model'} -type f ! -name '.DS_Store' -exec ls -lh {{}} \\; | awk '{{print $5, $9}}'",
        shell=True, capture_output=True, text=True
    )
    
    files_list = result.stdout.strip().split('\n')
    files_list = [f for f in files_list if f]
    
    print(f"\n✓ 파일 목록:")
    for line in files_list:
        print(f"  {line}")
    
    # 필수 파일 확인
    print(f"\n✓ 필수 파일 확인:")
    REQUIRED_FILES = [
        "config.json",
        "model.safetensors",
        "generation_config.json",
        "preprocessor_config.json",
        "tokenizer.json",
    ]
    
    all_found = True
    for req_file in REQUIRED_FILES:
        file_path = models_dir / "model" / req_file
        if file_path.exists():
            size = file_path.stat().st_size / (1024**2)
            print(f"  ✓ {req_file} ({size:.2f}MB)")
        else:
            print(f"  ✗ {req_file} (MISSING)")
            all_found = False
    
    if not all_found:
        print("\n⚠️  일부 필수 파일이 누락되었습니다!")
        sys.exit(1)
    
    # 전체 크기 확인
    result = subprocess.run(
        f"du -sh {models_dir / 'model'}",
        shell=True, capture_output=True, text=True
    )
    print(f"\n📏 전체 크기: {result.stdout.strip()}")
    
    print("\n✅ 모델 다운로드 및 검증 완료!")
    print("\n📋 다음 단계:")
    print("  1. 모델 구조 확인: python validate_model.py")
    print("  2. 모델 압축: python compress_model.py")
    print("  3. 서버로 전송: bash scripts/transfer-to-server.sh")
    
except ImportError:
    print("❌ huggingface-hub이 설치되어 있지 않습니다")
    print("설치: pip install huggingface-hub")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ 오류 발생: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
