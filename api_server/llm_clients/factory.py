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
        base_url: Optional[str] = None,
        llm_type: Optional[str] = None,
        **kwargs
    ) -> vLLMClient:
        """
        vLLM 클라이언트 생성
        
        Args:
            model_name: 사용할 모델명 (예: 'qwen30_thinking_2507')
            vllm_api_url: 직접 지정한 전체 URL (legacy, 이제는 base_url 사용)
            base_url: vLLM API 베이스 URL (예: http://localhost:8001/v1)
                     vLLMClient가 /chat/completions를 자동으로 추가함
            llm_type: LLM 타입 (현재는 'vllm'만 지원, 무시됨)
            **kwargs: 추가 파라미터
        
        Returns:
            vLLMClient 인스턴스
        
        Raises:
            ValueError: 설정 오류 발생 시
        """
        # 베이스 URL 결정 (우선순위: base_url > vllm_api_url > 환경변수)
        if base_url is None and vllm_api_url is None:
            # 환경변수에서 읽기 (VLLM_BASE_URL은 /v1 포함, VLLM_API_ENDPOINT는 deprecated)
            vllm_base = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
            base_url = vllm_base
        elif vllm_api_url is not None and base_url is None:
            # Legacy: vllm_api_url이 지정된 경우
            base_url = vllm_api_url
        
        # base_url 정규화 (vLLMClient에서도 하지만, 로깅 전에 미리 정규화)
        base_url = base_url.rstrip('/').rstrip('v1')
        if not base_url.endswith('/v1'):
            base_url = base_url.rstrip('/') + '/v1'
        
        try:
            logger.info(f"[LLMClientFactory] Creating vLLMClient (model={model_name}, base_url={base_url}, llm_type={llm_type})")
            return vLLMClient(
                model_name=model_name,
                api_url=base_url,  # vLLMClient는 api_url을 base_url로 해석함
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
