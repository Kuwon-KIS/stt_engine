#!/usr/bin/env python3
"""
FastAPI를 사용한 STT(Speech-to-Text) 서버
Whisper 모델을 사용하여 음성을 텍스트로 변환합니다.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from pathlib import Path
import tempfile
import torch
from stt_engine import WhisperSTT

app = FastAPI(
    title="Whisper STT API",
    version="1.0.0",
    description="OpenAI Whisper를 사용한 음성 인식 API"
)

# 모델 초기화
device = "cuda" if torch.cuda.is_available() else "cpu"
model_path = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"

try:
    stt = WhisperSTT(str(model_path), device=device)
    print(f"✅ STT 모델 로드 완료 (Device: {device})")
except Exception as e:
    print(f"❌ 모델 로드 실패: {e}")
    stt = None


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "device": device,
        "models_loaded": stt is not None
    }


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = None
):
    """
    음성 파일을 텍스트로 변환합니다.
    
    Parameters:
        file: 음성 파일 (WAV, MP3, FLAC, OGG)
        language: 음성 언어 코드 (예: 'ko', 'en', None은 자동 감지)
    
    Returns:
        {"success": bool, "text": str, "language": str}
    """
    if stt is None:
        raise HTTPException(status_code=503, detail="STT 모델이 로드되지 않았습니다.")
    
    try:
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        
        # STT 처리
        result = stt.transcribe(tmp_path, language=language)
        
        # 임시 파일 삭제
        Path(tmp_path).unlink()
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
