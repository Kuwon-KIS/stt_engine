# API 테스트 가이드 (vLLM & Ollama)

**작성일**: 2026년 2월 25일  
**대상**: Phase 3 LLM Client 구현 후 API 테스트

---

## 목차

1. [환경 설정](#환경-설정)
2. [사전 준비](#사전-준비)
3. [curl 테스트](#curl-테스트)
4. [Python 클라이언트 테스트](#python-클라이언트-테스트)
5. [통합 테스트](#통합-테스트)
6. [에러 처리](#에러-처리)
7. [성능 테스트](#성능-테스트)

---

## 환경 설정

### 1. vLLM 설치 및 시작

```bash
# vLLM 설치
pip install vllm

# vLLM 서버 시작 (터미널 1)
python -m vllm.entrypoints.openai.api_server \
  --model mistral-7b-instruct-v0.2 \
  --host 0.0.0.0 \
  --port 8000

# 또는 다른 모델 사용
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --host 0.0.0.0 \
  --port 8000
```

**확인**:
```bash
curl -s http://localhost:8000/v1/models | python -m json.tool
```

**예상 응답**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "mistral-7b-instruct-v0.2",
      "object": "model",
      "owned_by": "vllm"
    }
  ]
}
```

### 2. Ollama 설치 및 시작

```bash
# Ollama 다운로드 및 설치 (홈페이지)
# https://ollama.ai

# Ollama 시작 (백그라운드)
ollama serve &

# 모델 다운로드 (터미널 2)
ollama pull neural-chat
ollama pull mistral
ollama pull llama2
```

**확인**:
```bash
curl -s http://localhost:11434/api/tags | python -m json.tool
```

**예상 응답**:
```json
{
  "models": [
    {
      "name": "neural-chat:latest",
      "modified_at": "2024-02-25T12:00:00.000000Z",
      "size": 4000000000
    }
  ]
}
```

### 3. STT 엔진 API 시작

```bash
# 터미널 3에서 API 서버 시작
cd /Users/a113211/workspace/stt_engine
python main.py
# 또는
python -m uvicorn api_server.app:app --host 0.0.0.0 --port 8003

# 또는 웹 UI와 함께 시작
cd web_ui
python -m uvicorn main:app --host 0.0.0.0 --port 8100
```

**확인**:
```bash
curl -s http://localhost:8003/health | python -m json.tool
```

---

## 사전 준비

### 1. 필요한 패키지 설치

```bash
pip install httpx pytest python-dotenv
```

### 2. .env 파일 설정 (선택사항)

```bash
# /Users/a113211/workspace/stt_engine/.env
VLLM_API_URL=http://localhost:8000
VLLM_MODEL_NAME=mistral-7b-instruct-v0.2
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL_NAME=neural-chat
DEFAULT_LLM_TYPE=vllm
```

### 3. 테스트 오디오/텍스트 준비

```bash
# 테스트용 텍스트 샘플
cat > /tmp/test_samples.txt << 'EOF'
# 텔레마케팅
안녕하세요. 저희 회사에서는 새로운 보험 상품을 출시했습니다. 지금 가입하면 50% 할인을 받을 수 있습니다.

# 고객 서비스
주문하신 제품이 배송되었습니다. 우체국 택배로 배송되며, 예정 배송일은 내일입니다.

# 부당권유판매
이 상품은 지금만 구매 가능합니다. 시간이 제한되어 있으니 빨리 결정하세요. 더 이상 이런 가격은 없을 겁니다.
EOF
```

---

## curl 테스트

### Test 1: 기본 분류 (vLLM)

```bash
curl -X POST http://localhost:8003/transcribe \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'stt_text=안녕하세요. 저희는 새로운 상품을 소개하고 있습니다.' \
  -d 'classification=true' \
  -d 'classification_llm_type=vllm' \
  | python -m json.tool
```

**예상 응답**:
```json
{
  "stt_text": "안녕하세요. 저희는 새로운 상품을 소개하고 있습니다.",
  "classification": {
    "category": "TELEMARKETING",
    "confidence": 0.95
  },
  "status": "success"
}
```

### Test 2: 기본 분류 (Ollama)

```bash
curl -X POST http://localhost:8003/transcribe \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'stt_text=주문하신 물품이 배송되었습니다.' \
  -d 'classification=true' \
  -d 'classification_llm_type=ollama' \
  -d 'ollama_model_name=neural-chat' \
  | python -m json.tool
```

**예상 응답**:
```json
{
  "stt_text": "주문하신 물품이 배송되었습니다.",
  "classification": {
    "category": "CUSTOMER_SERVICE",
    "confidence": 0.92
  },
  "status": "success"
}
```

### Test 3: 요소 탐지 (vLLM)

```bash
curl -X POST http://localhost:8003/transcribe \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'stt_text=이 상품은 반드시 지금 구매해야 합니다. 제한된 시간만 할인 중입니다.' \
  -d 'element_detection=true' \
  -d 'detection_api_type=local' \
  -d 'detection_llm_type=vllm' \
  -d 'detection_types=aggressive_sales,incomplete_sales' \
  | python -m json.tool
```

**예상 응답**:
```json
{
  "stt_text": "이 상품은 반드시 지금 구매해야 합니다. 제한된 시간만 할인 중입니다.",
  "element_detection": {
    "detected_elements": [
      {
        "type": "aggressive_sales",
        "confidence": 0.98,
        "reason": "시간 제한 압박"
      }
    ]
  },
  "status": "success"
}
```

### Test 4: 요소 탐지 (Ollama)

```bash
curl -X POST http://localhost:8003/transcribe \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'stt_text=당신의 보험을 지금 변경하면 더 많은 혜택을 받을 수 있습니다.' \
  -d 'element_detection=true' \
  -d 'detection_api_type=local' \
  -d 'detection_llm_type=ollama' \
  -d 'ollama_model_name=neural-chat' \
  | python -m json.tool
```

### Test 5: 분류 + 요소 탐지 (vLLM)

```bash
curl -X POST http://localhost:8003/transcribe \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'stt_text=새로운 보험 상품을 소개합니다. 지금만 특별 할인을 받으실 수 있습니다. 서명하시면 바로 혜택이 시작됩니다.' \
  -d 'classification=true' \
  -d 'classification_llm_type=vllm' \
  -d 'element_detection=true' \
  -d 'detection_api_type=local' \
  -d 'detection_llm_type=vllm' \
  | python -m json.tool
```

### Test 6: 혼합 LLM 사용

```bash
curl -X POST http://localhost:8003/transcribe \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'stt_text=상담 내용 테스트' \
  -d 'classification=true' \
  -d 'classification_llm_type=vllm' \
  -d 'element_detection=true' \
  -d 'detection_api_type=local' \
  -d 'detection_llm_type=ollama' \
  -d 'ollama_model_name=neural-chat' \
  | python -m json.tool
```

---

## Python 클라이언트 테스트

### Test 1: vLLM 클라이언트 직접 테스트

```python
import asyncio
from api_server.llm_clients import LLMClientFactory

async def test_vllm():
    """vLLM 클라이언트 테스트"""
    
    # 클라이언트 생성
    client = LLMClientFactory.create_client(
        llm_type="vllm",
        model_name="mistral-7b-instruct-v0.2",
        vllm_api_url="http://localhost:8000"
    )
    
    print("✅ vLLM 클라이언트 생성됨")
    
    # 가용성 확인
    available = await client.is_available()
    print(f"✅ vLLM 서버 가용성: {available}")
    
    if available:
        # LLM 호출
        prompt = "다음 텍스트를 분류하세요: 새로운 상품 소개"
        response = await client.call(prompt=prompt)
        print(f"✅ vLLM 응답:\n{response}")
    
    return True

# 실행
asyncio.run(test_vllm())
```

### Test 2: Ollama 클라이언트 직접 테스트

```python
import asyncio
from api_server.llm_clients import LLMClientFactory

async def test_ollama():
    """Ollama 클라이언트 테스트"""
    
    # 클라이언트 생성
    client = LLMClientFactory.create_client(
        llm_type="ollama",
        model_name="neural-chat",
        ollama_api_url="http://localhost:11434"
    )
    
    print("✅ Ollama 클라이언트 생성됨")
    
    # 가용성 확인
    available = await client.is_available()
    print(f"✅ Ollama 서버 가용성: {available}")
    
    if available:
        # LLM 호출
        prompt = "다음을 분류하세요: 고객 서비스 상담"
        response = await client.call(prompt=prompt)
        print(f"✅ Ollama 응답:\n{response}")
    
    return True

# 실행
asyncio.run(test_ollama())
```

### Test 3: 팩토리를 통한 다중 클라이언트 테스트

```python
import asyncio
from api_server.llm_clients import LLMClientFactory

async def test_factory_caching():
    """팩토리 캐싱 테스트"""
    
    # 첫 번째 호출 (생성)
    client1 = LLMClientFactory.create_client(llm_type="vllm")
    print(f"✅ 클라이언트 1 생성됨: {type(client1).__name__}")
    
    # 두 번째 호출 (캐시)
    client2 = LLMClientFactory.get_cached_client("vllm")
    print(f"✅ 클라이언트 2 조회됨: {type(client2).__name__}")
    
    # 동일한 인스턴스 확인
    assert client1 is client2, "캐시 작동 안 함!"
    print(f"✅ 캐싱 정상 작동 (같은 인스턴스)")
    
    return True

# 실행
asyncio.run(test_factory_caching())
```

---

## 통합 테스트

### 전체 파이프라인 테스트 (Python)

```python
import asyncio
from api_server.transcribe_endpoint import (
    perform_classification,
    perform_element_detection
)

async def test_full_pipeline():
    """전체 파이프라인 테스트"""
    
    test_text = "새로운 보험 상품을 소개합니다. 지금만 특별 할인을 받으실 수 있습니다."
    
    print("=" * 60)
    print("분류 테스트 (vLLM)")
    print("=" * 60)
    
    # 분류 실행
    classification_result = await perform_classification(
        text=test_text,
        prompt_type="classification_default_v1",
        llm_type="vllm"
    )
    print(f"분류 결과:\n{classification_result}")
    
    print("\n" + "=" * 60)
    print("요소 탐지 테스트 (Ollama)")
    print("=" * 60)
    
    # 요소 탐지 실행
    detection_result = await perform_element_detection(
        text=test_text,
        api_type="local",
        llm_type="ollama",
        detection_types=["aggressive_sales", "incomplete_sales"]
    )
    print(f"탐지 결과:\n{detection_result}")
    
    return True

# 실행
asyncio.run(test_full_pipeline())
```

---

## 에러 처리

### Test: vLLM 서버 미연결

```bash
# vLLM 서버 종료 후 테스트
curl -X POST http://localhost:8003/transcribe \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'stt_text=테스트' \
  -d 'classification=true' \
  -d 'classification_llm_type=vllm' \
  | python -m json.tool
```

**예상 응답** (에러):
```json
{
  "error": "vLLM 서버에 연결할 수 없습니다.",
  "details": "localhost:8000에서 가용한 서버를 확인하세요.",
  "status": "error"
}
```

### Test: 잘못된 모델명

```bash
curl -X POST http://localhost:8003/transcribe \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'stt_text=테스트' \
  -d 'classification=true' \
  -d 'classification_llm_type=ollama' \
  -d 'ollama_model_name=nonexistent-model' \
  | python -m json.tool
```

### Test: 잘못된 API 타입

```bash
curl -X POST http://localhost:8003/transcribe \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'stt_text=테스트' \
  -d 'element_detection=true' \
  -d 'detection_api_type=invalid_type' \
  | python -m json.tool
```

---

## 성능 테스트

### 응답 시간 측정

```bash
# 단일 요청 시간 측정
time curl -X POST http://localhost:8003/transcribe \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'stt_text=테스트 텍스트' \
  -d 'classification=true' \
  -d 'classification_llm_type=vllm' \
  -o /dev/null -s

# 또는 Python으로
python << 'EOF'
import asyncio
import time
from api_server.llm_clients import LLMClientFactory

async def benchmark():
    client = LLMClientFactory.create_client(llm_type="vllm")
    
    start = time.time()
    response = await client.call(prompt="테스트 프롬프트")
    elapsed = time.time() - start
    
    print(f"응답 시간: {elapsed:.2f}초")
    print(f"응답: {response[:100]}...")

asyncio.run(benchmark())
EOF
```

### 스트레스 테스트

```bash
# 동시 요청 10개 (vLLM)
for i in {1..10}; do
  curl -X POST http://localhost:8003/transcribe \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d 'stt_text=테스트 텍스트' \
    -d 'classification=true' \
    -d 'classification_llm_type=vllm' \
    &
done

# 모든 백그라운드 작업 완료 대기
wait
echo "✅ 모든 요청 완료"
```

---

## 체크리스트

### 기본 테스트
- [ ] vLLM 서버 시작 확인
- [ ] Ollama 서버 시작 확인
- [ ] STT API 서버 시작 확인
- [ ] 각 서버의 헬스 체크 통과

### curl 테스트
- [ ] vLLM 분류 테스트 통과
- [ ] Ollama 분류 테스트 통과
- [ ] vLLM 요소 탐지 테스트 통과
- [ ] Ollama 요소 탐지 테스트 통과
- [ ] 혼합 LLM 테스트 통과

### Python 클라이언트 테스트
- [ ] vLLM 클라이언트 직접 테스트 통과
- [ ] Ollama 클라이언트 직접 테스트 통과
- [ ] 팩토리 캐싱 테스트 통과

### 통합 테스트
- [ ] 전체 파이프라인 테스트 통과

### 에러 처리
- [ ] 서버 미연결 에러 처리 확인
- [ ] 잘못된 모델명 에러 처리 확인
- [ ] 잘못된 API 타입 에러 처리 확인

### 성능
- [ ] 응답 시간 측정 완료 (목표: 1-10초)
- [ ] 스트레스 테스트 통과

---

## 문제 해결

### vLLM 서버가 응답하지 않음

```bash
# 프로세스 확인
ps aux | grep vllm

# 포트 확인
lsof -i :8000

# 수동 시작 및 로그 확인
python -m vllm.entrypoints.openai.api_server \
  --model mistral-7b-instruct-v0.2 \
  --host 0.0.0.0 \
  --port 8000
```

### Ollama 서버가 응답하지 않음

```bash
# 프로세스 확인
ps aux | grep ollama

# 포트 확인
lsof -i :11434

# 모델 확인
ollama list

# 서버 재시작
killall ollama
ollama serve
```

### 메모리 부족

```bash
# 메모리 상태 확인
free -h

# Ollama 메모리 확인
du -sh ~/.ollama/

# vLLM GPU 메모리 확인
nvidia-smi
```

---

**작성자**: GitHub Copilot  
**마지막 수정**: 2026년 2월 25일
