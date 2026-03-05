"""
LLM Client Factory - vLLM 클라이언트 생성
"""

from typing import Optional, Dict
import logging
import os
from .vllm_client import vLLMClient

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """vLLM 클라이언트 팩토리"""
    
    _clients: Dict[str, vLLMClient] = {}
    
    @staticmethod
    def create_client(
        model_name: Optional[str] = None,
        vllm_api_url: Optional[str] = None,
        **kwargs
    ) -> vLLMClient:
        """
        vLLM 클라이언트 생성
        
        Args:
            model_name: 사용할 모델명 (예: 'qwen30_thinking_2507')
            vllm_api_url: vLLM API URL (예: http://localhost:8001/v1/chat/completions)
                         없으면 VLLM_BASE_URL + VLLM_API_ENDPOINT 조합
            **kwargs: 추가 파라미터
        
        Returns:
            vLLMClient 인스턴스
        
        Raises:
            ValueError: 설정 오류 발생 시
        """
        # 환경변수에서 기본값 읽기
        if vllm_api_url is None:
            vllm_base = os.getenv("VLLM_BASE_URL", "http://localhost:8001")
            vllm_endpoint = os.getenv("VLLM_API_ENDPOINT", "/v1/chat/completions")
            vllm_api_url = vllm_base.rstrip('/') + vllm_endpoint
        
        try:
            logger.info(f"[LLMClientFactory] Creating vLLMClient (model={model_name}, url={vllm_api_url})")
            return vLLMClient(
                model_name=model_name,
                api_url=vllm_api_url,
                **kwargs
            )
        
        except Exception as e:
            logger.error(f"[LLMClientFactory] Error creating vLLMClient: {str(e)}")
            raise
    
    @staticmethod
    def get_cached_client(
        model_name: Optional[str] = None,
        **kwargs
    ) -> vLLMClient:
        """
        캐시된 클라이언트 가져오기 (같은 설정은 재사용)
        
        Args:
            model_name: 모델명
            **kwargs: 추가 파라미터
        
        Returns:
            캐시된 또는 새로 생성된 vLLMClient 인스턴스
        """
        cache_key = f"vllm:{model_name}"
        
        if cache_key not in LLMClientFactory._clients:
            LLMClientFactory._clients[cache_key] = LLMClientFactory.create_client(
                model_name=model_name,
                **kwargs
            )
            logger.debug(f"[LLMClientFactory] Created and cached client: {cache_key}")
        else:
            logger.debug(f"[LLMClientFactory] Using cached client: {cache_key}")
        
        return LLMClientFactory._clients[cache_key]
