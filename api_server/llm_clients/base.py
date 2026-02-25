"""
Abstract base class for LLM clients
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """LLM Client 추상 클래스"""
    
    def __init__(self, model_name: Optional[str] = None, **kwargs):
        """
        Args:
            model_name: 사용할 모델명 (LLM 제공자별로 다를 수 있음)
            **kwargs: 추가 설정 옵션
        """
        self.model_name = model_name
        self.kwargs = kwargs
    
    @abstractmethod
    async def call(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        LLM 호출
        
        Args:
            prompt: 프롬프트 텍스트
            temperature: 응답 다양성 (0.0 ~ 2.0)
            max_tokens: 최대 토큰 수
            **kwargs: 추가 파라미터
        
        Returns:
            LLM의 응답 텍스트
        
        Raises:
            Exception: LLM 호출 실패 시
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        LLM 서버 가용성 확인
        
        Returns:
            True if LLM is available, False otherwise
        """
        pass
