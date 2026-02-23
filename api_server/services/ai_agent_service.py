"""
AI Agent Service (Fallback: Dummy Agent)

STT 결과 텍스트를 외부 AI Agent에 전달하여 처리합니다.
- 다양한 Agent 백엔드 지원 (URL + 요청 형식으로 자동 판정)
- Streaming 지원
- Chat Thread ID 유지
- Fallback 처리 (Dummy Agent)
"""

import logging
import json
import asyncio
from typing import Optional, Dict, Any
import os
import time

logger = logging.getLogger(__name__)


class AIAgentService:
    """
    AI Agent 호출 서비스
    
    음성인식 결과 텍스트를 외부 AI Agent에 전달합니다.
    - 스트리밍 지원
    - Chat Thread ID 유지
    - vLLM 기반 Fallback 지원
    """
    
    def __init__(
        self,
        agent_url: Optional[str] = None,
        vllm_base_url: Optional[str] = None,
        vllm_model: Optional[str] = None,
        enable_fallback: bool = True
    ):
        """
        AIAgentService 초기화
        
        Args:
            agent_url: Agent 서버 URL (기본값: env 또는 fallback 사용)
            vllm_base_url: vLLM 서버 URL (fallback용)
            vllm_model: vLLM 모델명 (fallback용)
            enable_fallback: vLLM 또는 Dummy로 fallback 가능 여부
        """
        self.agent_url = agent_url or os.getenv('AGENT_URL', None)
        self.vllm_base_url = vllm_base_url or os.getenv('VLLM_BASE_URL', 'http://localhost:8001')
        self.vllm_model = vllm_model or os.getenv('VLLM_MODEL', 'Qwen3-30B-A3B-Thinking-2507-FP8')
        self.enable_fallback = enable_fallback
        
        logger.info(f"[AIAgentService] 초기화 완료")
        logger.info(f"  Agent URL: {self.agent_url or '(설정 안 됨 - Fallback 사용)'}")
        logger.info(f"  vLLM Base URL: {self.vllm_base_url}")
        logger.info(f"  vLLM Model: {self.vllm_model}")
        logger.info(f"  Fallback 활성화: {self.enable_fallback}")
        
        self._check_agent_availability()
    
    def _check_agent_availability(self):
        """Agent 서버 가용성 확인"""
        if not self.agent_url:
            logger.info(f"[AIAgentService] Agent URL이 설정되지 않음 - Fallback 모드")
            return
        
        try:
            import requests
            response = requests.get(f"{self.agent_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info(f"[AIAgentService] ✓ Agent 서버 사용 가능")
            else:
                logger.warning(f"[AIAgentService] Agent 서버 응답 비정상 (status={response.status_code})")
        except Exception as e:
            logger.warning(f"[AIAgentService] Agent 서버 접속 실패: {e}")
    
    async def process(
        self,
        user_query: str,
        agent_url: str,
        request_format: str = "text_only",
        use_streaming: bool = False,
        chat_thread_id: Optional[str] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        텍스트를 Agent로 처리
        
        Args:
            user_query: 사용자 쿼리 (정제된 STT 텍스트)
            agent_url: Agent 서버 URL
            request_format: "text_only" 또는 "prompt_based"
            use_streaming: 스트리밍 모드 사용 여부
            chat_thread_id: 채팅 스레드 ID (대화 연속성 유지)
            timeout: 요청 타임아웃 (초)
        
        Returns:
            {
                'success': bool,
                'response': str,              # Agent의 응답 텍스트
                'chat_thread_id': str,       # 반환받은 또는 기존 chat_thread_id
                'use_streaming': bool,       # 스트리밍 사용 여부
                'agent_type': str,           # 'external', 'vllm', 'dummy'
                'processing_time_sec': float,
                'error': str                 # 에러 메시지 (실패 시)
            }
        """
        logger.info(f"[AIAgent] 처리 시작 (query 길이: {len(user_query)}, url={agent_url}, format={request_format})")
        
        start_time = time.time()
        
        try:
            # AgentBackend을 통한 호출
            from api_server.services.agent_backend import get_agent_backend
            
            agent_backend = get_agent_backend()
            
            # Agent 호출 시도
            if agent_url:
                logger.info(f"[AIAgent] Agent 호출: {agent_url}")
                result = await agent_backend.call(
                    request_text=user_query,
                    url=agent_url,
                    request_format=request_format,
                    chat_thread_id=chat_thread_id,
                    timeout=timeout
                )
                
                if result['success']:
                    result['processing_time_sec'] = time.time() - start_time
                    return result
                else:
                    logger.warning(f"[AIAgent] Agent 호출 실패: {result.get('error')} → Dummy로 Fallback")
            else:
                logger.warning(f"[AIAgent] Agent URL이 설정되지 않음 → Dummy로 Fallback")
            
            # Fallback: Dummy Agent
            logger.info(f"[AIAgent] Dummy Agent로 Fallback 처리")
            result = self._call_dummy_agent(
                user_query=user_query,
                chat_thread_id=chat_thread_id
            )
            result['processing_time_sec'] = time.time() - start_time
            return result
        
        except Exception as e:
            logger.error(f"[AIAgent] 처리 중 오류: {type(e).__name__}: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"{type(e).__name__}: {str(e)}",
                'response': None,
                'chat_thread_id': chat_thread_id,
                'agent_type': 'error',
                'processing_time_sec': time.time() - start_time,
                'use_streaming': use_streaming
            }
    
    async def _call_external_agent(
        self,
        user_query: str,
        use_streaming: bool,
        chat_thread_id: Optional[str],
        timeout: int
    ) -> Dict[str, Any]:
        """외부 Agent API 호출"""
        
        try:
            import aiohttp
            
            payload = {
                "use_streaming": use_streaming,
                "chat_thread_id": chat_thread_id,
                "parameters": {
                    "user_query": user_query
                }
            }
            
            logger.debug(f"[AIAgent] 외부 Agent 요청 전송: {self.agent_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.agent_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"[AIAgent] ✅ 외부 Agent 응답 수신")
                        
                        return {
                            'success': True,
                            'response': data.get('response', ''),
                            'chat_thread_id': data.get('chat_thread_id') or chat_thread_id,
                            'use_streaming': use_streaming,
                            'agent_type': 'external'
                        }
                    else:
                        error_msg = f"Agent API 에러 (status={response.status})"
                        logger.error(f"[AIAgent] {error_msg}")
                        return {
                            'success': False,
                            'error': error_msg,
                            'agent_type': 'external'
                        }
        
        except asyncio.TimeoutError:
            error_msg = "Agent API 타임아웃"
            logger.error(f"[AIAgent] {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'agent_type': 'external'
            }
        
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"[AIAgent] 외부 Agent 호출 오류: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'agent_type': 'external'
            }
    
    async def _call_vllm_agent(
        self,
        user_query: str,
        timeout: int
    ) -> Dict[str, Any]:
        """vLLM을 Agent로 사용하는 Fallback"""
        
        try:
            import aiohttp
            import asyncio
            
            payload = {
                "model": self.vllm_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정확하고 친절하게 답변해주세요."
                    },
                    {
                        "role": "user",
                        "content": user_query
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
                "top_p": 0.95,
            }
            
            logger.debug(f"[AIAgent] vLLM Fallback 요청 전송: {self.vllm_base_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.vllm_base_url}/v1/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        message_content = data['choices'][0]['message']['content']
                        logger.info(f"[AIAgent] ✅ vLLM Fallback 응답 수신")
                        
                        return {
                            'success': True,
                            'response': message_content,
                            'chat_thread_id': None,
                            'use_streaming': False,
                            'agent_type': 'vllm'
                        }
                    else:
                        error_msg = f"vLLM API 에러 (status={response.status})"
                        logger.error(f"[AIAgent] {error_msg}")
                        return {
                            'success': False,
                            'error': error_msg,
                            'agent_type': 'vllm'
                        }
        
        except asyncio.TimeoutError:
            error_msg = "vLLM API 타임아웃"
            logger.error(f"[AIAgent] {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'agent_type': 'vllm'
            }
        
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"[AIAgent] vLLM Fallback 오류: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'agent_type': 'vllm'
            }
    
    def _call_dummy_agent(
        self,
        user_query: str,
        chat_thread_id: Optional[str]
    ) -> Dict[str, Any]:
        """Dummy Agent - 테스트용"""
        
        logger.info(f"[AIAgent] Dummy Agent로 응답 생성 (query 길이: {len(user_query)})")
        
        # Query의 핵심 키워드 추출
        keywords = []
        if "구매" in user_query or "가격" in user_query:
            keywords.append("구매 관련")
        if "문제" in user_query or "오류" in user_query:
            keywords.append("기술 지원")
        if "불만" in user_query or "불량" in user_query:
            keywords.append("클레임")
        if "배송" in user_query or "주문" in user_query:
            keywords.append("주문 조회")
        
        keyword_str = ", ".join(keywords) if keywords else "일반 문의"
        
        # Dummy 응답 생성
        response = f"""[AI Agent Dummy Response]

귀하의 문의 내용({keyword_str})에 대해 다음과 같이 안내드립니다:

1. 현황 파악:
   - 제공하신 텍스트를 분석했습니다.
   - 주요 키워드: {keyword_str}

2. 권장 사항:
   - 더 상세한 정보가 필요하신 경우 추가 상담을 권장드립니다.
   - 관련 부서로 연결하여 신속하게 처리해드리겠습니다.

3. 다음 단계:
   - 담당자가 곧 연락드리겠습니다.
   - 추가 질문이 있으시면 언제든 문의해주세요.

---
This is a dummy AI agent response for testing purposes.
The actual external agent will be integrated in the production environment.
"""
        
        return {
            'success': True,
            'response': response,
            'chat_thread_id': chat_thread_id,
            'use_streaming': False,
            'agent_type': 'dummy'
        }


# 글로벌 서비스 인스턴스 (싱글톤)
_service_instance: Optional[AIAgentService] = None


async def get_ai_agent_service() -> AIAgentService:
    """
    AIAgentService의 싱글톤 인스턴스 반환
    
    FastAPI 의존성으로 사용 가능:
    ```python
    async def my_endpoint(service: AIAgentService = Depends(get_ai_agent_service)):
        result = await service.process(text)
    ```
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = AIAgentService()
    return _service_instance
