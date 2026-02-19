"""
Privacy Removal Service
LLM을 사용하여 STT 결과에서 개인정보를 제거하는 서비스
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class LLMProcessorForPrivacy:
    """
    STT 결과 텍스트에서 개인정보를 제거하는 클래스
    
    특징:
    1. LLM(vLLM)에 프롬프트를 전달하여 개인정보 제거
    2. 프롬프트 템플릿 캐싱으로 성능 최적화
    3. 결과는 통일된 딕셔너리 형태로 반환
    """
    
    def __init__(
        self, 
        vllm_client,
        prompts_dir: Optional[Path] = None
    ):
        """
        LLMProcessorForPrivacy 초기화
        
        Args:
            vllm_client: vLLM 클라이언트 객체 (기존 STT 서버에서 사용하는 것)
            prompts_dir: 프롬프트 파일 디렉토리 (기본값: 현재 파일 위치의 prompts)
        """
        self.vllm_client = vllm_client
        
        if prompts_dir is None:
            # Docker 환경: /app/api_server/services/privacy_removal/prompts
            # 로컬 개발: api_server/services/privacy_removal/prompts
            current_file_dir = Path(__file__).parent
            self.prompts_dir = current_file_dir / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)
        
        # 프롬프트 캐시
        self._prompt_cache: Dict[str, str] = {}
        logger.info(f"[PrivacyRemoval] 프롬프트 디렉토리: {self.prompts_dir}")
    
    def _load_prompt_template(self, prompt_type: str = "privacy_remover_default_v6") -> str:
        """
        프롬프트 파일 로드 (캐싱 지원)
        
        Args:
            prompt_type: 프롬프트 타입
            
        Returns:
            프롬프트 템플릿 문자열
            
        Raises:
            FileNotFoundError: 프롬프트 파일 없을 때
        """
        if prompt_type in self._prompt_cache:
            return self._prompt_cache[prompt_type]
        
        prompt_file = self.prompts_dir / f"{prompt_type}.prompt"
        
        if not prompt_file.exists():
            available = self.get_available_prompt_types()
            raise FileNotFoundError(
                f"프롬프트 파일 없음: {prompt_file}\n"
                f"사용 가능한 타입: {available}"
            )
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            template = f.read()
        
        self._prompt_cache[prompt_type] = template
        logger.info(f"[PrivacyRemoval] 프롬프트 로드: {prompt_type}")
        return template
    
    def get_available_prompt_types(self) -> list:
        """사용 가능한 프롬프트 타입 목록"""
        if not self.prompts_dir.exists():
            return []
        
        prompt_files = self.prompts_dir.glob("*.prompt")
        return [f.stem for f in sorted(prompt_files)]
    
    def _create_prompt(self, template: str, text: str) -> str:
        """프롬프트 템플릿에 텍스트 삽입"""
        return template.replace("{usertxt}", text)
    
    async def remove_privacy(
        self,
        text: str,
        prompt_type: str = "privacy_remover_default_v6",
        max_tokens: int = 8192,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        텍스트에서 개인정보 제거
        
        Args:
            text: 원본 STT 텍스트
            prompt_type: 사용할 프롬프트 타입
            max_tokens: 최대 토큰 수
            temperature: LLM 온도 설정
            
        Returns:
            {
                'privacy_exist': str,        # Y/N
                'exist_reason': str,         # 개인정보 사유 (20자 이내)
                'privacy_rm_text': str,      # 개인정보 제거된 텍스트
                'success': bool              # 처리 성공 여부
            }
        """
        try:
            # 프롬프트 로드 및 생성
            template = self._load_prompt_template(prompt_type)
            prompt = self._create_prompt(template, text)
            
            logger.info(f"[PrivacyRemoval] 개인정보 제거 시작 (길이: {len(text)})")
            
            # vLLM 호출
            response = await self.vllm_client.generate_response(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # 응답 파싱
            result = self._parse_response(response, text)
            logger.info(f"[PrivacyRemoval] 결과: {result['privacy_exist']}, 사유: {result['exist_reason']}")
            
            return result
            
        except Exception as e:
            logger.error(f"[PrivacyRemoval] 처리 실패: {str(e)}", exc_info=True)
            return {
                'privacy_exist': 'N',
                'exist_reason': 'Error in privacy removal',
                'privacy_rm_text': text,
                'success': False
            }
    
    def _parse_response(self, response: str, original_text: str) -> Dict[str, Any]:
        """
        LLM 응답을 파싱하여 구조화된 결과로 반환
        
        Args:
            response: LLM 응답 (JSON 형식)
            original_text: 원본 텍스트
            
        Returns:
            구조화된 결과 딕셔너리
        """
        try:
            # JSON 파싱
            json_str = response.strip()
            
            # JSON 시작/종료 찾기
            json_start = json_str.find('{')
            json_end = json_str.rfind('}') + 1
            
            if json_start == -1 or json_end <= json_start:
                # JSON 형식이 아닌 경우
                return {
                    'privacy_exist': 'N',
                    'exist_reason': 'Invalid response format',
                    'privacy_rm_text': original_text,
                    'success': False
                }
            
            json_str = json_str[json_start:json_end]
            data = json.loads(json_str)
            
            # 응답에서 필요한 필드 추출
            return {
                'privacy_exist': data.get('privacy_exist', 'N').upper(),
                'exist_reason': data.get('exist_reason', ''),
                'privacy_rm_text': data.get('privacy_rm_usertxt', original_text),
                'success': True
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"[PrivacyRemoval] JSON 파싱 실패: {str(e)}")
            return {
                'privacy_exist': 'N',
                'exist_reason': 'JSON parse error',
                'privacy_rm_text': original_text,
                'success': False
            }
