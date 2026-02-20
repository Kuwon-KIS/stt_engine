"""
Web UI 서버 메인 앱
"""
import asyncio
import time
import aiohttp
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import logging

# 커스텀 로거 설정
from utils.logger import get_logger
logger = get_logger(__name__)

# 설정 및 서비스 임포트
from config import (
    WEB_HOST, WEB_PORT, 
    CORS_ORIGINS,
    UPLOAD_DIR, RESULT_DIR, BATCH_INPUT_DIR,
    STT_API_URL
)
from models.schemas import (
    FileUploadResponse, TranscribeRequest, TranscribeResponse,
    BatchFileListResponse, BatchStartRequest, BatchStartResponse,
    BatchProgressResponse
)
from services.stt_service import stt_service
from services.file_service import file_service
from services.batch_service import batch_service, FileStatus
from services.job_queue import transcribe_queue, JobStatus

# FastAPI 앱 생성
app = FastAPI(
    title="KIS 불완전판매 예방 녹취 분석 시스템",
    version="1.0.0",
    description="금융상품 판매 사전 녹취 음성을 텍스트로 변환하여 불완전판매 예방 및 규정 준수 검토"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if isinstance(CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CSP (Content Security Policy) 헤더 설정 - 보안 프로그램 호환성 개선
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # CSP 헤더 설정 - 보안 프로그램(Menlo Security 등)과의 호환성 개선
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' http://* https://*; "
            "style-src 'self' 'unsafe-inline' http://* https://* https://fonts.googleapis.com; "
            "font-src 'self' http://* https://* https://fonts.gstatic.com data:; "
            "img-src 'self' http://* https://* data:; "
            "connect-src 'self' http://* https://* wss://*; "
            "frame-src 'self'; "
            "object-src 'none';"
        )
        return response

app.add_middleware(CSPMiddleware)

# 정적 파일 마운트
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# 템플릿
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# ============================================================================
# 1. 대시보드 및 기본 라우트
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """대시보드 페이지"""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"대시보드 로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """헬스 체크"""
    stt_healthy = await stt_service.health_check()
    return {
        "status": "healthy" if stt_healthy else "degraded",
        "stt_api": "ok" if stt_healthy else "unreachable"
    }


@app.get("/api/backend/current")
async def get_backend_info():
    """STT API의 현재 백엔드 정보 조회"""
    try:
        backend_info = await stt_service.get_backend_info()
        return backend_info
    except Exception as e:
        logger.error(f"백엔드 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="백엔드 정보를 조회할 수 없습니다")


@app.post("/api/backend/reload")
async def reload_backend(request_data: dict = None):
    """STT API의 백엔드 재로드"""
    try:
        backend = None
        if request_data and isinstance(request_data, dict):
            backend = request_data.get("backend")
        
        logger.info(f"[Web UI] 백엔드 재로드 요청: {backend or '자동 선택'}")
        
        # STT API에 백엔드 재로드 요청
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            if backend:
                data.add_field("backend", backend)
            
            async with session.post(
                f"{STT_API_URL}/backend/reload",
                json={"backend": backend},
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                result = await response.json()
                logger.info(f"[Web UI] API 백엔드 재로드 완료: {result}")
                return result
    except Exception as e:
        logger.error(f"백엔드 재로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"백엔드 재로드 실패: {str(e)}")


# ============================================================================
# 2. 파일 업로드 라우트
# ============================================================================

@app.post("/api/upload/", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    """파일 업로드"""
    try:
        # 파일 데이터 읽기
        file_data = await file.read()
        file_size = len(file_data)
        
        logger.info(f"파일 업로드: {file.filename} ({file_size / (1024*1024):.2f}MB)")
        
        # 유효성 검증
        is_valid, error_msg = file_service.validate_file(file.filename, file_size)
        if not is_valid:
            logger.warning(f"파일 검증 실패: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 파일 저장
        start_time = time.time()
        file_id, saved_path = file_service.save_upload_file(file_data, file.filename)
        upload_time = time.time() - start_time
        
        return FileUploadResponse(
            success=True,
            file_id=file_id,
            filename=file.filename,
            original_filename=file.filename,
            file_size_mb=file_size / (1024 * 1024),
            upload_time_sec=upload_time
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 3. STT 처리 라우트
# ============================================================================

@app.post("/api/transcribe/", response_model=TranscribeResponse)
async def transcribe(request: TranscribeRequest) -> TranscribeResponse:
    """업로드된 파일 STT 처리"""
    try:
        # 파일 경로 재구성
        file_path = UPLOAD_DIR / f"{request.file_id}*"
        files = list(UPLOAD_DIR.glob(f"{request.file_id}*"))
        
        logger.info(f"[Transcribe] POST /api/transcribe/ 요청 수신")
        logger.info(f"[Transcribe] file_id: {request.file_id}")
        logger.info(f"[Transcribe] 업로드 디렉토리 검색: {UPLOAD_DIR}")
        logger.info(f"[Transcribe] 발견된 파일 수: {len(files)}")
        
        if not files:
            logger.error(f"[Transcribe] 파일을 찾을 수 없습니다: {request.file_id}")
            logger.error(f"[Transcribe] 업로드 디렉토리 내용:")
            try:
                for item in UPLOAD_DIR.iterdir():
                    logger.error(f"  - {item}")
            except:
                logger.error(f"[Transcribe] 디렉토리 읽기 실패")
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
        
        file_path = str(files[0])
        logger.info(f"[Transcribe] 파일 발견: {file_path}")
        
        logger.info(f"[Transcribe] ===== 처리 시작 =====")
        logger.info(f"[Transcribe] 파일: {file_path}")
        logger.info(f"[Transcribe] 언어: {request.language}, 스트리밍: {request.is_stream}, 백엔드: {request.backend}")
        logger.info(f"[Transcribe] 처리 단계: Privacy={request.privacy_removal}, Classification={request.classification}, AI={request.ai_agent}, IncompleteElements={request.incomplete_elements_check}")
        if request.incomplete_elements_check and request.agent_url:
            logger.info(f"[Transcribe] Agent URL: {request.agent_url}, Format: {request.agent_request_format}")
        logger.info(f"[Transcribe] STT API URL: {STT_API_URL}")
        
        start_time = time.time()
        
        try:
            logger.info(f"[Transcribe] STT 서비스 호출 시작...")
            result = await stt_service.transcribe_local_file(
                file_path=file_path,
                language=request.language,
                is_stream=request.is_stream,
                backend=request.backend,
                privacy_removal=request.privacy_removal,
                classification=request.classification,
                ai_agent=request.ai_agent,
                incomplete_elements_check=request.incomplete_elements_check,
                agent_url=request.agent_url,
                agent_request_format=request.agent_request_format
            )
            logger.info(f"[Transcribe] STT 서비스 호출 완료")
            logger.info(f"[Transcribe] 결과 구조: success={result.get('success')}, keys={list(result.keys())}")
        except Exception as api_call_error:
            logger.error(f"[Transcribe] API 호출 중 예외 발생: {type(api_call_error).__name__}: {api_call_error}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"API 호출 실패: {str(api_call_error)}"
            )
        
        processing_time = time.time() - start_time
        logger.info(f"[Transcribe] 처리 시간: {processing_time:.2f}초")
        
        if not result.get("success"):
            error_msg = result.get("message", "처리 중 오류 발생")
            error_code = result.get("error_code", result.get("error", "UNKNOWN"))
            logger.error(f"[Transcribe] 처리 실패 (code={error_code}): {error_msg}")
            logger.error(f"[Transcribe] 전체 결과: {result}")
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )
        
        # 처리 단계 로깅
        processing_steps = result.get("processing_steps", {})
        logger.info(f"[Transcribe] 처리 단계 완료: STT={processing_steps.get('stt')}, Privacy={processing_steps.get('privacy_removal')}, Classification={processing_steps.get('classification')}, AI={processing_steps.get('ai_agent')}, IncompleteElements={processing_steps.get('incomplete_elements')}")
        
        # 불완전판매요소 검증 결과 로깅
        if request.incomplete_elements_check and result.get('incomplete_elements'):
            incomplete_result = result.get('incomplete_elements', {})
            logger.info(f"[Transcribe] 불완전판매요소 검증 결과: agent_type={incomplete_result.get('agent_type')}")
        
        # Privacy Removal 결과 로깅
        if request.privacy_removal and result.get("privacy_removal"):
            privacy_result = result.get("privacy_removal", {})
            logger.info(f"[Transcribe] Privacy Removal 결과: 개인정보 존재={privacy_result.get('privacy_exist')}, 사유={privacy_result.get('exist_reason')}")
        
        # Classification 결과 로깅
        if request.classification and result.get("classification"):
            class_result = result.get("classification", {})
            logger.info(f"[Transcribe] Classification 결과: 코드={class_result.get('code')}, 신뢰도={class_result.get('confidence')}%, 카테고리={class_result.get('category')}")
        
        # 결과 저장
        file_service.save_result(request.file_id, result.get("text", ""), {
            "filename": Path(file_path).name,
            "language": request.language,
            "duration_sec": result.get("duration", 0),
            "processing_time_sec": processing_time,
            "backend": result.get("backend", "unknown"),
            "processing_steps": processing_steps,
            "privacy_removal": result.get("privacy_removal"),
            "classification": result.get("classification"),
            "incomplete_elements": result.get("incomplete_elements")
        })
        
        # 성능 메트릭 저장
        if result.get("performance"):
            file_service.save_performance_log(request.file_id, result.get("performance"))
        
        logger.info(f"[Transcribe] ===== 처리 완료 =====")
        logger.info(f"[Transcribe] 소요 시간: {processing_time:.2f}초")
        logger.info(f"[Transcribe] 텍스트 길이: {len(result.get('text', ''))} 글자")
        
        text = result.get("text", "")
        word_count = len(text) if text else 0
        
        return TranscribeResponse(
            success=True,
            file_id=request.file_id,
            filename=Path(file_path).name,
            text=text,
            language=request.language,
            duration_sec=result.get("duration", 0),
            processing_time_sec=processing_time,
            backend=result.get("backend", "unknown"),
            word_count=word_count,
            performance=result.get("performance"),
            processing_steps=result.get("processing_steps"),
            privacy_removal=result.get("privacy_removal"),
            classification=result.get("classification"),
            incomplete_elements=result.get("incomplete_elements")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Transcribe] STT 처리 중 예외: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 4. 배치 처리 라우트
# ============================================================================

@app.get("/api/batch/files/")
async def list_batch_files(
    path: str = str(BATCH_INPUT_DIR),
    extension: str = ".wav"
) -> BatchFileListResponse:
    """배치 입력 디렉토리의 파일 목록"""
    try:
        files = file_service.list_batch_files(path, extension)
        logger.info(f"배치 파일 목록 조회: {len(files)}개")
        
        return BatchFileListResponse(
            total=len(files),
            files=files  # type: ignore
        )
    except Exception as e:
        logger.error(f"배치 파일 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/batch/start/", response_model=BatchStartResponse)
async def start_batch(
    request: BatchStartRequest,
    background_tasks: BackgroundTasks
) -> BatchStartResponse:
    """배치 처리 시작"""
    try:
        # 요청 데이터 로깅
        logger.info(f"[배치] ===== 요청 수신 =====")
        logger.info(f"[배치] 경로: {request.path}")
        logger.info(f"[배치] 확장자: {request.extension}")
        logger.info(f"[배치] 언어: {request.language}")
        logger.info(f"[배치] 병렬 처리: {request.parallel_count}")
        logger.info(f"[배치] 처리 단계: Privacy={getattr(request, 'privacy_removal', False)}, Classification={getattr(request, 'classification', False)}, AI={getattr(request, 'ai_agent', False)}, IncompleteElements={getattr(request, 'incomplete_elements_check', False)}")
        if getattr(request, 'incomplete_elements_check', False) and getattr(request, 'agent_url', ''):
            logger.info(f"[배치] Agent URL: {request.agent_url}, Format: {getattr(request, 'agent_request_format', 'text_only')}")
        
        # BATCH_INPUT_DIR 값 확인
        logger.info(f"[배치] BATCH_INPUT_DIR 설정값 = {BATCH_INPUT_DIR}")
        logger.info(f"[배치] BATCH_INPUT_DIR 절대경로 = {BATCH_INPUT_DIR.absolute()}")
        
        # 배치 경로 정규화 (상대경로 -> 절대경로)
        batch_path = request.path
        logger.info(f"[배치] 입력 경로: {batch_path}")
        logger.info(f"[배치] startswith('/'): {batch_path.startswith('/')}")
        
        if not batch_path.startswith("/"):
            # 상대경로면 BATCH_INPUT_DIR 사용
            batch_path = str(BATCH_INPUT_DIR)
            logger.info(f"[배치] 상대경로 → BATCH_INPUT_DIR 사용: {batch_path}")
        else:
            logger.info(f"[배치] 절대경로 사용: {batch_path}")
        
        logger.info(f"[배치] 최종 조회 경로: {batch_path}")
        
        # 파일 목록 조회
        logger.info(f"[배치] 파일 목록 조회 시작 (경로: {batch_path})")
        files = file_service.list_batch_files(batch_path, request.extension)
        logger.info(f"[배치] 파일 목록 조회 완료: {len(files)}개 파일")
        
        if not files:
            logger.error(f"[배치] 에러: 처리할 파일이 없음 (경로: {batch_path})")
            raise HTTPException(status_code=400, detail="처리할 파일이 없습니다")
        
        # 배치 작업 생성
        from services.batch_service import BatchFile
        
        # 파일 경로를 API가 접근 가능한 경로로 변환
        # Web UI: /app/data/batch_input/... -> API: /app/web_ui/data/batch_input/...
        batch_files = []
        for f in files:
            file_path = f["path"]
            # Web UI 경로를 API 경로로 변환
            if file_path.startswith("/app/data/"):
                api_path = file_path.replace("/app/data/", "/app/web_ui/data/")
            else:
                api_path = file_path
            
            batch_files.append(BatchFile(name=f["name"], path=api_path))
            logger.debug(f"[배치] 파일 경로 변환: {file_path} -> {api_path}")
        
        batch_id = batch_service.create_job(batch_files)
        logger.info(f"[배치] 작업 생성: {batch_id} ({len(batch_files)}개 파일)")
        
        # 처리 옵션 로깅
        privacy_removal = getattr(request, 'privacy_removal', False)
        classification = getattr(request, 'classification', False)
        ai_agent = getattr(request, 'ai_agent', False)
        logger.info(f"[배치] 처리 옵션: Privacy={privacy_removal}, Classification={classification}, AI={ai_agent}")
        
        # 백그라운드에서 배치 처리 시작
        async def process_batch_bg():
            logger.info(f"[배치] 백그라운드 처리 시작 (batch_id: {batch_id})")
            
            async def process_file(file_path: str) -> dict:
                logger.info(f"[배치] 파일 처리 시작: {file_path}")
                try:
                    result = await stt_service.transcribe_local_file(
                        file_path=file_path,
                        language=request.language,
                        is_stream=False,
                        privacy_removal=privacy_removal,
                        classification=classification,
                        ai_agent=ai_agent,
                        incomplete_elements_check=getattr(request, 'incomplete_elements_check', False),
                        agent_url=getattr(request, 'agent_url', ''),
                        agent_request_format=getattr(request, 'agent_request_format', 'text_only')
                    )
                    logger.info(f"[배치] 파일 처리 완료: {file_path}")
                    return result
                except Exception as file_error:
                    logger.error(f"[배치] 파일 처리 중 오류 (file={file_path}): {type(file_error).__name__}: {file_error}", exc_info=True)
                    return {
                        "success": False,
                        "error": "processing_error",
                        "error_code": "FILE_PROCESSING_ERROR",
                        "message": f"파일 처리 실패: {str(file_error)}"
                    }
            
            await batch_service.process_batch(
                batch_id=batch_id,
                processor_fn=process_file,
                parallel_count=request.parallel_count
            )
            logger.info(f"[배치] 백그라운드 처리 완료 (batch_id: {batch_id})")
        
        background_tasks.add_task(process_batch_bg)
        
        logger.info(f"[배치] ===== 요청 완료 =====")
        
        return BatchStartResponse(
            batch_id=batch_id,
            total_files=len(batch_files),
            status="started"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[배치] 배치 처리 시작 실패: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"배치 처리 시작 실패: {str(e)}")


@app.get("/api/batch/progress/{batch_id}/")
async def get_batch_progress(batch_id: str) -> BatchProgressResponse:
    """배치 진행 상황"""
    try:
        logger.info(f"[배치] 진행 상황 조회: {batch_id}")
        progress = batch_service.get_progress(batch_id)
        
        if not progress:
            logger.error(f"[배치] 배치 작업을 찾을 수 없음: {batch_id}")
            raise HTTPException(status_code=404, detail="배치 작업을 찾을 수 없습니다")
        
        logger.info(f"[배치] 진행 상황: 총={progress['total']}, 완료={progress['completed']}, 실패={progress['failed']}, 진행 중={progress['in_progress']}")
        
        # 파일별 상태 로깅
        if progress.get("files"):
            for file_info in progress["files"]:
                status = file_info.get("status", "unknown")
                if status == "failed":
                    logger.warning(f"[배치] 실패 파일: {file_info.get('name')} - {file_info.get('error_message', 'Unknown error')}")
                elif status == "done":
                    logger.debug(f"[배치] 완료 파일: {file_info.get('name')}")
        
        return BatchProgressResponse(  # type: ignore
            batch_id=progress["batch_id"],
            total=progress["total"],
            completed=progress["completed"],
            failed=progress["failed"],
            in_progress=progress["in_progress"],
            current_file=None,
            estimated_remaining_sec=progress["estimated_remaining_sec"],
            files=progress["files"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[배치] 배치 진행 조회 실패: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 5. 결과 조회 라우트
# ============================================================================

@app.get("/api/results/{file_id}/")
async def get_result(file_id: str):
    """처리 결과 조회"""
    try:
        logger.info(f"[결과] 결과 조회: {file_id}")
        result_path = RESULT_DIR / f"{file_id}.txt"
        
        if not result_path.exists():
            logger.error(f"[결과] 결과 파일을 찾을 수 없음: {file_id}")
            raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다")
        
        with open(result_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        logger.info(f"[결과] 결과 조회 완료: {file_id} ({len(text)} 글자)")
        
        return {
            "success": True,
            "file_id": file_id,
            "text": text
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[결과] 결과 조회 실패: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/results/{file_id}/export/")
async def export_result(file_id: str, format: str = "txt"):
    """결과 다운로드"""
    try:
        logger.info(f"[결과] 결과 내보내기: {file_id} (형식: {format})")
        result_path = RESULT_DIR / f"{file_id}.txt"
        
        if not result_path.exists():
            logger.error(f"[결과] 결과 파일을 찾을 수 없음: {file_id}")
            raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다")
        
        if format == "json":
            import json
            with open(result_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            json_data = {
                "file_id": file_id,
                "text": text,
                "exported_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.info(f"[결과] JSON 형식으로 내보내기 완료: {file_id}")
            
            return JSONResponse(
                content=json_data,
                media_type="application/json"
            )
        else:  # txt
            logger.info(f"[결과] TXT 형식으로 내보내기 완료: {file_id}")
            return FileResponse(
                result_path,
                filename=f"{file_id}_result.txt",
                media_type="text/plain"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[결과] 결과 내보내기 실패: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 에러 핸들러
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 핸들러"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail
        }
    )


# ============================================================================
# 서버 시작/종료
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """서버 시작"""
    logger.info("=" * 60)
    logger.info("STT Web UI Server 시작")
    logger.info(f"주소: http://{WEB_HOST}:{WEB_PORT}")
    logger.info(f"업로드 디렉토리: {UPLOAD_DIR}")
    logger.info(f"결과 디렉토리: {RESULT_DIR}")
    logger.info(f"배치 입력: {BATCH_INPUT_DIR}")
    logger.info("=" * 60)
    
    # STT API 헬스 체크
    if await stt_service.health_check():
        logger.info("STT API 연결 ✓")
    else:
        logger.warning("STT API 연결 실패 ⚠️")


# ============================================================================
# 4. 비동기 STT 처리 라우트 (장시간 작업용)
# ============================================================================

@app.post("/api/transcribe-async/")
async def transcribe_async(request: TranscribeRequest) -> dict:
    """
    비동기 STT 처리 (즉시 응답, 백그라운드 처리)
    
    Returns:
        job_id: 작업 ID (상태 조회용)
        status: 작업 상태
    """
    try:
        # 파일 경로 재구성
        file_path = UPLOAD_DIR / f"{request.file_id}*"
        files = list(UPLOAD_DIR.glob(f"{request.file_id}*"))
        
        if not files:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
        
        file_path = str(files[0])
        
        # 작업 큐에 추가
        job_id = await transcribe_queue.enqueue(
            file_path=file_path,
            language=request.language,
            is_stream=False
        )
        
        logger.info(f"비동기 STT 처리 시작: {job_id} (파일: {file_path})")
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "pending",
            "message": "작업이 큐에 추가되었습니다. /api/transcribe-status/{job_id}로 상태를 확인하세요."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"비동기 STT 처리 요청 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transcribe-status/{job_id}")
async def get_transcribe_status(job_id: str) -> dict:
    """
    비동기 작업 상태 조회
    
    Returns:
        작업 상태, 진행률, 결과 (완료 시)
    """
    job_info = transcribe_queue.get_job_status(job_id)
    
    if not job_info:
        raise HTTPException(status_code=404, detail=f"작업을 찾을 수 없습니다: {job_id}")
    
    return job_info


@app.get("/api/transcribe-jobs/")
async def list_transcribe_jobs() -> dict:
    """
    모든 비동기 작업 목록 조회
    """
    jobs = transcribe_queue.get_all_jobs()
    return {
        "total": len(jobs),
        "jobs": jobs
    }

@app.get("/api/health")
async def api_health() -> dict:
    """
    Web UI + STT API 헬스 체크
    클라이언트에서 호출하는 엔드포인트
    """
    # Web UI 상태
    web_ui_healthy = True
    
    # STT API 상태 확인
    stt_api_healthy = await stt_service.health_check()
    
    return {
        "success": web_ui_healthy and stt_api_healthy,
        "web_ui": "ok" if web_ui_healthy else "error",
        "stt_api": "ok" if stt_api_healthy else "error",
        "stt_api_url": STT_API_URL
    }

# ============================================================================
# Privacy Removal API 라우트 ✨
# ============================================================================

@app.post("/api/privacy-removal/")
async def privacy_removal(request: Request) -> dict:
    """
    Privacy Removal 처리
    
    Request:
    {
        "text": "처리할 텍스트",
        "prompt_type": "privacy_remover_default_v6" (optional)
    }
    
    Response:
    {
        "success": bool,
        "privacy_exist": "Y/N",
        "exist_reason": "설명",
        "privacy_rm_text": "처리된 텍스트"
    }
    """
    try:
        # 요청 본문 파싱
        body = await request.json()
        
        text = body.get("text", "")
        prompt_type = body.get("prompt_type", "privacy_remover_default_v6")
        
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="텍스트가 비어있습니다")
        
        logger.info(f"[Privacy Removal API] 요청: 텍스트 길이={len(text)}, 프롬프트={prompt_type}")
        
        # STT Service를 통해 Privacy Removal 처리
        result = await stt_service.process_privacy_removal(
            text=text,
            prompt_type=prompt_type
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Privacy Removal API] 처리 오류: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "privacy_rm_text": body.get("text", "") if 'body' in locals() else ""
        }

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 비동기 워커 시작"""
    logger.info("STT Web UI Server 시작")
    
    # 비동기 워커 시작 (2개 동시 실행)
    asyncio.create_task(
        transcribe_queue.worker_loop(stt_service.process_transcribe_job)
    )
    logger.info("[Startup] 비동기 STT 처리 워커 시작 (동시 처리: 2개)")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료"""
    logger.info("STT Web UI Server 종료")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=WEB_HOST,
        port=WEB_PORT,
        reload=True
    )
