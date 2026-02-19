"""
vLLM Client Wrapper
기존 stt-engine에서 사용하는 vLLM 서비스와 통합
"""

import httpx
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class VLLMClient:
    """
    vLLM 서비스와 통신하는 클라이언트
    
    기존 STT 서버에서 사용하는 vLLM 서비스를 활용합니다.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = 60
    ):
        """
        VLLMClient 초기화
        
        Args:
            base_url: vLLM 서버 URL (기본값: http://localhost:8001)
            model_name: 모델명 (기본값: 환경변수 VLLM_MODEL 또는 기본값)
            timeout: 요청 타임아웃 (초)
        """
        self.base_url = base_url or os.getenv("VLLM_API_URL", "http://localhost:8001")
        self.model_name = model_name or os.getenv("VLLM_MODEL", "Qwen3-30B-A3B-Thinking-2507-FP8")
        self.timeout = timeout
        
        logger.info(f"[VLLMClient] URL: {self.base_url}, Model: {self.model_name}")
    
    async def generate_response(
        self,
        prompt: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        top_p: float = 0.9
    ) -> str:
        """
        vLLM에 프롬프트를 전송하여 응답 생성
        
        Args:
            prompt: 입력 프롬프트
            max_tokens: 최대 토큰 수
            temperature: 샘플링 온도
            top_p: 누적 확률
            
        Returns:
            LLM 응답 텍스트
            
        Raises:
            Exception: vLLM 서비스 오류
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}/v1/completions"
                
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "stop": ["</s>", "[INST]"],  # 일반적인 중지 토큰
                }
                
                logger.debug(f"[VLLMClient] 요청 URL: {url}")
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                # vLLM 응답 형식
                if "choices" in data and len(data["choices"]) > 0:
                    result = data["choices"][0].get("text", "")
                    logger.info(f"[VLLMClient] 응답 생성 (길이: {len(result)})")
                    return result
                else:
                    logger.warning(f"[VLLMClient] 예상 응답 없음: {data}")
                    return ""
                    
        except httpx.TimeoutException:
            logger.error(f"[VLLMClient] 타임아웃: {self.base_url}")
            raise Exception(f"vLLM 요청 타임아웃 (URL: {self.base_url})")
        except httpx.ConnectError:
            logger.error(f"[VLLMClient] 연결 실패: {self.base_url}")
            raise Exception(f"vLLM 서버 연결 실패 (URL: {self.base_url})")
        except Exception as e:
            logger.error(f"[VLLMClient] 오류: {str(e)}", exc_info=True)
            raise
