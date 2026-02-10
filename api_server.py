#!/usr/bin/env python3
"""
FastAPI를 사용한 STT(Speech-to-Text) 서버

지원 백엔드 (우선순위):
1. faster-whisper + CTranslate2 (가장 빠름, 권장)
2. transformers WhisperForConditionalGeneration (HF 모델 직접 지원)
3. OpenAI Whisper (공식 모델만 지원)

모델 형식:
- CTranslate2: model.bin (매우 빠름)
- PyTorch/SafeTensors: pytorch_model.bin, model.safetensors (더 느림)
- OpenAI Whisper: 공식 모델명만 (tiny, base, small, medium, large)
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from pathlib import Path
import tempfile
import os
import logging
from stt_engine import WhisperSTT
from stt_utils import check_memory_available, check_audio_file

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Whisper STT API",
    version="1.0.0",
    description="다중 백엔드 STT API (faster-whisper, transformers, OpenAI Whisper)"
)

# 모델 초기화
# 환경변수 STT_DEVICE로 cpu/cuda 선택 가능 (기본값: cpu)
try:
    model_path = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"
    device = os.getenv("STT_DEVICE", "cpu")
    
    # 환경변수로 compute_type 지정 가능 (기본값: device에 따라 자동)
    compute_type = os.getenv("STT_COMPUTE_TYPE")
    if compute_type is None:
        compute_type = "float16" if device == "cuda" else "float32"  # CPU는 float32가 더 안정적
    
    logger.info(f"STT 모델 로드 시작 (다중 백엔드)")
    logger.info(f"  모델: openai_whisper-large-v3-turbo")
    logger.info(f"  경로: {model_path}")
    logger.info(f"  디바이스: {device}")
    logger.info(f"  Compute Type: {compute_type}")
    logger.info(f"  우선순위:")
    logger.info(f"    1. faster-whisper (CTranslate2)")
    logger.info(f"    2. transformers (PyTorch/SafeTensors)")
    logger.info(f"    3. OpenAI Whisper (공식 모델만)")
    
    stt = WhisperSTT(
        str(model_path),
        device=device,
        compute_type=compute_type
    )
    
    # 로드된 백엔드 타입 확인
    backend_type = type(stt.backend).__name__
    logger.info(f"✅ STT 모델 로드 완료")
    logger.info(f"   Backend Type: {backend_type}")
    logger.info(f"   Device: {device}")
    print(f"✅ STT 모델 로드 완료 (Backend: {backend_type}, Device: {device})")
    
except FileNotFoundError as e:
    logger.error(f"❌ 모델 파일을 찾을 수 없음: {e}")
    logger.error(f"  확인 사항:")
    logger.error(f"  1. 모델이 다운로드되었는가? (python3 download_model_hf.py)")
    logger.error(f"  2. 필요한 파일들:")
    logger.error(f"     - CTranslate2: models/openai_whisper-large-v3-turbo/ctranslate2_model/model.bin")
    logger.error(f"     - PyTorch: models/openai_whisper-large-v3-turbo/pytorch_model.bin 또는 model.safetensors")
    logger.error(f"  3. Docker 실행 시 마운트:")
    logger.error(f"     docker run -v /path/to/models:/app/models ...")
    print(f"❌ 모델 로드 실패: {e}")
    stt = None
    
except RuntimeError as e:
    logger.error(f"❌ 모든 백엔드 로드 실패: {e}")
    logger.error(f"  해결 방법:")
    logger.error(f"  1. EC2에서 모델 다운로드 및 변환:")
    logger.error(f"     python3 download_model_hf.py")
    logger.error(f"  2. 변환된 모델 확인:")
    logger.error(f"     ls -lh models/openai_whisper-large-v3-turbo/")
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
    """헬스 체크 (메모리 정보 포함)"""
    if stt is None:
        return {
            "status": "error",
            "message": "STT 모델을 로드할 수 없음"
        }
    
    # 메모리 상태 확인
    memory_info = check_memory_available(logger=logger)
    
    # 백엔드 정보 조회
    backend_info = stt.get_backend_info()
    
    return {
        "status": "ok",
        "version": "1.0.0",
        "backend": backend_info['current_backend'],
        "backend_type": backend_info['backend_type'],
        "model": "openai_whisper-large-v3-turbo",
        "device": stt.device,
        "compute_type": stt.compute_type,
        "memory": {
            "available_mb": memory_info['available_mb'],
            "total_mb": memory_info['total_mb'],
            "used_percent": memory_info['used_percent'],
            "status": "warning" if memory_info['warning'] else ("critical" if memory_info['critical'] else "ok"),
            "message": memory_info['message']
        }
    }


@app.get("/backend/current")
async def get_current_backend():
    """
    현재 로드된 백엔드 정보 조회
    
    Returns:
    - current_backend: 현재 로드된 백엔드 이름
    - backend_type: Python 클래스명
    - device: 사용 중인 디바이스 (cpu/cuda)
    - compute_type: 계산 타입 (float32/float16/int8)
    - model_path: 모델 경로
    - available_backends: 설치된 백엔드 목록
    - loaded: 백엔드 로드 여부
    """
    if stt is None:
        raise HTTPException(status_code=503, detail="STT 모델이 로드되지 않음")
    
    backend_info = stt.get_backend_info()
    logger.info(f"[API] 현재 백엔드 조회: {backend_info['current_backend']}")
    
    return backend_info


@app.post("/backend/reload")
async def reload_backend(backend: str = None):
    """
    백엔드를 재로드합니다.
    
    Parameters:
    - backend: 로드할 백엔드 (선택사항)
               - "faster-whisper": faster-whisper 사용
               - "transformers": transformers 사용
               - "openai-whisper": OpenAI Whisper 사용
               - null: 기본 순서대로 자동 선택 (faster-whisper → transformers → openai-whisper)
    
    Returns:
    - status: "success" | "error"
    - message: 처리 결과 메시지
    - loaded_backend: 로드된 백엔드 이름
    - backend_info: 로드 후 백엔드 정보
    
    예시:
    - POST /backend/reload {"backend": "transformers"}
    - POST /backend/reload (기본 순서로 자동 선택)
    """
    if stt is None:
        raise HTTPException(status_code=503, detail="STT 모델이 로드되지 않음")
    
    try:
        # 현재 백엔드 정보 로깅
        old_backend = stt.get_backend_info()['current_backend']
        
        # 백엔드 재로드
        logger.info(f"[API] 백엔드 재로드 시작: {backend or '자동 선택'}")
        loaded_backend = stt.reload_backend(backend)
        logger.info(f"[API] 백엔드 재로드 완료: {old_backend} → {loaded_backend}")
        
        # 재로드 후 백엔드 정보
        new_backend_info = stt.get_backend_info()
        
        return {
            "status": "success",
            "message": f"백엔드가 {loaded_backend}로 변경되었습니다",
            "previous_backend": old_backend,
            "loaded_backend": loaded_backend,
            "backend_info": new_backend_info
        }
    
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"[API] 백엔드 재로드 실패: {error_msg}")
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": error_msg,
                "supported_backends": ["faster-whisper", "transformers", "openai-whisper"]
            }
        )
    
    except RuntimeError as e:
        error_msg = str(e)
        logger.error(f"[API] 백엔드 재로드 실패: {error_msg}")
        backend_info = stt.get_backend_info()
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": error_msg,
                "current_backend": backend_info['current_backend'],
                "available_backends": backend_info['available_backends']
            }
        )
    
    except Exception as e:
        logger.error(f"[API] 예상치 못한 오류: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error_type": type(e).__name__,
                "message": str(e)
            }
        )


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = None, backend: str = None):
    """
    음성 파일을 받아 텍스트로 변환
    
    Parameters:
    - file: 음성 파일 (WAV, MP3, M4A, FLAC 등)
    - language: 언어 코드 (선택사항, 예: "en", "ko", "ja")
    - backend: (무시됨, 호환성 유지용) 
               백엔드를 변경하려면 POST /backend/reload를 사용하세요.
               예: POST /backend/reload {"backend": "transformers"}
    
    Returns:
    - success: 처리 성공 여부
    - text: 인식된 텍스트
    - language: 감지된 언어
    - duration: 오디오 길이 (초)
    - backend: 사용된 백엔드
    - file_size_mb: 업로드된 파일 크기
    - memory_info: 메모리 상태 정보 (경고/오류 시)
    """
    if stt is None:
        logger.error("[API] STT 모델이 로드되지 않음")
        raise HTTPException(status_code=503, detail="STT 모델이 로드되지 않음")
    
    tmp_path = None
    try:
        # 파일 정보 로깅
        backend_param = f", backend: {backend}" if backend else ""
        logger.info(f"[API] 음성 파일 업로드 요청: {file.filename}{backend_param}")
        
        # backend 파라미터가 전달된 경우 경고
        if backend:
            logger.warning(f"[API] ⚠️  backend 파라미터는 무시됩니다. 백엔드를 변경하려면 POST /backend/reload를 사용하세요.")
        
        logger.debug(f"[API] Content-Type: {file.content_type}, Size: {file.size if hasattr(file, 'size') else 'unknown'}")

        
        # 임시 파일에 저장
        logger.debug(f"[API] 임시 파일에 저장 중...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            try:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name
                logger.debug(f"✓ 임시 파일 저장 완료: {tmp_path}")
            except Exception as e:
                logger.error(f"❌ 파일 저장 실패: {type(e).__name__}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "파일 저장 실패",
                        "message": str(e)
                    }
                )
        
        file_size_mb = len(content) / (1024**2)
        logger.info(f"[API] 파일 크기: {file_size_mb:.2f}MB, 임시 경로: {tmp_path}")
        
        # 파일 검증
        logger.debug(f"[API] 파일 검증 중...")
        try:
            file_check = check_audio_file(tmp_path, logger=logger)
            if not file_check['valid']:
                error_msg = file_check['errors'][0] if file_check['errors'] else "알 수 없는 오류"
                logger.error(f"[API] 파일 검증 실패: {error_msg}")
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "파일 검증 실패",
                        "message": error_msg,
                        "file_size_mb": file_size_mb
                    }
                )
            
            logger.info(f"✓ 파일 검증 완료 (길이: {file_check['duration_sec']:.1f}초)")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[API] 파일 검증 중 오류: {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "파일 검증 중 오류",
                    "message": str(e)
                }
            )
        
        # 경고 로깅
        for warning in file_check['warnings']:
            logger.warning(f"[API] {warning}")
        
        # 메모리 상태 확인
        logger.debug(f"[API] 메모리 확인 중...")
        try:
            memory_info = check_memory_available(logger=logger)
            if memory_info['critical']:
                logger.error(f"[API] 메모리 부족: {memory_info['message']}")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "메모리 부족",
                        "message": memory_info['message'],
                        "memory_info": memory_info
                    }
                )
            
            logger.info(f"✓ 메모리 확인 완료 (사용 가능: {memory_info['available_mb']:.0f}MB)")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[API] 메모리 확인 중 오류: {type(e).__name__}: {e}", exc_info=True)
            memory_info = {}
        
        # STT 처리
        logger.info(f"[API] STT 처리 시작 (파일: {file.filename}, 길이: {file_check['duration_sec']:.1f}초, 언어: {language})")
        try:
            result = stt.transcribe(tmp_path, language=language, backend=backend)
            logger.info(f"[API] STT 처리 완료 - 백엔드: {result.get('backend', 'unknown')}, 성공: {result.get('success', False)}")
        except Exception as e:
            logger.error(f"[API] STT 처리 중 예상치 못한 오류: {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "STT 처리 중 오류",
                    "message": str(e),
                    "error_type": type(e).__name__
                }
            )
        
        # 에러 확인
        if "error" in result or not result.get('success', False):
            error_msg = result.get('error', '알 수 없는 오류')
            logger.error(f"[API] STT 처리 오류: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_type": result.get('error_type', 'unknown'),
                "backend": result.get('backend', 'unknown'),
                "file_size_mb": file_size_mb,
                "memory_info": memory_info,
                "segment_failed": result.get('segment_failed'),
                "partial_text": result.get('partial_text', ''),
                "suggestion": result.get('suggestion')
            }
        
        logger.info(f"[API] ✅ STT 처리 성공 - 텍스트: {len(result.get('text', ''))} 글자")
        
        return {
            "success": True,
            "text": result.get("text", ""),
            "language": result.get("language", "unknown"),
            "duration": result.get("duration", None),
            "backend": result.get("backend", "unknown"),
            "file_size_mb": file_size_mb,
            "segments_processed": result.get("segments_processed"),
            "memory_info": {
                "available_mb": memory_info['available_mb'],
                "used_percent": memory_info['used_percent']
            }
        }
    
    except HTTPException:
        raise
    
    except MemoryError as e:
        logger.error(f"[API] 메모리 부족 오류: {str(e)}")
        memory_info = check_memory_available(logger=logger)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "메모리 부족",
                "message": str(e),
                "memory_info": memory_info,
                "suggestion": "서버 메모리를 늘리거나 더 작은 파일을 처리하세요"
            }
        )
    
    except Exception as e:
        logger.error(f"[API] 예상치 못한 오류: {type(e).__name__}: {str(e)}")
        logger.error("Traceback:", exc_info=True)
        memory_info = check_memory_available(logger=logger)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "처리 오류",
                "error_type": type(e).__name__,
                "message": str(e)[:200],
                "memory_info": memory_info
            }
        )
    
    finally:
        # 임시 파일 삭제
        if tmp_path and Path(tmp_path).exists():
            try:
                Path(tmp_path).unlink()
                logger.debug(f"[API] 임시 파일 삭제: {tmp_path}")
            except Exception as e:
                logger.warning(f"[API] 임시 파일 삭제 실패: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
