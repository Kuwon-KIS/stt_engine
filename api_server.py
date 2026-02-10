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

from fastapi import FastAPI, File, UploadFile, HTTPException, Body, Form
from pathlib import Path
import tempfile
import os
import logging
from stt_engine import WhisperSTT
from stt_utils import check_memory_available, check_audio_file
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 스트리밍 청크 크기 (10MB)
STREAM_CHUNK_SIZE = 10 * 1024 * 1024

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
async def reload_backend(request_body: dict = Body(None)):
    """
    백엔드를 재로드합니다.
    
    Parameters:
    - backend: 로드할 백엔드 (선택사항, JSON body에서)
               - "faster-whisper": faster-whisper 사용
               - "transformers": transformers 사용
               - "openai-whisper": OpenAI Whisper 사용
               - null/생략: 기본 순서대로 자동 선택 (faster-whisper → transformers → openai-whisper)
    
    Returns:
    - status: "success" | "error"
    - message: 처리 결과 메시지
    - loaded_backend: 로드된 백엔드 이름
    - backend_info: 로드 후 백엔드 정보
    
    예시 (curl):
    - curl -X POST http://localhost:8003/backend/reload -H "Content-Type: application/json" -d '{"backend": "transformers"}'
    - curl -X POST http://localhost:8003/backend/reload -H "Content-Type: application/json" -d '{}'
    """
    if stt is None:
        raise HTTPException(status_code=503, detail="STT 모델이 로드되지 않음")
    
    # JSON body에서 backend 파라미터 추출
    backend = None
    if request_body and isinstance(request_body, dict):
        backend = request_body.get('backend')
    
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
async def transcribe(file_path: str = Form(...), language: str = Form("ko"), is_stream: str = Form("false")):
    """
    서버 로컬 파일을 음성인식으로 변환 (권장 방식)
    
    Parameters:
    - file_path: 서버의 절대 경로 또는 상대 경로 (예: /app/audio/samples/test.wav)
    - language: 언어 코드 (기본: "ko", 예: "en", "ja")
    - is_stream: 스트리밍 모드 활성화 (기본: "false", "true"로 설정 가능)
                 - "false": 전체 파일을 메모리에 로드 (일반 파일용)
                 - "true": 청크 단위로 순차 처리 (대용량 파일용)
    
    Returns:
    - success: 처리 성공 여부
    - text: 인식된 텍스트
    - language: 감지된 언어
    - duration: 오디오 길이 (초)
    - backend: 사용된 백엔드
    - file_path: 처리한 파일 경로
    - file_size_mb: 파일 크기
    - memory_info: 메모리 상태 정보
    - processing_mode: "normal" | "streaming"
    
    예시 (curl):
    - curl -X POST http://localhost:8003/transcribe -F 'file_path=/app/audio/samples/test.wav'
    - curl -X POST http://localhost:8003/transcribe -F 'file_path=/app/audio/samples/test.wav' -F 'language=en'
    - curl -X POST http://localhost:8003/transcribe -F 'file_path=/app/audio/samples/large.wav' -F 'is_stream=true'
    """
    if stt is None:
        logger.error("[API] STT 모델이 로드되지 않음")
        raise HTTPException(status_code=503, detail="STT 모델이 로드되지 않음")
    
    # is_stream 파라미터 변환
    is_streaming = is_stream.lower() in ['true', '1', 'yes', 'on']
    processing_mode = "streaming" if is_streaming else "normal"
    
    try:
        # 1. 파일 경로 검증 (보안: /app 내부만 허용)
        file_path_obj = Path(file_path).resolve()
        allowed_dir = Path("/app").resolve() if Path("/app").exists() else Path.cwd().resolve()
        
        logger.info(f"[API] 파일 경로 처리 시작")
        logger.debug(f"[API] 요청 경로: {file_path}")
        logger.debug(f"[API] 확인된 경로: {file_path_obj}")
        logger.debug(f"[API] 허용 디렉토리: {allowed_dir}")
        
        # 경로가 허용 디렉토리 내에 있는지 확인
        try:
            file_path_obj.relative_to(allowed_dir)
        except ValueError:
            error_msg = f"파일 경로가 허용된 디렉토리 외에 있음: {file_path}"
            logger.error(f"[API] ❌ {error_msg}")
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "접근 금지",
                    "message": error_msg,
                    "allowed_directory": str(allowed_dir)
                }
            )
        
        # 파일 존재 확인
        if not file_path_obj.exists():
            error_msg = f"파일을 찾을 수 없음: {file_path_obj}"
            logger.error(f"[API] ❌ {error_msg}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "파일 없음",
                    "message": error_msg,
                    "file_path": str(file_path_obj)
                }
            )
        
        # 일반 파일인지 확인
        if not file_path_obj.is_file():
            error_msg = f"경로가 파일이 아님: {file_path_obj}"
            logger.error(f"[API] ❌ {error_msg}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "잘못된 경로",
                    "message": error_msg
                }
            )
        
        file_size_mb = file_path_obj.stat().st_size / (1024**2)
        logger.info(f"[API] 로컬 파일 요청: {file_path_obj.name} ({file_size_mb:.2f}MB)")
        logger.info(f"[API] 처리 모드: {processing_mode}, 언어: {language}")
        
        # 2. 파일 검증
        logger.debug(f"[API] 파일 검증 중...")
        try:
            file_check = check_audio_file(str(file_path_obj), logger=logger)
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
        
        # 3. 메모리 확인
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
        
        # 4. 처리 방식에 따른 STT 처리
        logger.info(f"[API] STT 처리 시작 (파일: {file_path_obj.name}, 길이: {file_check['duration_sec']:.1f}초, 언어: {language})")
        
        if is_streaming:
            # 스트리밍 모드: 청크 단위 처리
            result = await _transcribe_streaming(str(file_path_obj), language, file_size_mb)
        else:
            # 일반 모드: 직접 처리
            try:
                result = stt.transcribe(str(file_path_obj), language=language)
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
        
        # 5. 에러 확인
        if "error" in result or not result.get('success', False):
            error_msg = result.get('error', '알 수 없는 오류')
            logger.error(f"[API] STT 처리 오류: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_type": result.get('error_type', 'unknown'),
                "backend": result.get('backend', 'unknown'),
                "file_path": str(file_path_obj),
                "file_size_mb": file_size_mb,
                "processing_mode": processing_mode,
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
            "file_path": str(file_path_obj),
            "file_size_mb": file_size_mb,
            "processing_mode": processing_mode,
            "segments_processed": result.get("segments_processed"),
            "memory_info": {
                "available_mb": memory_info.get('available_mb', 0),
                "used_percent": memory_info.get('used_percent', 0)
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
                "suggestion": "서버 메모리를 늘리거나 더 작은 파일을 처리하세요. is_stream=true로 스트리밍 모드를 시도하세요."
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


async def _transcribe_streaming(file_path: str, language: str, file_size_mb: float):
    """
    스트리밍 모드로 파일 처리 (청크 단위)
    대용량 파일을 청크로 나누어 순차 처리
    """
    logger.info(f"[STREAM] 스트리밍 모드로 처리 시작: {file_path}")
    logger.info(f"[STREAM] 청크 크기: {STREAM_CHUNK_SIZE / (1024**2):.1f}MB, 파일 크기: {file_size_mb:.2f}MB")
    
    tmp_path = None
    try:
        # 청크 단위로 파일 읽기
        with open(file_path, 'rb') as f:
            chunk_count = 0
            tmp_paths = []
            
            while True:
                chunk_data = f.read(STREAM_CHUNK_SIZE)
                if not chunk_data:
                    break
                
                chunk_count += 1
                chunk_size_mb = len(chunk_data) / (1024**2)
                logger.info(f"[STREAM] 청크 {chunk_count} 읽기 완료 ({chunk_size_mb:.2f}MB)")
                
                # 임시 파일에 청크 저장
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    tmp.write(chunk_data)
                    tmp_path = tmp.name
                    tmp_paths.append(tmp_path)
                    logger.debug(f"[STREAM] 청크 {chunk_count} 임시 파일: {tmp_path}")
                
                # 청크 처리
                try:
                    logger.info(f"[STREAM] 청크 {chunk_count} 처리 중...")
                    result = stt.transcribe(tmp_path, language=language)
                    
                    if not result.get('success', False):
                        logger.warning(f"[STREAM] 청크 {chunk_count} 처리 실패: {result.get('error', '알 수 없는 오류')}")
                    else:
                        logger.info(f"[STREAM] 청크 {chunk_count} 처리 완료: {len(result.get('text', ''))} 글자")
                
                except Exception as e:
                    logger.error(f"[STREAM] 청크 {chunk_count} 처리 중 오류: {type(e).__name__}: {e}", exc_info=True)
                    
                    # 청크 처리 실패시 임시 파일 정리
                    for tmp in tmp_paths:
                        try:
                            Path(tmp).unlink()
                        except:
                            pass
                    
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "error": "청크 처리 중 오류",
                            "message": str(e),
                            "chunk_number": chunk_count,
                            "chunks_processed": chunk_count - 1
                        }
                    )
        
        # 모든 청크 처리 완료
        logger.info(f"[STREAM] 모든 청크 처리 완료 ({chunk_count}개 청크)")
        
        # 최종 결과 반환
        result = stt.transcribe(file_path, language=language)
        
        # 임시 파일 정리
        for tmp in tmp_paths:
            try:
                Path(tmp).unlink()
                logger.debug(f"[STREAM] 임시 파일 삭제: {tmp}")
            except:
                pass
        
        return result
    
    except HTTPException:
        # 임시 파일 정리
        if tmp_path and Path(tmp_path).exists():
            try:
                Path(tmp_path).unlink()
            except:
                pass
        raise
    
    except Exception as e:
        logger.error(f"[STREAM] 스트리밍 처리 중 예상치 못한 오류: {type(e).__name__}: {e}", exc_info=True)
        # 임시 파일 정리
        if tmp_path and Path(tmp_path).exists():
            try:
                Path(tmp_path).unlink()
            except:
                pass
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "스트리밍 처리 중 오류",
                "error_type": type(e).__name__,
                "message": str(e)
            }
        )


@app.post("/transcribe_by_upload")
async def transcribe_by_upload(file: UploadFile = File(...), language: str = Form("ko")):
    """
    파일 업로드를 통한 음성인식 (파일 전송 필요)
    
    Parameters:
    - file: 업로드할 음성 파일 (WAV, MP3, M4A, FLAC 등)
    - language: 언어 코드 (기본: "ko", 예: "en", "ja")
    
    Returns:
    - success: 처리 성공 여부
    - text: 인식된 텍스트
    - language: 감지된 언어
    - duration: 오디오 길이 (초)
    - backend: 사용된 백엔드
    - file_size_mb: 업로드된 파일 크기
    - memory_info: 메모리 상태 정보
    
    예시 (curl):
    - curl -X POST http://localhost:8003/transcribe_by_upload -F 'file=@test.wav'
    - curl -X POST http://localhost:8003/transcribe_by_upload -F 'file=@test.wav' -F 'language=en'
    
    주의사항:
    - 백엔드를 변경하려면 먼저 POST /backend/reload를 호출하세요
    """
    if stt is None:
        logger.error("[API] STT 모델이 로드되지 않음")
        raise HTTPException(status_code=503, detail="STT 모델이 로드되지 않음")
    
    tmp_path = None
    try:
        # 파일 정보 로깅
        language_param = f", language: {language}" if language else ""
        logger.info(f"[API] 음성 파일 업로드 요청: {file.filename}{language_param}")
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
            result = stt.transcribe(tmp_path, language=language)
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
                "available_mb": memory_info.get('available_mb', 0),
                "used_percent": memory_info.get('used_percent', 0)
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
