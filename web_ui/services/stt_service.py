"""
STT API와의 통신을 담당하는 서비스
"""
import aiohttp
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
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"[STT Service] 헬스 체크 실패: {e}")
            return False
    
    async def transcribe_local_file(
        self,
        file_path: str,
        language: str = "ko",
        is_stream: bool = False
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
        
        Returns:
            처리 결과 딕셔너리
        """
        try:
            logger.info(f"[STT Service] 파일 처리: {file_path} (언어: {language}, 스트림: {is_stream})")
            
            # 파일 경로 변환 (Web UI 볼륨 -> API 접근 경로)
            # Web UI: /app/data/uploads/file.wav
            # API가 마운트된 볼륨: /app/web_ui/data/uploads/file.wav
            if file_path.startswith("/app/data/"):
                # /app/data/ 경로를 /app/web_ui/data/로 변환
                api_file_path = file_path.replace("/app/data/", "/app/web_ui/data/")
            else:
                api_file_path = file_path
            
            logger.debug(f"[STT Service] 경로 변환: {file_path} -> {api_file_path}")
            
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field("file_path", api_file_path)
                data.add_field("language", language)
                data.add_field("is_stream", str(is_stream).lower())
                
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
                    f"{self.api_url}/info",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"[STT Service] 백엔드 정보 조회 실패: {e}")
            return {}


# 싱글톤 인스턴스
stt_service = STTService()
