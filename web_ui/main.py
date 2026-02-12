"""
Web UI 서버 메인 앱
"""
import asyncio
import time
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
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
    title="STT Web UI",
    version="1.0.0",
    description="Speech-to-Text Web UI Server"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if isinstance(CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        
        if not files:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
        
        file_path = str(files[0])
        
        logger.info(f"STT 처리 시작: {file_path} (언어: {request.language})")
        
        start_time = time.time()
        result = await stt_service.transcribe_local_file(
            file_path=file_path,
            language=request.language,
            is_stream=False
        )
        processing_time = time.time() - start_time
        
        if not result.get("success"):
            logger.error(f"STT 처리 실패: {result}")
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "처리 중 오류 발생")
            )
        
        # 결과 저장
        file_service.save_result(request.file_id, result.get("text", ""), {
            "filename": Path(file_path).name,
            "language": request.language,
            "duration_sec": result.get("duration_sec", 0),
            "processing_time_sec": processing_time,
            "backend": result.get("backend", "unknown")
        })
        
        logger.info(f"STT 처리 완료: {processing_time:.2f}초")
        
        return TranscribeResponse(
            success=True,
            file_id=request.file_id,
            filename=Path(file_path).name,
            text=result.get("text", ""),
            language=request.language,
            duration_sec=result.get("duration_sec", 0),
            processing_time_sec=processing_time,
            backend=result.get("backend", "unknown")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT 처리 중 오류: {e}", exc_info=True)
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
        logger.info(f"배치 처리 시작 요청: {request.path} (병렬: {request.parallel_count})")
        
        # 파일 목록 조회
        files = file_service.list_batch_files(request.path, request.extension)
        
        if not files:
            raise HTTPException(status_code=400, detail="처리할 파일이 없습니다")
        
        # 배치 작업 생성
        from services.batch_service import BatchFile
        batch_files = [
            BatchFile(name=f["name"], path=f["path"])
            for f in files
        ]
        batch_id = batch_service.create_job(batch_files)
        
        # 백그라운드에서 배치 처리 시작
        async def process_batch_bg():
            async def process_file(file_path: str) -> dict:
                return await stt_service.transcribe_local_file(
                    file_path=file_path,
                    language=request.language,
                    is_stream=False
                )
            
            await batch_service.process_batch(
                batch_id=batch_id,
                processor_fn=process_file,
                parallel_count=request.parallel_count
            )
        
        background_tasks.add_task(process_batch_bg)
        
        return BatchStartResponse(
            batch_id=batch_id,
            total_files=len(batch_files),
            status="started"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"배치 처리 시작 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/batch/progress/{batch_id}/")
async def get_batch_progress(batch_id: str) -> BatchProgressResponse:
    """배치 진행 상황"""
    try:
        progress = batch_service.get_progress(batch_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail="배치 작업을 찾을 수 없습니다")
        
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
        logger.error(f"배치 진행 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 5. 결과 조회 라우트
# ============================================================================

@app.get("/api/results/{file_id}/")
async def get_result(file_id: str):
    """처리 결과 조회"""
    try:
        result_path = RESULT_DIR / f"{file_id}.txt"
        
        if not result_path.exists():
            raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다")
        
        with open(result_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        return {
            "success": True,
            "file_id": file_id,
            "text": text
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"결과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/results/{file_id}/export/")
async def export_result(file_id: str, format: str = "txt"):
    """결과 다운로드"""
    try:
        result_path = RESULT_DIR / f"{file_id}.txt"
        
        if not result_path.exists():
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
            
            return JSONResponse(
                content=json_data,
                media_type="application/json"
            )
        else:  # txt
            return FileResponse(
                result_path,
                filename=f"{file_id}_result.txt",
                media_type="text/plain"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"결과 내보내기 실패: {e}")
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
