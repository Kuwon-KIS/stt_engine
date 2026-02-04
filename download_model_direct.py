#!/usr/bin/env python3
import os
import sys
import ssl
import urllib.request
import json
from pathlib import Path

# SSL 인증서 검증 완전 비활성화
ssl._create_default_https_context = ssl._create_unverified_context

print("🔄 Whisper Large-V3-Turbo 모델 파일 다운로드...")
print("=" * 60)

models_dir = Path("/Users/a113211/workspace/stt_engine/models")
models_dir.mkdir(exist_ok=True)

try:
    # 필요한 모델 파일들
    files = {
        "model.safetensors": "https://huggingface.co/openai/whisper-large-v3-turbo/resolve/main/model.safetensors",
        "config.json": "https://huggingface.co/openai/whisper-large-v3-turbo/resolve/main/config.json",
        "preprocessor_config.json": "https://huggingface.co/openai/whisper-large-v3-turbo/resolve/main/preprocessor_config.json",
        "tokenizer.json": "https://huggingface.co/openai/whisper-large-v3-turbo/resolve/main/tokenizer.json",
        "vocab.json": "https://huggingface.co/openai/whisper-large-v3-turbo/resolve/main/vocab.json",
        "merges.txt": "https://huggingface.co/openai/whisper-large-v3-turbo/resolve/main/merges.txt",
        "tokenizer_config.json": "https://huggingface.co/openai/whisper-large-v3-turbo/resolve/main/tokenizer_config.json",
        "generation_config.json": "https://huggingface.co/openai/whisper-large-v3-turbo/resolve/main/generation_config.json",
    }
    
    print(f"📁 저장 경로: {models_dir}")
    print(f"📦 다운로드 파일: {len(files)}개")
    print()
    
    for filename, url in files.items():
        filepath = models_dir / filename
        
        # 이미 다운로드된 파일 확인
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"✅ {filename} (이미 존재: {size:,} bytes)")
            continue
            
        print(f"⏳ {filename} 다운로드 중...", end=" ", flush=True)
        
        try:
            urllib.request.urlretrieve(url, filepath)
            size = filepath.stat().st_size
            print(f"✅ ({size:,} bytes)")
        except Exception as e:
            print(f"❌ 실패: {e}")
            # 모델 파일(model.safetensors)는 필수, 나머지는 선택
            if filename == "model.safetensors":
                raise
    
    print()
    print("=" * 60)
    print("✅ 모델 다운로드 완료!")
    print("=" * 60)
    
    # 확인
    files_list = list(models_dir.glob("*"))
    print(f"\n📊 준비된 파일: {len(files_list)}개")
    
    total_size = sum(f.stat().st_size for f in files_list if f.is_file())
    print(f"📏 총 크기: {total_size / (1024**3):.2f} GB")
    
    print("\n📁 파일 목록:")
    for f in sorted(files_list):
        if f.is_file():
            size = f.stat().st_size
            print(f"   - {f.name}: {size:,} bytes")
    
    print("\n✅ Docker 컨테이너에 반입 준비 완료!")
    print(f"마운트 경로: /Users/a113211/workspace/stt_engine/models:/app/models")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
