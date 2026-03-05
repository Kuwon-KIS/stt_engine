# vLLM 환경변수 & 호출 정리

> **목적**: VLLM_QWEN_API_BASE vs VLLM_BASE_URL 사용 차이 명확화 및 현행 값 기록

---

## 🎯 핵심 정리

### 두 가지 환경변수, 같은 서버, 다른 용도

| 변수 | 목적 | 사용 기술 | 설정값 | 사용 모듈 |
|------|------|---------|--------|---------|
| **`VLLM_QWEN_API_BASE`** | Privacy Removal (OpenAI SDK 방식) | OpenAI SDK (`openai` 패키지) | `http://localhost:8001/v1` | `privacy_remover.py` |
| **`VLLM_BASE_URL`** | Element Detection, Classification | Direct HTTP (`requests`) | `http://localhost:8001` | `classification_service.py`, `ai_agent_service.py` |

**결론**: 같은 vLLM 서버(`:8001`)를 가리키지만, **OpenAI SDK 방식** vs **HTTP 직접 호출** 방식에 따라 변수를 분리

---

## 📍 Privacy Removal 호출 (VLLM_QWEN_API_BASE)

### 변수 정의

**파일**: `api_server/services/privacy_remover.py:304`

```python
class QwenClient:
    def __init__(self, model_name: str):
        api_key = os.getenv("VLLM_QWEN_API_KEY") or os.getenv("OPENAI_API_KEY") or "dummy"
        api_base = os.getenv("VLLM_QWEN_API_BASE") or os.getenv("OPENAI_API_BASE") or "http://localhost:8001/v1"
        
        # ✅ OpenAI SDK 사용 (base_url으로 vLLM 가리킴)
        self.client = openai.OpenAI(api_key=api_key, base_url=api_base)
        self.model_name = model_name
```

### 호출 흐름

```
Web UI (upload.html): privacy_removal=True
    ↓
stt_service: "true" (FormData)
    ↓
API Server: privacy_removal="true" → True (boolean)
    ↓
perform_privacy_removal(llm_type="vllm", vllm_model_name="/model/qwen30_thinking_2507")
    ↓
LLMClientFactory.create_client("Qwen...") → QwenClient(model_name)
    ↓
QwenClient.__init__():
    ├─ api_base = os.getenv("VLLM_QWEN_API_BASE") or "http://localhost:8001/v1"  ✅
    ├─ self.client = openai.OpenAI(api_key="dummy", base_url=api_base)
    └─ # OpenAI SDK이 자동으로 /v1/chat/completions 엔드포인트 생성
    ↓
await QwenClient.generate_response():
    ├─ model = "/model/qwen30_thinking_2507"
    ├─ self.client.chat.completions.create(model=model, ...)
    │  # OpenAI SDK이 자동으로 다음 URL 호출:
    │  # http://localhost:8001/v1/chat/completions
    └─ 응답 반환
```

### 환경변수 설정

**Docker Compose**:
```yaml
services:
  stt-engine:
    environment:
      - VLLM_QWEN_API_BASE=http://localhost:8001/v1  # ✅ /v1까지만 (OpenAI SDK base_url용)
      - VLLM_QWEN_API_KEY=dummy  # ✅ 로컬 vLLM용
```

**우선순위**:
1. `VLLM_QWEN_API_BASE` (Privacy Removal 전용, OpenAI SDK 호환)
2. `OPENAI_API_BASE` (fallback, OpenAI 호환)
3. 기본값: `http://localhost:8001/v1`

---

## 📍 Element Detection & Classification 호출 (VLLM_BASE_URL)

### 변수 정의

**파일**: `api_server/services/classification_service.py:46`

```python
class ClassificationService:
    def __init__(self, vllm_base_url: Optional[str] = None, ...):
        # ✅ 환경변수에서 읽음 (파라미터로도 받을 수 있음)
        self.vllm_base_url = vllm_base_url or os.getenv('VLLM_BASE_URL', 'http://localhost:8001')
        self.vllm_model = vllm_model or os.getenv('VLLM_MODEL', 'Qwen3-30B-A3B-Thinking-2507-FP8')
```

**파일**: `api_server/services/ai_agent_service.py:48`

```python
class AIAgentService:
    def __init__(self, vllm_base_url: Optional[str] = None, ...):
        # ✅ 환경변수에서 읽음 (파라미터로도 받을 수 있음)
        self.vllm_base_url = vllm_base_url or os.getenv('VLLM_BASE_URL', 'http://localhost:8001')
        self.vllm_model = vllm_model or os.getenv('VLLM_MODEL', 'Qwen3-30B-A3B-Thinking-2507-FP8')
```

### 호출 흐름

**Classification**:
```
API Server: POST /transcribe
    ├─ classification=True
    ↓
perform_classification(llm_type="vllm", ...)
    ↓
ClassificationService(vllm_base_url, vllm_model)
    ├─ self.vllm_base_url = os.getenv('VLLM_BASE_URL', 'http://localhost:8001')  ✅
    ├─ self.vllm_model = os.getenv('VLLM_MODEL', 'Qwen3-30B-A3B-Thinking-2507-FP8')
    └─
    ↓
await classify_call():
    ├─ requests.post(
    │   f"{self.vllm_base_url}/v1/chat/completions",  ⚠️ 경로 직접 추가
    │   json={...}
    │ )
    └─ 응답 파싱 (JSON)
```

**Element Detection (AI Agent Fallback)**:
```
API Server: POST /transcribe
    ├─ ai_agent=True
    ├─ agent_url="" (미설정)
    ↓
perform_ai_agent(agent_url="", ...)
    ↓
AIAgentService(agent_url="", vllm_base_url, vllm_model)
    ├─ self.agent_url = "" (미설정)
    ├─ self.vllm_base_url = os.getenv('VLLM_BASE_URL', 'http://localhost:8001')  ✅
    └─ self.vllm_model = os.getenv('VLLM_MODEL', 'Qwen3-30B-A3B-Thinking-2507-FP8')
    ↓
await detect_elements():
    ├─ if not self.agent_url:  # agent_url 미설정
    │   ├─ logger.debug(f"[AIAgent] vLLM Fallback 요청")
    │   ├─ requests.post(
    │   │   f"{self.vllm_base_url}/v1/chat/completions",  ⚠️ 경로 직접 추가
    │   │   json={...}
    │   │ )
    │   └─ 응답 파싱 (JSON)
    └─
```

### 환경변수 설정

**Docker Compose** (api_server/app.py:582):
```yaml
services:
  stt-engine:
    environment:
      - VLLM_BASE_URL=http://localhost:8001  # ✅ 경로 제외 (코드에서 추가)
      - VLLM_MODEL=Qwen3-30B-A3B-Thinking-2507-FP8
```

**우선순위**:
1. 파라미터 `vllm_base_url` (함수 인자로 전달)
2. 환경변수 `VLLM_BASE_URL`
3. 기본값: `http://localhost:8001`

---

## 🔄 현행 호출값 정리

### Privacy Removal (VLLM_QWEN_API_BASE 사용)

| 항목 | 값 | 코드 위치 |
|------|------|---------|
| **환경변수** | `VLLM_QWEN_API_BASE=http://localhost:8001/v1` | docker-compose.yml |
| **파일 경로** | `/app/data/uploads/...` | analysis_service.py:657 |
| **privacy_removal** | `True` (Python boolean) | analysis_service.py:661 |
| **llm_type** | `"vllm"` (기본값) | transcribe_endpoint.py:232 |
| **vllm_model_name** | `/model/qwen30_thinking_2507` | analysis_service.py:667 |
| **temperature** | `0.3` | transcribe_endpoint.py:272 |
| **max_tokens** | `32768` | transcribe_endpoint.py:271 |
| **prompt_type** | `privacy_remover_default_v6` | transcribe_endpoint.py:268 |
| **SDK** | `openai.OpenAI` (base_url로 vLLM 가리킴) | privacy_remover.py:318 |
| **최종 URL** | `http://localhost:8001/v1/chat/completions` | SDK 자동 생성 |
| **Fallback** | Regex (JSON 파싱 실패 시) | privacy_remover.py:630-650 |

**호출 경로**:
```
openai.OpenAI(api_key="dummy", base_url="http://localhost:8001/v1")
    ↓
self.client.chat.completions.create(
    model="/model/qwen30_thinking_2507",
    messages=[...],
    ...
)
    ↓
OpenAI SDK 자동으로 엔드포인트 생성:
http://localhost:8001/v1/chat/completions
```

---

### Element Detection & Classification (VLLM_BASE_URL 사용)

| 항목 | 값 | 코드 위치 |
|------|------|---------|
| **환경변수** | `VLLM_BASE_URL=http://localhost:8001` | docker-compose.yml / api_server/app.py:582 |
| **VLLM_MODEL** | `Qwen3-30B-A3B-Thinking-2507-FP8` | env 또는 기본값 |
| **서비스** | `ClassificationService`, `AIAgentService` | classification_service.py, ai_agent_service.py |
| **HTTP 라이브러리** | `requests` (직접 호출) | classification_service.py:236 |
| **최종 URL** | `http://localhost:8001/v1/chat/completions` | 코드에서 경로 추가 |
| **Fallback** | Dummy response 또는 원본 반환 | ai_agent_service.py:260 |

**호출 경로**:
```
ClassificationService(vllm_base_url="http://localhost:8001", vllm_model="Qwen...")
    ↓
await classify_call():
    requests.post(
        f"{self.vllm_base_url}/v1/chat/completions",  # ⚠️ 경로 직접 추가
        json={
            "model": "Qwen3-30B-A3B-Thinking-2507-FP8",
            "messages": [...],
            ...
        }
    )
    ↓
http://localhost:8001/v1/chat/completions 호출
```

---

## ⚠️ 주의사항

### 1. 경로 포함 여부

| 변수 | 경로 포함 여부 | 예시 |
|------|-------------|------|
| **`VLLM_QWEN_API_BASE`** | ✅ **포함** (`/v1`, OpenAI SDK용) | `http://localhost:8001/v1` |
| **`VLLM_BASE_URL`** | ❌ **제외** | `http://localhost:8001` |

**이유**:
- `VLLM_QWEN_API_BASE`: OpenAI SDK의 `base_url` 파라미터로 사용 → SDK가 `/chat/completions` 추가
- `VLLM_BASE_URL`: 직접 HTTP 요청 → 코드에서 `/v1/chat/completions` 경로 직접 추가

### 2. 모델명 설정

**Privacy Removal** (QwenClient):
```python
# 고정값, 환경변수로 관리하지 않음
model_name = "/model/qwen30_thinking_2507"
```

**Classification / Element Detection**:
```python
# 환경변수로 관리
vllm_model = os.getenv('VLLM_MODEL', 'Qwen3-30B-A3B-Thinking-2507-FP8')
```

### 3. 인증 (API Key)

**Privacy Removal**:
```python
api_key = os.getenv("QWEN_API_KEY") or os.getenv("OPENAI_API_KEY") or "dummy"
# 로컬 vLLM은 "dummy"로 진행
```

**Classification / Element Detection**:
```python
# 인증 없음, requests로 직접 호출
# Authorization 헤더 불필요
```

---

## ✅ 환경변수 체크리스트

### Docker Compose 설정 (현행)

```yaml
services:
  stt-engine:
    environment:
      # Privacy Removal (OpenAI SDK)
      - VLLM_QWEN_API_BASE=http://localhost:8001/v1  ✅ /v1 포함
      - VLLM_QWEN_API_KEY=dummy  ✅ 로컬 vLLM용
      
      # Element Detection, Classification (HTTP 직접)
      - VLLM_BASE_URL=http://localhost:8001  ✅ 경로 제외
      - VLLM_MODEL=Qwen3-30B-A3B-Thinking-2507-FP8  ✅
```

### 검증 방법

```bash
# Privacy Removal 테스트
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "/model/qwen30_thinking_2507", "messages": [...]}'

# Element Detection 테스트
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen3-30B-A3B-Thinking-2507-FP8", "messages": [...]}'
```

---

## 📝 요약

```
같은 vLLM 서버 (http://localhost:8001)를 사용하지만:

1️⃣ Privacy Removal (OpenAI SDK 방식)
   - 환경변수: VLLM_QWEN_API_BASE=http://localhost:8001/v1
   - API Key: VLLM_QWEN_API_KEY=dummy
   - 경로 포함: ✅ /v1
   - SDK: openai.OpenAI(base_url=api_base)
   - 최종 호출: http://localhost:8001/v1/chat/completions

2️⃣ Element Detection (HTTP 직접 호출)
   - 환경변수: VLLM_BASE_URL=http://localhost:8001
   - 경로 제외: ❌ 경로 없음
   - 라이브러리: requests.post(f"{base_url}/v1/chat/completions")
   - 최종 호출: http://localhost:8001/v1/chat/completions
```
