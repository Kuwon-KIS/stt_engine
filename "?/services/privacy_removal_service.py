"""
Privacy Removal Service
STT 결과에 개인정보 제거 로직을 적용하는 서비스
"""

import logging
from typing import Optional, Dict, Any

from .privacy_removal.vllm_client import VLLMClient
from .privacy_removal.privacy_remover import LLMProcessorForPrivacy

logger = logging.getLogger(__name__)


class PrivacyRemovalService:
    """
    STT 텍스트에서 개인정보를 제거하는 서비스
    
    워크플로우:
    1. vLLM 클라이언트 초기화
    2. LLMProcessor 생성
    3. 텍스트 입력
    4. LLM 호출하여 개인정보 제거
    5. 결과 반환
    """
    
    def __init__(
        self,
        vllm_base_url: Optional[str] = None,
        vllm_model: Optional[str] = None
    ):
        """
        PrivacyRemovalService 초기화
        
        Args:
            vllm_base_url: vLLM 서버 URL (기본값: localhost:8001)
            vllm_model: vLLM 모델명 (기본값: Qwen3-30B-A3B-Thinking-2507-FP8)
        """
        self.vllm_client = VLLMClient(
            base_url=vllm_base_url,
            model_name=vllm_model
        )
        self.processor = LLMProcessorForPrivacy(
            vllm_client=self.vllm_client
        )
        
        logger.info("[PrivacyRemovalService] 초기화 완료")
    
    async def remove_privacy_from_stt(
        self,
        stt_text: str,
        prompt_type: str = "privacy_remover_default_v6",
        max_tokens: int = 8192,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        STT 결과에서 개인정보 제거
        
        Args:
            stt_text: STT 결과 텍스트
            prompt_type: 사용할 프롬프트 타입
            max_tokens: 최대 토큰 수
            temperature: LLM 온도
            
        Returns:
            {
                'privacy_exist': str,       # Y/N
                'exist_reason': str,        # 개인정보 발견 사유
                'privacy_rm_text': str,     # 개인정보 제거된 텍스트
                'success': bool             # 처리 성공 여부
            }
        """
        return await self.processor.remove_privacy(
            text=stt_text,
            prompt_type=prompt_type,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    def get_available_prompts(self) -> list:
        """사용 가능한 프롬프트 타입 목록"""
        return self.processor.get_available_prompt_types()


# 글로벌 서비스 인스턴스 (싱글톤)
_service_instance: Optional[PrivacyRemovalService] = None


async def get_privacy_removal_service() -> PrivacyRemovalService:
    """
    PrivacyRemovalService의 싱글톤 인스턴스 반환
    
    FastAPI 의존성으로 사용 가능:
    ```python
    async def my_endpoint(service: PrivacyRemovalService = Depends(get_privacy_removal_service)):
        result = await service.remove_privacy_from_stt(text)
    ```
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = PrivacyRemovalService()
    return _service_instance
