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

from api_server.services.privacy_removal import PrivacyRemovalService


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
            print(f"   - Processed Text: {result['privacy_rm_text'][:50]}...")
            print(f"   - Success: {result['success']}")
            
        except Exception as e:
            print(f"❌ 처리 실패: {e}")
    
    print("\n" + "=" * 70)
    print("테스트 완료")
    print("=" * 70)


async def test_direct_processor():
    """LLMProcessor 직접 테스트 (vLLM 없이)"""
    
    from api_server.services.privacy_removal.privacy_remover import LLMProcessorForPrivacy
    from api_server.services.privacy_removal.vllm_client import VLLMClient
    
    print("\n" + "=" * 70)
    print("Direct LLMProcessor Test")
    print("=" * 70)
    
    # vLLM 클라이언트 생성
    print("\n1️⃣ vLLM 클라이언트 초기화...")
    vllm_client = VLLMClient(
        base_url="http://localhost:8000",
        model_name="meta-llama/Llama-2-7b-hf"
    )
    print("✅ vLLM 클라이언트 준비됨")
    
    # LLMProcessor 생성
    print("\n2️⃣ LLMProcessor 초기화...")
    processor = LLMProcessorForPrivacy(vllm_client=vllm_client)
    print("✅ LLMProcessor 초기화 완료")
    
    # 프롬프트 확인
    print("\n3️⃣ 프롬프트 파일 로드...")
    try:
        template = processor._load_prompt_template("privacy_remover_default_v6")
        print(f"✅ 프롬프트 로드 완료 (크기: {len(template)} bytes)")
        print(f"   첫 100글자: {template[:100]}...")
    except FileNotFoundError as e:
        print(f"❌ 프롬프트 파일 없음: {e}")
        return
    
    print("\n테스트 완료")


if __name__ == "__main__":
    import sys
    import os
    
    print("\n🚀 Privacy Removal Integration Test Suite\n")
    
    # vLLM 연결 확인
    print("📡 vLLM 연결 확인...")
    import subprocess
    try:
        # vLLM 서버 확인 (curl으로 헬스 체크)
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8000/health"],
            timeout=5,
            capture_output=True
        )
        
        if result.returncode == 0 and result.stdout.decode().strip() in ["200", "404"]:
            print("✅ vLLM 서버 연결됨 (http://localhost:8000)")
        else:
            print("⚠️ vLLM 서버 미응답 (테스트는 계속 진행하되, 실제 개인정보 제거는 동작하지 않음)")
    except Exception as e:
        print(f"⚠️ vLLM 연결 확인 실패: {e}")
        print("   → vLLM 서버를 시작하세요: docker run --gpus all -p 8000:8000 vllm/vllm-openai")
    
    # 테스트 선택
    print("\n테스트 옵션:")
    print("1. Privacy Removal Service 테스트 (vLLM 필요)")
    print("2. LLMProcessor 직접 테스트")
    print("3. 프롬프트 파일만 확인")
    
    choice = input("\n선택 (기본값 3): ").strip() or "3"
    
    if choice == "1":
        print("\n→ Privacy Removal Service 테스트 시작...")
        print("⚠️ vLLM 서버가 실행 중이어야 합니다!")
        asyncio.run(test_privacy_removal())
    elif choice == "2":
        print("\n→ LLMProcessor 직접 테스트 시작...")
        asyncio.run(test_direct_processor())
    elif choice == "3":
        print("\n→ 프롬프트 파일 확인...")
        prompts_dir = Path(__file__).parent / "api_server" / "services" / "privacy_removal" / "prompts"
        print(f"프롬프트 디렉토리: {prompts_dir}")
        
        if prompts_dir.exists():
            prompt_files = list(prompts_dir.glob("*.prompt"))
            if prompt_files:
                print(f"✅ 찾은 프롬프트 파일:")
                for f in prompt_files:
                    size = f.stat().st_size
                    print(f"   - {f.name} ({size:,} bytes)")
            else:
                print("❌ 프롬프트 파일이 없습니다")
        else:
            print(f"❌ 디렉토리가 없습니다: {prompts_dir}")
    else:
        print("❌ 잘못된 선택")
