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
        로컬 파일 내용을 읽어서 STT 처리 (파일 전송 방식)
        
        Args:
            file_path: 파일 경로
            language: 언어 코드
            is_stream: 스트리밍 모드 사용 여부
        
        Returns:
            처리 결과 딕셔너리
        """
        try:
            logger.info(f"[STT Service] 파일 처리: {file_path} (언어: {language}, 스트림: {is_stream})")
            
            # 파일 읽기
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # 파일명 추출
            from pathlib import Path
            filename = Path(file_path).name
            
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field("file", file_content, filename=filename)
                data.add_field("language", language)
                data.add_field("is_stream", str(is_stream))
                
                async with session.post(
                    f"{self.api_url}/transcribe",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        logger.info(f"[STT Service] 처리 완료: {len(result.get('text', ''))} 글자")
                    else:
                        logger.error(f"[STT Service] 처리 실패: {result}")
                    
                    return result
        
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
