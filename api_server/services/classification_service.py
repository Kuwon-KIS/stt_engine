"""
Classification Service

STT 결과 텍스트를 분석하여 통화 카테고리 분류
vLLM을 통한 LLM 기반 분류
"""

import logging
import asyncio
from typing import Optional, Dict, Any
import os

try:
    import aiohttp
except ImportError:
    aiohttp = None

logger = logging.getLogger(__name__)


class ClassificationService:
    """
    통화 분류 서비스
    
    음성인식 결과 텍스트를 vLLM을 통해 분류합니다.
    - 사전판매 (PRE_SALES)
    - 고객 서비스 (CUSTOMER_SERVICE)
    - 기술 지원 (TECHNICAL_SUPPORT)
    - 일반 통화 (GENERAL)
    - 불만/클레임 (COMPLAINT)
    - 지원 (SUPPORT)
    """
    
    def __init__(
        self,
        vllm_base_url: Optional[str] = None,
        vllm_model: Optional[str] = None
    ):
        """
        ClassificationService 초기화
        
        Args:
            vllm_base_url: vLLM 서버 URL (기본값: env 또는 localhost:8001)
            vllm_model: vLLM 모델명 (기본값: env 또는 Qwen3-30B-A3B-Thinking-2507-FP8)
        """
        self.vllm_base_url = vllm_base_url or os.getenv('VLLM_BASE_URL', 'http://localhost:8001')
        self.vllm_model = vllm_model or os.getenv('VLLM_MODEL', 'Qwen3-30B-A3B-Thinking-2507-FP8')
        
        logger.info(f"[ClassificationService] 초기화 완료")
        logger.info(f"  vLLM Base URL: {self.vllm_base_url}")
        logger.info(f"  vLLM Model: {self.vllm_model}")
        
        self._check_vllm_availability()
    
    def _check_vllm_availability(self):
        """vLLM 서버 가용성 확인"""
        try:
            import requests
            response = requests.get(f"{self.vllm_base_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info(f"[ClassificationService] ✓ vLLM 서버 사용 가능")
            else:
                logger.warning(f"[ClassificationService] vLLM 서버 응답 비정상 (status={response.status_code})")
        except Exception as e:
            logger.warning(f"[ClassificationService] vLLM 서버 접속 실패: {e}")
    
    async def classify_call(
        self,
        text: str,
        prompt_type: str = "classification_default_v1",
        temperature: float = 0.3,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """
        통화 내용 분류
        
        Args:
            text: 분류할 텍스트
            prompt_type: 사용할 프롬프트 타입
            temperature: LLM 온도 (0~1)
            max_tokens: 최대 토큰 수
        
        Returns:
            {
                'code': str,              # CLASS_PRE_SALES 등
                'category': str,          # 사전판매 등
                'confidence': float,      # 신뢰도 (0-100)
                'reason': str,           # 분류 사유
                'success': bool,         # 처리 성공 여부
                'error': str             # 에러 메시지 (실패 시)
            }
        """
        logger.info(f"[ClassificationService] 분류 시작 (텍스트 길이: {len(text)}, 프롬프트: {prompt_type})")
        
        try:
            # 프롬프트 생성
            prompt = self._get_classification_prompt(text, prompt_type)
            
            # vLLM 호출
            result = await self._call_vllm(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if not result.get('success'):
                logger.error(f"[ClassificationService] vLLM 호출 실패: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'code': 'CLASS_UNKNOWN',
                    'category': '분류 불가',
                    'confidence': 0.0,
                    'reason': 'vLLM error'
                }
            
            # 응답 파싱
            classification_result = self._parse_classification_response(
                result.get('response', ''),
                text
            )
            
            logger.info(f"[ClassificationService] ✅ 분류 완료: {classification_result['code']}")
            return classification_result
        
        except Exception as e:
            logger.error(f"[ClassificationService] 분류 중 오류: {type(e).__name__}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'code': 'CLASS_UNKNOWN',
                'category': '분류 불가',
                'confidence': 0.0,
                'reason': f'Classification error: {str(e)}'
            }
    
    def _get_classification_prompt(self, text: str, prompt_type: str) -> str:
        """분류용 프롬프트 생성"""
        
        if prompt_type == "classification_default_v1":
            return f"""다음 통화 내용을 분류하세요.

통화 내용:
{text}

다음 카테고리 중 하나로 분류해주세요:
1. CLASS_PRE_SALES: 사전판매 관련 상담 (제품 구매, 가격 문의 등)
2. CLASS_CUSTOMER_SERVICE: 고객 서비스 (주문 조회, 배송 상태 등)
3. CLASS_TECHNICAL_SUPPORT: 기술 지원 (제품 사용법, 기술 문제 해결)
4. CLASS_GENERAL: 일반 통화 (특정 카테고리 없음)
5. CLASS_COMPLAINT: 불만/클레임 (제품 불량, 서비스 불만)
6. CLASS_SUPPORT: 지원 (기타 지원)

응답 형식 (JSON):
{{
    "code": "분류 코드",
    "confidence": 신뢰도 (0-100),
    "reason": "분류 사유"
}}"""
        
        elif prompt_type == "classification_pre_sales_focus":
            return f"""다음 통화 내용을 분석하여 사전판매 여부를 판단하세요.

통화 내용:
{text}

사전판매 판단:
- CLASS_PRE_SALES: 제품 구매, 가격 문의, 사양 확인, 구매 결정 단계
- CLASS_GENERAL: 사전판매가 아닌 기타 통화

응답 형식 (JSON):
{{
    "code": "분류 코드",
    "confidence": 신뢰도 (0-100),
    "reason": "판단 사유"
}}"""
        
        else:
            # 기본값
            return f"""다음 통화 내용을 분류하세요.

통화 내용:
{text}

분류 카테고리:
- CLASS_PRE_SALES: 사전판매
- CLASS_CUSTOMER_SERVICE: 고객 서비스
- CLASS_TECHNICAL_SUPPORT: 기술 지원
- CLASS_GENERAL: 일반
- CLASS_COMPLAINT: 불만/클레임
- CLASS_SUPPORT: 지원

응답 형식 (JSON):
{{
    "code": "분류 코드",
    "confidence": 신뢰도 (0-100),
    "reason": "사유"
}}"""
    
    async def _call_vllm(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """vLLM API 호출"""
        
        try:
            if aiohttp is None:
                return {
                    'success': False,
                    'error': 'aiohttp not installed'
                }
            
            payload = {
                "model": self.vllm_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "당신은 통화 내용 분류 전문가입니다. 주어진 통화 내용을 분석하여 정확히 분류해주세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": 0.95,
            }
            
            logger.debug(f"[ClassificationService] vLLM 호출: {self.vllm_base_url}/v1/chat/completions")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.vllm_base_url}/v1/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        message_content = data['choices'][0]['message']['content']
                        logger.debug(f"[ClassificationService] vLLM 응답 수신 (길이: {len(message_content)})")
                        
                        return {
                            'success': True,
                            'response': message_content
                        }
                    else:
                        error_msg = f"vLLM API 에러 (status={response.status})"
                        logger.error(f"[ClassificationService] {error_msg}")
                        return {
                            'success': False,
                            'error': error_msg
                        }
        
        except asyncio.TimeoutError:
            error_msg = "vLLM API 타임아웃"
            logger.error(f"[ClassificationService] {error_msg}")
            return {'success': False, 'error': error_msg}
        
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"[ClassificationService] vLLM 호출 오류: {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _parse_classification_response(self, response: str, original_text: str) -> Dict[str, Any]:
        """vLLM 응답 파싱"""
        
        try:
            import json
            import re
            
            # JSON 부분 추출
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                logger.warning(f"[ClassificationService] JSON 응답 추출 실패, 응답: {response[:200]}")
                return {
                    'success': False,
                    'error': 'Failed to parse response',
                    'code': 'CLASS_UNKNOWN',
                    'category': '분류 불가',
                    'confidence': 0.0,
                    'reason': 'Parse error'
                }
            
            json_str = json_match.group(0)
            data = json.loads(json_str)
            
            code = data.get('code', 'CLASS_UNKNOWN')
            confidence = min(max(float(data.get('confidence', 0)), 0), 100)
            reason = data.get('reason', '')
            
            # 카테고리명 매핑
            category_map = {
                'CLASS_PRE_SALES': '사전판매',
                'CLASS_CUSTOMER_SERVICE': '고객 서비스',
                'CLASS_TECHNICAL_SUPPORT': '기술 지원',
                'CLASS_GENERAL': '일반 통화',
                'CLASS_COMPLAINT': '불만/클레임',
                'CLASS_SUPPORT': '지원',
                'CLASS_OTHER': '기타',
                'CLASS_UNKNOWN': '분류 불가',
            }
            
            category = category_map.get(code, '분류 불가')
            
            return {
                'success': True,
                'code': code,
                'category': category,
                'confidence': confidence,
                'reason': reason
            }
        
        except Exception as e:
            logger.error(f"[ClassificationService] 응답 파싱 오류: {type(e).__name__}: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 'CLASS_UNKNOWN',
                'category': '분류 불가',
                'confidence': 0.0,
                'reason': 'Parse error'
            }


# 글로벌 서비스 인스턴스 (싱글톤)
_service_instance: Optional[ClassificationService] = None


async def get_classification_service() -> ClassificationService:
    """
    ClassificationService의 싱글톤 인스턴스 반환
    
    FastAPI 의존성으로 사용 가능:
    ```python
    async def my_endpoint(service: ClassificationService = Depends(get_classification_service)):
        result = await service.classify_call(text)
    ```
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = ClassificationService()
    return _service_instance
