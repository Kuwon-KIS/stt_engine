"""
FormDataConfig 테스트

FormData 요청 파싱 및 설정 추상화 계층의 유닛 테스트
"""

import os
import pytest
from unittest.mock import Mock
from api_server.config import FormDataConfig


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
        result = config.get_vllm_model_name('privacy')
        assert result == 'custom_model'
    
    def test_get_vllm_model_name_with_path_normalization(self):
        """경로 제거 정규화"""
        config = self.create_config({'privacy_vllm_model_name': '/model/qwen30_thinking_2507'})
        result = config.get_vllm_model_name('privacy')
        assert result == 'qwen30_thinking_2507'
    
    def test_get_vllm_model_name_from_task_env_var(self, monkeypatch):
        """작업별 환경변수 우선순위"""
        monkeypatch.setenv('PRIVACY_VLLM_MODEL_NAME', 'env_privacy_model')
        config = self.create_config({})
        result = config.get_vllm_model_name('privacy')
        assert result == 'env_privacy_model'
    
    def test_get_vllm_model_name_from_common_env_var(self, monkeypatch):
        """공용 환경변수 우선순위"""
        monkeypatch.delenv('PRIVACY_VLLM_MODEL_NAME', raising=False)
        monkeypatch.setenv('VLLM_MODEL_NAME', 'common_model')
        config = self.create_config({})
        result = config.get_vllm_model_name('privacy')
        assert result == 'common_model'
    
    def test_get_vllm_model_name_from_default_fallback(self, monkeypatch):
        """기본값 fallback"""
        monkeypatch.delenv('PRIVACY_VLLM_MODEL_NAME', raising=False)
        monkeypatch.delenv('VLLM_MODEL_NAME', raising=False)
        config = self.create_config({})
        result = config.get_vllm_model_name('privacy', default_fallback='fallback_model')
        assert result == 'fallback_model'
    
    def test_get_vllm_model_name_priority_form_over_env(self, monkeypatch):
        """FormData가 환경변수보다 우선"""
        monkeypatch.setenv('PRIVACY_VLLM_MODEL_NAME', 'env_model')
        config = self.create_config({'privacy_vllm_model_name': 'form_model'})
        result = config.get_vllm_model_name('privacy')
        assert result == 'form_model'
    
    def test_get_vllm_model_name_priority_task_over_common_env(self, monkeypatch):
        """작업별 환경변수가 공용 환경변수보다 우선"""
        monkeypatch.setenv('PRIVACY_VLLM_MODEL_NAME', 'task_specific')
        monkeypatch.setenv('VLLM_MODEL_NAME', 'common')
        config = self.create_config({})
        result = config.get_vllm_model_name('privacy')
        assert result == 'task_specific'
    
    # ============================================================================
    # get_agent_url 메서드 테스트 (우선순위 검증)
    # ============================================================================
    
    def test_get_agent_url_from_form_data(self):
        """FormData에서 URL 추출"""
        config = self.create_config({'agent_url': 'http://localhost:8002/detect'})
        result = config.get_agent_url()
        assert result == 'http://localhost:8002/detect'
    
    def test_get_agent_url_from_external_api_url_env(self, monkeypatch):
        """EXTERNAL_API_URL 환경변수 사용"""
        monkeypatch.setenv('EXTERNAL_API_URL', 'http://api.example.com/detect')
        monkeypatch.delenv('AGENT_URL', raising=False)
        config = self.create_config({})
        result = config.get_agent_url()
        assert result == 'http://api.example.com/detect'
    
    def test_get_agent_url_from_legacy_agent_url_env(self, monkeypatch):
        """레거시 AGENT_URL 환경변수 지원"""
        monkeypatch.delenv('EXTERNAL_API_URL', raising=False)
        monkeypatch.setenv('AGENT_URL', 'http://legacy.example.com/detect')
        config = self.create_config({})
        result = config.get_agent_url()
        assert result == 'http://legacy.example.com/detect'
    
    def test_get_agent_url_priority_form_over_env(self, monkeypatch):
        """FormData가 환경변수보다 우선"""
        monkeypatch.setenv('EXTERNAL_API_URL', 'http://api.example.com/detect')
        config = self.create_config({'agent_url': 'http://form.example.com/detect'})
        result = config.get_agent_url()
        assert result == 'http://form.example.com/detect'
    
    def test_get_agent_url_priority_external_over_legacy(self, monkeypatch):
        """EXTERNAL_API_URL이 AGENT_URL보다 우선"""
        monkeypatch.setenv('EXTERNAL_API_URL', 'http://api.example.com/detect')
        monkeypatch.setenv('AGENT_URL', 'http://legacy.example.com/detect')
        config = self.create_config({})
        result = config.get_agent_url()
        assert result == 'http://api.example.com/detect'
    
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
        assert config.get_vllm_model_name('privacy') == 'privacy_model_v2'
        assert config.get_vllm_model_name('classification') == 'default_model'
        assert config.get_agent_url() == 'http://api.example.com/detect'
        assert config.get_str('detection_types') == 'aggressive_sales,incomplete_sales'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
