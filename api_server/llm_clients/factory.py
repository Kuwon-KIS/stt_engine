"""
LLM Client Factory - LLM 제공자 선택 및 생성
"""

from typing import Optional, Dict
import logging
from .base import LLMClient
from .vllm_client import vLLMClient
from .ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """LLM 클라이언트 팩토리"""
    
    _clients: Dict[str, LLMClient] = {}
    
    @staticmethod
    def create_client(
        llm_type: str = "vllm",
        model_name: Optional[str] = None,
        vllm_api_url: str = "http://localhost:8000",
        ollama_api_url: str = "http://localhost:11434",
        **kwargs
    ) -> LLMClient:
        """
        LLM 클라이언트 생성
        
        Args:
            llm_type: LLM 제공자 타입
                     - 'vllm': vLLM 로컬 서버 (기본값)
                     - 'ollama': Ollama 로컬 서버
            model_name: 사용할 모델명 (llm_type에 따라 다름)
            vllm_api_url: vLLM API URL (기본값: http://localhost:8000)
            ollama_api_url: Ollama API URL (기본값: http://localhost:11434)
            **kwargs: 추가 파라미터
        
        Returns:
            LLMClient 인스턴스
        
        Raises:
            ValueError: 지원하지 않는 llm_type
        """
        try:
            if llm_type == "vllm":
                logger.info(f"[LLMClientFactory] Creating vLLMClient (model={model_name}, url={vllm_api_url})")
                return vLLMClient(
                    model_name=model_name,
                    api_url=vllm_api_url,
                    **kwargs
                )
            
            elif llm_type == "ollama":
                logger.info(f"[LLMClientFactory] Creating OllamaClient (model={model_name}, url={ollama_api_url})")
                return OllamaClient(
                    model_name=model_name,
                    api_url=ollama_api_url,
                    **kwargs
                )
            
            else:
                raise ValueError(f"Unsupported LLM type: {llm_type}. Supported: vllm, ollama")
        
        except Exception as e:
            logger.error(f"[LLMClientFactory] Error creating client: {str(e)}")
            raise
    
    @staticmethod
    def get_cached_client(
        llm_type: str = "vllm",
        model_name: Optional[str] = None,
        **kwargs
    ) -> LLMClient:
        """
        캐시된 클라이언트 가져오기 (같은 설정은 재사용)
        
        Args:
            llm_type: LLM 제공자 타입 (기본값: vllm)
            model_name: 모델명
            **kwargs: 추가 파라미터
        
        Returns:
            캐시된 또는 새로 생성된 LLMClient 인스턴스
        """
        cache_key = f"{llm_type}:{model_name}"
        
        if cache_key not in LLMClientFactory._clients:
            LLMClientFactory._clients[cache_key] = LLMClientFactory.create_client(
                llm_type=llm_type,
                model_name=model_name,
                **kwargs
            )
            logger.debug(f"[LLMClientFactory] Created and cached client: {cache_key}")
        else:
            logger.debug(f"[LLMClientFactory] Using cached client: {cache_key}")
        
        return LLMClientFactory._clients[cache_key]
