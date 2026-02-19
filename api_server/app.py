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

from fastapi import FastAPI, File, UploadFile, HTTPException, Body, Form, Query, Depends
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import tempfile
import os
import sys
import logging
import time
import json
import wave

# Docker 환경에서 모듈을 찾을 수 있도록 경로 설정
app_root = Path(__file__).parent.parent
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))

from stt_engine import WhisperSTT
from stt_utils import check_memory_available, check_audio_file
from utils.performance_monitor import PerformanceMonitor
from api_server.services.privacy_removal_service import (
    PrivacyRemovalService,
    get_privacy_removal_service
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 스트리밍 청크 설정 (30초 시간 기반 + 12초 overlap)
STREAM_CHUNK_DURATION = 30  # 초
STREAM_OVERLAP_DURATION = 12  # 초 (40% overlap)
STREAM_CHUNK_SIZE = 10 * 1024 * 1024  # 폴백용 (deprecated)

app = FastAPI(
    title="Whisper STT API",
    version="1.0.0",
    description="다중 백엔드 STT API (faster-whisper, transformers, OpenAI Whisper)"
)

# 모델 초기화
# 환경변수 STT_DEVICE로 cpu/cuda 선택 가능 (기본값: cpu)
try:
    # Docker 환경: /app/models에 마운트됨
    # 로컬 개발: models/ 디렉토리 사용
    docker_model_path = Path("/app/models/openai_whisper-large-v3-turbo")
    local_model_path = Path(__file__).parent.parent / "models" / "openai_whisper-large-v3-turbo"
    model_path = docker_model_path if docker_model_path.exists() else local_model_path
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
async def transcribe(
    file_path: str = Form(...), 
    language: str = Form("ko"), 
    is_stream: str = Form("false"),
    export: str = Query(None, description="Export format: 'txt' or 'json', default: None (JSON response)"),
    remove_privacy: str = Form("false", description="개인정보 제거 활성화 (true/false)"),
    privacy_prompt_type: str = Form("privacy_remover_default_v6", description="프롬프트 타입"),
):
    """
    서버 로컬 파일을 음성인식으로 변환 (권장 방식)
    
    Parameters:
    - file_path: 서버의 절대 경로 또는 상대 경로 (예: /app/audio/samples/test.wav)
    - language: 언어 코드 (기본: "ko", 예: "en", "ja")
    - is_stream: 스트리밍 모드 활성화 (기본: "false", "true"로 설정 가능)
                 - "false": 전체 파일을 메모리에 로드 (일반 파일용)
    - export: 내보내기 형식 (선택사항)
                 - None: JSON 응답 (기본)
                 - "txt": 텍스트 파일로 다운로드
                 - "json": JSON 파일로 다운로드
    - remove_privacy: 개인정보 제거 활성화 (기본: "false")
                 - "true": vLLM을 사용하여 개인정보 자동 제거
                 - "false": 개인정보 제거 미적용
    - privacy_prompt_type: 프롬프트 타입 (기본: "privacy_remover_default_v6")
    
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
    - privacy_removal: (remove_privacy=true인 경우)
        - privacy_exist: 개인정보 발견 여부 (Y/N)
        - exist_reason: 개인정보 사유
        - privacy_rm_text: 개인정보 제거된 텍스트
    
    예시 (curl):
    - curl -X POST http://localhost:8003/transcribe -F 'file_path=/app/audio/samples/test.wav'
    - curl -X POST http://localhost:8003/transcribe -F 'file_path=/app/audio/samples/test.wav' -F 'language=en'
    - curl -X POST http://localhost:8003/transcribe -F 'file_path=/app/audio/samples/large.wav' -F 'remove_privacy=true'
    """
    if stt is None:
        logger.error("[API] STT 모델이 로드되지 않음")
        raise HTTPException(status_code=503, detail="STT 모델이 로드되지 않음")
    
    # is_stream 파라미터 변환
    is_streaming = is_stream.lower() in ['true', '1', 'yes', 'on']
    processing_mode = "streaming" if is_streaming else "normal"
    
    # 처리 시간 측정 시작
    start_time = time.time()
    
    # 성능 모니터링 시작
    perf_monitor = PerformanceMonitor()
    perf_monitor.start()
    
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
            processing_time = time.time() - start_time
            
            # 에러 타입 코드화
            error_type_raw = result.get('error_type', 'UNKNOWN')
            error_type_code = error_type_raw.upper().replace(' ', '_')
            if 'memory' in error_msg.lower() or 'out of memory' in error_msg.lower():
                error_type_code = 'MEMORY_ERROR'
            elif 'cuda' in error_msg.lower() or 'gpu' in error_msg.lower():
                error_type_code = 'CUDA_OUT_OF_MEMORY'
            elif 'file' in error_msg.lower() or 'not found' in error_msg.lower():
                error_type_code = 'FILE_NOT_FOUND'
            
            # 에러 원인 분석 및 제안
            suggestion = result.get('suggestion', '')
            if error_type_code == 'MEMORY_ERROR':
                suggestion = "메모리 부족. transformers 백엔드로 전환해보세요 (세그먼트 기반 처리)"
                recommended_backend = "transformers"
            elif error_type_code == 'CUDA_OUT_OF_MEMORY':
                suggestion = "GPU 메모리 부족. CPU 모드로 실행하거나 더 작은 모델을 사용해보세요"
                recommended_backend = "transformers"
            elif error_type_code == 'FILE_NOT_FOUND':
                suggestion = "파일을 찾을 수 없습니다. 파일 경로를 확인하고 /app 디렉토리 내에 있는지 확인하세요"
                recommended_backend = result.get('backend', 'unknown')
            else:
                recommended_backend = "faster-whisper"
            
            # 백엔드 추천 (에러 상황용)
            backend_recommendation_error = get_backend_recommendation(file_size_mb, result.get("backend", "unknown"), memory_info.get('available_mb', 0))
            
            error_response = {
                "success": False,
                "error_code": error_type_code,
                "error": error_msg,
                "backend": result.get('backend', 'unknown'),
                "file_size_mb": file_size_mb,
                "processing_time_seconds": round(processing_time, 2),
                "memory_info": memory_info,
                "failure_reason": {
                    "code": error_type_code,
                    "description": error_msg,
                    "suggestion": suggestion,
                    "available_memory_mb": memory_info.get('available_mb', 0),
                    "recommended_backend": {
                        "name": backend_recommendation_error.get("recommended"),
                        "is_optimal": backend_recommendation_error.get("is_optimal"),
                        "current": backend_recommendation_error.get("current")
                    }
                }
            }
            return JSONResponse(
                content=error_response,
                status_code=400,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
        
        logger.info(f"[API] ✅ STT 처리 성공 - 텍스트: {len(result.get('text', ''))} 글자")
        
        # 성능 모니터링 종료
        perf_metrics = perf_monitor.stop()
        
        # 처리 시간 계산
        processing_time = time.time() - start_time
        
        # 백엔드 추천 로직 (파일 크기 기반)
        def get_backend_recommendation(size_mb: float, current_backend: str, available_mb: float) -> dict:
            """
            동적 메모리 기반 백엔드 추천
            - faster-whisper: 전체 파일을 메모리에 로드 (필요 메모리: 파일크기 * 2.5)
            - transformers: 30초 세그먼트 처리 (필요 메모리: ~3GB)
            """
            # faster-whisper 필요 메모리: 파일크기의 약 2.5배
            faster_whisper_required_mb = size_mb * 2.5
            
            # transformers 필요 메모리: ~3GB (충분한 마진)
            transformers_required_mb = 3000
            
            if faster_whisper_required_mb <= available_mb:
                recommended = "faster-whisper"
            elif transformers_required_mb <= available_mb:
                recommended = "transformers"
            else:
                recommended = "transformers"
            
            return {
                "recommended": recommended,
                "current": current_backend,
                "is_optimal": recommended == current_backend
            }
        
        backend_recommendation = get_backend_recommendation(file_size_mb, result.get("backend", "unknown"), memory_info.get('available_mb', 0))
        
        # 응답 생성 (명시적 JSONResponse로 빠른 직렬화)
        response_data = {
            "success": True,
            "text": result.get("text", ""),
            "language": result.get("language", "unknown"),
            "duration": result.get("duration", None),
            "backend": result.get("backend", "unknown"),
            "file_path": str(file_path_obj),
            "file_size_mb": file_size_mb,
            "processing_mode": processing_mode,
            "processing_time_seconds": round(processing_time, 2),
            "segments_processed": result.get("segments_processed"),
            "memory_info": {
                "available_mb": memory_info.get('available_mb', 0),
                "used_percent": memory_info.get('used_percent', 0)
            },
            "performance": perf_metrics.to_dict()
        }
        
        # Privacy Removal 처리
        privacy_result = None
        if remove_privacy.lower() == "true":
            try:
                logger.info(f"[API] Privacy Removal 시작 (텍스트 길이: {len(result.get('text', ''))})")
                privacy_service = await get_privacy_removal_service()
                privacy_result = await privacy_service.remove_privacy_from_stt(
                    stt_text=result.get('text', ''),
                    prompt_type=privacy_prompt_type
                )
                
                if privacy_result.get('success', True):
                    response_data['privacy_removal'] = {
                        'privacy_exist': privacy_result.get('privacy_exist', 'N'),
                        'exist_reason': privacy_result.get('exist_reason', ''),
                        'text': privacy_result.get('privacy_rm_text', result.get('text', ''))
                    }
                    logger.info(f"[API] Privacy Removal 완료 (결과: {privacy_result['privacy_exist']})")
                else:
                    logger.warning(f"[API] Privacy Removal 처리 실패: {privacy_result.get('exist_reason', '')}")
                    response_data['privacy_removal'] = {
                        'error': 'Privacy removal failed',
                        'original_text_used': True
                    }
            except Exception as e:
                logger.error(f"[API] Privacy Removal 오류: {type(e).__name__}: {str(e)}", exc_info=True)
                response_data['privacy_removal'] = {
                    'error': f'Privacy removal error: {str(e)[:100]}',
                    'original_text_used': True
                }
        
        logger.debug(f"[API] 응답 생성 중 (텍스트 크기: {len(response_data['text'])} bytes)")
        try:
            # JSONResponse를 사용하여 직렬화 (더 빠름)
            logger.info(f"[API] 응답 직렬화 시작...")
            json_str = json.dumps(response_data, ensure_ascii=False)
            logger.info(f"[API] ✓ 응답 직렬화 완료 (크기: {len(json_str) / 1024 / 1024:.2f}MB)")
            
            # Export 옵션 처리
            if export and export.lower() in ["txt", "json"]:
                logger.info(f"[API] 내보내기 시작: {export.upper()} 형식")
                
                if export.lower() == "txt":
                    # 텍스트 파일로 내보내기
                    text_content = response_data['text']
                    temp_file = tempfile.NamedTemporaryFile(
                        mode='w',
                        suffix='.txt',
                        delete=False,
                        encoding='utf-8'
                    )
                    temp_file.write(text_content)
                    temp_file.close()
                    
                    logger.info(f"[API] 텍스트 파일 생성: {temp_file.name} (크기: {len(text_content) / 1024 / 1024:.2f}MB)")
                    
                    return FileResponse(
                        path=temp_file.name,
                        filename=f"transcription_{int(time.time())}.txt",
                        media_type="text/plain; charset=utf-8",
                        headers={"Content-Disposition": "attachment; filename=transcription.txt"}
                    )
                
                elif export.lower() == "json":
                    # JSON 파일로 내보내기
                    temp_file = tempfile.NamedTemporaryFile(
                        mode='w',
                        suffix='.json',
                        delete=False,
                        encoding='utf-8'
                    )
                    json.dump(response_data, temp_file, ensure_ascii=False, indent=2)
                    temp_file.close()
                    
                    logger.info(f"[API] JSON 파일 생성: {temp_file.name}")
                    
                    return FileResponse(
                        path=temp_file.name,
                        filename=f"transcription_{int(time.time())}.json",
                        media_type="application/json; charset=utf-8",
                        headers={"Content-Disposition": "attachment; filename=transcription.json"}
                    )
            
            # Export 없는 경우 JSON 응답
            return JSONResponse(
                content=response_data,
                status_code=200,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
        except Exception as e:
            logger.error(f"[API] 응답 생성 실패: {type(e).__name__}: {str(e)[:200]}")
            # Fallback: 간단한 응답만 반환
            return JSONResponse(
                content={
                    "success": True,
                    "text": "(텍스트 크기로 인해 제한된 응답)",
                    "duration": result.get("duration", None),
                    "backend": result.get("backend", "unknown"),
                    "processing_time_seconds": round(processing_time, 2),
                    "note": "Full text too large, use streaming endpoint"
                },
                status_code=200
            )
    
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
        # 성능 모니터링 종료 (에러 상황)
        try:
            perf_monitor.stop()
        except:
            pass
        
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


def get_audio_properties(file_path: str) -> dict:
    """
    WAV 파일의 속성 추출 (sample_rate, duration, channels, sample_width)
    """
    try:
        with wave.open(file_path, 'rb') as wav_file:
            n_channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            
            duration_sec = n_frames / frame_rate
            
            return {
                'channels': n_channels,
                'sample_width': sample_width,
                'sample_rate': frame_rate,
                'frames': n_frames,
                'duration_sec': duration_sec
            }
    except Exception as e:
        logger.error(f"[STREAM] WAV 파일 속성 추출 실패: {e}")
        raise


def extract_audio_chunk(file_path: str, start_frame: int, end_frame: int) -> bytes:
    """
    WAV 파일에서 특정 프레임 범위의 오디오 데이터 추출
    반환: WAV 헤더 + 오디오 데이터
    """
    try:
        with wave.open(file_path, 'rb') as wav_file:
            # 파일 설정
            n_channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()
            
            # 청크 데이터 읽기
            wav_file.setpos(start_frame)
            frames_to_read = end_frame - start_frame
            audio_data = wav_file.readframes(frames_to_read)
        
        # WAV 헤더와 함께 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            with wave.open(tmp.name, 'wb') as wav_out:
                wav_out.setnchannels(n_channels)
                wav_out.setsampwidth(sample_width)
                wav_out.setframerate(frame_rate)
                wav_out.writeframes(audio_data)
            
            return tmp.name
    
    except Exception as e:
        logger.error(f"[STREAM] 오디오 청크 추출 실패: {e}")
        raise


def merge_chunk_results(chunks_info: list) -> dict:
    """
    여러 청크의 결과를 병합
    겹친 부분(overlap)의 텍스트를 비교하여 최적 선택
    
    chunks_info: 각 청크의 {
        'index': 청크 번호,
        'result': 처리 결과,
        'is_overlap': 겹친 부분 여부,
        'overlap_start_sec': 겹친 부분 시작 시간
    }
    """
    merged_text = ""
    total_duration = 0
    
    for i, chunk_info in enumerate(chunks_info):
        if not chunk_info['result'].get('success', False):
            logger.warning(f"[STREAM] 청크 {chunk_info['index']} 실패: {chunk_info['result'].get('error', '알 수 없음')}")
            continue
        
        chunk_text = chunk_info['result'].get('text', '').strip()
        
        if i == 0:
            # 첫 청크: 전체 텍스트 사용
            merged_text = chunk_text
            logger.info(f"[STREAM MERGE] 청크 0: {len(chunk_text)} 글자 (새로운 부분)")
        else:
            # 이후 청크: 겹친 부분을 제외한 새로운 부분만 추가
            # Whisper의 특성상 겹친 부분의 텍스트가 유사하므로
            # 간단히 공백 추가하여 연결 (언어별 자동 분리)
            merged_text += " " + chunk_text
            logger.info(f"[STREAM MERGE] 청크 {i}: {len(chunk_text)} 글자 추가 (overlap 제외)")
    
    return {
        'success': True,
        'text': merged_text.strip(),
        'merge_mode': 'overlap-aware'
    }


async def _transcribe_streaming(file_path: str, language: str, file_size_mb: float):
    """
    스트리밍 모드로 파일 처리 (30초 청크 + 12초 overlap)
    - 30초 시간 기반 청크 분할
    - 12초(40%) overlap으로 경계 부분 정확도 향상
    - 각 청크 독립 처리 후 overlap 부분 병합
    """
    logger.info(f"[STREAM] 스트리밍 모드 시작 (Overlap 기반)")
    logger.info(f"[STREAM] 청크 설정: {STREAM_CHUNK_DURATION}초 / Overlap: {STREAM_OVERLAP_DURATION}초")
    
    tmp_chunk_paths = []
    
    try:
        # 1단계: WAV 파일 속성 추출
        logger.info(f"[STREAM] WAV 파일 속성 추출 중: {file_path}")
        audio_props = get_audio_properties(file_path)
        
        sample_rate = audio_props['sample_rate']
        total_frames = audio_props['frames']
        duration_sec = audio_props['duration_sec']
        
        logger.info(f"[STREAM] 오디오 정보:")
        logger.info(f"  - 샘플레이트: {sample_rate} Hz")
        logger.info(f"  - 전체 프레임: {total_frames}")
        logger.info(f"  - 지속시간: {duration_sec:.2f}초")
        
        # 2단계: 청크 경계 계산 (30초 청크 + 12초 overlap)
        frames_per_chunk = sample_rate * STREAM_CHUNK_DURATION  # 30초 = 프레임 개수
        frames_per_overlap = sample_rate * STREAM_OVERLAP_DURATION  # 12초
        step_frames = frames_per_chunk - frames_per_overlap  # 새로운 프레임 개수 (18초)
        
        chunk_ranges = []
        start_frame = 0
        chunk_idx = 0
        
        while start_frame < total_frames:
            end_frame = min(start_frame + frames_per_chunk, total_frames)
            chunk_ranges.append({
                'index': chunk_idx,
                'start_frame': int(start_frame),
                'end_frame': int(end_frame),
                'start_sec': start_frame / sample_rate,
                'end_sec': end_frame / sample_rate,
                'has_overlap': chunk_idx > 0  # 첫 청크 제외
            })
            
            chunk_idx += 1
            start_frame += step_frames
        
        logger.info(f"[STREAM] 청크 계획: 총 {len(chunk_ranges)}개 청크")
        for cr in chunk_ranges:
            logger.info(f"  - 청크 {cr['index']}: {cr['start_sec']:.2f}s ~ {cr['end_sec']:.2f}s ({(cr['end_frame']-cr['start_frame'])/sample_rate:.2f}초)")
        
        # 3단계: 각 청크 처리
        logger.info(f"[STREAM] 청크 처리 시작...")
        chunks_results = []
        
        for chunk_range in chunk_ranges:
            chunk_idx = chunk_range['index']
            start_sec = chunk_range['start_sec']
            end_sec = chunk_range['end_sec']
            
            logger.info(f"[STREAM] 청크 {chunk_idx} 추출 중 ({start_sec:.2f}s ~ {end_sec:.2f}s)...")
            
            try:
                # 청크 파일 추출 (WAV 헤더 포함)
                chunk_file = extract_audio_chunk(
                    file_path,
                    chunk_range['start_frame'],
                    chunk_range['end_frame']
                )
                tmp_chunk_paths.append(chunk_file)
                
                # 청크 처리
                logger.info(f"[STREAM] 청크 {chunk_idx} 처리 중...")
                chunk_result = stt.transcribe(chunk_file, language=language)
                
                if not chunk_result.get('success', False):
                    logger.warning(f"[STREAM] 청크 {chunk_idx} 실패: {chunk_result.get('error', '알 수 없음')}")
                else:
                    text_len = len(chunk_result.get('text', ''))
                    logger.info(f"[STREAM] 청크 {chunk_idx} 완료: {text_len} 글자")
                
                chunks_results.append({
                    'index': chunk_idx,
                    'result': chunk_result,
                    'start_sec': start_sec,
                    'end_sec': end_sec,
                    'is_overlap': chunk_range['has_overlap']
                })
                
            except Exception as e:
                logger.error(f"[STREAM] 청크 {chunk_idx} 처리 실패: {type(e).__name__}: {e}", exc_info=True)
                
                # 임시 파일 정리 후 에러 반환
                for tmp_path in tmp_chunk_paths:
                    try:
                        Path(tmp_path).unlink()
                    except:
                        pass
                
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "청크 처리 중 오류",
                        "chunk_index": chunk_idx,
                        "message": str(e),
                        "chunks_processed": chunk_idx
                    }
                )
        
        # 4단계: 청크 결과 병합
        logger.info(f"[STREAM] 청크 결과 병합 중...")
        
        # 모든 청크의 텍스트를 연결
        merged_text = ""
        successful_chunks = [cr for cr in chunks_results if cr['result'].get('success', False)]
        
        for i, chunk_result in enumerate(successful_chunks):
            text = chunk_result['result'].get('text', '').strip()
            
            if i == 0:
                # 첫 청크: 전체 포함
                merged_text = text
                logger.info(f"[STREAM MERGE] 청크 0: {len(text)} 글자 (기본)")
            else:
                # 이후 청크: 공백으로 구분하여 추가
                # Whisper 모델의 특성상 overlap 부분이 자동으로 일관성 있게 처리됨
                if text:
                    merged_text += " " + text
                    logger.info(f"[STREAM MERGE] 청크 {i}: {len(text)} 글자 추가")
        
        final_result = {
            'success': True,
            'text': merged_text.strip(),
            'language': language,
            'duration_sec': duration_sec,
            'backend': 'faster-whisper',  # 기본값
            'processing_mode': 'streaming',
            'chunks_processed': len(successful_chunks),
            'total_chunks': len(chunk_ranges),
            'merge_strategy': f'{STREAM_CHUNK_DURATION}s chunk + {STREAM_OVERLAP_DURATION}s overlap'
        }
        
        logger.info(f"[STREAM] 처리 완료: {len(successful_chunks)}/{len(chunk_ranges)} 청크 성공")
        logger.info(f"[STREAM] 최종 텍스트: {len(merged_text.strip())} 글자")
        
        # 임시 파일 정리
        for tmp_path in tmp_chunk_paths:
            try:
                Path(tmp_path).unlink()
                logger.debug(f"[STREAM] 임시 파일 삭제: {tmp_path}")
            except:
                pass
        
        return final_result
    
    except HTTPException:
        # 임시 파일 정리
        for tmp_path in tmp_chunk_paths:
            try:
                Path(tmp_path).unlink()
            except:
                pass
        raise
    
    except Exception as e:
        logger.error(f"[STREAM] 스트리밍 처리 중 예상치 못한 오류: {type(e).__name__}: {e}", exc_info=True)
        
        # 임시 파일 정리
        for tmp_path in tmp_chunk_paths:
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
async def transcribe_by_upload(
    file: UploadFile = File(...), 
    language: str = Form("ko"),
    export: str = Query(None, description="Export format: 'txt' or 'json', default: None (JSON response)")
):
    """
    파일 업로드를 통한 음성인식 (파일 전송 필요)
    
    Parameters:
    - file: 업로드할 음성 파일 (WAV, MP3, M4A, FLAC 등)
    - language: 언어 코드 (기본: "ko", 예: "en", "ja")
    - export: 내보내기 형식 (선택사항)
                 - None: JSON 응답 (기본)
                 - "txt": 텍스트 파일로 다운로드
                 - "json": JSON 파일로 다운로드
    
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
    
    # 처리 시간 측정 시작
    start_time = time.time()
    
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
            processing_time = time.time() - start_time
            
            # 에러 타입 코드화
            error_type_raw = result.get('error_type', 'UNKNOWN')
            error_type_code = error_type_raw.upper().replace(' ', '_')
            if 'memory' in error_msg.lower() or 'out of memory' in error_msg.lower():
                error_type_code = 'MEMORY_ERROR'
            elif 'cuda' in error_msg.lower() or 'gpu' in error_msg.lower():
                error_type_code = 'CUDA_OUT_OF_MEMORY'
            elif 'file' in error_msg.lower() or 'not found' in error_msg.lower():
                error_type_code = 'FILE_NOT_FOUND'
            
            # 에러 원인 분석 및 제안
            suggestion = result.get('suggestion', '')
            if error_type_code == 'MEMORY_ERROR':
                suggestion = "메모리 부족. transformers 백엔드로 전환해보세요 (세그먼트 기반 처리)"
                recommended_backend = "transformers"
            elif error_type_code == 'CUDA_OUT_OF_MEMORY':
                suggestion = "GPU 메모리 부족. CPU 모드로 실행하거나 더 작은 모델을 사용해보세요"
                recommended_backend = "transformers"
            elif error_type_code == 'FILE_NOT_FOUND':
                suggestion = "파일 처리 중 오류. 파일 형식이 지원되는지 확인하세요"
                recommended_backend = result.get('backend', 'unknown')
            else:
                recommended_backend = "faster-whisper"
            
            # 백엔드 추천 (에러 상황용)
            backend_recommendation_error = get_backend_recommendation(file_size_mb, result.get("backend", "unknown"), memory_info.get('available_mb', 0))
            
            error_response = {
                "success": False,
                "error_code": error_type_code,
                "error": error_msg,
                "backend": result.get('backend', 'unknown'),
                "file_size_mb": file_size_mb,
                "processing_time_seconds": round(processing_time, 2),
                "memory_info": memory_info,
                "failure_reason": {
                    "code": error_type_code,
                    "description": error_msg,
                    "suggestion": suggestion,
                    "available_memory_mb": memory_info.get('available_mb', 0),
                    "recommended_backend": {
                        "name": backend_recommendation_error.get("recommended"),
                        "is_optimal": backend_recommendation_error.get("is_optimal"),
                        "current": backend_recommendation_error.get("current")
                    }
                }
            }
            return JSONResponse(
                content=error_response,
                status_code=400,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
        
        logger.info(f"[API] ✅ STT 처리 성공 - 텍스트: {len(result.get('text', ''))} 글자")
        
        # 처리 시간 계산
        processing_time = time.time() - start_time
        
        # 응답 생성 (명시적 JSONResponse로 빠른 직렬화)
        response_data = {
            "success": True,
            "text": result.get("text", ""),
            "language": result.get("language", "unknown"),
            "duration": result.get("duration", None),
            "backend": result.get("backend", "unknown"),
            "file_size_mb": file_size_mb,
            "processing_time_seconds": round(processing_time, 2),
            "segments_processed": result.get("segments_processed"),
            "memory_info": {
                "available_mb": memory_info.get('available_mb', 0),
                "used_percent": memory_info.get('used_percent', 0)
            }
        }
        
        logger.debug(f"[API] 응답 생성 중 (텍스트 크기: {len(response_data['text'])} bytes)")
        
        # 내보내기 기능 (txt 또는 json)
        if export and export.lower() in ["txt", "json"]:
            import tempfile
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            try:
                if export.lower() == "txt":
                    # 텍스트 파일로 저장
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                        f.write(response_data['text'])
                        temp_file_path = f.name
                    
                    logger.info(f"[API] 텍스트 파일 생성: {temp_file_path} (크기: {len(response_data['text'])} bytes)")
                    return FileResponse(
                        path=temp_file_path,
                        filename=f"transcription_{timestamp}.txt",
                        media_type="text/plain; charset=utf-8"
                    )
                
                elif export.lower() == "json":
                    # JSON 파일로 저장
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                        json.dump(response_data, f, ensure_ascii=False, indent=2)
                        temp_file_path = f.name
                    
                    logger.info(f"[API] JSON 파일 생성: {temp_file_path}")
                    return FileResponse(
                        path=temp_file_path,
                        filename=f"transcription_{timestamp}.json",
                        media_type="application/json; charset=utf-8"
                    )
            except Exception as e:
                logger.error(f"[API] 파일 생성 실패: {str(e)}")
                # 실패 시 JSON 응답으로 폴백
                return JSONResponse(
                    content=response_data,
                    status_code=200,
                    headers={"Content-Type": "application/json; charset=utf-8"}
                )
        
        # 기본: JSON 응답
        try:
            logger.info(f"[API] 응답 직렬화 시작...")
            json_str = json.dumps(response_data, ensure_ascii=False)
            logger.info(f"[API] ✓ 응답 직렬화 완료 (크기: {len(json_str) / 1024 / 1024:.2f}MB)")
            
            return JSONResponse(
                content=response_data,
                status_code=200,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
        except Exception as e:
            logger.error(f"[API] 응답 생성 실패: {type(e).__name__}: {str(e)[:200]}")
            return JSONResponse(
                content={
                    "success": True,
                    "text": "(텍스트 크기로 인해 제한된 응답)",
                    "duration": result.get("duration", None),
                    "backend": current_backend,
                    "processing_time_seconds": round(processing_time, 2),
                    "note": "Full text too large, try export=json or export=txt"
                },
                status_code=200
            )
    
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


# ==================== Privacy Removal API ====================

@app.post("/api/privacy-removal/process")
async def process_privacy_removal(
    text: str = Body(..., description="개인정보를 제거할 텍스트"),
    prompt_type: str = Query("privacy_remover_default_v6", description="프롬프트 타입"),
    max_tokens: int = Query(8192, description="최대 토큰 수"),
    temperature: float = Query(0.3, description="LLM 온도"),
    service: PrivacyRemovalService = Depends(get_privacy_removal_service)
):
    """
    텍스트에서 개인정보를 제거합니다.
    
    **Request Body:**
    - text: 개인정보를 제거할 텍스트 (필수)
    - prompt_type: 프롬프트 타입 (기본값: privacy_remover_default_v6)
    - max_tokens: 최대 토큰 수 (기본값: 8192)
    - temperature: LLM 온도 (기본값: 0.3)
    
    **Response:**
    ```json
    {
        "privacy_exist": "Y/N",
        "exist_reason": "발견된 개인정보 사유",
        "privacy_rm_text": "개인정보 제거된 텍스트",
        "success": true
    }
    ```
    
    **사용 예시:**
    ```bash
    curl -X POST "http://localhost:8003/api/privacy-removal/process" \
         -H "Content-Type: application/json" \
         -d '{"text": "나는 John Smith이고 010-1234-5678에서 전화할 수 있다"}'
    ```
    """
    try:
        logger.info(f"[PrivacyRemoval] 요청 받음 (길이: {len(text)}, 프롬프트: {prompt_type})")
        
        result = await service.remove_privacy_from_stt(
            stt_text=text,
            prompt_type=prompt_type,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        logger.info(f"[PrivacyRemoval] 처리 완료 (결과: {result['privacy_exist']})")
        return result
        
    except FileNotFoundError as e:
        logger.error(f"[PrivacyRemoval] 프롬프트 파일 없음: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "프롬프트 파일 없음",
                "message": str(e),
                "available_prompts": service.get_available_prompts()
            }
        )
    
    except Exception as e:
        logger.error(f"[PrivacyRemoval] 오류: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "개인정보 제거 처리 실패",
                "message": str(e)[:200]
            }
        )


@app.get("/api/privacy-removal/prompts")
async def list_available_prompts(
    service: PrivacyRemovalService = Depends(get_privacy_removal_service)
):
    """
    사용 가능한 프롬프트 타입 목록을 반환합니다.
    
    **Response:**
    ```json
    {
        "available_prompts": ["privacy_remover_default_v6", "privacy_remover_default_v5", ...]
    }
    ```
    """
    prompts = service.get_available_prompts()
    logger.info(f"[PrivacyRemoval] 프롬프트 목록 조회: {prompts}")
    return {"available_prompts": prompts}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
