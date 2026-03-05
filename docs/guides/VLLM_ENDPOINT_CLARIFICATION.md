# vLLM 엔드포인트 환경변수 정리

## ⚠️ 혼동되는 부분: VLLM_QWEN_API_BASE vs VLLM_BASE_URL

현재 코드에 두 개의 환경변수가 중복되어 있어 혼동을 야기합니다. 정확히 어디서 어떻게 사용되는지 정리했습니다.

---

## 📊 환경변수 사용처

| 환경변수 | 값 | 사용처 | 용도 |
|---------|-----|--------|------|
| **VLLM_QWEN_API_BASE** | `http://localhost:8001/v1` | Privacy Removal (QwenClient) | OpenAI SDK base_url |
| **VLLM_BASE_URL** | `http://localhost:8001/v1/chat/completions` | Element Detection, Classification | 직접 HTTP 요청 |

---

## 🔍 정확한 사용 위치

### 1️⃣ Privacy Removal (privacy_llm_type="vllm")

**파일**: `api_server/services/privacy_remover.py:300-320`

```python
class QwenClient:
    def __init__(self, model_name: str):
        load_dotenv()
        try:
            import openai
            # ✅ VLLM_QWEN_API_BASE 사용 (우선순위)
            api_base = os.getenv("VLLM_QWEN_API_BASE") or os.getenv("OPENAI_API_BASE") or "http://localhost:8001/v1"
            
            # OpenAI SDK가 자동으로 /v1/chat/completions 추가
            if not api_base.endswith('/v1'):
                if api_base.endswith('/'):
                    api_base = api_base + 'v1'
                else:
                    api_base = api_base + '/v1'
            
            # OpenAI SDK 초기화 (base_url 자동 추가)
            self.client = openai.OpenAI(api_key=api_key, base_url=api_base)
            self.model_name = model_name
```

**현행 설정값**:
- `VLLM_QWEN_API_BASE = "http://localhost:8001/v1"` (env에서 읽음)
- 또는 기본값: `"http://localhost:8001/v1"`
- OpenAI SDK가 자동으로 `/v1/chat/completions`를 추가함
- **최종 호출 URL**: `http://localhost:8001/v1/chat/completions`

---

### 2️⃣ Element Detection (ai_agent 또는 element_detection)

**파일**: `api_server/services/ai_agent_service.py:34-55`

```python
class AIAgentService:
    def __init__(self, vllm_base_url: Optional[str] = None, ...):
        # ✅ VLLM_BASE_URL 사용 (우선순위, 아니면 파라미터, 아니면 기본값)
        self.vllm_base_url = vllm_base_url or os.getenv('VLLM_BASE_URL', 'http://localhost:8001')
        # 기본값 주의: 파라미터/env가 없으면 'http://localhost:8001'만 설정됨
        
        logger.info(f"  vLLM Base URL: {self.vllm_base_url}")
```

**호출 부분** (ai_agent_service.py:251-260):
```python
logger.debug(f"[AIAgent] vLLM Fallback 요청 전송: {self.vllm_base_url}")
response = requests.post(
    f"{self.vllm_base_url}/v1/chat/completions",  # ✅ /v1/chat/completions 추가
    json=payload,
    timeout=60
)
```

**현행 설정값**:
- 초기화: `os.getenv('VLLM_BASE_URL', 'http://localhost:8001')` 
- env가 없으면: `'http://localhost:8001'` (API 없음!)
- **최종 호출 URL**: `http://localhost:8001/v1/chat/completions`

---

### 3️⃣ Classification (classification=true)

**파일**: `api_server/services/classification_service.py:36-60`

```python
class ClassificationService:
    def __init__(self, vllm_base_url: Optional[str] = None, ...):
        # ✅ VLLM_BASE_URL 사용 (element detection과 동일)
        self.vllm_base_url = vllm_base_url or os.getenv('VLLM_BASE_URL', 'http://localhost:8001')
```

**호출 부분** (classification_service.py:232-240):
```python
logger.debug(f"[ClassificationService] vLLM 호출: {self.vllm_base_url}/v1/chat/completions")
response = requests.post(
    f"{self.vllm_base_url}/v1/chat/completions",
    json=payload,
    timeout=60
)
```

**현행 설정값**:
- env `VLLM_BASE_URL` 사용 (또는 기본값 'http://localhost:8001')
- **최종 호출 URL**: `http://localhost:8001/v1/chat/completions`

---

## ⚙️ 초기화 시점

### API 서버 시작 (api_server/app.py:570-600)

```python
@app.get("/health")
async def health_check():
    vllm_base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1/chat/completions")  # ✅ 전체 경로
    
    # Element Detection 초기화
    ai_agent_service = AIAgentService(
        vllm_base_url=vllm_base_url  # ✅ 파라미터로 전달
    )
    
    # Classification 초기화
    classification_service = ClassificationService(
        vllm_base_url=vllm_base_url  # ✅ 파라미터로 전달
    )
```

---

## 🚨 현재의 문제점

### 문제 1: 환경변수 혼동

| 경우 | 설정된 값 | 실제 호출 |
|------|---------|---------|
| env 없음 | - | ❌ `http://localhost:8001/v1/chat/completions` (Privacy Removal만 가능) |
| `VLLM_QWEN_API_BASE` 설정 | `http://localhost:8001/v1` | ✅ Privacy Removal OK |
| `VLLM_BASE_URL` 설정 | `http://localhost:8001/v1/chat/completions` | ✅ Element Detection, Classification OK |
| 둘 다 설정 | 위의 조합 | ⚠️ 중복, 혼동 야기 |

### 문제 2: 기본값 불일치

**Privacy Removal**:
```python
api_base = os.getenv("VLLM_QWEN_API_BASE") or "http://localhost:8001/v1"  # ✅ 전체 경로 포함
```

**Element Detection**:
```python
self.vllm_base_url = os.getenv('VLLM_BASE_URL', 'http://localhost:8001')  # ❌ API 경로 없음!
# 최종: http://localhost:8001/v1/chat/completions (코드에서 추가)
```

---

## ✅ 권장 정리안

### 단일 환경변수로 통일: VLLM_BASE_URL

```bash
# ✅ 권장 (단일 환경변수)
export VLLM_BASE_URL=http://localhost:8001/v1/chat/completions

# Privacy Removal (QwenClient)
api_base = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1/chat/completions")
if api_base.endswith('/chat/completions'):
    api_base = api_base.replace('/chat/completions', '')  # /v1만 남김
self.client = openai.OpenAI(api_key=api_key, base_url=api_base)

# Element Detection, Classification
vllm_base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1/chat/completions")
response = requests.post(f"{vllm_base_url}", ...)
```

---

## 📝 현행 설정값 정리

### 🔴 현재 (혼동 상태)

**Privacy Removal**:
- 환경변수: `VLLM_QWEN_API_BASE` (없으면 `OPENAI_API_BASE`, 없으면 기본값)
- 기본값: `"http://localhost:8001/v1"`
- 실제 호출: `"http://localhost:8001/v1/chat/completions"` (OpenAI SDK가 추가)

**Element Detection**:
- 환경변수: `VLLM_BASE_URL` (없으면 기본값)
- 기본값: `'http://localhost:8001'` (❌ API 경로 없음)
- 실제 호출: `"http://localhost:8001/v1/chat/completions"` (코드에서 추가)

**Classification**:
- 환경변수: `VLLM_BASE_URL` (없으면 기본값)
- 기본값: `'http://localhost:8001'` (❌ API 경로 없음)
- 실제 호출: `"http://localhost:8001/v1/chat/completions"` (코드에서 추가)

---

## 🎯 명확히 해야할 점

### Q1: privacy_llm_type="vllm"일 때 어느 환경변수를 쓰는가?

**A**: `VLLM_QWEN_API_BASE`를 사용합니다. 
- Privacy Removal은 OpenAI SDK를 사용하므로 base_url이 필요
- `base_url = "http://localhost:8001/v1"` (SDK가 `/chat/completions` 추가)

### Q2: element_detection과 privacy_removal에서 같은 vLLM 서버를 쓰는가?

**A**: 예, 같은 서버입니다 (http://localhost:8001).
- 하지만 설정 방식이 다름:
  - Privacy Removal: OpenAI SDK 사용 → `base_url="/v1"` 전달
  - Element Detection: requests 직접 사용 → 전체 URL 전달

### Q3: 모델명이 별도 변수로 필요한가?

**A**: 아닙니다. 불필요합니다.
- vLLM은 URL만으로 충분
- 모델명은 이미 vLLM 서버에 로드되어 있음
- 중복된 설정이 혼동을 야기

---

## 🔧 정리 방안

1. **VLLM_QWEN_API_BASE 제거** → VLLM_BASE_URL로 통일
2. **Privacy Removal 코드 변경**:
   ```python
   api_base = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1/chat/completions")
   if api_base.endswith('/chat/completions'):
       api_base = api_base[:-len('/chat/completions')]  # /v1만 남김
   ```
3. **기본값 명시**:
   - 모든 곳에서: `"http://localhost:8001/v1/chat/completions"`
   - Privacy Removal에서는 `/chat/completions` 제거 후 사용

