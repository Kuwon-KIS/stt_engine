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
        api_type: str = "fallback",
        llm_type: str = "vllm",
        vllm_model_name: Optional[str] = None,
        vllm_base_url: Optional[str] = None,
        external_api_url: Optional[str] = None,
        detection_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        요소 탐지 (Fallback 메커니즘 포함)
        
        Args:
            text: 처리할 텍스트
            api_type: "fallback"=자동선택, "external"=외부만, "vllm"=로컬만
            llm_type: LLM 타입 ('vllm')
            vllm_model_name: vLLM 모델명
            vllm_base_url: vLLM API base URL
            external_api_url: 외부 API 주소
            detection_types: 탐지 대상 목록
        
        Returns:
            {
                'success': bool,
                'detection_results': dict,
                'api_type': str,
                'fallback_chain': list,
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
                logger.info("[ElementDetection] Fallback 모드: 외부 API → 로컬 vLLM")
                
                # 1️⃣ 외부 AI Agent 시도
                fallback_chain.append("external_api")
                result = await self._call_external_api(text, external_api_url)
                if result:
                    logger.info("[ElementDetection] ✅ 외부 API 성공")
                    return {
                        'success': True,
                        'detection_results': result,
                        'api_type': 'external',
                        'fallback_chain': fallback_chain
                    }
                
                logger.warning("[ElementDetection] 외부 API 실패, 로컬 vLLM으로 전환")
                
                # 2️⃣ 로컬 vLLM 호출
                fallback_chain.append("local_vllm")
                result = await self._call_local_llm(
                    text, vllm_model_name, vllm_base_url, detection_types
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
            
            # Single API 모드
            elif api_type_normalized == "external":
                logger.info("[ElementDetection] 외부 API 모드")
                result = await self._call_external_api(text, external_api_url)
                
                if result:
                    return {
                        'success': True,
                        'detection_results': result,
                        'api_type': 'external'
                    }
                else:
                    return {
                        'success': False,
                        'detection_results': None,
                        'api_type': 'external',
                        'error': 'External API call failed'
                    }
            
            elif api_type_normalized == "vllm":
                logger.info("[ElementDetection] 로컬 vLLM 모드")
                result = await self._call_local_llm(
                    text, vllm_model_name, vllm_base_url, detection_types
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
    
    async def _call_external_api(self, text: str, external_api_url: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        외부 AI Agent API 호출
        
        Returns:
            성공 시 dict, 실패 시 None
        """
        if not external_api_url:
            logger.warning("[ElementDetection] 외부 API URL 미설정")
            return None
        
        try:
            logger.info(f"[ElementDetection] 외부 AI Agent 호출: {external_api_url}")
            
            payload = {
                "chat_thread_id": "",
                "parameters": {
                    "user_query": text
                }
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    external_api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
            
            if response.status_code != 200:
                logger.warning(f"[ElementDetection] 외부 API 실패 (status={response.status_code})")
                return None
            
            result = response.json()
            logger.info(f"[ElementDetection] ✅ 외부 API 응답 수신")
            
            # 응답 파싱 및 정규화
            detection_data = self._parse_external_api_response(result)
            
            return {
                "detected_yn": detection_data.get("detected_yn", "N"),
                "detected_sentences": detection_data.get("detected_sentences", []),
                "detected_reasons": detection_data.get("detected_reasons", []),
                "detected_keywords": detection_data.get("detected_keywords", []),
                "category": detection_data.get("category", [])
            }
        
        except Exception as e:
            logger.warning(f"[ElementDetection] 외부 API 호출 중 오류: {type(e).__name__}: {str(e)}")
            return None
    
    async def _call_local_llm(
        self,
        text: str,
        vllm_model_name: Optional[str],
        vllm_base_url: Optional[str],
        detection_types: Optional[List[str]]
    ) -> Optional[Dict[str, Any]]:
        """
        로컬 vLLM 호출
        
        Returns:
            성공 시 dict, 실패 시 None
        """
        try:
            config = FormDataConfig(form_data={})
            
            # 기본값 설정
            vllm_model_name = vllm_model_name or os.getenv("VLLM_MODEL_NAME", "qwen30_thinking_2507")
            vllm_base_url = vllm_base_url or config.get_vllm_api_base('element_detection')
            
            logger.info(f"[ElementDetection] 로컬 vLLM 호출: model={vllm_model_name}, url={vllm_base_url}")
            
            # LLM 클라이언트 초기화
            await self.initialize(vllm_model_name, vllm_base_url)
            
            # 요소 탐지 프롬프트 생성
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
            logger.warning(f"[ElementDetection] 로컬 vLLM 호출 중 오류: {type(e).__name__}: {str(e)}")
            return None
    
    @staticmethod
    def _normalize_api_type(api_type: str) -> str:
        """API 타입 정규화 (레거시 지원)"""
        api_type_map = {
            'external': 'external',
            'ai_agent': 'external',
            'local': 'vllm',
            'vllm': 'vllm',
            'fallback': 'fallback'
        }
        normalized = api_type_map.get(api_type.lower(), 'fallback')
        if normalized != api_type:
            logger.debug(f"API 타입 정규화: {api_type} → {normalized}")
        return normalized
    
    @staticmethod
    def _build_element_detection_prompt(text: str, detection_types: Optional[List[str]]) -> str:
        """요소 탐지 프롬프트 생성"""
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
    def _parse_external_api_response(result: dict) -> Dict[str, Any]:
        """외부 API 응답 파싱"""
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
