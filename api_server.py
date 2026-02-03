#!/usr/bin/env python3
"""
FastAPI를 사용한 STT(Speech-to-Text) 서버
faster-whisper 모델을 사용하여 음성을 텍스트로 변환합니다.
더 빠른 추론 속도와 낮은 메모리 사용량으로 최적화됨
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from pathlib import Path
import tempfile
import os
from stt_engine import WhisperSTT

app = FastAPI(
    title="Whisper STT API",
    version="1.0.0",
    description="faster-whisper를 사용한 고속 음성 인식 API"
)

# 모델 초기화
# 환경변수 STT_DEVICE로 cpu/cuda 선택 가능 (기본값: cpu)
try:
    model_path = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"
    device = os.getenv("STT_DEVICE", "cpu")
    compute_type = "float16" if device == "cuda" else "int8"  # CPU는 int8이 더 효율적
    
    stt = WhisperSTT(
        str(model_path),
        device=device,
        compute_type=compute_type
    )
    print(f"✅ faster-whisper 모델 로드 완료 (Device: {device}, compute: {compute_type})")
except Exception as e:
    print(f"❌ 모델 로드 실패: {e}")
    stt = None


@app.get("/health")
async def health():
    """헬스 체크"""
    if stt is None:
        return {"status": "error", "message": "STT 모델을 로드할 수 없음"}
    return {"status": "ok", "version": "1.0.0", "engine": "faster-whisper"}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = None):
    """
    음성 파일을 받아 텍스트로 변환
    
    Parameters:
    - file: 음성 파일 (WAV, MP3, M4A, FLAC 등)
    - language: 언어 코드 (선택사항, 예: "en", "ko", "ja")
    
    Returns:
    - text: 인식된 텍스트
    - language: 감지된 언어
    - duration: 오디오 길이 (초)
    """
    if stt is None:
        raise HTTPException(status_code=503, detail="STT 모델이 로드되지 않음")
    
    try:
        # 임시 파일에 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # STT 처리
        result = stt.transcribe(tmp_path, language=language)
        
        return {
            "success": result.get("success", False),
            "text": result.get("text", ""),
            "language": result.get("language", "unknown"),
            "duration": result.get("duration", None)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # 임시 파일 삭제
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
