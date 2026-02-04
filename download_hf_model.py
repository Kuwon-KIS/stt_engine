#!/usr/bin/env python3
import os
import sys
import ssl

# SSL 인증서 검증 비활성화
ssl._create_default_https_context = ssl._create_unverified_context

print("🔄 Whisper Large-V3-Turbo 모델 다운로드 중...")
print("=" * 60)

models_dir = "/Users/a113211/workspace/stt_engine/models"
os.makedirs(models_dir, exist_ok=True)

try:
    from huggingface_hub import snapshot_download
    
    print(f"📁 모델 저장 경로: {models_dir}")
    print(f"📦 모델명: openai/whisper-large-v3-turbo")
    print(f"⏳ huggingface_hub로 다운로드 중 (약 2.9GB)...")
    print()
    
    # Hugging Face에서 전체 모델 다운로드
    model_path = snapshot_download(
        repo_id="openai/whisper-large-v3-turbo",
        cache_dir=models_dir,
        local_files_only=False
    )
    
    print()
    print("=" * 60)
    print("✅ 모델 다운로드 완료!")
    print("=" * 60)
    
    print(f"\n📊 모델 경로: {model_path}")
    
    # 확인
    import subprocess
    result = subprocess.run(f"find {models_dir} -type f", 
                          shell=True, capture_output=True, text=True)
    files = result.stdout.strip().split('\n')
    files = [f for f in files if f]
    
    print(f"📊 다운로드된 파일 수: {len(files)}")
    
    result = subprocess.run(f"du -sh {models_dir}", 
                          shell=True, capture_output=True, text=True)
    print(f"📏 총 크기: {result.stdout.strip()}")
    
    print("\n📁 주요 파일:")
    result = subprocess.run(f"ls -lh {model_path}/", 
                          shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    print("\n✅ 모델 준비 완료!")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
