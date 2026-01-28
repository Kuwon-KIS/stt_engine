#!/usr/bin/env python3
"""
FastAPI를 사용한 STT 서버
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import tempfile
import torch
from stt_engine import WhisperSTT
from vllm_client import VLLMClient, VLLMConfig

app = FastAPI(title="STT Engine API", version="1.0.0")

# 모델 초기화
device = "cuda" if torch.cuda.is_available() else "cpu"
model_path = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"

try:
    stt = WhisperSTT(str(model_path), device=device)
    vllm_client = VLLMClient(VLLMConfig())
except Exception as e:
    print(f"❌ 모델 로드 실패: {e}")
    stt = None
    vllm_client = None


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
        language: 음성 언어 코드 (예: 'ko', 'en')
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


@app.post("/transcribe-and-process")
async def transcribe_and_process(
    file: UploadFile = File(...),
    language: str = None,
    instruction: str = "다음 텍스트를 요약해주세요:"
):
    """
    음성 파일을 텍스트로 변환한 후 vLLM으로 처리합니다.
    
    Parameters:
        file: 음성 파일
        language: 음성 언어 코드
        instruction: vLLM 처리 지시사항
    """
    if stt is None:
        raise HTTPException(status_code=503, detail="STT 모델이 로드되지 않았습니다.")
    
    if vllm_client is None:
        raise HTTPException(status_code=503, detail="vLLM 클라이언트가 초기화되지 않았습니다.")
    
    try:
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        
        # STT 처리
        stt_result = stt.transcribe(tmp_path, language=language)
        
        # 임시 파일 삭제
        Path(tmp_path).unlink()
        
        if not stt_result["success"]:
            return stt_result
        
        # vLLM으로 처리
        vllm_result = vllm_client.process_stt_with_vllm(
            stt_result["text"],
            instruction=instruction
        )
        
        return {
            "success": True,
            "stt_result": stt_result,
            "vllm_result": vllm_result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
