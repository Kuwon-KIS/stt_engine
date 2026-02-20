"""
불완전판매요소 검증 서비스

통화 기록에서 불완전판매요소(완료되지 않은 판매 단계)를 식별합니다.
- 고객 요구사항 미확인
- 제안 부족
- 가격 협상 미완료
- 다음 단계 미정
- 계약 미완료
"""

import logging
from typing import Optional, Dict, Any
import time

logger = logging.getLogger(__name__)


class IncompleteElementsValidator:
    """
    불완전판매요소 검증 서비스
    
    통화 기록을 분석하여 완료되지 않은 판매 단계를 식별합니다.
    외부 Agent 또는 vLLM을 통해 AI 기반 분석을 수행합니다.
    """
    
    def __init__(self, agent_backend):
        """
        IncompleteElementsValidator 초기화
        
        Args:
            agent_backend: AgentBackend 인스턴스
        """
        self.agent_backend = agent_backend
        logger.info(f"[IncompleteElementsValidator] 초기화 완료")
    
    async def validate(
        self,
        call_transcript: str,
        agent_config: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        통화 기록에서 불완전판매요소 검증
        
        Args:
            call_transcript: 통화 전사 텍스트
            agent_config: Agent 설정
                {
                    "url": "http://...",              # Agent 서버 URL
                    "request_format": "text_only",    # "text_only" or "prompt_based"
                    "chat_thread_id": "string"        # 선택사항
                }
            timeout: 요청 타임아웃 (초)
        
        Returns:
            {
                'success': bool,
                'incomplete_elements': {
                    'customer_requirements_not_confirmed': bool,
                    'proposal_not_made': bool,
                    'price_negotiation_incomplete': bool,
                    'next_steps_not_defined': bool,
                    'contract_not_completed': bool,
                    'summary': str
                },
                'analysis': str,                      # 상세 분석 결과
                'agent_type': str,                    # 'external' or 'vllm'
                'processing_time_sec': float,
                'error': str                          # 에러 메시지 (실패 시)
            }
        """
        logger.info(f"[IncompleteElementsValidator] 검증 시작 (transcript 길이: {len(call_transcript)})")
        
        start_time = time.time()
        
        if not agent_config:
            logger.error("[IncompleteElementsValidator] agent_config 필수")
            return {
                'success': False,
                'error': 'agent_config is required',
                'processing_time_sec': time.time() - start_time
            }
        
        try:
            # Agent 호출을 통한 분석
            result = await self.agent_backend.call(
                request_text=call_transcript,
                url=agent_config.get('url'),
                request_format=agent_config.get('request_format', 'text_only'),
                chat_thread_id=agent_config.get('chat_thread_id'),
                timeout=timeout,
                prompt_type='incomplete_sales_elements'  # 불완전판매요소 검증 프롬프트
            )
            
            if not result['success']:
                logger.error(f"[IncompleteElementsValidator] 분석 실패: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error'),
                    'agent_type': result.get('agent_type'),
                    'processing_time_sec': time.time() - start_time
                }
            
            # 응답 파싱 및 구조화
            analysis_text = result.get('response', '')
            
            # 불완전판매요소 추출 (간단한 키워드 기반 + AI 응답)
            incomplete_elements = self._parse_incomplete_elements(analysis_text)
            
            logger.info(f"[IncompleteElementsValidator] ✅ 검증 완료 (agent_type: {result.get('agent_type')})")
            
            return {
                'success': True,
                'incomplete_elements': incomplete_elements,
                'analysis': analysis_text,
                'agent_type': result.get('agent_type'),
                'chat_thread_id': result.get('chat_thread_id'),
                'processing_time_sec': time.time() - start_time
            }
        
        except Exception as e:
            logger.error(f"[IncompleteElementsValidator] 검증 오류: {type(e).__name__}: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"{type(e).__name__}: {str(e)}",
                'processing_time_sec': time.time() - start_time
            }
    
    def _parse_incomplete_elements(self, analysis_text: str) -> Dict[str, Any]:
        """
        AI 분석 결과에서 불완전판매요소 추출
        
        Args:
            analysis_text: AI Agent의 분석 텍스트
        
        Returns:
            불완전판매요소 구조화된 데이터
        """
        # 키워드 기반 간단한 파싱 (실제로는 AI 응답에 구조화된 데이터가 포함됨)
        keywords = {
            'customer_requirements_not_confirmed': [
                '고객 요구사항 미확인', '요구사항 확인 안됨', '고객 니즈 미파악',
                'requirements not confirmed', 'needs not identified'
            ],
            'proposal_not_made': [
                '제안 부족', '제안 미실시', '솔루션 미제시',
                'proposal not made', 'no proposal'
            ],
            'price_negotiation_incomplete': [
                '가격 협상 미완료', '가격 협상 실패', '가격 결정 미완료',
                'price negotiation incomplete', 'pricing not agreed'
            ],
            'next_steps_not_defined': [
                '다음 단계 미정', 'follow-up 미정', '다음 액션 미정',
                'next steps not defined', 'follow-up not scheduled'
            ],
            'contract_not_completed': [
                '계약 미완료', '서명 미실시', '계약 미체결',
                'contract not completed', 'no signature'
            ]
        }
        
        analysis_lower = analysis_text.lower()
        
        parsed = {
            'customer_requirements_not_confirmed': any(kw in analysis_lower for kw in keywords['customer_requirements_not_confirmed']),
            'proposal_not_made': any(kw in analysis_lower for kw in keywords['proposal_not_made']),
            'price_negotiation_incomplete': any(kw in analysis_lower for kw in keywords['price_negotiation_incomplete']),
            'next_steps_not_defined': any(kw in analysis_lower for kw in keywords['next_steps_not_defined']),
            'contract_not_completed': any(kw in analysis_lower for kw in keywords['contract_not_completed']),
            'summary': analysis_text[:500]  # 처음 500자를 요약으로 사용
        }
        
        return parsed


def get_incomplete_elements_validator(agent_backend):
    """IncompleteElementsValidator 싱글톤 인스턴스 반환"""
    if not hasattr(get_incomplete_elements_validator, '_instance'):
        get_incomplete_elements_validator._instance = IncompleteElementsValidator(agent_backend)
    return get_incomplete_elements_validator._instance
