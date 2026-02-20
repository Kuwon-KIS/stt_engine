"""
Agent 호출 추상화 계층

다양한 Agent 백엔드 (외부 Agent, vLLM 등)를 통합 인터페이스로 호출합니다.
URL과 요청 형식만으로 백엔드 선택이 결정됩니다.
"""

import logging
import time
import asyncio
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AgentBackend:
    """
    Agent 호출 통합 인터페이스
    
    Request Format:
    - text_only: 텍스트만 전송 (외부 Agent)
    - prompt_based: 프롬프트 템플릿으로 구성하여 전송 (vLLM)
    """
    
    def __init__(self):
        """AgentBackend 초기화"""
        self.text_only_prompts = {
            'incomplete_sales_elements': '다음 통화 기록에서 불완전판매요소를 분석하세요.'
        }
        
        self.prompt_based_prompts = {
            'incomplete_sales_elements': """당신은 판매 컨설턴트입니다. 다음 통화 기록을 분석하여 불완전판매요소를 식별하세요.

불완전판매요소는:
1. 고객 요구사항 미확인 - 고객의 실제 필요를 파악하지 못함
2. 제안 부족 - 명확한 솔루션/제안을 제시하지 않음
3. 가격 협상 미완료 - 가격 결정이나 협상이 이루어지지 않음
4. 다음 단계 미정 - 후속 조치가 명확하지 않음
5. 계약 미완료 - 최종 계약이나 서명이 없음

통화 내용:
{transcript}

분석 결과를 다음 형식으로 제시하세요:
- 고객 요구사항 확인 여부: [확인됨/미확인]
- 제안 제시 여부: [제시됨/미제시]
- 가격 협상 상태: [완료/진행중/미완료]
- 다음 단계: [명확함/불명확]
- 계약 상태: [완료/미완료]
- 종합 분석: [주요 문제점과 개선 사항]"""
        }
        
        logger.info(f"[AgentBackend] 초기화 완료")
    
    async def call(
        self,
        request_text: str,
        url: str,
        request_format: str = "text_only",
        chat_thread_id: Optional[str] = None,
        timeout: int = 30,
        prompt_type: str = "incomplete_sales_elements"
    ) -> Dict[str, Any]:
        """
        Agent 호출
        
        Args:
            request_text: 요청 텍스트 (통화 기록 등)
            url: Agent 서버 URL
            request_format: "text_only" 또는 "prompt_based"
            chat_thread_id: 채팅 스레드 ID (선택사항)
            timeout: 요청 타임아웃 (초)
            prompt_type: 프롬프트 템플릿 타입
        
        Returns:
            {
                'success': bool,
                'response': str,              # Agent의 응답
                'agent_type': str,            # 'external' or 'vllm'
                'chat_thread_id': str,        # 채팅 스레드 ID
                'processing_time_sec': float,
                'error': str                  # 에러 메시지 (실패 시)
            }
        """
        start_time = time.time()
        
        logger.info(f"[AgentBackend] 호출 시작 (url={url}, format={request_format}, timeout={timeout}s)")
        
        try:
            # URL 기반으로 Agent 타입 자동 판정
            agent_type = self._detect_agent_type(url)
            
            # 요청 형식에 따라 처리
            if request_format == "prompt_based":
                # 프롬프트 템플릿 사용 (일반적으로 vLLM)
                response = await self._call_with_prompt(
                    request_text=request_text,
                    url=url,
                    prompt_type=prompt_type,
                    chat_thread_id=chat_thread_id,
                    timeout=timeout,
                    agent_type=agent_type
                )
            else:
                # 텍스트만 전송 (외부 Agent)
                response = await self._call_text_only(
                    request_text=request_text,
                    url=url,
                    chat_thread_id=chat_thread_id,
                    timeout=timeout,
                    agent_type=agent_type
                )
            
            if response['success']:
                logger.info(f"[AgentBackend] ✅ 호출 완료 (agent_type={agent_type})")
            
            response['agent_type'] = agent_type
            response['processing_time_sec'] = time.time() - start_time
            return response
        
        except asyncio.TimeoutError:
            logger.error(f"[AgentBackend] 타임아웃: {timeout}초 초과")
            logger.warning(f"[AgentBackend] Dummy 응답으로 fallback (로깅됨)")
            return self._create_dummy_response(
                error=f'Agent 호출 타임아웃 ({timeout}s)',
                error_type='TimeoutError',
                request_text=request_text,
                start_time=start_time
            )
        
        except ConnectionError as e:
            logger.error(f"[AgentBackend] 연결 실패: {str(e)}")
            logger.warning(f"[AgentBackend] Dummy 응답으로 fallback (로깅됨)")
            return self._create_dummy_response(
                error=f'Agent 서버 연결 실패: {str(e)}',
                error_type='ConnectionError',
                request_text=request_text,
                start_time=start_time
            )
        
        except Exception as e:
            logger.error(f"[AgentBackend] 호출 오류: {type(e).__name__}: {e}", exc_info=True)
            logger.warning(f"[AgentBackend] Dummy 응답으로 fallback (로깅됨)")
            return self._create_dummy_response(
                error=f"{type(e).__name__}: {str(e)}",
                error_type=type(e).__name__,
                request_text=request_text,
                start_time=start_time
            )
    
    def _create_dummy_response(
        self,
        error: str,
        error_type: str,
        request_text: str,
        start_time: float,
        chat_thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dummy Agent 응답 생성
        
        Args:
            error: 에러 메시지
            error_type: 에러 타입
            request_text: 원래 요청 텍스트
            start_time: 호출 시작 시간
            chat_thread_id: 채팅 스레드 ID
        
        Returns:
            Dummy Agent 응답
        """
        processing_time = time.time() - start_time
        
        return {
            'success': False,
            'response': '[Dummy Agent] 분석을 수행할 수 없습니다.',
            'agent_type': 'dummy',
            'is_dummy': True,
            'dummy_reason': error,
            'error': error,
            'error_type': error_type,
            'processing_time_sec': processing_time,
            'chat_thread_id': chat_thread_id
        }
    
    async def _call_text_only(
        self,
        request_text: str,
        url: str,
        chat_thread_id: Optional[str],
        timeout: int,
        agent_type: str
    ) -> Dict[str, Any]:
        """
        텍스트만 전송하는 형식으로 Agent 호출
        
        요청 형식:
        {
            "use_streaming": false,
            "chat_thread_id": "string",
            "parameters": {
                "user_query": "string"
            }
        }
        """
        logger.info(f"[AgentBackend] 텍스트 형식 호출 ({agent_type})")
        
        import aiohttp
        
        payload = {
            "use_streaming": False,
            "chat_thread_id": chat_thread_id,
            "parameters": {
                "user_query": request_text
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'success': True,
                            'response': data.get('response') or data.get('result', ''),
                            'chat_thread_id': data.get('chat_thread_id', chat_thread_id),
                            'agent_type': agent_type
                        }
                    else:
                        logger.error(f"[AgentBackend] 응답 오류 (status={response.status})")
                        return {
                            'success': False,
                            'error': f"HTTP {response.status}",
                            'agent_type': agent_type
                        }
        
        except Exception as e:
            logger.error(f"[AgentBackend] 텍스트 형식 호출 오류: {e}")
            raise
    
    async def _call_with_prompt(
        self,
        request_text: str,
        url: str,
        prompt_type: str,
        chat_thread_id: Optional[str],
        timeout: int,
        agent_type: str
    ) -> Dict[str, Any]:
        """
        프롬프트 템플릿으로 구성하여 Agent 호출
        
        vLLM의 /v1/chat/completions 형식:
        {
            "model": "model_name",
            "messages": [{"role": "user", "content": "..."}],
            "temperature": 0.7,
            "max_tokens": 2048
        }
        """
        logger.info(f"[AgentBackend] 프롬프트 형식 호출 ({agent_type})")
        
        import aiohttp
        
        # 프롬프트 템플릿 선택
        prompt_template = self.prompt_based_prompts.get(prompt_type, '')
        if not prompt_template:
            logger.error(f"[AgentBackend] 알 수 없는 프롬프트 타입: {prompt_type}")
            return {
                'success': False,
                'error': f'Unknown prompt type: {prompt_type}',
                'agent_type': agent_type
            }
        
        # 프롬프트 구성 (transcript 변수 치환)
        final_prompt = prompt_template.replace('{transcript}', request_text)
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": final_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2048
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # vLLM 응답 포맷 처리
                        if 'choices' in data:
                            response_text = data['choices'][0]['message']['content']
                        else:
                            response_text = data.get('response', str(data))
                        
                        return {
                            'success': True,
                            'response': response_text,
                            'chat_thread_id': chat_thread_id,
                            'agent_type': agent_type
                        }
                    else:
                        logger.error(f"[AgentBackend] 응답 오류 (status={response.status})")
                        return {
                            'success': False,
                            'error': f"HTTP {response.status}",
                            'agent_type': agent_type
                        }
        
        except Exception as e:
            logger.error(f"[AgentBackend] 프롬프트 형식 호출 오류: {e}")
            raise
    
    def _detect_agent_type(self, url: str) -> str:
        """URL 기반으로 Agent 타입 자동 판정"""
        if '/v1/chat' in url or 'vllm' in url.lower():
            return 'vllm'
        return 'external'


def get_agent_backend():
    """AgentBackend 싱글톤 인스턴스 반환"""
    if not hasattr(get_agent_backend, '_instance'):
        get_agent_backend._instance = AgentBackend()
    return get_agent_backend._instance
