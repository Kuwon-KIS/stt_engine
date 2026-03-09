"""
Element Detection Service - 요소 탐지 서비스 (불완전판매, 부당권유 등)

LLM 또는 외부 AI Agent를 사용하여 통화에서 규제 대상 요소를 탐지합니다.
Fallback 메커니즘: 외부 API 실패 시 로컬 vLLM으로 자동 전환
"""
import os
import json
import httpx
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

from api_server.llm_clients import LLMClientFactory
from api_server.config import FormDataConfig

logger = logging.getLogger(__name__)


class ElementDetectionService:
    """요소 탐지 서비스"""
    
    def __init__(self):
        """서비스 초기화"""
        load_dotenv()
        self.llm_client = None
        self._initialized = False
        self._llm_clients_cache = {}  # 모델별 클라이언트 캐시
        
        logger.info("ElementDetectionService 초기화")
    
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
    
    async def detect_elements(
        self,
        text: str,
        api_type: str = "ai_agent",
        llm_type: str = "vllm",
        vllm_model_name: Optional[str] = None,
        vllm_base_url: Optional[str] = None,
        agent_url: Optional[str] = None,
        detection_types: Optional[List[str]] = None,
        prompt_type: str = "element_detection_qwen"
    ) -> Dict[str, Any]:
        """
        요소 탐지 (에이전트 우선, vLLM 폴백)
        
        Args:
            text: 처리할 텍스트
            api_type: "ai_agent"=AI Agent만 (기본값), "vllm"=로컬 vLLM만, "fallback"=Agent→vLLM
            llm_type: LLM 타입 ('vllm')
            vllm_model_name: vLLM 모델명 (ai_agent 모드에서는 무시됨)
            vllm_base_url: vLLM API base URL (ai_agent 모드에서는 무시됨)
            agent_url: AI Agent 엔드포인트 URL
            detection_types: 탐지 대상 목록
            prompt_type: vLLM 프롬프트 타입 (기본값: "element_detection_qwen")
        
        Returns:
            {
                'success': bool,
                'detection_results': dict,
                'api_type': str,
                'fallback_chain': list (fallback 모드일 때만),
                'error': str
            }
        """
        fallback_chain = []
        
        try:
            logger.info(f"[ElementDetection] 요소 탐지 시작: api_type={api_type}, text_len={len(text)}")
            
            # API 타입 정규화 (레거시 지원)
            api_type_normalized = self._normalize_api_type(api_type)
            
            # Fallback 흐름
            if api_type_normalized == "fallback":
                logger.info("[ElementDetection] Fallback 모드: AI Agent → 로컬 vLLM")
                
                # 1️⃣ AI Agent 시도
                fallback_chain.append("agent_api")
                result = await self._call_agent_api(text, agent_url)
                if result:
                    logger.info("[ElementDetection] ✅ AI Agent 성공")
                    return {
                        'success': True,
                        'detection_results': result,
                        'api_type': 'ai_agent',
                        'fallback_chain': fallback_chain
                    }
                
                logger.warning("[ElementDetection] AI Agent 실패, 로컬 vLLM으로 전환")
                
                # 2️⃣ 로컬 vLLM 호출
                fallback_chain.append("vllm_service")
                result = await self._call_vllm_service(
                    text, vllm_model_name, vllm_base_url, detection_types, prompt_type
                )
                if result:
                    logger.info("[ElementDetection] ✅ 로컬 vLLM 성공")
                    return {
                        'success': True,
                        'detection_results': result,
                        'api_type': 'vllm',
                        'fallback_chain': fallback_chain
                    }
                
                logger.warning("[ElementDetection] 로컬 vLLM 실패, Dummy 결과 반환")
                # 3️⃣ 모두 실패 시 Dummy 결과
                return {
                    'success': True,
                    'detection_results': self._get_dummy_result(),
                    'api_type': 'dummy',
                    'fallback_chain': fallback_chain,
                    'error': 'All detection methods failed, returning dummy result'
                }
            
            # AI Agent 단독 모드
            elif api_type_normalized == "ai_agent":
                logger.info("[ElementDetection] AI Agent 모드")
                result = await self._call_agent_api(text, agent_url)
                
                if result:
                    return {
                        'success': True,
                        'detection_results': result,
                        'api_type': 'ai_agent'
                    }
                else:
                    return {
                        'success': False,
                        'detection_results': None,
                        'api_type': 'ai_agent',
                        'error': 'AI Agent API call failed'
                    }
            
            elif api_type_normalized == "vllm":
                logger.info("[ElementDetection] 로컬 vLLM 모드")
                result = await self._call_vllm_service(
                    text, vllm_model_name, vllm_base_url, detection_types, prompt_type
                )
                
                if result:
                    return {
                        'success': True,
                        'detection_results': result,
                        'api_type': 'vllm'
                    }
                else:
                    return {
                        'success': False,
                        'detection_results': None,
                        'api_type': 'vllm',
                        'error': 'Local vLLM call failed'
                    }
            
            else:
                raise ValueError(f"지원하지 않는 api_type: {api_type_normalized}")
        
        except Exception as e:
            logger.error(f"[ElementDetection] 요소 탐지 오류: {type(e).__name__}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'detection_results': None,
                'api_type': api_type_normalized,
                'fallback_chain': fallback_chain,
                'error': f"{type(e).__name__}: {str(e)}"
            }
    
    async def _call_agent_api(self, text: str, agent_url: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        AI Agent API 호출
        
        Returns:
            성공 시 dict, 실패 시 None
        """
        if not agent_url:
            logger.warning("[ElementDetection] AI Agent URL 미설정")
            return None
        
        try:
            logger.info(f"[ElementDetection] AI Agent 호출: {agent_url}")
            
            payload = {
                "chat_thread_id": "",
                "parameters": {
                    "user_query": text
                }
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    agent_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
            
            if response.status_code != 200:
                logger.warning(f"[ElementDetection] 외부 API 실패 (status={response.status_code})")
                return None
            
            result = response.json()
            logger.info(f"[ElementDetection] ✅ 외부 API 응답 수신")
            
            # 응답 파싱 및 정규화
            detection_data = self._parse_agent_api_response(result)
            
            return {
                "detected_yn": detection_data.get("detected_yn", "N"),
                "detected_sentences": detection_data.get("detected_sentences", []),
                "detected_reasons": detection_data.get("detected_reasons", []),
                "detected_keywords": detection_data.get("detected_keywords", []),
                "category": detection_data.get("category", [])
            }
        
        except Exception as e:
            logger.warning(f"[ElementDetection] AI Agent 호출 중 오류: {type(e).__name__}: {str(e)}")
            return None
    
    async def _call_vllm_service(
        self,
        text: str,
        vllm_model_name: Optional[str],
        vllm_base_url: Optional[str],
        detection_types: Optional[List[str]],
        prompt_type: str = "element_detection_qwen"
    ) -> Optional[Dict[str, Any]]:
        """
        로컬 vLLM 서비스 호출
        
        Args:
            text: 처리할 텍스트
            vllm_model_name: vLLM 모델명
            vllm_base_url: vLLM API base URL
            detection_types: 탐지 대상 목록
            prompt_type: 프롬프트 타입 (기본값: "element_detection_qwen")
        
        Returns:
            성공 시 dict, 실패 시 None
        """
        try:
            config = FormDataConfig(form_data={})
            
            # 기본값 설정 (둘 다 필수)
            vllm_model_name = vllm_model_name or os.getenv("VLLM_MODEL_NAME", "qwen30_thinking_2507")
            vllm_base_url = vllm_base_url or config.get_vllm_api_base('element_detection')
            
            # vLLM이 미설정이면 실패 반환
            if not vllm_model_name or not vllm_base_url:
                logger.warning(f"[ElementDetection] vLLM 미설정: model={vllm_model_name}, url={vllm_base_url}")
                return None
            
            logger.info(f"[ElementDetection] 로컬 vLLM 호출: model={vllm_model_name}, url={vllm_base_url}")
            
            # LLM 클라이언트 초기화
            await self.initialize(vllm_model_name, vllm_base_url)
            
            # 프롬프트 파일 로드
            try:
                from pathlib import Path
                prompt_file_path = Path(__file__).parent / "prompts" / f"{prompt_type}.prompt"
                with open(prompt_file_path, 'r', encoding='utf-8') as f:
                    prompt_template = f.read()
                
                # {usertxt} 플레이스홀더를 실제 텍스트로 교체
                prompt = prompt_template.replace("{usertxt}", text)
                logger.info(f"[ElementDetection] 프롬프트 파일 로드 완료: {prompt_type}")
            except Exception as file_err:
                logger.warning(f"[ElementDetection] 프롬프트 파일 로드 실패: {str(file_err)}, 기본 프롬프트 사용")
                # Fallback: 기본 프롬프트 사용
                prompt = self._build_element_detection_prompt(text, detection_types)
            
            # LLM API 호출
            response = await self.llm_client.call(
                prompt=prompt,
                temperature=0.3,
                max_tokens=8192
            )
            
            logger.debug(f"[ElementDetection] vLLM 응답 수신: {response[:100]}...")
            
            # 응답 파싱
            result = self._parse_llm_response(response)
            
            logger.info(f"[ElementDetection] ✅ vLLM 탐지 완료: detected_yn={result.get('detected_yn')}")
            
            return result
        
        except Exception as e:
            logger.warning(f"[ElementDetection] vLLM 서비스 호출 중 오류: {type(e).__name__}: {str(e)}")
            return None
    
    @staticmethod
    def _normalize_api_type(api_type: str) -> str:
        """API 타입 정규화"""
        api_type_map = {
            'ai_agent': 'ai_agent',
            'vllm': 'vllm',
            'fallback': 'fallback'
        }
        normalized = api_type_map.get(api_type.lower())
        if normalized is None:
            raise ValueError(f"지원하지 않는 api_type: {api_type}. 지원 값: ai_agent, vllm, fallback")
        return normalized
    
    @staticmethod
    def _build_element_detection_prompt(text: str, detection_types: Optional[List[str]]) -> str:
        """요소 탐지 기본 프롬프트 생성 (Fallback용)"""
        types_str = ", ".join(detection_types) if detection_types else "사전판매, 부당권유 등"
        
        return f"""다음 고객 상담 통화 전사문을 분석하여 규제 대상 요소를 탐지하세요.

탐지 대상: {types_str}

전사문:
{text}

JSON 형식으로 다음과 같이 반환하세요:
{{
    "detected_yn": "Y" 또는 "N",
    "detected_sentences": ["탐지된 문장1", "탐지된 문장2", ...],
    "detected_reasons": ["이유1", "이유2", ...],
    "detected_keywords": ["키워드1", "키워드2", ...],
    "category": ["사전판매", "부당권유", ...]
}}
"""
    
    @staticmethod
    def _parse_llm_response(response: str) -> Dict[str, Any]:
        """LLM 응답 파싱"""
        try:
            result = json.loads(response)
            
            detected_yn = str(result.get("detected_yn", "N")).upper()
            if isinstance(detected_yn, list):
                detected_yn = str(detected_yn[0]).upper() if detected_yn else "N"
            
            return {
                "detected_yn": detected_yn,
                "detected_sentences": result.get("detected_sentences", []),
                "detected_reasons": result.get("detected_reasons", []),
                "detected_keywords": result.get("detected_keywords", []),
                "category": result.get("category", [])
            }
        except json.JSONDecodeError:
            logger.warning(f"LLM 응답 파싱 실패: {response[:200]}")
            return {
                "detected_yn": "N",
                "detected_sentences": [],
                "detected_reasons": [],
                "detected_keywords": [],
                "category": []
            }
    
    @staticmethod
    def _parse_agent_api_response(result: dict) -> Dict[str, Any]:
        """AI Agent API 응답 파싱"""
        try:
            # 다양한 응답 형식 대응
            if "detected_yn" in result:
                detection_data = result
            elif "answer" in result:
                answer_field = result.get("answer", {})
                if isinstance(answer_field, dict):
                    inner_answer = answer_field.get("answer")
                    if isinstance(inner_answer, str):
                        detection_data = json.loads(inner_answer)
                    else:
                        detection_data = inner_answer or result
                else:
                    detection_data = result
            elif "message" in result:
                message_str = result.get("message", "{}")
                if isinstance(message_str, str):
                    detection_data = json.loads(message_str)
                else:
                    detection_data = result
            else:
                detection_data = result
            
            detected_yn = str(detection_data.get("detected_yn", "N")).upper()
            if isinstance(detected_yn, list):
                detected_yn = str(detected_yn[0]).upper() if detected_yn else "N"
            
            return {
                "detected_yn": detected_yn,
                "detected_sentences": detection_data.get("detected_sentences", []),
                "detected_reasons": detection_data.get("detected_reasons", []),
                "detected_keywords": detection_data.get("detected_keywords", []),
                "category": detection_data.get("category", [])
            }
        except (json.JSONDecodeError, KeyError):
            logger.warning(f"외부 API 응답 파싱 실패: {str(result)[:200]}")
            return {
                "detected_yn": "N",
                "detected_sentences": [],
                "detected_reasons": [],
                "detected_keywords": [],
                "category": []
            }
    
    @staticmethod
    def _get_dummy_result() -> Dict[str, Any]:
        """Dummy 결과 반환"""
        return {
            "detected_yn": "N",
            "detected_sentences": [],
            "detected_reasons": [],
            "detected_keywords": [],
            "category": []
        }


# ============================================================================
# Singleton 패턴: 전역 서비스 인스턴스
# ============================================================================

_element_detection_service: Optional[ElementDetectionService] = None


def get_element_detection_service() -> ElementDetectionService:
    """
    ElementDetectionService의 싱글톤 인스턴스 반환
    
    Returns:
        ElementDetectionService 인스턴스
    """
    global _element_detection_service
    
    if _element_detection_service is None:
        logger.info("ElementDetectionService 싱글톤 생성")
        _element_detection_service = ElementDetectionService()
    
    return _element_detection_service


async def _async_get_element_detection_service() -> ElementDetectionService:
    """
    FastAPI Depends()와 호환되는 async 래퍼
    ElementDetectionService의 싱글톤 인스턴스 반환
    
    Returns:
        ElementDetectionService 인스턴스
    """
    return get_element_detection_service()
