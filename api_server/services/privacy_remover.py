"""
Privacy Remover Service
LLM을 사용하여 STT 텍스트에서 개인정보를 제거합니다.
Regex fallback이 포함되어 있습니다.

scratch/prompt_test_all의 privacy_remover_runner.py 로직을 독립적으로 구현합니다.
"""

import re
import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv


class LLMClientFactory:
    """LLM 클라이언트를 생성하는 팩토리"""
    
    @staticmethod
    def create_client(model_name: str):
        """
        모델명에 따라 적절한 LLM 클라이언트 생성
        
        Args:
            model_name: 모델명 (예: 'gpt-4o', 'claude-sonnet-4', 'gemini-2.5-flash')
            
        Returns:
            LLM 클라이언트 인스턴스
        """
        model_lower = model_name.lower()
        
        # OpenAI models
        if 'gpt' in model_lower or 'o1' in model_lower:
            return OpenAIClient(model_name)
        # Anthropic models
        elif 'claude' in model_lower:
            return AnthropicClient(model_name)
        # Google models
        elif 'gemini' in model_lower or 'google' in model_lower:
            return GoogleGenerativeAIClient(model_name)
        else:
            raise ValueError(f"지원하지 않는 모델: {model_name}")


class OpenAIClient:
    """OpenAI LLM 클라이언트"""
    
    def __init__(self, model_name: str):
        """
        OpenAI 클라이언트 초기화
        
        Args:
            model_name: 모델명 (예: 'gpt-4o', 'gpt-4-turbo')
        """
        load_dotenv()
        try:
            import openai
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model_name = model_name
        except ImportError:
            raise ImportError("openai 패키지를 설치하세요: pip install openai")
    
    async def generate_response(
        self, 
        prompt: str,
        model_name: Optional[str] = None,
        max_tokens: int = 32768,
        temperature: float = 0.3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        OpenAI API를 통해 응답 생성
        
        Args:
            prompt: 프롬프트
            model_name: 사용할 모델명 (None이면 초기화된 모델 사용)
            max_tokens: 최대 토큰 수
            temperature: 창의성 정도 (0.0~2.0)
            
        Returns:
            {
                'text': str,           # 응답 텍스트
                'input_tokens': int,   # 입력 토큰
                'output_tokens': int,  # 출력 토큰
                'cached_tokens': int   # 캐시된 토큰 (0)
            }
        """
        try:
            model = model_name or self.model_name
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return {
                'text': response.choices[0].message.content,
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens,
                'cached_tokens': 0
            }
        except Exception as e:
            raise RuntimeError(f"OpenAI API 오류: {str(e)}")


class AnthropicClient:
    """Anthropic (Claude) LLM 클라이언트"""
    
    def __init__(self, model_name: str):
        """
        Anthropic 클라이언트 초기화
        
        Args:
            model_name: 모델명 (예: 'claude-sonnet-4', 'claude-opus-4')
        """
        load_dotenv()
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model_name = model_name
        except ImportError:
            raise ImportError("anthropic 패키지를 설치하세요: pip install anthropic")
    
    async def generate_response(
        self, 
        prompt: str,
        model_name: Optional[str] = None,
        max_tokens: int = 32768,
        temperature: float = 0.3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Anthropic API를 통해 응답 생성
        
        Args:
            prompt: 프롬프트
            model_name: 사용할 모델명 (None이면 초기화된 모델 사용)
            max_tokens: 최대 토큰 수
            temperature: 창의성 정도 (0.0~1.0)
            
        Returns:
            {
                'text': str,           # 응답 텍스트
                'input_tokens': int,   # 입력 토큰
                'output_tokens': int,  # 출력 토큰
                'cached_tokens': int   # 캐시된 토큰
            }
        """
        try:
            model = model_name or self.model_name
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # 캐시 토큰 추출
            cached_tokens = 0
            if hasattr(response.usage, 'cache_read_input_tokens'):
                cached_tokens = response.usage.cache_read_input_tokens
            
            return {
                'text': response.content[0].text,
                'input_tokens': response.usage.input_tokens,
                'output_tokens': response.usage.output_tokens,
                'cached_tokens': cached_tokens
            }
        except Exception as e:
            raise RuntimeError(f"Anthropic API 오류: {str(e)}")


class GoogleGenerativeAIClient:
    """Google Generative AI (Gemini) LLM 클라이언트"""
    
    def __init__(self, model_name: str):
        """
        Google Generative AI 클라이언트 초기화
        
        Args:
            model_name: 모델명 (예: 'gemini-2.5-flash', 'gemini-1.5-pro')
        """
        load_dotenv()
        try:
            import google.generativeai as genai
            self.genai = genai
            api_key = os.getenv("GOOGLE_API_KEY")
            genai.configure(api_key=api_key)
            self.model_name = model_name
        except ImportError:
            raise ImportError("google-generativeai 패키지를 설치하세요: pip install google-generativeai")
    
    async def generate_response(
        self, 
        prompt: str,
        model_name: Optional[str] = None,
        max_tokens: int = 32768,
        temperature: float = 0.3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Google Generative AI를 통해 응답 생성
        
        Args:
            prompt: 프롬프트
            model_name: 사용할 모델명 (None이면 초기화된 모델 사용)
            max_tokens: 최대 토큰 수
            temperature: 창의성 정도 (0.0~2.0)
            
        Returns:
            {
                'text': str,           # 응답 텍스트
                'input_tokens': int,   # 입력 토큰
                'output_tokens': int,  # 출력 토큰
                'cached_tokens': int   # 캐시된 토큰
            }
        """
        try:
            model = model_name or self.model_name
            client = self.genai.GenerativeModel(model)
            response = client.generate_content(
                prompt,
                generation_config=self.genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature
                )
            )
            
            # 토큰 정보 추출
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, 'usage_metadata'):
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
            
            return {
                'text': response.text,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'cached_tokens': 0
            }
        except Exception as e:
            raise RuntimeError(f"Google Generative AI 오류: {str(e)}")


class SimplePromptProcessor:
    """간단한 프롬프트 처리기"""
    
    # 기본 프롬프트 템플릿 (scratch/prompt_test_all의 privacy_remover 프롬프트 로직 적용)
    PRIVACY_REMOVER_DEFAULT = """당신은 고객 상담 기록에서 개인정보를 제거하는 전문가입니다.

다음 텍스트를 분석하여 개인정보(전화번호, 이메일, 계좌번호, 주민등록번호 등)가 포함되어 있는지 확인하세요.

개인정보가 있으면 제거하고, 없으면 원본 텍스트를 그대로 반환하세요.

응답은 반드시 다음 JSON 형식으로 반환하세요:
{
    "privacy_exist": "Y 또는 N",
    "exist_reason": "개인정보 존재 사유 (없으면 빈 문자열)",
    "privacy_rm_usertxt": "개인정보가 제거된 텍스트 또는 원본 텍스트"
}

분석할 텍스트:
{usertxt}"""

    PRIVACY_REMOVER_LOOSED_CONTACT = """당신은 고객 상담 기록에서 개인정보를 제거하는 전문가입니다.

다음 연락처 정보 텍스트를 분석하여 개인정보(전화번호, 이메일, 계좌번호, 주민등록번호 등)가 포함되어 있는지 확인하세요.

개인정보가 있으면 제거하고, 없으면 원본 텍스트를 그대로 반환하세요.

응답은 반드시 다음 JSON 형식으로 반환하세요:
{
    "privacy_exist": "Y 또는 N",
    "exist_reason": "개인정보 존재 사유 (없으면 빈 문자열)",
    "privacy_rm_usertxt": "개인정보가 제거된 텍스트 또는 원본 텍스트"
}

분석할 텍스트:
{usertxt}"""

    def __init__(self):
        """프롬프트 처리기 초기화"""
        self.prompts = {
            'privacy_remover_default': self.PRIVACY_REMOVER_DEFAULT,
            'privacy_remover_loosed_contact': self.PRIVACY_REMOVER_LOOSED_CONTACT
        }
    
    def get_prompt(self, prompt_type: str, text: str) -> str:
        """
        프롬프트 템플릿에서 텍스트로 프롬프트 생성
        
        Args:
            prompt_type: 프롬프트 타입
            text: 사용자 텍스트
            
        Returns:
            완성된 프롬프트
        """
        template = self.prompts.get(
            prompt_type, 
            self.PRIVACY_REMOVER_DEFAULT
        )
        return template.replace("{usertxt}", text)


class PrivacyRemoverService:
    """개인정보 제거 서비스"""
    
    def __init__(self):
        """서비스 초기화"""
        load_dotenv()
        self.model_name = os.getenv("LLM_MODEL_NAME", "gpt-4o")
        self.llm_client = None
        self.prompt_processor = SimplePromptProcessor()
        self._initialized = False
    
    async def initialize(self):
        """LLM 클라이언트 초기화"""
        if self._initialized:
            return
        
        try:
            # LLMClientFactory를 통해 클라이언트 생성
            self.llm_client = LLMClientFactory.create_client(self.model_name)
            self._initialized = True
            print(f"✅ LLM 클라이언트 초기화: {self.model_name}")
        except Exception as e:
            print(f"⚠️ LLM 클라이언트 초기화 실패: {e}")
            self._initialized = False
    
    async def remove_privacy_from_text(
        self, 
        text: str, 
        prompt_type: str = "privacy_remover_default"
    ) -> Dict[str, Any]:
        """
        STT 텍스트에서 개인정보 제거
        
        Args:
            text: 원본 텍스트
            prompt_type: 프롬프트 타입
            
        Returns:
            {
                'success': bool,
                'text': str,              # 처리된 텍스트
                'removed_count': int,     # 제거된 개인정보 개수
                'removed_items': List,    # 제거된 항목 리스트
                'method': str             # 'llm' 또는 'regex'
            }
        """
        if not text or not text.strip():
            return {
                'success': True,
                'text': text,
                'removed_count': 0,
                'removed_items': [],
                'method': 'none'
            }
        
        # LLM 기반 처리 시도
        if not self._initialized:
            await self.initialize()
        
        if self._initialized and self.llm_client:
            try:
                result = await self._remove_privacy_with_llm(text, prompt_type)
                if result['success']:
                    return result
            except Exception as e:
                print(f"⚠️ LLM 처리 실패: {e}, Regex fallback 사용")
        
        # Regex fallback
        return await self._remove_privacy_with_regex(text)
    
    async def _remove_privacy_with_llm(
        self, 
        text: str, 
        prompt_type: str
    ) -> Dict[str, Any]:
        """
        LLM을 사용한 개인정보 제거
        
        Privacy Remover Runner의 process_text 로직을 따릅니다.
        """
        try:
            # 프롬프트 생성
            prompt = self.prompt_processor.get_prompt(prompt_type, text)
            
            # LLM 호출
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=32768,
                temperature=0.3
            )
            
            # 응답 파싱
            result = self._extract_data_from_response(response, text)
            
            return result
        except Exception as e:
            print(f"LLM 처리 중 오류: {e}")
            raise
    
    def _extract_data_from_response(
        self, 
        response: Dict[str, Any],
        original_text: str
    ) -> Dict[str, Any]:
        """
        LLM 응답에서 데이터 추출
        
        LLMProcessor의 _extract_data_from_response 로직을 따릅니다.
        """
        try:
            response_text = response.get('text', '')
            
            # JSON 파싱 시도
            try:
                # JSON 코드 블록 제거 (```json ... ``` 형식)
                cleaned_text = response_text.strip()
                if cleaned_text.startswith('```json'):
                    cleaned_text = cleaned_text.split('```json')[1]
                if cleaned_text.startswith('```'):
                    cleaned_text = cleaned_text.split('```')[1]
                if cleaned_text.endswith('```'):
                    cleaned_text = cleaned_text.rsplit('```', 1)[0]
                
                cleaned_text = cleaned_text.strip()
                
                # JSON 파싱
                parsed = json.loads(cleaned_text)
                
                privacy_exist = parsed.get('privacy_exist', 'N').upper()
                exist_reason = parsed.get('exist_reason', '')
                
                # privacy_exist가 "Y"이면 처리된 텍스트 사용
                if privacy_exist == 'Y':
                    privacy_rm_usertxt = parsed.get('privacy_rm_usertxt', response_text)
                else:
                    # privacy_exist가 "N"이면 원본 텍스트 유지
                    privacy_rm_usertxt = original_text
                
                removed_items = []
                if privacy_exist == 'Y' and exist_reason:
                    removed_items.append(exist_reason)
                
                return {
                    'success': True,
                    'text': privacy_rm_usertxt,
                    'removed_count': len(removed_items),
                    'removed_items': removed_items,
                    'method': 'llm'
                }
                
            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                # JSON 파싱 실패 시 regex fallback
                print(f"JSON 파싱 실패: {str(e)}")
                return {
                    'success': False,
                    'text': original_text,
                    'removed_count': 0,
                    'removed_items': [],
                    'method': 'llm'
                }
                
        except Exception as e:
            print(f"응답 데이터 추출 중 오류: {str(e)}")
            return {
                'success': False,
                'text': original_text,
                'removed_count': 0,
                'removed_items': [],
                'method': 'llm'
            }
    
    async def _remove_privacy_with_regex(
        self, 
        text: str
    ) -> Dict[str, Any]:
        """Regex를 사용한 개인정보 제거 (fallback)"""
        if not text:
            return {
                'success': True,
                'text': text,
                'removed_count': 0,
                'removed_items': [],
                'method': 'regex'
            }
        
        processed_text = text
        removed_items = []
        
        # 전화번호 패턴 (010-1234-5678, 02-123-4567 등)
        phone_pattern = r'\b\d{2,4}[-.]?\d{3,4}[-.]?\d{4}\b'
        phone_matches = re.findall(phone_pattern, processed_text)
        if phone_matches:
            processed_text = re.sub(phone_pattern, '[전화번호]', processed_text)
            removed_items.append(f"전화번호: {len(phone_matches)}개")
        
        # 이메일 패턴
        email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
        email_matches = re.findall(email_pattern, processed_text)
        if email_matches:
            processed_text = re.sub(email_pattern, '[이메일]', processed_text)
            removed_items.append(f"이메일: {len(email_matches)}개")
        
        # 계좌번호 패턴 (10~20자리 숫자)
        account_pattern = r'\b\d{10,20}\b'
        account_matches = re.findall(account_pattern, processed_text)
        if account_matches:
            processed_text = re.sub(account_pattern, '[계좌번호]', processed_text)
            removed_items.append(f"계좌번호: {len(account_matches)}개")
        
        # 주민등록번호 패턴 (XXXXXX-XXXXXXX)
        ssn_pattern = r'\d{6}-\d{7}'
        ssn_matches = re.findall(ssn_pattern, processed_text)
        if ssn_matches:
            processed_text = re.sub(ssn_pattern, '[주민등록번호]', processed_text)
            removed_items.append(f"주민등록번호: {len(ssn_matches)}개")
        
        return {
            'success': True,
            'text': processed_text,
            'removed_count': len(removed_items),
            'removed_items': removed_items,
            'method': 'regex'
        }


# Singleton pattern for dependency injection
_privacy_remover_service = None

def get_privacy_remover_service() -> PrivacyRemoverService:
    """PrivacyRemoverService 싱글톤 인스턴스 반환"""
    global _privacy_remover_service
    if _privacy_remover_service is None:
        _privacy_remover_service = PrivacyRemoverService()
    return _privacy_remover_service
