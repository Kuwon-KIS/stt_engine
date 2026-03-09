"""
FormDataConfig 테스트

FormData 요청 파싱 및 설정 추상화 계층의 유닛 테스트
"""

import os
import pytest
from unittest.mock import Mock
from api_server.config import FormDataConfig, STTConfig, LLMConfig, ElementDetectionConfig
from api_server import config as config_module


class TestFormDataConfig:
    """FormDataConfig 클래스 테스트"""
    
    @pytest.fixture
    def mock_form_data(self):
        """FormData 모의 객체 생성"""
        return {}
    
    def create_config(self, form_data_dict):
        """테스트용 FormDataConfig 생성"""
        form_data = Mock()
        form_data.get = lambda key, default="": form_data_dict.get(key, default)
        return FormDataConfig(form_data, debug=False)
    
    # ============================================================================
    # get_str 메서드 테스트
    # ============================================================================
    
    def test_get_str_from_form_data(self):
        """FormData에서 문자열 추출"""
        config = self.create_config({'language': 'ko'})
        assert config.get_str('language') == 'ko'
    
    def test_get_str_with_default(self):
        """기본값 제공"""
        config = self.create_config({})
        assert config.get_str('language', 'en') == 'en'
    
    def test_get_str_empty_string(self):
        """빈 문자열 처리"""
        config = self.create_config({'language': ''})
        assert config.get_str('language', 'en') == 'en'
    
    def test_get_str_whitespace(self):
        """공백 정규화"""
        config = self.create_config({'language': '  ko  '})
        assert config.get_str('language') == 'ko'
    
    # ============================================================================
    # get_bool 메서드 테스트
    # ============================================================================
    
    def test_get_bool_true_variants(self):
        """True 변환 테스트"""
        for value in ['true', 'True', 'TRUE', '1', 'yes', 'YES', 'on', 'ON']:
            config = self.create_config({'enabled': value})
            assert config.get_bool('enabled') is True, f"Failed for value: {value}"
    
    def test_get_bool_false_variants(self):
        """False 변환 테스트"""
        for value in ['false', 'False', 'FALSE', '0', 'no', 'NO', 'off', 'OFF', '']:
            config = self.create_config({'enabled': value})
            assert config.get_bool('enabled') is False, f"Failed for value: {value}"
    
    def test_get_bool_with_default(self):
        """기본값 제공"""
        config = self.create_config({})
        assert config.get_bool('enabled', True) is True
        assert config.get_bool('enabled', False) is False
    
    def test_get_bool_whitespace(self):
        """공백 정규화"""
        config = self.create_config({'enabled': '  true  '})
        assert config.get_bool('enabled') is True
    
    # ============================================================================
    # get_int 메서드 테스트
    # ============================================================================
    
    def test_get_int_valid_value(self):
        """유효한 정수 변환"""
        config = self.create_config({'count': '42'})
        assert config.get_int('count') == 42
    
    def test_get_int_with_default(self):
        """기본값 제공"""
        config = self.create_config({})
        assert config.get_int('count', 10) == 10
    
    def test_get_int_invalid_value(self):
        """유효하지 않은 값 처리"""
        config = self.create_config({'count': 'abc'})
        assert config.get_int('count', 10) == 10
    
    def test_get_int_empty_string(self):
        """빈 문자열 처리"""
        config = self.create_config({'count': ''})
        assert config.get_int('count', 10) == 10
    
    def test_get_int_whitespace(self):
        """공백 정규화"""
        config = self.create_config({'count': '  42  '})
        assert config.get_int('count') == 42
    
    def test_get_int_negative_value(self):
        """음수 처리"""
        config = self.create_config({'count': '-5'})
        assert config.get_int('count') == -5
    
    # ============================================================================
    # get_vllm_model_name 메서드 테스트 (우선순위 검증)
    # ============================================================================
    
    def test_get_vllm_model_name_from_form_data(self):
        """FormData에서 모델명 추출"""
        config = self.create_config({'privacy_vllm_model_name': 'custom_model'})
        result = config.get_vllm_model_name('privacy_removal')
        assert result == 'custom_model'
    
    def test_get_vllm_model_name_with_path_normalization(self):
        """경로 제거 정규화"""
        config = self.create_config({'privacy_vllm_model_name': '/model/qwen30_thinking_2507'})
        result = config.get_vllm_model_name('privacy_removal')
        assert result == 'qwen30_thinking_2507'
    
    def test_get_vllm_model_name_from_task_env_var(self, monkeypatch):
        """작업별 환경변수 우선순위"""
        monkeypatch.setenv('PRIVACY_REMOVAL_VLLM_MODEL_NAME', 'env_privacy_model')
        config = self.create_config({})
        result = config.get_vllm_model_name('privacy_removal')
        assert result == 'env_privacy_model'
    
    def test_get_vllm_model_name_from_common_env_var(self, monkeypatch):
        """공용 환경변수 우선순위"""
        monkeypatch.delenv('PRIVACY_REMOVAL_VLLM_MODEL_NAME', raising=False)
        monkeypatch.setenv('VLLM_MODEL_NAME', 'common_model')
        config = self.create_config({})
        result = config.get_vllm_model_name('privacy_removal')
        assert result == 'common_model'
    
    def test_get_vllm_model_name_from_default_fallback(self, monkeypatch):
        """기본값 fallback"""
        monkeypatch.delenv('PRIVACY_REMOVAL_VLLM_MODEL_NAME', raising=False)
        monkeypatch.delenv('VLLM_MODEL_NAME', raising=False)
        config = self.create_config({})
        result = config.get_vllm_model_name('privacy_removal', default_fallback='fallback_model')
        assert result == 'fallback_model'
    
    def test_get_vllm_model_name_priority_form_over_env(self, monkeypatch):
        """FormData가 환경변수보다 우선"""
        monkeypatch.setenv('PRIVACY_REMOVAL_VLLM_MODEL_NAME', 'env_model')
        config = self.create_config({'privacy_vllm_model_name': 'form_model'})
        result = config.get_vllm_model_name('privacy_removal')
        assert result == 'form_model'
    
    def test_get_vllm_model_name_priority_task_over_common_env(self, monkeypatch):
        """작업별 환경변수가 공용 환경변수보다 우선"""
        monkeypatch.setenv('PRIVACY_REMOVAL_VLLM_MODEL_NAME', 'task_specific')
        monkeypatch.setenv('VLLM_MODEL_NAME', 'common')
        config = self.create_config({})
        result = config.get_vllm_model_name('privacy_removal')
        assert result == 'task_specific'
    
    # ============================================================================
    # get_agent_url 메서드 테스트 (우선순위 검증)
    # ============================================================================
    
    def test_get_agent_url_from_form_data(self):
        """FormData에서 URL 추출"""
        config = self.create_config({'agent_url': 'http://localhost:8002/detect'})
        result = config.get_agent_url()
        assert result == 'http://localhost:8002/detect'
    
    def test_get_agent_url_from_element_detection_agent_url_env(self, monkeypatch):
        """ELEMENT_DETECTION_AGENT_URL 환경변수 사용"""
        monkeypatch.setenv('ELEMENT_DETECTION_AGENT_URL', 'http://api.example.com/detect')
        config = self.create_config({})
        result = config.get_agent_url()
        assert result == 'http://api.example.com/detect'
        config = self.create_config({})
        result = config.get_agent_url()
        assert result == 'http://api.example.com/detect'
    
    def test_get_agent_url_priority_form_over_env(self, monkeypatch):
        """FormData가 환경변수보다 우선"""
        monkeypatch.setenv('ELEMENT_DETECTION_AGENT_URL', 'http://api.example.com/detect')
        config = self.create_config({'agent_url': 'http://form.example.com/detect'})
        result = config.get_agent_url()
        assert result == 'http://form.example.com/detect'
    
    def test_get_agent_url_empty_string_fallback(self, monkeypatch):
        """모든 소스가 없을 때 빈 문자열 반환"""
        monkeypatch.delenv('EXTERNAL_API_URL', raising=False)
        monkeypatch.delenv('AGENT_URL', raising=False)
        config = self.create_config({})
        result = config.get_agent_url()
        assert result == ''
    
    # ============================================================================
    # _normalize_model_name 정적 메서드 테스트
    # ============================================================================
    
    def test_normalize_model_name_with_path(self):
        """경로 제거"""
        result = FormDataConfig._normalize_model_name('/model/qwen30_thinking_2507')
        assert result == 'qwen30_thinking_2507'
    
    def test_normalize_model_name_without_path(self):
        """경로 없는 모델명 유지"""
        result = FormDataConfig._normalize_model_name('qwen30_thinking_2507')
        assert result == 'qwen30_thinking_2507'
    
    def test_normalize_model_name_empty_string(self):
        """빈 문자열 처리"""
        result = FormDataConfig._normalize_model_name('')
        assert result == ''
    
    def test_normalize_model_name_multiple_slashes(self):
        """여러 슬래시 처리"""
        result = FormDataConfig._normalize_model_name('/model/subdir/qwen30')
        # 첫 번째 /model/ 만 제거됨
        assert result == 'subdir/qwen30'
    
    # ============================================================================
    # 통합 테스트 (현실적인 시나리오)
    # ============================================================================
    
    def test_full_transcribe_config_scenario(self, monkeypatch):
        """전체 transcribe 요청 설정 파싱"""
        monkeypatch.setenv('VLLM_MODEL_NAME', 'default_model')
        monkeypatch.setenv('EXTERNAL_API_URL', 'http://api.example.com/detect')
        
        form_data_dict = {
            'file_path': '/app/audio/test.wav',
            'language': 'ko',
            'privacy_removal': 'true',
            'classification': 'false',
            'element_detection': 'true',
            'privacy_vllm_model_name': '/model/privacy_model_v2',
            'detection_types': 'aggressive_sales,incomplete_sales',
        }
        
        config = self.create_config(form_data_dict)
        
        # 각 설정 검증
        assert config.get_str('file_path') == '/app/audio/test.wav'
        assert config.get_str('language') == 'ko'
        assert config.get_bool('privacy_removal') is True
        assert config.get_bool('classification') is False
        assert config.get_bool('element_detection') is True
        assert config.get_vllm_model_name('privacy_removal') == 'privacy_model_v2'
        assert config.get_vllm_model_name('classification') == 'default_model'
        assert config.get_agent_url() == 'http://api.example.com/detect'
        assert config.get_str('detection_types') == 'aggressive_sales,incomplete_sales'


# ============================================================================
# STTConfig 테스트
# ============================================================================

class TestSTTConfig:
    """STTConfig 클래스 테스트"""
    
    def create_config(self, form_data_dict):
        """테스트용 STTConfig 생성"""
        form_data = Mock()
        form_data.get = lambda key, default="": form_data_dict.get(key, default)
        return STTConfig(form_data, debug=False)
    
    def test_get_device_from_form_data(self):
        """FormData에서 디바이스 추출"""
        cfg = self.create_config({'stt_device': 'cuda'})
        assert cfg.get_device() == 'cuda'
    
    def test_get_device_case_insensitive(self):
        """디바이스 선택 시 대소문자 무시"""
        cfg = self.create_config({'stt_device': 'CUDA'})
        assert cfg.get_device() == 'cuda'
    
    def test_get_device_invalid_fallback(self):
        """지원하지 않는 디바이스는 기본값으로 폴백"""
        cfg = self.create_config({'stt_device': 'invalid_device'})
        assert cfg.get_device() == 'auto'
    
    def test_get_device_from_env(self, monkeypatch):
        """환경변수에서 디바이스 추출"""
        monkeypatch.setenv('STT_DEVICE', 'mps')
        cfg = self.create_config({})
        assert cfg.get_device() == 'mps'
    
    def test_get_compute_type_auto_cuda(self):
        """CUDA 디바이스는 float16 자동 선택"""
        cfg = self.create_config({})
        compute_type = cfg.get_compute_type(device='cuda')
        assert compute_type == 'float16'
    
    def test_get_compute_type_auto_cpu(self):
        """CPU 디바이스는 float32 자동 선택"""
        cfg = self.create_config({})
        compute_type = cfg.get_compute_type(device='cpu')
        assert compute_type == 'float32'
    
    def test_get_compute_type_from_form_data(self):
        """FormData에서 연산 타입 추출"""
        cfg = self.create_config({'stt_compute_type': 'float16'})
        assert cfg.get_compute_type() == 'float16'
    
    def test_get_compute_type_invalid_fallback(self):
        """지원하지 않는 연산 타입은 기본값으로 폴백"""
        cfg = self.create_config({'stt_compute_type': 'invalid_type'})
        assert cfg.get_compute_type() == 'float32'
    
    def test_get_backend_from_form_data(self):
        """FormData에서 백엔드 추출"""
        cfg = self.create_config({'stt_backend': 'transformers'})
        assert cfg.get_backend() == 'transformers'
    
    def test_get_backend_hyphen_normalization(self):
        """하이픈을 언더스코어로 정규화 (faster-whisper -> faster_whisper)"""
        cfg = self.create_config({'stt_backend': 'faster-whisper'})
        assert cfg.get_backend() == 'faster_whisper'
    
    def test_get_backend_invalid_fallback(self):
        """지원하지 않는 백엔드는 기본값으로 폴백"""
        cfg = self.create_config({'stt_backend': 'invalid_backend'})
        assert cfg.get_backend() == 'faster_whisper'
    
    def test_get_preset_from_form_data(self):
        """FormData에서 프리셋 추출"""
        cfg = self.create_config({'stt_preset': 'balanced'})
        assert cfg.get_preset() == 'balanced'
    
    def test_get_preset_from_env(self, monkeypatch):
        """환경변수에서 프리셋 추출"""
        monkeypatch.setenv('STT_PRESET', 'speed')
        cfg = self.create_config({})
        assert cfg.get_preset() == 'speed'
    
    def test_get_preset_invalid_fallback(self):
        """지원하지 않는 프리셋은 기본값으로 폴백"""
        cfg = self.create_config({'stt_preset': 'invalid_preset'})
        assert cfg.get_preset() == 'accuracy'
    
    def test_get_preset_custom(self):
        """커스텀 프리셋 지원"""
        cfg = self.create_config({'stt_preset': 'custom'})
        assert cfg.get_preset() == 'custom'


# ============================================================================
# LLMConfig 테스트
# ============================================================================

class TestLLMConfig:
    """LLMConfig 클래스 테스트"""
    
    def create_config(self, form_data_dict):
        """테스트용 LLMConfig 생성"""
        form_data = Mock()
        form_data.get = lambda key, default="": form_data_dict.get(key, default)
        return LLMConfig(form_data, debug=False)
    
    def test_get_llm_type_from_form_data(self):
        """FormData에서 LLM 타입 추출"""
        cfg = self.create_config({'privacy_llm_type': 'ollama'})
        assert cfg.get_llm_type('privacy') == 'ollama'
    
    def test_get_llm_type_invalid_fallback(self):
        """지원하지 않는 LLM 타입은 기본값으로 폴백"""
        cfg = self.create_config({'privacy_llm_type': 'invalid_llm'})
        assert cfg.get_llm_type('privacy') == 'vllm'
    
    def test_get_vllm_endpoint_from_form_data(self):
        """FormData에서 vLLM 엔드포인트 추출"""
        cfg = self.create_config({'privacy_vllm_endpoint': 'http://api.example.com:8000/v1'})
        assert cfg.get_vllm_endpoint('privacy_removal') == 'http://api.example.com:8000/v1'
    
    def test_get_vllm_endpoint_default(self):
        """vLLM 엔드포인트 기본값"""
        cfg = self.create_config({})
        assert cfg.get_vllm_endpoint('privacy_removal') == 'http://localhost:8000/v1'
    
    def test_get_vllm_endpoint_from_env(self, monkeypatch):
        """환경변수에서 vLLM 엔드포인트 추출"""
        monkeypatch.setenv('PRIVACY_REMOVAL_VLLM_ENDPOINT', 'http://custom.example.com:8000/v1')
        cfg = self.create_config({})
        assert cfg.get_vllm_endpoint('privacy_removal') == 'http://custom.example.com:8000/v1'


# ============================================================================
# ElementDetectionConfig 테스트
# ============================================================================

class TestElementDetectionConfig:
    """ElementDetectionConfig 클래스 테스트"""
    
    def create_config(self, form_data_dict):
        """테스트용 ElementDetectionConfig 생성"""
        form_data = Mock()
        form_data.get = lambda key, default="": form_data_dict.get(key, default)
        return ElementDetectionConfig(form_data, debug=False)
    
    def test_get_detection_api_type_from_form_data(self):
        """FormData에서 API 타입 추출"""
        cfg = self.create_config({'detection_api_type': 'vllm'})
        assert cfg.get_detection_api_type() == 'vllm'
    
    def test_get_detection_api_type_default(self):
        """API 타입 기본값 (ai_agent)"""
        cfg = self.create_config({})
        assert cfg.get_detection_api_type() == 'ai_agent'
    
    def test_get_detection_api_type_invalid_fallback(self):
        """지원하지 않는 API 타입은 기본값으로 폴백"""
        cfg = self.create_config({'detection_api_type': 'invalid_api'})
        assert cfg.get_detection_api_type() == 'ai_agent'
    
    def test_get_detection_types_csv_parsing(self):
        """CSV 형식의 탐지 타입 파싱"""
        cfg = self.create_config({'detection_types': 'aggressive_sales, incomplete_sales'})
        types = cfg.get_detection_types()
        assert types == ['aggressive_sales', 'incomplete_sales']
    
    def test_get_detection_types_case_insensitive(self):
        """탐지 타입 대소문자 정규화"""
        cfg = self.create_config({'detection_types': 'AGGRESSIVE_SALES,INCOMPLETE_SALES'})
        types = cfg.get_detection_types()
        assert types == ['aggressive_sales', 'incomplete_sales']
    
    def test_get_detection_types_invalid_filtered(self):
        """지원하지 않는 타입은 필터링"""
        cfg = self.create_config({'detection_types': 'aggressive_sales, invalid_type, incomplete_sales'})
        types = cfg.get_detection_types()
        assert types == ['aggressive_sales', 'incomplete_sales']
    
    def test_get_detection_types_empty(self):
        """탐지 타입 미지정 시 빈 리스트 반환"""
        cfg = self.create_config({})
        assert cfg.get_detection_types() == []
    
    # ============================================================================
    # ElementDetectionConfig 모드별 필수 파라미터 검증
    # ============================================================================
    
    def test_validate_ai_agent_mode_success(self):
        """ai_agent 모드 검증 성공"""
        cfg = self.create_config({'agent_url': 'http://api.example.com/detect'})
        is_valid, error = cfg.validate_for_ai_agent_mode()
        assert is_valid is True
        assert error == ""
    
    def test_validate_ai_agent_mode_missing_agent_url(self):
        """ai_agent 모드: agent_url 누락"""
        cfg = self.create_config({})
        is_valid, error = cfg.validate_for_ai_agent_mode()
        assert is_valid is False
        assert "agent_url" in error
    
    def test_validate_vllm_mode_success(self, monkeypatch):
        """vllm 모드 검증 성공"""
        monkeypatch.setenv('VLLM_MODEL_NAME', 'qwen30')
        monkeypatch.setenv('VLLM_ENDPOINT', 'http://vllm:8000/v1')
        cfg = self.create_config({})
        is_valid, error = cfg.validate_for_vllm_mode()
        assert is_valid is True
        assert error == ""
    
    def test_validate_vllm_mode_missing_model_name(self, monkeypatch):
        """vllm 모드: 모델명 누락"""
        monkeypatch.setenv('VLLM_ENDPOINT', 'http://vllm:8000/v1')
        monkeypatch.delenv('VLLM_MODEL_NAME', raising=False)
        cfg = self.create_config({})
        is_valid, error = cfg.validate_for_vllm_mode()
        assert is_valid is False
        assert "detection_vllm_model_name" in error
    
    def test_validate_vllm_mode_missing_endpoint(self, monkeypatch):
        """vllm 모드: 엔드포인트 누락"""
        monkeypatch.setenv('VLLM_MODEL_NAME', 'qwen30')
        monkeypatch.delenv('VLLM_ENDPOINT', raising=False)
        cfg = self.create_config({})
        is_valid, error = cfg.validate_for_vllm_mode()
        assert is_valid is False
        assert "엔드포인트" in error or "endpoint" in error.lower()
    
    def test_get_agent_url_for_detection(self):
        """ai_agent 모드용 agent_url 추출"""
        cfg = self.create_config({'agent_url': 'http://api.example.com/detect'})
        assert cfg.get_agent_url_for_detection() == 'http://api.example.com/detect'
    
    def test_get_vllm_model_name_for_detection(self):
        """vllm 모드용 모델명 추출"""
        cfg = self.create_config({'detection_vllm_model_name': 'qwen30_custom'})
        assert cfg.get_vllm_model_name_for_detection() == 'qwen30_custom'
    
    def test_get_vllm_endpoint_for_detection(self):
        """vllm 모드용 엔드포인트 추출"""
        cfg = self.create_config({'detection_vllm_endpoint': 'http://custom-vllm:8000/v1'})
        assert cfg.get_vllm_endpoint_for_detection() == 'http://custom-vllm:8000/v1'
    
    def test_get_vllm_endpoint_for_detection_default(self):
        """vllm 모드용 엔드포인트 기본값"""
        cfg = self.create_config({})
        assert cfg.get_vllm_endpoint_for_detection() == 'http://localhost:8000/v1'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

