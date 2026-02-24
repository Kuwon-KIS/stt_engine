#!/usr/bin/env python3
"""
Privacy Removal Feature Integration Test Script
개인정보 제거 기능 테스트
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from api_server.services import PrivacyRemovalService


async def test_privacy_removal():
    """Privacy Removal 기능 테스트"""
    
    print("=" * 70)
    print("Privacy Removal Feature Test")
    print("=" * 70)
    
    # 서비스 초기화
    print("\n1️⃣ PrivacyRemovalService 초기화...")
    try:
        service = PrivacyRemovalService(
            vllm_base_url="http://localhost:8000",
            vllm_model="meta-llama/Llama-2-7b-hf"
        )
        print("✅ 서비스 초기화 완료")
    except Exception as e:
        print(f"❌ 서비스 초기화 실패: {e}")
        return
    
    # 사용 가능한 프롬프트 확인
    print("\n2️⃣ 사용 가능한 프롬프트 타입 조회...")
    try:
        available_prompts = service.get_available_prompts()
        print(f"✅ 사용 가능한 프롬프트: {available_prompts}")
        
        if not available_prompts:
            print("⚠️ 프롬프트 파일이 없습니다")
            return
    except Exception as e:
        print(f"❌ 프롬프트 조회 실패: {e}")
        return
    
    # 테스트 텍스트 준비
    test_texts = [
        "나는 John Smith이고 010-1234-5678에서 전화할 수 있습니다",
        "제 이름은 김철수이고, 이메일은 kim.chulsu@example.com입니다. 주소는 서울시 강남구입니다",
        "일반적인 STT 결과 텍스트입니다. 특별한 개인정보가 없습니다"
    ]
    
    # 각 텍스트에 대해 privacy removal 실행
    print("\n3️⃣ Privacy Removal 처리...")
    for i, text in enumerate(test_texts, 1):
        print(f"\n테스트 {i}: {text[:50]}...")
        
        try:
            result = await service.remove_privacy_from_stt(
                stt_text=text,
                prompt_type="privacy_remover_default_v6",
                max_tokens=8192,
                temperature=0.3
            )
            
            print(f"✅ 처리 성공")
            print(f"   - Privacy Exist: {result['privacy_exist']}")
            print(f"   - Reason: {result['exist_reason'][:50]}")
            print(f"   - Processed Text: {result['privacy_rm_usertxt'][:50]}...")
            print(f"   - Success: {result['success']}")
            
        except Exception as e:
            print(f"❌ 처리 실패: {e}")
    
    print("\n" + "=" * 70)
    print("테스트 완료")
    print("=" * 70)


if __name__ == "__main__":
    import sys
    import os
    
    print("\n🚀 Privacy Removal Integration Test\n")
    
    print("→ Privacy Removal Service 테스트 시작...")
    print("⚠️ 필수 환경변수 확인:")
    print("   - OPENAI_API_KEY / ANTHROPIC_API_KEY / GOOGLE_API_KEY / QWEN_API_KEY 중 하나")
    
    asyncio.run(test_privacy_removal())
