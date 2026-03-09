"""
FormData 요청 파싱 및 설정 추상화 계층

설정 우선순위 (높음 → 낮음):
1. HTTP FormData 파라미터
2. 작업별 환경변수 (PRIVACY_VLLM_MODEL_NAME 등)
3. 공용 환경변수 (VLLM_MODEL_NAME 등)
4. 코드 기본값 (constants.py)

이 모듈은 FormData 요청에서 설정을 추출하고, 타입 변환 및 검증을 수행합니다.
"""

import os
import logging
from typing import Optional, Any
from starlette.datastructures import FormData

from api_server.constants import VLLM_MODEL_NAME, EXTERNAL_API_URL

logger = logging.getLogger(__name__)


class FormDataConfig:
    """
    HTTP FormData 요청에서 설정을 추출하는 클래스
    
    모든 FormData 파라미터는 문자열 타입이므로, 각 메서드에서 필요한 타입으로 변환합니다.
    우선순위에 따라 다단계 fallback을 제공합니다.
    """
    
    def __init__(self, form_data: FormData, debug: bool = False):
        """
        FormDataConfig 초기화
        
        Args:
            form_data: Starlette FormData 객체
            debug: 디버그 로깅 활성화 여부
        """
        self.form_data = form_data
        self.debug = debug
    
    def get_str(self, key: str, default: str = "") -> str:
        """
        FormData에서 문자열 값 추출
        
        우선순위:
        1. FormData 파라미터
        2. 코드 기본값
        
        Args:
            key: 파라미터 키
            default: 기본값 (FormData와 환경변수에서 찾지 못할 때)
        
        Returns:
            추출된 문자열값
        """
        value = self.form_data.get(key, "").strip()
        result = value if value else default
        
        if self.debug:
            logger.info(f"[FormDataConfig] get_str('{key}'): {repr(value)} -> {repr(result)}")
        
        return result
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        FormData에서 불린 값 추출 및 변환
        
        우선순위:
        1. FormData 파라미터 ("true", "1", "yes", "on" -> True)
        2. 코드 기본값
        
        Args:
            key: 파라미터 키
            default: 기본값 (FormData에서 찾지 못할 때)
        
        Returns:
            변환된 불린값
        """
        value = self.form_data.get(key, "").strip()
        
        if value:
            result = value.lower() in ['true', '1', 'yes', 'on']
        else:
            result = default
        
        if self.debug:
            logger.info(f"[FormDataConfig] get_bool('{key}'): {repr(value)} -> {result}")
        
        return result
    
    def get_int(self, key: str, default: int = 0) -> int:
        """
        FormData에서 정수 값 추출 및 변환
        
        우선순위:
        1. FormData 파라미터 (문자열 → 정수 변환)
        2. 코드 기본값
        
        Args:
            key: 파라미터 키
            default: 기본값 (FormData에서 찾지 못하거나 변환 실패할 때)
        
        Returns:
            변환된 정수값
        """
        value = self.form_data.get(key, "").strip()
        
        try:
            result = int(value) if value else default
        except (ValueError, TypeError):
            logger.warning(f"[FormDataConfig] get_int('{key}'): Failed to convert {repr(value)} to int, using default {default}")
            result = default
        
        if self.debug:
            logger.info(f"[FormDataConfig] get_int('{key}'): {repr(value)} -> {result}")
        
        return result
    
    def get_vllm_model_name(self, task: str, default_fallback: Optional[str] = None) -> str:
        """
        vLLM 모델명 추출 (Privacy, Classification, Element Detection 용)
        
        우선순위:
        1. FormData 파라미터 (예: privacy_vllm_model_name)
        2. 작업별 환경변수 (예: PRIVACY_VLLM_MODEL_NAME)
        3. 공용 환경변수 (VLLM_MODEL_NAME)
        4. 코드 기본값 (constants.VLLM_MODEL_NAME)
        
        모델명 정규화: "/model/xxx" -> "xxx" 형식의 경로 제거
        
        Args:
            task: 작업명 (privacy, classification, detection)
            default_fallback: 추가 기본값 (constants.VLLM_MODEL_NAME 이전에 시도)
        
        Returns:
            정규화된 vLLM 모델명 (경로 없는 순수 모델명)
        """
        # 1. FormData 파라미터에서 먼저 확인
        form_key = f"{task}_vllm_model_name"
        form_value = self.form_data.get(form_key, "").strip()
        
        if form_value:
            result = self._normalize_model_name(form_value)
            if self.debug:
                logger.info(f"[FormDataConfig] get_vllm_model_name('{task}'): from FormData[{form_key}] -> {repr(result)}")
            return result
        
        # 2. 작업별 환경변수에서 확인
        env_key = f"{task.upper()}_VLLM_MODEL_NAME"
        env_value = os.getenv(env_key, "").strip()
        
        if env_value:
            result = self._normalize_model_name(env_value)
            if self.debug:
                logger.info(f"[FormDataConfig] get_vllm_model_name('{task}'): from env[{env_key}] -> {repr(result)}")
            return result
        
        # 3. 공용 환경변수에서 확인
        common_env_value = os.getenv("VLLM_MODEL_NAME", "").strip()
        
        if common_env_value:
            result = self._normalize_model_name(common_env_value)
            if self.debug:
                logger.info(f"[FormDataConfig] get_vllm_model_name('{task}'): from env[VLLM_MODEL_NAME] -> {repr(result)}")
            return result
        
        # 4. 추가 기본값 시도
        if default_fallback:
            result = self._normalize_model_name(default_fallback)
            if self.debug:
                logger.info(f"[FormDataConfig] get_vllm_model_name('{task}'): from default_fallback -> {repr(result)}")
            return result
        
        # 5. 코드 기본값
        result = self._normalize_model_name(VLLM_MODEL_NAME)
        if self.debug:
            logger.info(f"[FormDataConfig] get_vllm_model_name('{task}'): from constants.VLLM_MODEL_NAME -> {repr(result)}")
        return result
    
    def get_agent_url(self) -> str:
        """
        External API URL 추출 (Element Detection 용)
        
        우선순위:
        1. FormData 파라미터 (agent_url)
        2. 환경변수 (EXTERNAL_API_URL - 새 표준)
        3. 레거시 환경변수 (AGENT_URL - 이전 버전)
        4. 코드 기본값 (constants.EXTERNAL_API_URL)
        
        Returns:
            External API URL (없을 경우 빈 문자열)
        """
        # 1. FormData 파라미터에서 먼저 확인
        form_value = self.form_data.get("agent_url", "").strip()
        
        if form_value:
            if self.debug:
                logger.info(f"[FormDataConfig] get_agent_url(): from FormData[agent_url] -> {repr(form_value)}")
            return form_value
        
        # 2. 새 표준 환경변수 확인
        external_url = os.getenv("EXTERNAL_API_URL", "").strip()
        
        if external_url:
            if self.debug:
                logger.info(f"[FormDataConfig] get_agent_url(): from env[EXTERNAL_API_URL] -> {repr(external_url)}")
            return external_url
        
        # 3. 레거시 환경변수 확인 (이전 버전 호환성)
        legacy_url = os.getenv("AGENT_URL", "").strip()
        
        if legacy_url:
            logger.warning("[FormDataConfig] Using legacy AGENT_URL environment variable. Please migrate to EXTERNAL_API_URL.")
            if self.debug:
                logger.info(f"[FormDataConfig] get_agent_url(): from env[AGENT_URL] (legacy) -> {repr(legacy_url)}")
            return legacy_url
        
        # 4. 코드 기본값
        default_url = EXTERNAL_API_URL or ""
        if self.debug:
            logger.info(f"[FormDataConfig] get_agent_url(): from constants.EXTERNAL_API_URL -> {repr(default_url)}")
        return default_url
    
    @staticmethod
    def _normalize_model_name(model_name: str) -> str:
        """
        모델명 정규화: 경로 제거
        
        예:
        - "/model/qwen30_thinking_2507" -> "qwen30_thinking_2507"
        - "qwen30_thinking_2507" -> "qwen30_thinking_2507"
        
        Args:
            model_name: 원본 모델명 (경로 포함 가능)
        
        Returns:
            정규화된 모델명 (경로 없음)
        """
        if not model_name:
            return ""
        
        if model_name.startswith('/model/'):
            return model_name.replace('/model/', '', 1)
        
        return model_name
