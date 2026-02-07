#!/usr/bin/env python3
"""
FastAPI를 사용한 STT(Speech-to-Text) 서버

백엔드: faster-whisper + CTranslate2 (유일하게 지원되는 조합)
- 모델 형식: CTranslate2 (model.bin)
- 지원 모델: Hugging Face 커스텀 모델 (large-v3-turbo 포함)

참고: OpenAI Whisper는 공식 모델만 지원하므로 large-v3-turbo 사용 불가
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from pathlib import Path
import tempfile
import os
import logging
from stt_engine import WhisperSTT

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Whisper STT API",
    version="1.0.0",
    description="faster-whisper + CTranslate2를 사용한 음성 인식 API"
)

# 모델 초기화
# 환경변수 STT_DEVICE로 cpu/cuda 선택 가능 (기본값: cpu)
try:
    model_path = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"
    device = os.getenv("STT_DEVICE", "cpu")
    compute_type = "float16" if device == "cuda" else "float32"  # CPU는 float32가 더 안정적
    
    logger.info(f"STT 모델 로드 시작")
    logger.info(f"  모델: openai_whisper-large-v3-turbo")
    logger.info(f"  백엔드: faster-whisper + CTranslate2")
    logger.info(f"  경로: {model_path}")
    logger.info(f"  디바이스: {device}")
    logger.info(f"  Compute Type: {compute_type}")
    
    stt = WhisperSTT(
        str(model_path),
        device=device,
        compute_type=compute_type
    )
    logger.info(f"✅ STT 모델 로드 완료 (Backend: {stt.backend})")
    print(f"✅ STT 모델 로드 완료 (Device: {device}, Backend: {stt.backend})")
    
except FileNotFoundError as e:
    logger.error(f"❌ 모델 파일을 찾을 수 없음: {e}")
    logger.error(f"  확인 사항:")
    logger.error(f"  1. 모델이 다운로드되었는가? (python3 download_model_hf.py)")
    logger.error(f"  2. models/openai_whisper-large-v3-turbo/ 폴더가 존재하는가?")
    logger.error(f"  3. ctranslate2_model/model.bin이 1.5GB 이상인가?")
    logger.error(f"  4. Docker 실행 시 -v 옵션으로 마운트했는가?")
    logger.error(f"     docker run -v /path/to/models:/app/models ...")
    print(f"❌ 모델 로드 실패: {e}")
    stt = None
    
except RuntimeError as e:
    logger.error(f"❌ 모델 로드 실패 (CTranslate2 문제): {e}")
    logger.error(f"  해결 방법:")
    logger.error(f"  1. EC2에서 모델 삭제 및 재다운로드:")
    logger.error(f"     rm -rf models/openai_whisper-large-v3-turbo build/output/*")
    logger.error(f"     python3 download_model_hf.py  (30-45분)")
    logger.error(f"  2. 모델 파일 검증:")
    logger.error(f"     ls -lh models/openai_whisper-large-v3-turbo/ctranslate2_model/")
    logger.error(f"     필수: model.bin (1.5GB+), config.json (2.2KB), vocabulary.json")
    logger.error(f"  3. Docker 이미지 재빌드:")
    logger.error(f"     bash scripts/build-server-image.sh")
    print(f"❌ 모델 로드 실패: {e}")
    stt = None
    
except Exception as e:
    logger.error(f"❌ 예상치 못한 오류: {type(e).__name__}: {e}")
    print(f"❌ 모델 로드 실패: {e}")
    stt = None


@app.get("/health")
async def health():
    """헬스 체크"""
    if stt is None:
        return {"status": "error", "message": "STT 모델을 로드할 수 없음"}
    return {
        "status": "ok",
        "version": "1.0.0",
        "backend": stt.backend
    }


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = None):
    """
    음성 파일을 받아 텍스트로 변환
    
    Parameters:
    - file: 음성 파일 (WAV, MP3, M4A, FLAC 등)
    - language: 언어 코드 (선택사항, 예: "en", "ko", "ja")
    
    Returns:
    - success: 처리 성공 여부
    - text: 인식된 텍스트
    - language: 감지된 언어
    - duration: 오디오 길이 (초)
    - backend: 사용된 백엔드 (faster-whisper 또는 whisper)
    """
    if stt is None:
        raise HTTPException(status_code=503, detail="STT 모델이 로드되지 않음")
    
    tmp_path = None
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
            "duration": result.get("duration", None),
            "backend": result.get("backend", "unknown")
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # 임시 파일 삭제
        if tmp_path and Path(tmp_path).exists():
            Path(tmp_path).unlink()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
