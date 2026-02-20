# AI Agent 통합 가이드

## 개요

STT Engine에 AI Agent 처리 기능을 추가했습니다. 외부 AI Agent로 정제된 텍스트를 전달하고 결과를 받을 수 있습니다.

**특징:**
- ✅ 외부 AI Agent 호출
- ✅ vLLM Fallback 지원 (외부 Agent 실패 시)
- ✅ Dummy Agent (테스트용)
- ✅ Streaming 지원
- ✅ Chat Thread ID 유지 (대화 연속성)
- ✅ 자동 실패 감지 및 재시도

---

## API 엔드포인트

### 1. AI Agent 처리 (`POST /ai-agent/process`)

정제된 텍스트를 AI Agent로 처리합니다.

**Request:**
```bash
curl -X POST "http://localhost:8003/ai-agent/process" \
-H "Content-Type: application/json" \
-d '{
    "use_streaming": false,
    "chat_thread_id": null,
    "parameters": {
        "user_query": "사용자 쿼리 텍스트"
    }
}'
```

**Response:**
```json
{
    "success": true,
    "response": "AI Agent의 응답 텍스트",
    "chat_thread_id": "thread_123",
    "agent_type": "external|vllm|dummy",
    "processing_time_sec": 2.5,
    "error": null
}
```

### 2. Dummy Agent 테스트 (`POST /ai-agent/dummy`)

Dummy Agent로 응답을 생성합니다 (테스트용).

**Request:**
```bash
curl -X POST "http://localhost:8003/ai-agent/dummy" \
-H "Content-Type: application/json" \
-d '{
    "user_query": "테스트 쿼리",
    "chat_thread_id": null
}'
```

**Response:**
```json
{
    "success": true,
    "response": "[AI Agent Dummy Response]...",
    "chat_thread_id": null,
    "agent_type": "dummy",
    "processing_time_sec": 0.1
}
```

### 3. AI Agent 헬스 체크 (`GET /ai-agent/health`)

AI Agent 서비스 상태를 확인합니다.

**Request:**
```bash
curl "http://localhost:8003/ai-agent/health"
```

**Response:**
```json
{
    "status": "ok",
    "agent_url": "http://external-agent-server:5000",
    "vllm_url": "http://localhost:8001",
    "external_agent_available": true,
    "vllm_available": true,
    "fallback_enabled": true
}
```

---

## Transcribe 엔드포인트 통합

### AI Agent 포함 단일 파일 처리

```bash
curl -X POST "http://localhost:8003/transcribe" \
-F "file_path=/app/audio/samples/test.wav" \
-F "language=ko" \
-F "privacy_removal=true" \
-F "classification=true" \
-F "ai_agent=true"
```

**Response:**
```json
{
    "success": true,
    "text": "안녕하세요, 제품 구매 문의입니다.",
    "language": "ko",
    "backend": "faster-whisper",
    "privacy_removal": {
        "privacy_exist": "N",
        "exist_reason": "",
        "text": "안녕하세요, 제품 구매 문의입니다."
    },
    "classification": {
        "code": "CLASS_PRE_SALES",
        "category": "사전판매",
        "confidence": 92.3,
        "reason": "제품 구매 의사 표현"
    },
    "agent_response": "AI Agent 응답...",
    "agent_type": "external",
    "chat_thread_id": null,
    "processing_steps": {
        "stt": true,
        "privacy_removal": true,
        "classification": true,
        "ai_agent": true
    },
    "processing_time_seconds": 12.5,
    "memory_info": {...},
    "performance": {...}
}
```

---

## 설정

### 환경 변수

```bash
# AI Agent URL (설정되지 않으면 Fallback 사용)
export AGENT_URL="http://ai-agent-server:5000"

# vLLM Fallback
export VLLM_BASE_URL="http://localhost:8001"
export VLLM_MODEL="Qwen3-30B-A3B-Thinking-2507-FP8"

# STT Device
export STT_DEVICE="cuda"  # or "cpu"
export STT_COMPUTE_TYPE="float16"  # or "float32"
```

### Docker Compose

```yaml
services:
  stt-engine:
    image: stt-engine:latest
    environment:
      AGENT_URL: "http://ai-agent:5000"
      VLLM_BASE_URL: "http://vllm:8001"
      VLLM_MODEL: "Qwen3-30B-A3B-Thinking-2507-FP8"
      STT_DEVICE: "cuda"
    ports:
      - "8003:8003"
    depends_on:
      - vllm
      - ai-agent

  vllm:
    image: vllm/vllm-openai:latest
    environment:
      VLLM_ATTENTION_BACKEND: "xformers"
    ports:
      - "8001:8000"

  ai-agent:
    # 외부 AI Agent 서비스
    image: your-ai-agent:latest
    ports:
      - "5000:5000"
```

---

## Fallback 순서

### 정상 흐름

```
1. 외부 Agent (설정된 경우)
   ↓
   ✅ 성공 → 응답 반환
   ❌ 실패
   ↓
2. vLLM Fallback
   ↓
   ✅ 성공 → 응답 반환
   ❌ 실패 (또는 비활성화)
   ↓
3. Dummy Agent (테스트용)
   ↓
   ✅ 항상 성공 (더미 응답)
```

### 각 단계별 로그

```
[AIAgent] 외부 Agent 시도: http://ai-agent-server:5000
[AIAgent] 외부 Agent 응답 수신
✅ agent_type: "external"

[AIAgent] 외부 Agent 실패: Connection timeout
[AIAgent] vLLM Fallback 시도: http://localhost:8001
[AIAgent] ✅ vLLM Fallback 응답 수신
✅ agent_type: "vllm"

[AIAgent] vLLM Fallback 실패: API timeout
[AIAgent] Dummy Agent로 처리
[AIAgent] Dummy Agent로 응답 생성
✅ agent_type: "dummy"
```

---

## 외부 AI Agent API 호출 형식

외부 AI Agent가 구현해야 할 API 형식:

### 요청 (`POST /api/chat` 또는 설정된 URL)

```json
{
    "use_streaming": false,
    "chat_thread_id": "thread_123",
    "parameters": {
        "user_query": "정제된 STT 텍스트"
    }
}
```

### 응답

```json
{
    "response": "AI Agent의 응답 텍스트",
    "chat_thread_id": "thread_123",
    "additional_data": {}
}
```

---

## vLLM Fallback

외부 Agent를 사용할 수 없거나 실패할 경우 vLLM을 Fallback으로 사용합니다.

### vLLM 설치 및 실행

```bash
# 1. vLLM 설치
pip install vllm

# 2. 모델 다운로드
python -m vllm.model_loader Qwen3-30B-A3B-Thinking-2507-FP8

# 3. vLLM 서버 실행
python -m vllm.entrypoints.openai.api_server \
    --model Qwen3-30B-A3B-Thinking-2507-FP8 \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.9 \
    --port 8001
```

### Docker로 실행

```bash
docker run --gpus all -p 8001:8000 \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    vllm/vllm-openai:latest \
    --model Qwen3-30B-A3B-Thinking-2507-FP8 \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.9
```

---

## Dummy Agent

테스트 환경에서 외부 Agent 없이 동작시키기 위한 더미 응답입니다.

**특징:**
- ✅ 입력 텍스트 분석하여 키워드 추출
- ✅ 키워드 기반 더미 응답 생성
- ✅ 항상 성공 (테스트용)
- ✅ 간단한 구조로 빠른 응답

**예시 응답:**

```
[AI Agent Dummy Response]

귀하의 문의 내용(구매 관련, 기술 지원)에 대해 다음과 같이 안내드립니다:

1. 현황 파악:
   - 제공하신 텍스트를 분석했습니다.
   - 주요 키워드: 구매 관련, 기술 지원

2. 권장 사항:
   - 더 상세한 정보가 필요하신 경우 추가 상담을 권장드립니다.
   - 관련 부서로 연결하여 신속하게 처리해드리겠습니다.

3. 다음 단계:
   - 담당자가 곧 연락드리겠습니다.
   - 추가 질문이 있으시면 언제든 문의해주세요.

---
This is a dummy AI agent response for testing purposes.
The actual external agent will be integrated in the production environment.
```

---

## 처리 흐름

### 1. STT 결과 생성
```
입력 음성 파일
    ↓
STT 처리 (faster-whisper/transformers)
    ↓
원본 텍스트: "개인정보 포함된 텍스트"
```

### 2. Privacy Removal (선택)
```
원본 텍스트
    ↓
Privacy Removal (vLLM)
    ↓
정제된 텍스트: "개인정보 마스킹된 텍스트"
```

### 3. Classification (선택)
```
정제된 텍스트
    ↓
Classification (vLLM)
    ↓
분류 결과: CLASS_PRE_SALES, 신뢰도 92.3%
```

### 4. AI Agent 처리 (선택)
```
정제된 텍스트 + Classification 정보
    ↓
AI Agent 호출 (External/vLLM/Dummy)
    ↓
Agent 응답: "상담원 안내 메시지"
```

---

## 에러 처리

### 타임아웃 감지

```python
timeout: int = 30  # 초 단위

# 각 단계별 타임아웃
- 외부 Agent: 30초
- vLLM: 30초
- Dummy: 1초 (즉시)
```

### 자동 Fallback

```python
try:
    result = await call_external_agent()
    if result['success']:
        return result
except TimeoutError:
    # Fallback to vLLM
    result = await call_vllm_agent()
except Exception:
    # Fallback to Dummy
    result = call_dummy_agent()
```

### 에러 로깅

```
[AIAgent] 외부 Agent 시도
[AIAgent] Agent API 타임아웃
[AIAgent] 외부 Agent 호출 오류: TimeoutError: ...
[AIAgent] vLLM Fallback 시도
[AIAgent] ✅ vLLM Fallback 응답 수신
```

---

## 테스트

### 1. Dummy Agent 테스트

```bash
curl -X POST "http://localhost:8003/ai-agent/dummy" \
-H "Content-Type: application/json" \
-d '{
    "user_query": "제품 구매 문의",
    "chat_thread_id": null
}'
```

### 2. 헬스 체크

```bash
curl "http://localhost:8003/ai-agent/health"
```

### 3. Full Flow 테스트

```bash
curl -X POST "http://localhost:8003/transcribe" \
-F "file_path=/app/audio/samples/test.wav" \
-F "privacy_removal=true" \
-F "classification=true" \
-F "ai_agent=true"
```

### 4. 외부 Agent 시뮬레이션 (로컬 테스트)

```python
# test_agent.py
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.post("/api/chat")
async def chat(request: dict):
    return {
        "response": f"Echo: {request['parameters']['user_query']}",
        "chat_thread_id": request.get('chat_thread_id')
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
```

실행:
```bash
python test_agent.py
export AGENT_URL="http://localhost:5000/api/chat"
```

---

## 성능 최적화

### 병렬 처리

```python
# Classification + AI Agent 동시 처리 가능
results = await asyncio.gather(
    perform_classification(text),
    perform_ai_agent(text)
)
```

### 캐싱

```python
# 동일 쿼리에 대한 캐싱 (향후)
@cache(ttl=3600)
async def process_with_agent(query: str):
    ...
```

### 배치 처리

```python
# 여러 파일 동시 처리
results = await asyncio.gather(*[
    process_file(f) for f in files
])
```

---

## 추가 개선사항 (향후)

- [ ] Agent 응답 스트리밍
- [ ] 대화 히스토리 관리 (chat_thread_id 유지)
- [ ] Agent 응답 캐싱
- [ ] Circuit Breaker 패턴 (연속 실패 시 자동 Fallback)
- [ ] Agent 성능 모니터링
- [ ] 사용자 정의 Fallback 체인
- [ ] WebSocket 기반 실시간 처리

---

**버전:** 1.0
**상태:** 배포 준비 완료
**마지막 업데이트:** 2025년 2월 20일
