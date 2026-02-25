"""
Ollama Local LLM Client implementation
"""

from typing import Optional
import logging
import httpx
import json

from .base import LLMClient

logger = logging.getLogger(__name__)


class OllamaClient(LLMClient):
    """Ollama를 사용하는 로컬 LLM 클라이언트"""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        api_url: str = "http://localhost:11434",
        timeout: int = 300,
        **kwargs
    ):
        """
        Args:
            model_name: Ollama 모델명 (예: llama2, mistral, neural-chat 등)
            api_url: Ollama API 엔드포인트 URL (기본값: http://localhost:11434)
            timeout: 요청 타임아웃 (초단위)
            **kwargs: 추가 설정
        """
        super().__init__(model_name, **kwargs)
        self.model_name = model_name or "llama2"
        self.api_url = api_url
        self.timeout = timeout
        self.endpoint = f"{api_url}/api/generate"
    
    async def call(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Ollama API 호출
        
        Args:
            prompt: 프롬프트 텍스트
            temperature: 응답 다양성 (0.0 ~ 2.0)
            max_tokens: 최대 토큰 수
            **kwargs: 추가 파라미터
        
        Returns:
            LLM의 응답 텍스트
        
        Raises:
            Exception: Ollama 호출 실패 시
        """
        try:
            logger.debug(f"[OllamaClient] Calling {self.model_name} at {self.api_url} with prompt length: {len(prompt)}")
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "temperature": temperature,
                "num_predict": max_tokens,
                "stream": False,
                **kwargs
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.endpoint, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                if "response" in result:
                    text = result["response"].strip()
                    logger.info(f"[OllamaClient] Success: response length={len(text)}")
                    return text
                else:
                    raise ValueError(f"Unexpected response format: {result}")
            
        except httpx.TimeoutException as e:
            logger.error(f"[OllamaClient] Timeout: {str(e)}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"[OllamaClient] HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"[OllamaClient] Error: {str(e)}")
            raise
    
    async def is_available(self) -> bool:
        """Ollama 서버 가용성 확인"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.api_url}/api/tags")
                logger.info(f"[OllamaClient] Health check: {response.status_code}")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"[OllamaClient] Availability check failed: {str(e)}")
            return False
