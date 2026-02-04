#!/usr/bin/env python3
import os
import sys
import ssl

# SSL 인증서 검증 비활성화 (네트워크 문제 해결용)
ssl._create_default_https_context = ssl._create_unverified_context

print("🔄 Whisper Large-V3-Turbo 모델 다운로드 중...")
print("=" * 60)

models_dir = "/Users/a113211/workspace/stt_engine/models"
os.makedirs(models_dir, exist_ok=True)

try:
    from faster_whisper import WhisperModel
    
    print(f"📁 모델 저장 경로: {models_dir}")
    print(f"📦 모델명: openai/whisper-large-v3-turbo")
    print(f"⏳ faster_whisper로 다운로드 중 (약 2.9GB)...")
    print()
    
    # faster_whisper에서 Hugging Face repo ID 직접 사용
    model = WhisperModel(
        "openai/whisper-large-v3-turbo",
        device="cpu",
        download_root=models_dir,
        local_files_only=False
    )
    print()
    print("=" * 60)
    print("✅ 모델 다운로드 및 로드 완료!")
    print("=" * 60)
    
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
    
    print("\n📁 디렉토리 구조:")
    result = subprocess.run(f"ls -lh {models_dir}/", 
                          shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    print("\n✅ faster_whisper 모델 준비 완료!")
    print("이제 Docker 컨테이너에서 이 모델을 사용할 수 있습니다.")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
