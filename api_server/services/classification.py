"""
Classification Service - 통화 분류 서비스

LLM을 사용하여 고객 상담 통화를 분류합니다.
- TELEMARKETING: 텔레마케팅/영업 통화
- CUSTOMER_SERVICE: 고객 서비스/기술 지원
- SALES: 직판 영업
- SURVEY: 설문조사
- SCAM: 사기/불법
- UNKNOWN: 분류 불가
"""
import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv

from api_server.llm_clients import LLMClientFactory
from api_server.constants import ClassificationCode
from api_server.models import ClassificationResult

logger = logging.getLogger(__name__)


class ClassificationService:
    """통화 분류 서비스"""
    
    def __init__(self):
        """서비스 초기화"""
        load_dotenv()
        self.llm_client = None
        self._initialized = False
        self._llm_clients_cache = {}  # 모델별 클라이언트 캐시
        
        logger.info("ClassificationService 초기화")
    
    async def initialize(self, model_name: Optional[str] = None, api_base: Optional[str] = None):
        """
        LLM 클라이언트 초기화
        
        Args:
            model_name: 사용할 모델명
            api_base: API base URL
        """
        cache_key = f"{model_name}:{api_base}"
        
        # 이미 초기화된 모델인지 확인
        if cache_key in self._llm_clients_cache:
            logger.debug(f"LLM 클라이언트 캐시 사용: {cache_key}")
            self.llm_client = self._llm_clients_cache[cache_key]
            self._initialized = True
            return
        
        try:
            logger.info(f"LLM 클라이언트 초기화 시작: model={model_name}, api_base={api_base}")
            
            client = LLMClientFactory.create_client(
                model_name=model_name,
                base_url=api_base
            )
            
            self._llm_clients_cache[cache_key] = client
            self.llm_client = client
            self._initialized = True
            
            logger.info(f"LLM 클라이언트 초기화 완료: {cache_key}")
        except Exception as e:
            logger.error(f"LLM 클라이언트 초기화 실패: {str(e)}", exc_info=True)
            raise
    
    async def classify_text(
        self,
        text: str,
        prompt_type: str = "classification_default_v1",
        model_name: Optional[str] = None,
        api_base: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.3
    ) -> ClassificationResult:
        """
        텍스트 분류
        
        Args:
            text: 분류할 텍스트
            prompt_type: 프롬프트 타입
            model_name: 사용할 모델명 (None이면 기본값)
            api_base: API base URL (None이면 기본값)
            max_tokens: 최대 토큰 수
            temperature: 온도 값
        
        Returns:
            ClassificationResult 객체
        """
        try:
            # LLM 클라이언트 초기화 확인
            if not self._initialized or self.llm_client is None:
                await self.initialize(model_name, api_base)
            
            logger.info(f"[Classification] 분류 시작: text_len={len(text)}, prompt_type={prompt_type}")
            
            # 분류 프롬프트 생성
            classification_prompt = self._build_classification_prompt(text)
            
            # LLM API 호출
            logger.debug(f"[Classification] LLM API 호출: model={model_name or 'default'}")
            response = await self.llm_client.call(
                prompt=classification_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            logger.debug(f"[Classification] LLM 응답 수신: {response[:100]}...")
            
            # 응답 파싱
            result = self._parse_classification_response(response)
            
            logger.info(
                f"[Classification] ✅ 분류 완료: "
                f"category={result.category}, confidence={result.confidence}"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"[Classification] 분류 오류: {type(e).__name__}: {str(e)}", exc_info=True)
            return ClassificationResult(
                code=ClassificationCode.UNKNOWN.value,
                category="분류 오류",
                confidence=0.0,
                reason=f"Error: {str(e)}"
            )
    
    @staticmethod
    def _build_classification_prompt(text: str) -> str:
        """분류 프롬프트 생성"""
        return f"""다음 텍스트를 분류하세요. 고객 상담 통화의 성격을 파악하고 다음 중 하나로 분류해주세요:
- TELEMARKETING: 텔레마케팅/영업 통화
- CUSTOMER_SERVICE: 고객 서비스/기술 지원
- SALES: 직판 영업
- SURVEY: 설문조사
- SCAM: 사기/불법
- UNKNOWN: 분류 불가

텍스트: {text}

분류 결과를 JSON 형식으로 반환하세요:
{{"category": "분류", "confidence": 0.0~1.0 사이의 신뢰도}}
"""
    
    @staticmethod
    def _parse_classification_response(response: str) -> ClassificationResult:
        """
        LLM 응답 파싱
        
        Args:
            response: LLM 응답 텍스트
        
        Returns:
            ClassificationResult 객체
        """
        try:
            result_json = json.loads(response)
            category = result_json.get("category", "UNKNOWN")
            confidence = float(result_json.get("confidence", 0.0))
            
            logger.debug(f"응답 파싱 성공: category={category}, confidence={confidence}")
            
            return ClassificationResult(
                code=category,
                category=category,
                confidence=confidence,
                reason="LLM-based classification"
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"응답 파싱 실패: {str(e)}, response={response[:200]}")
            return ClassificationResult(
                code=ClassificationCode.UNKNOWN.value,
                category="분류 불가",
                confidence=0.0,
                reason=f"JSON parsing error: {str(e)}"
            )


# ============================================================================
# Singleton 패턴: 전역 서비스 인스턴스
# ============================================================================

_classification_service: Optional[ClassificationService] = None


def get_classification_service() -> ClassificationService:
    """
    ClassificationService의 싱글톤 인스턴스 반환
    
    Returns:
        ClassificationService 인스턴스
    """
    global _classification_service
    
    if _classification_service is None:
        logger.info("ClassificationService 싱글톤 생성")
        _classification_service = ClassificationService()
    
    return _classification_service


async def _async_get_classification_service() -> ClassificationService:
    """
    FastAPI Depends()와 호환되는 async 래퍼
    ClassificationService의 싱글톤 인스턴스 반환
    
    Returns:
        ClassificationService 인스턴스
    """
    return get_classification_service()
