#!/usr/bin/env python3
"""
요소 탐지 (Element Detection) 기능 테스트
"""

import asyncio
import sys
from pathlib import Path

app_root = Path(__file__).parent
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))

from api_server.transcribe_endpoint import perform_element_detection


async def test_element_detection():
    """테스트: 요소 탐지 기본 기능"""
    print("\n" + "="*60)
    print("Test 1: 외부 API 요소 탐지")
    print("="*60)
    
    result = await perform_element_detection(
        text="안녕하세요. 이 제품은 정말 좋습니다.",
        detection_types=["incomplete_sales", "aggressive_sales"],
        api_type="external",
        external_api_url="http://localhost:9000/detect"
    )
    
    print(f"✓ Result: {result}")
    assert result['success'] == True
    assert result['api_type'] == 'external'
    assert result['llm_type'] is None
    assert len(result['detection_results']) > 0
    print("✅ Test 1 passed!")
    
    print("\n" + "="*60)
    print("Test 2: 로컬 LLM (OpenAI) 요소 탐지")
    print("="*60)
    
    result = await perform_element_detection(
        text="안녕하세요. 이 제품은 정말 좋습니다.",
        detection_types=["incomplete_sales"],
        api_type="local",
        llm_type="openai"
    )
    
    print(f"✓ Result: {result}")
    assert result['success'] == True
    assert result['api_type'] == 'local'
    assert result['llm_type'] == 'openai'
    print("✅ Test 2 passed!")
    
    print("\n" + "="*60)
    print("Test 3: 로컬 LLM (vLLM) 요소 탐지")
    print("="*60)
    
    result = await perform_element_detection(
        text="안녕하세요. 이 제품은 정말 좋습니다.",
        detection_types=["incomplete_sales", "aggressive_sales"],
        api_type="local",
        llm_type="vllm",
        vllm_model_name="meta-llama/Llama-2-7b"
    )
    
    print(f"✓ Result: {result}")
    assert result['success'] == True
    assert result['api_type'] == 'local'
    assert result['llm_type'] == 'vllm'
    print("✅ Test 3 passed!")
    
    print("\n" + "="*60)
    print("Test 4: 로컬 LLM (Ollama) 요소 탐지")
    print("="*60)
    
    result = await perform_element_detection(
        text="안녕하세요. 이 제품은 정말 좋습니다.",
        detection_types=["aggressive_sales"],
        api_type="local",
        llm_type="ollama",
        ollama_model_name="mistral"
    )
    
    print(f"✓ Result: {result}")
    assert result['success'] == True
    assert result['api_type'] == 'local'
    assert result['llm_type'] == 'ollama'
    print("✅ Test 4 passed!")
    
    print("\n" + "="*60)
    print("Test 5: 기본값 테스트 (detection_types 미지정)")
    print("="*60)
    
    result = await perform_element_detection(
        text="안녕하세요. 이 제품은 정말 좋습니다.",
        api_type="external"
    )
    
    print(f"✓ Result: {result}")
    assert result['success'] == True
    assert len(result['detection_results']) == 2  # 기본값: incomplete_sales, aggressive_sales
    print("✅ Test 5 passed!")
    
    print("\n" + "="*60)
    print("Test 6: 에러 처리 - 잘못된 api_type")
    print("="*60)
    
    result = await perform_element_detection(
        text="안녕하세요.",
        api_type="invalid_type"
    )
    
    print(f"✓ Result: {result}")
    assert result['success'] == False
    assert 'error' in result
    print("✅ Test 6 passed!")
    
    print("\n" + "="*60)
    print("✅ All tests passed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_element_detection())
