"""
STT API와의 통신을 담당하는 서비스
"""
import aiohttp
import asyncio
import logging
from typing import Optional
from config import STT_API_URL, STT_API_TIMEOUT

logger = logging.getLogger(__name__)


class STTService:
    """STT Engine API 통신 클래스"""
    
    def __init__(self):
        self.api_url = STT_API_URL
        self.timeout = STT_API_TIMEOUT
    
    async def health_check(self) -> bool:
        """STT API 헬스 체크"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/health",
                    timeout=aiohttp.ClientTimeout(total=10)  # 10초: Docker 네트워크 지연 고려
                ) as response:
                    is_healthy = response.status == 200
                    if is_healthy:
                        logger.debug(f"[STT Service] 헬스 체크 OK: {self.api_url}/health")
                    return is_healthy
        except asyncio.TimeoutError:
            logger.error(f"[STT Service] 헬스 체크 타임아웃 (10초): Docker 네트워크 지연 또는 API 미응답")
            return False
        except Exception as e:
            logger.error(f"[STT Service] 헬스 체크 실패: {e}")
            return False
    
    async def transcribe_local_file(
        self,
        file_path: str,
        language: str = "ko",
        is_stream: bool = False,
        backend: str = None
    ) -> dict:
        """
        로컬 파일을 STT API에 전달 (파일 경로 방식)
        
        API가 접근 가능한 경로로 변환:
        - Web UI 경로: /app/data/uploads/... 
        - API 경로: /app/web_ui/data/uploads/... (마운트된 볼륨이 같음)
        
        Args:
            file_path: Web UI 컨테이너의 파일 경로 (/app/data/uploads/...)
            language: 언어 코드
            is_stream: 스트리밍 모드 사용 여부
            backend: 백엔드 선택 (faster-whisper, transformers, openai-whisper)
        
        Returns:
            처리 결과 딕셔너리
        """
        try:
            logger.info(f"[STT Service] 파일 처리: {file_path} (언어: {language}, 스트림: {is_stream})")
            
            # 파일 경로 변환 (Web UI 볼륨 -> API 접근 경로)
            # Web UI 컨테이너 마운트: /data/aiplatform/stt_engine_volumes/web_ui/data:/app/web_ui/data
            # 경우 1: /app/data/uploads/... (레거시 경로) -> /app/web_ui/data/uploads/...
            # 경우 2: /app/web_ui/data/... (현재 경로) -> 변환 불필요
            if file_path.startswith("/app/data/"):
                # /app/data/ 경로를 /app/web_ui/data/로 변환
                api_file_path = file_path.replace("/app/data/", "/app/web_ui/data/")
                logger.debug(f"[STT Service] 경로 변환 (레거시): {file_path} -> {api_file_path}")
            elif file_path.startswith("/app/web_ui/data/"):
                # 이미 올바른 경로 형식 (배치 처리 파일)
                api_file_path = file_path
                logger.debug(f"[STT Service] 경로 확인 (배치): {file_path} (변환 불필요)")
            else:
                # 다른 경로 형식은 그대로 사용
                api_file_path = file_path
                logger.warning(f"[STT Service] 알 수 없는 경로 형식: {file_path}")
            
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field("file_path", api_file_path)
                data.add_field("language", language)
                data.add_field("is_stream", str(is_stream).lower())
                
                # backend 지정
                if backend:
                    data.add_field("backend", backend)
                    logger.info(f"[STT Service] 백엔드 지정: {backend}")
                
                # 타임아웃을 파일 길이에 따라 동적으로 설정 (최소 600초)
                estimated_timeout = max(600, self.timeout)
                logger.info(f"[STT Service] 타임아웃 설정: {estimated_timeout}초")
                
                try:
                    async with session.post(
                        f"{self.api_url}/transcribe",
                        data=data,
                        timeout=aiohttp.ClientTimeout(total=estimated_timeout)
                    ) as response:
                        logger.info(f"[STT Service] API 응답 수신: status={response.status}")
                        result = await response.json()
                        logger.info(f"[STT Service] JSON 파싱 완료")
                        
                        if response.status == 200:
                            logger.info(f"[STT Service] 처리 완료: {len(result.get('text', ''))} 글자")
                        else:
                            logger.error(f"[STT Service] 처리 실패: {result}")
                        
                        return result
                except asyncio.TimeoutError as te:
                    logger.error(f"[STT Service] API 타임아웃 ({estimated_timeout}초): {file_path}")
                    return {
                        "success": False,
                        "error": "timeout",
                        "message": f"API 처리 시간 초과 ({estimated_timeout}초)"
                    }
                except Exception as ae:
                    logger.error(f"[STT Service] API 통신 오류: {ae}", exc_info=True)
                    return {
                        "success": False,
                        "error": "api_error",
                        "message": f"API 통신 오류: {str(ae)}"
                    }
        
        except asyncio.TimeoutError:
            logger.error(f"[STT Service] 타임아웃: {file_path}")
            return {
                "success": False,
                "error": "timeout",
                "message": f"처리 시간 초과 ({self.timeout}초)"
            }
        except Exception as e:
            logger.error(f"[STT Service] 에러: {e}", exc_info=True)
            return {
                "success": False,
                "error": "unknown",
                "message": str(e)
            }
    
    async def get_backend_info(self) -> dict:
        """STT API 백엔드 정보 조회"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/backend/current",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"[STT Service] 백엔드 정보 조회 실패: {e}")
            return {}
    
    async def process_transcribe_job(self, job) -> dict:
        """
        비동기 작업 큐에서 호출되는 메서드
        job 객체의 상태를 업데이트하면서 처리
        
        Args:
            job: TranscribeJob 객체
        
        Returns:
            처리 결과 딕셔너리
        """
        try:
            logger.info(f"[STT Service] 비동기 처리 시작: {job.job_id}")
            
            # 파일 경로 변환
            file_path = job.file_path
            if file_path.startswith("/app/data/"):
                api_file_path = file_path.replace("/app/data/", "/app/web_ui/data/")
            else:
                api_file_path = file_path
            
            logger.debug(f"[STT Service] 경로 변환: {file_path} -> {api_file_path}")
            
            # 진행률 업데이트: 준비 중
            job.progress = 15
            
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field("file_path", api_file_path)
                data.add_field("language", job.language)
                data.add_field("is_stream", str(job.is_stream).lower())
                
                # 장시간 처리를 고려하여 충분한 타임아웃 설정
                estimated_timeout = max(600, self.timeout)
                logger.info(f"[STT Service] 타임아웃 설정: {estimated_timeout}초 (job: {job.job_id})")
                
                try:
                    async with session.post(
                        f"{self.api_url}/transcribe",
                        data=data,
                        timeout=aiohttp.ClientTimeout(total=estimated_timeout)
                    ) as response:
                        logger.info(f"[STT Service] API 응답 수신: status={response.status} (job: {job.job_id})")
                        result = await response.json()
                        logger.info(f"[STT Service] JSON 파싱 완료 (job: {job.job_id})")
                        
                        # 진행률 업데이트: API 처리 완료
                        job.progress = 90
                        
                        if response.status == 200:
                            logger.info(f"[STT Service] 처리 완료: {len(result.get('text', ''))} 글자 (job: {job.job_id})")
                            job.progress = 100
                        else:
                            logger.error(f"[STT Service] 처리 실패: {result} (job: {job.job_id})")
                        
                        return result
                
                except asyncio.TimeoutError as te:
                    logger.error(f"[STT Service] API 타임아웃 ({estimated_timeout}초, job: {job.job_id})")
                    return {
                        "success": False,
                        "error": "timeout",
                        "message": f"API 처리 시간 초과 ({estimated_timeout}초)"
                    }
                except Exception as ae:
                    logger.error(f"[STT Service] API 통신 오류: {ae} (job: {job.job_id})", exc_info=True)
                    return {
                        "success": False,
                        "error": "api_error",
                        "message": f"API 통신 오류: {str(ae)}"
                    }
        
        except Exception as e:
            logger.error(f"[STT Service] 비동기 처리 오류: {e} (job: {job.job_id})", exc_info=True)
            return {
                "success": False,
                "error": "unknown",
                "message": str(e)
            }


# 싱글톤 인스턴스
stt_service = STTService()
