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
        Element Detection Agent URL 추출 (Element Detection ai_agent 모드 전용)
        
        우선순위:
        1. FormData 파라미터 (agent_url)
        2. 환경변수 (ELEMENT_DETECTION_AGENT_URL)
        3. 코드 기본값 (constants.EXTERNAL_API_URL)
        
        Returns:
            Element Detection Agent URL (없을 경우 빈 문자열)
        """
        # 1. FormData 파라미터에서 먼저 확인
        form_value = self.form_data.get("agent_url", "").strip()
        
        if form_value:
            if self.debug:
                logger.info(f"[FormDataConfig] get_agent_url(): from FormData[agent_url] -> {repr(form_value)}")
            return form_value
        
        # 2. 환경변수 확인 (ELEMENT_DETECTION_AGENT_URL)
        env_url = os.getenv("ELEMENT_DETECTION_AGENT_URL", "").strip()
        
        if env_url:
            if self.debug:
                logger.info(f"[FormDataConfig] get_agent_url(): from env[ELEMENT_DETECTION_AGENT_URL] -> {repr(env_url)}")
            return env_url
        
        # 3. 코드 기본값
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


class STTConfig(FormDataConfig):
    """
    STT (Speech-to-Text) 엔진 설정 추상화
    
    FormDataConfig를 기반으로 STT 엔진 설정에 특화된 메서드를 제공합니다.
    
    **⚠️ 중요: PRESET과 실제 성능 차이**
    
    PRESET별 실제 동작 (stt_engine.py의 reload_backend에서 결정):
    
    | PRESET | 백엔드 | 연산타입 | 성능 (30초 오디오 기준) | 특징 |
    |--------|--------|---------|----------------------|------|
    | speed | faster-whisper | int8 | ~8초 | ⚡ 가장 빠름, 정확도 낮음 |
    | balanced | faster-whisper | float16 | ~15초 | 🟡 중간 속도, 중간 정확도 |
    | accuracy | transformers | float32 | ~25초+ | 🐌 매우 느림, 정확도 최고 ⚠️ |
    | custom | 사용자 지정 | 사용자 지정 | - | 명시적으로 device/compute_type/backend 지정 |
    
    **성능 차이 분석:**
    - accuracy는 speed에 비해 **3배 이상 느림** (단순 2-3배가 아님!)
    - 주요 원인: transformers 전체 모델 vs faster-whisper 경량 모델
    - 세그멘트 설정 차이는 5% 미만의 성능 영향만 미침
    
    **설정 우선순위 (중요):**
    
    STT_PRESET이 최우선 우선순위입니다:
    1. FormData stt_preset (최우선)
    2. 환경변수 STT_PRESET
    3. 기본값 "accuracy"
    
    preset == "custom"일 때만 다음 설정들이 적용됩니다:
    - stt_device (FormData) > STT_DEVICE (env) > 기본값
    - stt_compute_type (FormData) > STT_COMPUTE_TYPE (env) > 기본값
    - stt_backend (FormData) > STT_BACKEND (env) > 기본값
    
    다른 preset (speed/balanced/accuracy)은 고정된 설정으로 작동합니다.
    
    **운영 권장사항:**
    - 실시간 처리 필요 → STT_PRESET=speed      (8초/30초 오디오)
    - 균형 필요 → STT_PRESET=balanced         (15초/30초 오디오)
    - 정확도 우선 → STT_PRESET=accuracy       (25초+/30초 오디오)
    """
    
    # STT 디바이스 지원 목록
    SUPPORTED_DEVICES = ['cpu', 'cuda', 'mps', 'auto']
    SUPPORTED_BACKENDS = ['faster_whisper', 'transformers', 'openai']
    SUPPORTED_COMPUTE_TYPES = ['float32', 'float16', 'bfloat16', 'int8']
    SUPPORTED_PRESETS = ['speed', 'balanced', 'accuracy', 'custom']
    
    def get_preset(self, default: str = "accuracy") -> str:
        """
        STT 프리셋 선택 (speed, balanced, accuracy, custom)
        
        *** 이것이 STT 설정의 가장 높은 우선순위입니다 ***
        
        우선순위:
        1. FormData 파라미터 (stt_preset) - 가장 높음
        2. 환경변수 (STT_PRESET)
        3. 기본값 "accuracy"
        
        각 PRESET의 실제 동작 (stt_engine.py의 reload_backend에서 결정):
        - "speed"     : faster-whisper + int8    (⚡ 가장 빠름, ~8초/30초 오디오)
        - "balanced"  : faster-whisper + float16 (🟡 중간 속도, ~15초/30초 오디오)
        - "accuracy"  : transformers + float32   (🐌 최고정확도, ~25초+/30초 오디오) ⚠️ 매우 느림!
        - "custom"    : device, compute_type, backend 개별 지정 (reload_backend()에서 직접 설정)
        
        Args:
            default: 기본값 (일반적으로 "accuracy")
        
        Returns:
            검증된 프리셋명
        
        Note:
            - "speed", "balanced", "accuracy": 고정된 백엔드 + 연산타입 조합 사용
            - "custom": device, compute_type, backend 개별 설정 사용
            - ⚠️ 성능 차이의 80%는 백엔드 선택(transformers vs faster-whisper)에서 발생!
            - 실제 성능: speed는 accuracy보다 3배 이상 빠름
        """
        preset = self.get_str('stt_preset') or os.getenv('STT_PRESET', default)
        preset = preset.lower()
        
        if preset not in self.SUPPORTED_PRESETS:
            logger.warning(f"[STTConfig] Unsupported preset: {preset}. Using default: {default}")
            preset = default
        
        if self.debug:
            logger.info(f"[STTConfig] get_preset(): {repr(preset)}")
        
        return preset
        우선순위:
        1. FormData 파라미터 (stt_device)
        2. 환경변수 (STT_DEVICE)
        3. 기본값
        
        Args:
            default: 기본값 (일반적으로 "auto" 또는 "cpu")
        
        Returns:
            검증된 디바이스명 (cpu/cuda/mps/auto)
        
        Note:
            preset이 "accuracy", "balanced", "fast" 중 하나면 이 값은 무시됩니다.
        """
        device = self.get_str('stt_device') or os.getenv('STT_DEVICE', default)
        device = device.lower()
        
        if device not in self.SUPPORTED_DEVICES:
            logger.warning(f"[STTConfig] Unsupported device: {device}. Using default: {default}")
            device = default
        
        if self.debug:
            logger.info(f"[STTConfig] get_device(): {repr(device)}")
        
        return device
    
    def get_compute_type(self, device: Optional[str] = None, default: str = "float32") -> str:
        """
        STT 연산 타입 추출 및 검증
        
        *** 이 메서드는 preset == "custom"일 때만 의미가 있습니다 ***
        
        우선순위:
        1. FormData 파라미터 (stt_compute_type)
        2. 환경변수 (STT_COMPUTE_TYPE)
        3. 자동 선택 (device에 따라: cuda -> float16, 기타 -> float32)
        
        Args:
            device: 디바이스 (자동 선택 시 고려)
            default: 기본값
        
        Returns:
            검증된 연산 타입 (float32/float16/bfloat16/int8)
        
        Note:
            preset이 "accuracy", "balanced", "fast" 중 하나면 이 값은 무시됩니다.
        """
        compute_type = self.get_str('stt_compute_type') or os.getenv('STT_COMPUTE_TYPE', '')
        
        if not compute_type:
            # 디바이스에 따라 자동 선택
            if device is None:
                device = self.get_device()
            
            if device == 'cuda':
                compute_type = "float16"  # CUDA는 float16 권장
            else:
                compute_type = "float32"  # CPU/MPS는 float32 권장
        
        compute_type = compute_type.lower()
        
        if compute_type not in self.SUPPORTED_COMPUTE_TYPES:
            logger.warning(f"[STTConfig] Unsupported compute_type: {compute_type}. Using default: {default}")
            compute_type = default
        
        if self.debug:
            logger.info(f"[STTConfig] get_compute_type(): {repr(compute_type)}")
        
        return compute_type
    
    def get_backend(self, default: str = "faster_whisper") -> str:
        """
        STT 백엔드 선택 (faster_whisper, transformers, openai)
        
        *** 이 메서드는 preset == "custom"일 때만 의미가 있습니다 ***
        
        우선순위:
        1. FormData 파라미터 (stt_backend)
        2. 환경변수 (STT_BACKEND)
        3. 기본값
        
        Args:
            default: 기본값 (일반적으로 "faster_whisper")
        
        Returns:
            검증된 백엔드명
        
        Note:
            preset이 "accuracy", "balanced", "fast" 중 하나면 이 값은 무시됩니다.
        """
        backend = self.get_str('stt_backend') or os.getenv('STT_BACKEND', default)
        backend = backend.lower().replace('-', '_')  # faster-whisper -> faster_whisper
        
        if backend not in self.SUPPORTED_BACKENDS:
            logger.warning(f"[STTConfig] Unsupported backend: {backend}. Using default: {default}")
            backend = default
        
        if self.debug:
            logger.info(f"[STTConfig] get_backend(): {repr(backend)}")
        
        return backend


class LLMConfig(FormDataConfig):
    """
    LLM (Large Language Model) 설정 추상화
    
    FormDataConfig를 기반으로 LLM 설정에 특화된 메서드를 제공합니다.
    현재는 vLLM 지원, 향후 Ollama/Llama.cpp 등으로 확장 가능합니다.
    
    설정 우선순위:
    1. HTTP FormData 파라미터
    2. 작업별 환경변수 (PRIVACY_VLLM_MODEL_NAME 등)
    3. 공용 환경변수 (VLLM_MODEL_NAME)
    4. 코드 기본값
    """
    
    SUPPORTED_LLM_TYPES = ['vllm', 'ollama', 'openai']
    
    def get_llm_type(self, task: str, default: str = "vllm") -> str:
        """
        LLM 타입 추출 및 검증 (vllm, ollama, openai 등)
        
        우선순위:
        1. FormData 파라미터 (예: privacy_llm_type)
        2. 환경변수 (예: PRIVACY_LLM_TYPE)
        3. 기본값
        
        Args:
            task: 작업명 (privacy, classification, detection)
            default: 기본값 (일반적으로 "vllm")
        
        Returns:
            검증된 LLM 타입
        """
        # 1. FormData에서 확인
        form_key = f"{task}_llm_type"
        form_value = self.get_str(form_key)
        
        if form_value:
            llm_type = form_value.lower()
            if llm_type in self.SUPPORTED_LLM_TYPES:
                if self.debug:
                    logger.info(f"[LLMConfig] get_llm_type('{task}'): from FormData -> {repr(llm_type)}")
                return llm_type
        
        # 2. 환경변수에서 확인
        env_key = f"{task.upper()}_LLM_TYPE"
        env_value = os.getenv(env_key, '').lower()
        
        if env_value and env_value in self.SUPPORTED_LLM_TYPES:
            if self.debug:
                logger.info(f"[LLMConfig] get_llm_type('{task}'): from env[{env_key}] -> {repr(env_value)}")
            return env_value
        
        # 3. 기본값
        if self.debug:
            logger.info(f"[LLMConfig] get_llm_type('{task}'): using default -> {repr(default)}")
        return default
    
    def get_vllm_endpoint(self, task: str, default: str = "http://localhost:8000/v1") -> str:
        """
        vLLM 서버 엔드포인트 URL 추출
        
        우선순위:
        1. FormData 파라미터 (예: privacy_vllm_endpoint)
        2. 작업별 환경변수 (예: PRIVACY_VLLM_ENDPOINT)
        3. 공용 환경변수 (VLLM_ENDPOINT)
        4. 기본값
        
        Args:
            task: 작업명 (privacy, classification, detection)
            default: 기본값
        
        Returns:
            vLLM 엔드포인트 URL
        """
        # 1. FormData에서 확인
        form_key = f"{task}_vllm_endpoint"
        form_value = self.get_str(form_key)
        
        if form_value:
            if self.debug:
                logger.info(f"[LLMConfig] get_vllm_endpoint('{task}'): from FormData -> {repr(form_value)}")
            return form_value
        
        # 2. 작업별 환경변수에서 확인
        env_key = f"{task.upper()}_VLLM_ENDPOINT"
        env_value = os.getenv(env_key, '')
        
        if env_value:
            if self.debug:
                logger.info(f"[LLMConfig] get_vllm_endpoint('{task}'): from env[{env_key}] -> {repr(env_value)}")
            return env_value
        
        # 3. 공용 환경변수에서 확인
        common_env_value = os.getenv('VLLM_ENDPOINT', '')
        
        if common_env_value:
            if self.debug:
                logger.info(f"[LLMConfig] get_vllm_endpoint('{task}'): from env[VLLM_ENDPOINT] -> {repr(common_env_value)}")
            return common_env_value
        
        # 4. 기본값
        if self.debug:
            logger.info(f"[LLMConfig] get_vllm_endpoint('{task}'): using default -> {repr(default)}")
        return default


class ElementDetectionConfig(FormDataConfig):
    """
    요소 탐지 (Element Detection) 설정 추상화
    
    FormDataConfig를 기반으로 요소 탐지 설정에 특화된 메서드를 제공합니다.
    
    중요: api_type에 따른 필수 파라미터
    - ai_agent 모드: element_detection_agent_url 필수 (ELEMENT_DETECTION_AGENT_URL 환경변수)
    - vllm 모드: detection_vllm_model_name, detection_vllm_endpoint 필수
    
    설정 우선순위:
    1. HTTP FormData 파라미터
    2. 환경변수 (ELEMENT_DETECTION_AGENT_URL, DETECTION_VLLM_MODEL_NAME 등)
    3. 코드 기본값
    """
    
    # 지원되는 탐지 타입
    SUPPORTED_DETECTION_TYPES = [
        'aggressive_sales',      # 부당권유
        'incomplete_sales',      # 불완전판매
        'unethical_practice'     # 비윤리적 관행
    ]
    
    # 지원되는 탐지 API 타입
    SUPPORTED_API_TYPES = ['vllm', 'ai_agent']
    
    def get_detection_api_type(self, default: str = "ai_agent") -> str:
        """
        요소 탐지 API 타입 추출 및 검증 (vllm, ai_agent)
        
        우선순위:
        1. FormData 파라미터 (detection_api_type)
        2. 환경변수 (ELEMENT_DETECTION_API_TYPE)
        3. 기본값
        
        Args:
            default: 기본값 (일반적으로 "ai_agent")
        
        Returns:
            검증된 API 타입
        """
        api_type = self.get_str('detection_api_type') or os.getenv('ELEMENT_DETECTION_API_TYPE', default)
        api_type = api_type.lower()
        
        if api_type not in self.SUPPORTED_API_TYPES:
            logger.warning(f"[ElementDetectionConfig] Unsupported API type: {api_type}. Using default: {default}")
            api_type = default
        
        if self.debug:
            logger.info(f"[ElementDetectionConfig] get_detection_api_type(): {repr(api_type)}")
        
        return api_type
    
    def get_agent_url_for_detection(self) -> str:
        """
        Element Detection AI Agent URL 추출 (ai_agent 모드 전용)
        
        우선순위:
        1. FormData 파라미터 (agent_url)
        2. 환경변수 (ELEMENT_DETECTION_AGENT_URL) - 명확한 이름
        3. 빈 문자열
        
        Returns:
            AI Agent URL (없으면 빈 문자열)
        
        Note:
            ai_agent 모드에서 이 값이 비어있으면 요청은 실패합니다.
            환경변수: ELEMENT_DETECTION_AGENT_URL=https://api.kis.com/v1/detect
        """
        return self.get_agent_url()
    
    def get_vllm_model_name_for_detection(self, default_fallback: Optional[str] = None) -> str:
        """
        Element Detection vLLM 모델명 추출 (vllm 모드 전용)
        
        우선순위:
        1. FormData 파라미터 (detection_vllm_model_name)
        2. 작업별 환경변수 (DETECTION_VLLM_MODEL_NAME)
        3. 공용 환경변수 (VLLM_MODEL_NAME)
        4. 기본값
        
        Returns:
            정규화된 vLLM 모델명 (경로 없음)
        
        Note:
            vllm 모드에서 필수 파라미터입니다.
        """
        return self.get_vllm_model_name('detection', default_fallback)
    
    def get_vllm_endpoint_for_detection(self, default: str = "http://localhost:8000/v1") -> str:
        """
        Element Detection vLLM 엔드포인트 URL 추출 (vllm 모드 전용)
        
        우선순위:
        1. FormData 파라미터 (detection_vllm_endpoint)
        2. 작업별 환경변수 (DETECTION_VLLM_ENDPOINT)
        3. 공용 환경변수 (VLLM_ENDPOINT)
        4. 기본값
        
        Args:
            default: 기본값
        
        Returns:
            vLLM 엔드포인트 URL
        
        Note:
            vllm 모드에서 필수 파라미터입니다.
        """
        # 1. FormData에서 확인
        form_key = "detection_vllm_endpoint"
        form_value = self.get_str(form_key)
        
        if form_value:
            if self.debug:
                logger.info(f"[ElementDetectionConfig] get_vllm_endpoint_for_detection(): from FormData -> {repr(form_value)}")
            return form_value
        
        # 2. 작업별 환경변수에서 확인
        env_key = "DETECTION_VLLM_ENDPOINT"
        env_value = os.getenv(env_key, '')
        
        if env_value:
            if self.debug:
                logger.info(f"[ElementDetectionConfig] get_vllm_endpoint_for_detection(): from env[{env_key}] -> {repr(env_value)}")
            return env_value
        
        # 3. 공용 환경변수에서 확인
        common_env_value = os.getenv('VLLM_ENDPOINT', '')
        
        if common_env_value:
            if self.debug:
                logger.info(f"[ElementDetectionConfig] get_vllm_endpoint_for_detection(): from env[VLLM_ENDPOINT] -> {repr(common_env_value)}")
            return common_env_value
        
        # 4. 기본값
        if self.debug:
            logger.info(f"[ElementDetectionConfig] get_vllm_endpoint_for_detection(): using default -> {repr(default)}")
        return default
    
    def validate_for_ai_agent_mode(self) -> tuple[bool, str]:
        """
        ai_agent 모드 필수 파라미터 검증
        
        Returns:
            (유효성, 에러메시지) 튜플
            - 유효: (True, "")
            - 무효: (False, "에러 메시지")
        
        Note:
            detection_api_type="ai_agent"일 때 호출해야 합니다.
        """
        agent_url = self.get_agent_url_for_detection()
        
        if not agent_url:
            return (
                False,
                "Element Detection ai_agent 모드에는 agent_url이 필수입니다. "
                "FormData 파라미터(agent_url) 또는 환경변수(ELEMENT_DETECTION_AGENT_URL)에서 설정하세요."
            )
        
        if self.debug:
            logger.info(f"[ElementDetectionConfig] ai_agent mode validation: PASS (agent_url={repr(agent_url)})")
        
        return (True, "")
    
    def validate_for_vllm_mode(self) -> tuple[bool, str]:
        """
        vllm 모드 필수 파라미터 검증
        
        Returns:
            (유효성, 에러메시지) 튜플
            - 유효: (True, "")
            - 무효: (False, "에러 메시지")
        
        Note:
            detection_api_type="vllm"일 때 호출해야 합니다.
        """
        model_name = self.get_vllm_model_name_for_detection()
        endpoint = self.get_vllm_endpoint_for_detection()
        
        if not model_name:
            return (
                False,
                "Element Detection vllm 모드에는 detection_vllm_model_name이 필수입니다. "
                "FormData 파라미터(detection_vllm_model_name) 또는 "
                "환경변수(DETECTION_VLLM_MODEL_NAME/VLLM_MODEL_NAME)에서 설정하세요."
            )
        
        if not endpoint:
            return (
                False,
                "Element Detection vllm 모드에는 vLLM 엔드포인트가 필수입니다. "
                "FormData 파라미터(detection_vllm_endpoint) 또는 "
                "환경변수(DETECTION_VLLM_ENDPOINT/VLLM_ENDPOINT)에서 설정하세요."
            )
        
        if self.debug:
            logger.info(f"[ElementDetectionConfig] vllm mode validation: PASS (model={repr(model_name)}, endpoint={repr(endpoint)})")
        
        return (True, "")
    
    def get_detection_types(self, default: str = "") -> list:
        """
        활성화된 탐지 타입 목록 추출 및 검증
        
        우선순위:
        1. FormData 파라미터 (detection_types, CSV 형식)
        2. 환경변수 (DETECTION_TYPES, CSV 형식)
        3. 기본값
        
        Args:
            default: 기본값 (CSV 문자열)
        
        Returns:
            검증된 탐지 타입 리스트
        """
        detection_types_str = self.get_str('detection_types') or os.getenv('DETECTION_TYPES', default)
        
        if not detection_types_str:
            if self.debug:
                logger.info(f"[ElementDetectionConfig] get_detection_types(): empty list (no types specified)")
            return []
        
        # CSV 문자열을 리스트로 변환
        types_list = [t.strip().lower() for t in detection_types_str.split(',')]
        
        # 지원되는 타입만 필터링
        validated_types = []
        for dtype in types_list:
            if dtype in self.SUPPORTED_DETECTION_TYPES:
                validated_types.append(dtype)
            else:
                logger.warning(f"[ElementDetectionConfig] Unsupported detection type: {dtype}. Skipping.")
        
        if self.debug:
            logger.info(f"[ElementDetectionConfig] get_detection_types(): {repr(validated_types)}")
        
        return validated_types
