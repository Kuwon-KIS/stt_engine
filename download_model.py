#!/usr/bin/env python3
"""
Whisper 모델 다운로드 스크립트
Hugging Face에서 openai/whisper-large-v3-turbo 모델을 로컬에 다운로드합니다.
"""

import os
import sys
from pathlib import Path
from huggingface_hub import snapshot_download
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq

def download_model(model_id: str, cache_dir: str) -> None:
    """
    모델을 다운로드합니다.
    
    Args:
        model_id: Hugging Face 모델 ID
        cache_dir: 모델을 저장할 디렉토리
    """
    print(f"📥 모델 다운로드를 시작합니다: {model_id}")
    print(f"💾 저장 경로: {cache_dir}")
    
    # 캐시 디렉토리 생성
    os.makedirs(cache_dir, exist_ok=True)
    
    try:
        # 모델 다운로드
        print("\n1️⃣  모델 파일 다운로드 중...")
        model_path = snapshot_download(
            repo_id=model_id,
            cache_dir=cache_dir,
            resume_download=True,
            local_dir=os.path.join(cache_dir, model_id.replace("/", "_"))
        )
        print(f"✅ 모델 파일 다운로드 완료: {model_path}")
        
        # Processor 다운로드
        print("\n2️⃣  Processor 다운로드 중...")
        processor = AutoProcessor.from_pretrained(model_id)
        processor.save_pretrained(model_path)
        print(f"✅ Processor 저장 완료")
        
        print("\n✨ 모든 다운로드가 완료되었습니다!")
        print(f"\n사용 방법:")
        print(f"  from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq")
        print(f"  processor = AutoProcessor.from_pretrained('{model_path}')")
        print(f"  model = AutoModelForSpeechSeq2Seq.from_pretrained('{model_path}')")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    model_id = "openai/whisper-large-v3-turbo"
    cache_dir = Path(__file__).parent / "models"
    
    download_model(str(model_id), str(cache_dir))
