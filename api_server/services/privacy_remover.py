"""
Privacy Remover Service
LLM을 사용하여 STT 텍스트에서 개인정보를 제거합니다.
프롬프트는 외부 파일에서 로드되며, Regex fallback이 포함되어 있습니다.

프롬프트 파일 위치: api_server/services/prompts/
- privacy_remover_default_v6.prompt: 기본 프롬프트 (전체 개인정보)
- privacy_remover_loosed_contact_v6.prompt: 로우즈드 버전 (연락처 정보 중심)

scratch/prompt_test_all의 privacy_remover_runner.py 로직을 독립적으로 구현합니다.
"""

import re
import os
import json
import asyncio
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

# 로깅 설정
logger = logging.getLogger(__name__)


class LLMClientFactory:
    """LLM 클라이언트를 생성하는 팩토리"""
    
    @staticmethod
    def create_client(model_name: str):
        """
        모델명에 따라 적절한 LLM 클라이언트 생성
        
        Args:
            model_name: 모델명 (예: 'gpt-4o', 'claude-sonnet-4', 'gemini-2.5-flash', 'Qwen3-30B-A3B-Thinking-2507-FP8')
            
        Returns:
            LLM 클라이언트 인스턴스
            
        Raises:
            ValueError: 지원하지 않는 모델인 경우
        """
        model_lower = model_name.lower()
        
        # OpenAI models
        if 'gpt' in model_lower or 'o1' in model_lower:
            logger.info(f"OpenAI 클라이언트 생성: {model_name}")
            return OpenAIClient(model_name)
        # Anthropic models
        elif 'claude' in model_lower:
            logger.info(f"Anthropic 클라이언트 생성: {model_name}")
            return AnthropicClient(model_name)
        # Google models
        elif 'gemini' in model_lower or 'google' in model_lower:
            logger.info(f"Google Generative AI 클라이언트 생성: {model_name}")
            return GoogleGenerativeAIClient(model_name)
        # Qwen (Alibaba) models
        elif 'qwen' in model_lower:
            logger.info(f"Qwen 클라이언트 생성: {model_name}")
            return QwenClient(model_name)
        else:
            logger.error(f"지원하지 않는 모델: {model_name}")
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
            logger.info(f"OpenAI 클라이언트 초기화 완료: {model_name}")
        except ImportError:
            logger.error("openai 패키지 미설치")
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
                'cached_tokens': int   # 캐시된 토큰
            }
        """
        try:
            model = model_name or self.model_name
            logger.debug(f"OpenAI API 호출: model={model}, max_tokens={max_tokens}, temperature={temperature}")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            logger.debug(f"OpenAI 응답 수신: input_tokens={response.usage.prompt_tokens}, output_tokens={response.usage.completion_tokens}")
            
            return {
                'text': response.choices[0].message.content,
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens,
                'cached_tokens': 0
            }
        except Exception as e:
            logger.error(f"OpenAI API 오류: {str(e)}", exc_info=True)
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
            logger.info(f"Anthropic 클라이언트 초기화 완료: {model_name}")
        except ImportError:
            logger.error("anthropic 패키지 미설치")
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
        Anthropic Claude API를 통해 응답 생성
        
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
            logger.debug(f"Anthropic API 호출: model={model}, max_tokens={max_tokens}, temperature={temperature}")
            
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
            
            logger.debug(f"Anthropic 응답 수신: input_tokens={response.usage.input_tokens}, output_tokens={response.usage.output_tokens}, cached_tokens={cached_tokens}")
            
            return {
                'text': response.content[0].text,
                'input_tokens': response.usage.input_tokens,
                'output_tokens': response.usage.output_tokens,
                'cached_tokens': cached_tokens
            }
        except Exception as e:
            logger.error(f"Anthropic API 오류: {str(e)}", exc_info=True)
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
            logger.info(f"Google Generative AI 클라이언트 초기화 완료: {model_name}")
        except ImportError:
            logger.error("google-generativeai 패키지 미설치")
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
            logger.debug(f"Google Generative AI API 호출: model={model}, max_tokens={max_tokens}, temperature={temperature}")
            
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
            
            logger.debug(f"Google Generative AI 응답 수신: input_tokens={input_tokens}, output_tokens={output_tokens}")
            
            return {
                'text': response.text,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'cached_tokens': 0
            }
        except Exception as e:
            logger.error(f"Google Generative AI 오류: {str(e)}", exc_info=True)
            raise RuntimeError(f"Google Generative AI 오류: {str(e)}")


class QwenClient:
    """Qwen (Alibaba) LLM 클라이언트"""
    
    def __init__(self, model_name: str):
        """
        Qwen 클라이언트 초기화
        
        Args:
            model_name: 모델명 (예: 'Qwen3-30B-A3B-Thinking-2507-FP8')
        """
        load_dotenv()
        try:
            import openai
            # Qwen은 OpenAI 호환 API 사용 (vLLM, Ollama, 또는 Qwen 공식 API)
            api_key = os.getenv("QWEN_API_KEY") or os.getenv("OPENAI_API_KEY") or "dummy"
            api_base = os.getenv("QWEN_API_BASE") or os.getenv("OPENAI_API_BASE") or "http://localhost:8001/v1"
            
            # vLLM 또는 Ollama의 /v1 엔드포인트 사용
            if not api_base.endswith('/v1'):
                if api_base.endswith('/'):
                    api_base = api_base + 'v1'
                else:
                    api_base = api_base + '/v1'
            
            self.client = openai.OpenAI(api_key=api_key, base_url=api_base)
            self.model_name = model_name
            self.api_base = api_base
            
            logger.info(f"Qwen 클라이언트 초기화 완료: {model_name} (base_url: {api_base})")
        except ImportError:
            logger.error("openai 패키지 미설치")
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
        Qwen API를 통해 응답 생성
        
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
            logger.info(f"[Qwen] API 호출 시작: model={model}, base_url={self.api_base}")
            logger.debug(f"[Qwen] 요청 파라미터: max_tokens={max_tokens}, temperature={temperature}, prompt_len={len(prompt)}")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            logger.info(f"[Qwen] 응답 수신 성공: input_tokens={response.usage.prompt_tokens}, output_tokens={response.usage.completion_tokens}")
            
            return {
                'text': response.choices[0].message.content,
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens,
                'cached_tokens': 0
            }
        except ConnectionError as e:
            logger.error(f"[Qwen] 연결 오류 (base_url: {self.api_base}): {str(e)}", exc_info=True)
            raise RuntimeError(f"vLLM/Qwen 서버 연결 실패 ({self.api_base}): {str(e)}")
        except TimeoutError as e:
            logger.error(f"[Qwen] 타임아웃 오류 (base_url: {self.api_base}): {str(e)}", exc_info=True)
            raise RuntimeError(f"vLLM/Qwen 서버 응답 시간 초과: {str(e)}")
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"[Qwen] API 오류 [{error_type}] (base_url: {self.api_base}): {str(e)}", exc_info=True)
            raise RuntimeError(f"Qwen API 오류: {error_type} - {str(e)}")


class PromptLoader:
    """프롬프트 파일 로더 - 다중 경로 지원"""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        프롬프트 로더 초기화
        
        Args:
            prompts_dir: 프롬프트 파일 디렉토리 경로 (기본: api_server/services/prompts)
                        또는 privacy_removal/prompts (legacy)
        """
        if prompts_dir is None:
            # 현재 파일 기준으로 prompts 디렉토리 찾기
            current_dir = Path(__file__).parent
            prompts_dir = current_dir / "prompts"
            
            # 폴백: legacy 경로도 확인
            legacy_dir = current_dir / "privacy_removal" / "prompts"
            
            if not prompts_dir.exists() and legacy_dir.exists():
                logger.info(f"Legacy 프롬프트 경로 사용: {legacy_dir}")
                prompts_dir = legacy_dir
        else:
            prompts_dir = Path(prompts_dir)
        
        self.prompts_dir = prompts_dir
        self._prompts_cache = {}
        
        logger.info(f"PromptLoader 초기화: {prompts_dir}")
        
        if not self.prompts_dir.exists():
            logger.warning(f"프롬프트 디렉토리가 없습니다: {self.prompts_dir}")
    
    def load_prompt(self, prompt_name: str) -> str:
        """
        프롬프트 파일 로드 (캐싱 지원)
        
        Args:
            prompt_name: 프롬프트 파일명 (확장자 제외, 예: 'privacy_remover_default_v6')
            
        Returns:
            프롬프트 내용
            
        Raises:
            FileNotFoundError: 프롬프트 파일이 없는 경우
        """
        # 캐시 확인
        if prompt_name in self._prompts_cache:
            logger.debug(f"캐시에서 프롬프트 로드: {prompt_name}")
            return self._prompts_cache[prompt_name]
        
        # 파일 경로 구성
        prompt_file = self.prompts_dir / f"{prompt_name}.prompt"
        
        logger.debug(f"프롬프트 파일 로드 시도: {prompt_file}")
        
        if not prompt_file.exists():
            # 사용 가능한 프롬프트 목록 수집
            available = []
            if self.prompts_dir.exists():
                available = [f.stem for f in sorted(self.prompts_dir.glob("*.prompt"))]
            
            logger.error(f"프롬프트 파일 없음: {prompt_file}, 사용 가능: {available}")
            raise FileNotFoundError(
                f"프롬프트 파일을 찾을 수 없습니다: {prompt_file}\n"
                f"사용 가능한 프롬프트: {available}"
            )
        
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 캐시에 저장
            self._prompts_cache[prompt_name] = content
            
            logger.debug(f"프롬프트 파일 로드 완료: {prompt_name} ({len(content)} chars)")
            
            return content
        except Exception as e:
            logger.error(f"프롬프트 파일 읽기 오류: {prompt_file}, {str(e)}", exc_info=True)
            raise
            raise


class SimplePromptProcessor:
    """프롬프트 처리기 - 파일 기반 로드"""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        프롬프트 처리기 초기화
        
        Args:
            prompts_dir: 프롬프트 파일 디렉토리 경로 (기본: api_server/services/prompts)
        """
        self.prompt_loader = PromptLoader(prompts_dir)
        self.prompt_mapping = {
            'privacy_remover_default': 'privacy_remover_default_v6',
            'privacy_remover_default_v6': 'privacy_remover_default_v6',
            'privacy_remover_loosed_contact': 'privacy_remover_loosed_contact_v6',
            'privacy_remover_loosed_contact_v6': 'privacy_remover_loosed_contact_v6'
        }
        logger.info("SimplePromptProcessor 초기화 완료")
    
    def get_prompt(self, prompt_type: str, text: str) -> str:
        """
        프롬프트 로드 및 템플릿 처리
        
        Args:
            prompt_type: 프롬프트 타입
            text: 사용자 텍스트
            
        Returns:
            완성된 프롬프트
        """
        logger.debug(f"프롬프트 생성: type={prompt_type}")
        
        # 프롬프트 타입 정규화
        normalized_type = self.prompt_mapping.get(prompt_type, 'privacy_remover_default_v6')
        
        if normalized_type != prompt_type:
            logger.debug(f"프롬프트 타입 정규화: {prompt_type} → {normalized_type}")
        
        # 프롬프트 파일 로드
        template = self.prompt_loader.load_prompt(normalized_type)
        
        # 텍스트 치환
        prompt = template.replace("{usertxt}", text)
        
        logger.debug(f"프롬프트 생성 완료: {len(prompt)} chars")
        
        return prompt


class PrivacyRemoverService:
    """개인정보 제거 서비스"""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        서비스 초기화
        
        Args:
            prompts_dir: 프롬프트 파일 디렉토리 경로 (기본: api_server/services/prompts)
        """
        load_dotenv()
        
        # LLM 모델: Qwen3-30B-A3B-Thinking-2507-FP8 (기본)
        # 또는 환경변수 LLM_MODEL_NAME으로 override 가능
        self.model_name = os.getenv("LLM_MODEL_NAME", "Qwen3-30B-A3B-Thinking-2507-FP8")
        self.llm_client = None
        self.prompt_processor = SimplePromptProcessor(prompts_dir)
        self._initialized = False
        
        logger.info(f"PrivacyRemoverService 초기화: model={self.model_name}")
    
    async def initialize(self):
        """LLM 클라이언트 초기화"""
        if self._initialized:
            logger.debug("LLM 클라이언트 이미 초기화됨")
            return
        
        try:
            logger.info(f"LLM 클라이언트 초기화 시작: {self.model_name}")
            self.llm_client = LLMClientFactory.create_client(self.model_name)
            self._initialized = True
            logger.info(f"LLM 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"LLM 클라이언트 초기화 실패: {str(e)}", exc_info=True)
            raise
    
    def get_available_prompts(self) -> List[str]:
        """
        사용 가능한 프롬프트 목록 반환
        
        Returns:
            프롬프트 파일명 리스트 (확장자 제외)
        """
        try:
            prompts_dir = self.prompt_processor.loader.prompts_dir
            if not prompts_dir.exists():
                logger.warning(f"프롬프트 디렉토리가 없습니다: {prompts_dir}")
                return []
            
            prompt_files = list(prompts_dir.glob("*.prompt"))
            prompt_names = [f.stem for f in prompt_files]  # 확장자 제외
            
            logger.debug(f"사용 가능한 프롬프트: {prompt_names}")
            return sorted(prompt_names)
        except Exception as e:
            logger.error(f"프롬프트 목록 조회 실패: {str(e)}")
            return []
    
    async def process_text(
        self, 
        usertxt: str,
        prompt_type: str = "privacy_remover_default_v6",
        max_tokens: int = 32768,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        텍스트의 개인정보 제거 - privacy_remover_runner.py의 process_text 로직 구현
        
        Args:
            usertxt: 원본 텍스트
            prompt_type: 프롬프트 타입
            max_tokens: 최대 토큰 수
            temperature: 온도 값
            
        Returns:
            {
                'success': bool,
                'privacy_exist': str,           # 'Y' 또는 'N'
                'exist_reason': str,            # 개인정보 사유
                'privacy_rm_usertxt': str,      # 처리된 텍스트
                'input_tokens': int,            # 입력 토큰
                'output_tokens': int,           # 출력 토큰
                'cached_tokens': int            # 캐시된 토큰
            }
        """
        try:
            # LLM 클라이언트 초기화 확인
            if not self._initialized:
                await self.initialize()
            
            logger.info(f"[PrivacyRemover] 텍스트 처리 시작: prompt_type={prompt_type}, text_len={len(usertxt)}")
            
            # 프롬프트 생성
            prompt = self.prompt_processor.get_prompt(prompt_type, usertxt)
            
            # LLM API 호출
            logger.debug(f"[PrivacyRemover] LLM API 호출: model={self.model_name}")
            llm_response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            logger.debug(f"[PrivacyRemover] LLM 응답 수신: {llm_response['input_tokens']} input tokens, {llm_response['output_tokens']} output tokens")
            
            # 응답 파싱
            response_text = llm_response['text'].strip()
            
            # JSON 파싱 시도
            try:
                # JSON 형식 추출 (마크다운 코드 블록 제거)
                if response_text.startswith('```'):
                    # ```json ... ``` 형식 처리
                    response_text = response_text.split('```')[1]
                    if response_text.startswith('json'):
                        response_text = response_text[4:]
                    response_text = response_text.strip()
                
                result = json.loads(response_text)
                
                logger.info(f"[PrivacyRemover] 텍스트 처리 완료 (LLM): privacy_exist={result.get('privacy_exist', 'N')}")
                
                return {
                    'success': True,
                    'privacy_exist': result.get('privacy_exist', 'N'),
                    'exist_reason': result.get('exist_reason', ''),
                    'privacy_rm_usertxt': result.get('privacy_rm_usertxt', usertxt),
                    'input_tokens': llm_response['input_tokens'],
                    'output_tokens': llm_response['output_tokens'],
                    'cached_tokens': llm_response['cached_tokens']
                }
            
            except json.JSONDecodeError as e:
                logger.warning(f"[PrivacyRemover] JSON 파싱 실패 (LLM 응답 형식 오류): {str(e)}")
                logger.warning(f"[PrivacyRemover] LLM 응답 내용: {response_text[:100]}...")
                logger.warning(f"[PrivacyRemover] Regex fallback으로 전환")
                
                # Regex fallback: 기본 패턴으로 개인정보 제거
                fallback_result = self._regex_fallback(usertxt)
                
                return {
                    'success': True,
                    'privacy_exist': fallback_result['privacy_exist'],
                    'exist_reason': fallback_result['exist_reason'],
                    'privacy_rm_usertxt': fallback_result['privacy_rm_usertxt'],
                    'input_tokens': llm_response['input_tokens'],
                    'output_tokens': llm_response['output_tokens'],
                    'cached_tokens': llm_response['cached_tokens']
                }
        
        except RuntimeError as e:
            # LLM API 오류 (연결 실패, 타임아웃 등)
            logger.error(f"[PrivacyRemover] LLM API 오류: {str(e)}")
            logger.warning(f"[PrivacyRemover] Regex fallback으로 전환")
            
            try:
                fallback_result = self._regex_fallback(usertxt)
                return {
                    'success': False,
                    'privacy_exist': fallback_result['privacy_exist'],
                    'exist_reason': f"[Fallback] LLM 호출 실패: {str(e)[:50]}",
                    'privacy_rm_usertxt': fallback_result['privacy_rm_usertxt']
                }
            except Exception as fallback_error:
                logger.error(f"[PrivacyRemover] Regex fallback도 실패: {str(fallback_error)}", exc_info=True)
                return {
                    'success': False,
                    'privacy_exist': 'N',
                    'exist_reason': f"[Error] 모든 처리 실패: {str(e)[:40]}",
                    'privacy_rm_usertxt': usertxt  # 원본 반환
                }
        
        except Exception as e:
            # 예상치 못한 오류
            logger.error(f"[PrivacyRemover] 예상치 못한 오류: {type(e).__name__}: {str(e)}", exc_info=True)
            logger.warning(f"[PrivacyRemover] Regex fallback으로 전환")
            
            # 실패 시 regex fallback
            try:
                fallback_result = self._regex_fallback(usertxt)
                return {
                    'success': False,
                    'privacy_exist': fallback_result['privacy_exist'],
                    'exist_reason': f"[Fallback] 처리 오류: {type(e).__name__}",
                    'privacy_rm_usertxt': fallback_result['privacy_rm_usertxt']
                }
            except Exception as fallback_error:
                logger.error(f"[PrivacyRemover] Regex fallback도 실패: {str(fallback_error)}", exc_info=True)
                return {
                    'success': False,
                    'privacy_exist': 'N',
                    'exist_reason': f"[Error] 모든 처리 실패",
                    'privacy_rm_usertxt': usertxt  # 원본 반환
                }
    
    async def remove_privacy_from_stt(
        self,
        stt_text: str,
        prompt_type: str = "privacy_remover_default_v6",
        max_tokens: int = 32768,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        STT 텍스트의 개인정보 제거 (app.py에서 호환성을 위한 래퍼)
        
        Args:
            stt_text: STT 변환 결과 텍스트
            prompt_type: 프롬프트 타입
            max_tokens: 최대 토큰 수
            temperature: 온도 값
            
        Returns:
            process_text와 동일한 결과 형식
        """
        return await self.process_text(
            usertxt=stt_text,
            prompt_type=prompt_type,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    def _regex_fallback(self, text: str) -> Dict[str, str]:
        """
        정규표현식을 사용한 기본 개인정보 제거 (LLM 실패 시 fallback)
        
        Args:
            text: 원본 텍스트
            
        Returns:
            {
                'privacy_exist': str,       # 'Y' 또는 'N'
                'exist_reason': str,        # 개인정보 타입
                'privacy_rm_usertxt': str   # 처리된 텍스트
            }
        """
        logger.info(f"[Fallback] Regex 기반 개인정보 제거 시작 (text_len={len(text)})")
        
        processed_text = text
        privacy_types = []
        
        # 전화번호 (010-xxxx-xxxx 형식 또는 연속된 10자리 숫자)
        phone_pattern = r'01[0-9]-\d{3,4}-\d{4}|\b01[0-9]\d{8}\b|\+\d{1,3}\s?\d{6,}'
        matches = re.findall(phone_pattern, processed_text)
        if matches:
            privacy_types.append(f"전화번호({len(matches)}개)")
            logger.debug(f"[Fallback] 전화번호 발견: {len(matches)}개")
            for match in matches:
                masked = match[0] + '*' * (len(match) - 1)
                processed_text = processed_text.replace(match, masked)
        
        # 이메일
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        matches = re.findall(email_pattern, processed_text)
        if matches:
            privacy_types.append(f"이메일({len(matches)}개)")
            logger.debug(f"[Fallback] 이메일 발견: {len(matches)}개")
            for match in matches:
                masked = match[0] + '*' * (len(match) - 1)
                processed_text = processed_text.replace(match, masked)
        
        # 계좌번호 (최소 6자리 연속 숫자)
        account_pattern = r'\b\d{6,}\b'
        matches = re.findall(account_pattern, processed_text)
        if matches:
            # 날짜나 다른 패턴과 구분 (가능한 계좌 범위: 8-16자리)
            account_matches = [m for m in matches if 8 <= len(m) <= 16]
            if account_matches:
                privacy_types.append(f"계좌번호({len(account_matches)}개)")
                logger.debug(f"[Fallback] 계좌번호 발견: {len(account_matches)}개")
                for match in account_matches:
                    masked = match[0] + '*' * (len(match) - 1)
                    processed_text = processed_text.replace(match, masked)
        
        # 주민등록번호 (XXXXXX-XXXXXXX)
        ssn_pattern = r'\d{6}-\d{7}'
        matches = re.findall(ssn_pattern, processed_text)
        if matches:
            privacy_types.append(f"주민등록번호({len(matches)}개)")
            logger.debug(f"[Fallback] 주민등록번호 발견: {len(matches)}개")
            for match in matches:
                masked = match[0] + '*' * (len(match) - 1)
                processed_text = processed_text.replace(match, masked)
        
        privacy_exist = 'Y' if privacy_types else 'N'
        exist_reason = ', '.join(privacy_types)[:50] if privacy_types else ''
        
        logger.info(f"[Fallback] Regex 처리 완료: privacy_exist={privacy_exist}, found={len(privacy_types)}개 타입: {exist_reason}")
        
        return {
            'privacy_exist': privacy_exist,
            'exist_reason': exist_reason,
            'privacy_rm_usertxt': processed_text
        }


# ============================================================================
# Singleton 패턴: 전역 서비스 인스턴스
# ============================================================================

_privacy_remover_service: Optional[PrivacyRemoverService] = None


def get_privacy_remover_service(prompts_dir: Optional[str] = None) -> PrivacyRemoverService:
    """
    PrivacyRemoverService의 싱글톤 인스턴스 반환
    
    Args:
        prompts_dir: 프롬프트 파일 디렉토리 경로 (첫 호출 시만 사용)
        
    Returns:
        PrivacyRemoverService 인스턴스
    """
    global _privacy_remover_service
    
    if _privacy_remover_service is None:
        logger.info("PrivacyRemoverService 싱글톤 생성")
        _privacy_remover_service = PrivacyRemoverService(prompts_dir)
    
    return _privacy_remover_service


async def _async_get_privacy_remover_service(prompts_dir: Optional[str] = None) -> PrivacyRemoverService:
    """
    FastAPI Depends()와 호환되는 async 래퍼
    PrivacyRemoverService의 싱글톤 인스턴스 반환
    
    Args:
        prompts_dir: 프롬프트 파일 디렉토리 경로
        
    Returns:
        PrivacyRemoverService 인스턴스
    """
    return get_privacy_remover_service(prompts_dir)


if __name__ == "__main__":
    # 기본 로깅 설정
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 테스트 코드
    async def test():
        service = get_privacy_remover_service()
        result = await service.process_text("홍길동님께서 010-1234-5678로 연락주셨습니다.")
        print("Result:", result)
    
    asyncio.run(test())
