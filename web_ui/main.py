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
from starlette.middleware.sessions import SessionMiddleware
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
    STT_API_URL,
    SESSION_SECRET_KEY
)
# Phase 1: 인증 및 DB 임포트
from app.utils.db import init_db
from app.routes import auth, files, analysis
# 아래 클래스들은 실제 구현에서 정의되지 않음 - 이후 필요시 각 서비스에서 import
# from app.models.schemas import (
#     FileUploadResponse, TranscribeRequest, TranscribeResponse,
#     BatchFileListResponse, BatchStartRequest, BatchStartResponse,
#     BatchProgressResponse
# )
from app.services.stt_service import stt_service
# from app.services.file_service import file_service
# from app.services.batch_service import batch_service, FileStatus
# from app.services.job_queue import transcribe_queue, JobStatus

# FastAPI 앱 생성
app = FastAPI(
    title="KIS 불완전판매 예방 녹취 분석 시스템",
    version="1.0.0",
    description="금융상품 판매 사전 녹취 음성을 텍스트로 변환하여 불완전판매 예방 및 규정 준수 검토"
)

# === Phase 1: SessionMiddleware 등록 (CORS 이전에 등록) ===
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# CORS 설정
# 주의: allow_credentials=True일 때 allow_origins는 ["*"]가 아니어야 함
cors_origins = CORS_ORIGINS if isinstance(CORS_ORIGINS, list) else ["*"]
# 만약 wildcard라면 localhost만 허용 (개발 환경)
if cors_origins == ["*"]:
    cors_origins = ["http://localhost:8100", "http://127.0.0.1:8100"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
# === Phase 1: 인증 라우터 등록 ===
# ============================================================================
app.include_router(auth.router)

# ============================================================================
# === Phase 2: 파일 관리 라우터 등록 ===
# ============================================================================
app.include_router(files.router)

# === Phase 3: 분석 라우터 등록 ===
# ============================================================================
app.include_router(analysis.router)

# ============================================================================
# 1. 대시보드 및 기본 라우트
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    """로그인 페이지 (root)"""
    try:
        return templates.TemplateResponse("login.html", {"request": request})
    except Exception as e:
        logger.error(f"로그인 페이지 로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/login", response_class=HTMLResponse)
async def login_page_alias(request: Request):
    """로그인 페이지 (별칭)"""
    try:
        return templates.TemplateResponse("login.html", {"request": request})
    except Exception as e:
        logger.error(f"로그인 페이지 로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/old", response_class=HTMLResponse)
async def dashboard(request: Request):
    """대시보드 페이지 (구 버전)"""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"대시보드 로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """파일 업로드 페이지 (Phase 2)"""
    # 세션 확인
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    try:
        return templates.TemplateResponse("upload.html", {"request": request})
    except Exception as e:
        logger.error(f"업로드 페이지 로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analysis", response_class=HTMLResponse)
async def analysis_page(request: Request):
    """분석 페이지 (Phase 3)"""
    # 세션 확인
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    try:
        return templates.TemplateResponse("analysis.html", {"request": request})
    except Exception as e:
        logger.error(f"분석 페이지 로드 실패: {e}")
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
# 서버 시작/종료
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """서버 시작"""
    # === Phase 1: DB 초기화 ===
    init_db()
    logger.info("✅ Database initialized")
    
    logger.info("=" * 60)
    logger.info("STT Web UI Server 시작")
    logger.info(f"주소: http://{WEB_HOST}:{WEB_PORT}")
    logger.info("=" * 60)


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
