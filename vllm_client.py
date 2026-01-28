#!/usr/bin/env python3
"""
vLLM 연동 모듈
STT 결과를 vLLM 서버로 전송하는 기능을 제공합니다.
"""

import os
from pathlib import Path
from typing import Optional, Dict
import requests
from pydantic import BaseModel
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class VLLMConfig(BaseModel):
    """vLLM 서버 설정"""
    api_url: str = os.getenv("VLLM_API_URL", "http://localhost:8000")
    model_name: str = os.getenv("VLLM_MODEL_NAME", "meta-llama/Llama-2-7b-hf")
    timeout: int = 60
    max_tokens: int = 512


class VLLMClient:
    """vLLM 서버와의 통신을 담당하는 클라이언트"""
    
    def __init__(self, config: VLLMConfig):
        """
        vLLM 클라이언트 초기화
        
        Args:
            config: vLLM 설정
        """
        self.config = config
        self.completion_endpoint = f"{config.api_url}/v1/completions"
        
        print(f"🔗 vLLM 서버 연결 설정")
        print(f"   API URL: {config.api_url}")
        print(f"   모델: {config.model_name}")
    
    def health_check(self) -> bool:
        """
        vLLM 서버 상태 확인
        
        Returns:
            서버 정상 여부
        """
        try:
            response = requests.get(
                f"{self.config.api_url}/health",
                timeout=5
            )
            is_healthy = response.status_code == 200
            status = "✅ 정상" if is_healthy else "❌ 오류"
            print(f"vLLM 서버 상태: {status}")
            return is_healthy
        except Exception as e:
            print(f"❌ vLLM 서버 연결 불가: {e}")
            return False
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Optional[str]:
        """
        vLLM 서버에서 텍스트 생성
        
        Args:
            prompt: 입력 프롬프트
            temperature: 온도 값 (낮을수록 결정적)
            top_p: Top-p 샘플링 값
        
        Returns:
            생성된 텍스트 또는 None
        """
        try:
            payload = {
                "model": self.config.model_name,
                "prompt": prompt,
                "max_tokens": self.config.max_tokens,
                "temperature": temperature,
                "top_p": top_p
            }
            
            print(f"\n📤 요청 전송 중...")
            response = requests.post(
                self.completion_endpoint,
                json=payload,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result["choices"][0]["text"]
                print(f"✅ 응답 수신 완료")
                return generated_text
            else:
                print(f"❌ 오류 (상태 코드: {response.status_code})")
                print(f"   응답: {response.text}")
                return None
        
        except Exception as e:
            print(f"❌ 요청 전송 실패: {e}")
            return None
    
    def process_stt_with_vllm(
        self,
        transcribed_text: str,
        instruction: str = "다음 텍스트를 요약해주세요:"
    ) -> Dict:
        """
        STT 결과를 vLLM으로 처리합니다.
        
        Args:
            transcribed_text: STT 결과 텍스트
            instruction: 처리 지시사항
        
        Returns:
            처리 결과 딕셔너리
        """
        prompt = f"{instruction}\n\n{transcribed_text}"
        
        result = self.generate(prompt)
        
        if result:
            return {
                "success": True,
                "original_text": transcribed_text,
                "processed_text": result,
                "instruction": instruction
            }
        else:
            return {
                "success": False,
                "original_text": transcribed_text,
                "error": "vLLM 처리 실패"
            }


def test_vllm_connection():
    """vLLM 서버 연결 테스트"""
    config = VLLMConfig()
    client = VLLMClient(config)
    
    # 서버 상태 확인
    if not client.health_check():
        print("⚠️  vLLM 서버가 실행 중이 아닙니다.")
        print("서버를 시작해주세요: vllm serve <model_name>")
        return
    
    # 간단한 요청 테스트
    print("\n🧪 테스트 요청 전송...")
    test_prompt = "안녕하세요, 저는 STT 엔진입니다."
    result = client.generate(test_prompt)
    
    if result:
        print(f"\n📝 생성된 텍스트:")
        print(result)
    else:
        print("❌ 요청 실패")


if __name__ == "__main__":
    test_vllm_connection()
