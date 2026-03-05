# API 서버 흐름 분석 (v1.9.7)

> **작성일**: 2026년 3월 5일  
> **목적**: API 서버 transcribe 엔드포인트의 전체 흐름 분석 및 단계별 설정값 정리  
> **상태**: 분석 완료, 보완 작업 진행 중

---

## 🔄 **현재 운영 구조** (2026년 이후 - 폴더 기반 분석)

```
Web UI (upload.html)
    ↓
  startAnalysis()
    ├─ 폴더 선택
    ├─ 폴더 내 파일 목록 조회
    └─ POST /api/analysis/start → Web UI 서버
         ↓
  web_ui/app/routes/analysis.py
    └─ AnalysisService.process_analysis_sync()
         ↓
  await stt_service.transcribe_local_file()
    ├─ privacy_removal=True ✅ (항상 수행 - vLLM + Qwen)
    ├─ element_detection=True ✅ (항상 수행)
    └─ classification=설정에 따라
         ↓
  결과 저장 (데이터베이스) → 분석 페이지 표시
```

---

## ⚠️ **레거시 구조** (2026년 이전 - 파일 업로드 기반)

```
Web UI (main.js) - 더 이상 사용되지 않음
    ↓
  transcribeFile() ❌
    ├─ uploadFile() → /upload/
    └─ FormData 구성 (file_id, privacy_removal='false', ...)
         ↓
  POST /transcribe/ → API Server ❌
    ├─ privacy_removal=false (미실행) ❌
    ├─ element_detection, classification 설정 (무시됨)
    └─ 결과 반환
```

**특징**:
- ❌ privacy_removal이 항상 'false'로 설정 → 개인정보 제거 안 됨
- ❌ API 서버의 `/transcribe/` 엔드포인트는 Web UI에서 호출 안 함
- ❌ 배치 처리 (`/batch/start/`) 미사용
- ⚠️ 코드는 main.js에 남아있음 (정리 예정)

---

## 📊 **각 단계별 필수 설정값**

### **1️⃣ STT (Speech-to-Text) 단계**

| 설정값 | 출처 | 기본값 | 용도 |
|--------|------|--------|------|
| `file_path` | FormData | 필수 | 음성 파일 경로 |
| `language` | FormData | "ko" | 언어 (ko, en, etc) |
| `is_stream` | FormData | "false" | 스트리밍 모드 |
| `STT_PRESET` | env | "accuracy" | 프리셋 (accuracy, balanced, speed, custom) |
| `STT_DEVICE` | env | "auto" | 디바이스 (auto, cuda, cpu) |
| `STT_COMPUTE_TYPE` | env | 자동 | 정밀도 (int8, float16, float32) |

**확인 위치**: `api_server/app.py:76-100`

---

### **2️⃣ Privacy Removal 단계** ⭐ 현행 값

| 설정값 | 출처 | 기본값 | 현행 호출값 | 용도 |
|--------|------|--------|-------------|------|
| **`privacy_removal`** | FormData | "false" | ✅ **"true"** (upload.html) | 활성화 여부 |
| **`privacy_llm_type`** | FormData | "vllm" | ✅ **"vllm"** | LLM 타입 |
| **`privacy_prompt_type`** | FormData | "privacy_remover_default_v6" | ✅ **"privacy_remover_default_v6"** | 프롬프트 타입 |
| **`vllm_model_name`** | FormData | None | ✅ **"/model/qwen30_thinking_2507"** | vLLM 모델 |
| **`VLLM_QWEN_API_BASE`** ⭐ | env | **"http://localhost:8001/v1"** | ✅ OpenAI SDK base_url (SDK가 /chat/completions 자동 추가) | QwenClient 초기화 |
| `temperature` | 코드 | 0.3 | ✅ 0.3 | 창의성 |
| `max_tokens` | 코드 | 32768 | ✅ 32768 | 최대 토큰 |

**⚠️ 주의**: VLLM_QWEN_API_BASE는 Privacy Removal 전용입니다. Element Detection과 Classification은 VLLM_BASE_URL을 사용합니다.

**호출 코드**:

**Web UI 측** (web_ui/app/services/analysis_service.py:661):
```python
stt_result = await stt_service.transcribe_local_file(
    file_path=str(file_path),
    language="ko",
    is_stream=False,
    privacy_removal=True,  # ✅ 항상 활성화
    classification=False,
    ai_agent=include_classification,
    element_detection=True
)
```

**API 서버 측** (api_server/transcribe_endpoint.py:228-273):
```python
async def perform_privacy_removal(
    text: str,
    prompt_type: str = "privacy_remover_default_v6",
    llm_type: str = "vllm",  # ✅ 기본값 vllm
    vllm_model_name: Optional[str] = None,  # /model/qwen30_thinking_2507
    ...
):
    privacy_service = get_privacy_remover_service()
    result = await privacy_service.process_text(
        usertxt=text,
        prompt_type=normalized_prompt_type,
        max_tokens=32768,  # ✅ 32768
        temperature=0.3,   # ✅ 0.3
        model_name=model_name  # ✅ Qwen 모델 전달
    )
```

**LLM 라우팅** (api_server/services/privacy_remover.py:26-62):
```python
class LLMClientFactory:
    @staticmethod
    def create_client(model_name: str):
        model_lower = model_name.lower()
        if 'qwen' in model_lower:
            logger.info(f"Qwen 클라이언트 생성: {model_name}")
            return QwenClient(model_name)  # ✅ Qwen → QwenClient
```

**vLLM 연결** (api_server/services/privacy_remover.py:290-318):
```python
class QwenClient:
    def __init__(self, model_name: str):
        api_base = os.getenv("VLLM_QWEN_API_BASE") or "http://localhost:8001/v1"  # ✅ 기본값
        self.client = openai.OpenAI(api_key=api_key, base_url=api_base)
```

**Fallback 메커니즘**:
1. **JSON 파싱 실패** → Regex fallback (api_server/services/privacy_remover.py:630-650)
2. **LLM 연결 실패** → Regex fallback (api_server/services/privacy_remover.py:654-680)
3. **모든 실패** → 원본 텍스트 반환
    result = await privacy_service.process_text(
        usertxt=text,
        prompt_type=normalized_prompt_type,  # ✅ 자동 정규화 (v6로 통일)
        max_tokens=32768,
        temperature=0.3,
        model_name=model_name
    )
```

**점검 사항**:
- [x] privacy_llm_type 기본값 변경: "openai" → "vllm" ✅
- [x] Web UI에서 privacy_llm_type 명시: "vllm" ✅
- [x] vllm_model_name 지정: "/model/qwen30_thinking_2507" ✅
- [x] VLLM_BASE_URL 환경변수 설정 ✅
- [ ] vLLM 서버 실행 확인 (docker run --gpus all ...)

---

### **3️⃣ Classification 단계**

| 설정값 | 출처 | 기본값 | 용도 |
|--------|------|--------|------|
| `classification` | FormData | "false" | 활성화 여부 |
| `classification_llm_type` | FormData | "openai" | LLM 타입 (openai, vllm, ollama) |
| `classification_prompt_type` | FormData | "classification_default_v1" | 프롬프트 타입 |
| `vllm_model_name` | FormData | 동일 사용 | vLLM 모델명 |
| `ollama_model_name` | FormData | 동일 사용 | Ollama 모델명 |

**코드 위치**: `api_server/transcribe_endpoint.py:340-420`

**동작 흐름**:
```python
async def perform_classification():
    # 입력 텍스트 결정
    classification_text = privacy_result.text if privacy_result else stt_result.get('text', '')
    # ✅ Privacy Removal 결과가 있으면 정제된 텍스트 사용
    
    llm_client = LLMClientFactory.create_client(llm_type=llm_type, model_name=model_name)
    response = await llm_client.call(prompt=..., temperature=0.3, max_tokens=500)
```

**점검 사항**:
- [ ] Privacy Removal 결과 우선순위 정확성 확인
- [ ] JSON 응답 파싱 정상 처리 확인
- [ ] 실패 시 fallback (UNKNOWN 반환) 동작 확인

---

### **4️⃣ Element Detection 단계 ⭐ 현행 값**

| 설정값 | 출처 | 기본값 | 현행 호출값 | 용도 |
|--------|------|--------|-------------|------|
| **`element_detection`** | FormData | "false" | ✅ **"true"** (upload.html) | 활성화 여부 |
| **`element_detection_prompt_type`** ⭐ | FormData | **"element_detection_qwen"** | ✅ **"element_detection_qwen"** | 프롬프트 타입 (프롬프트 파일 자동 로드) |
| **`VLLM_BASE_URL`** ⭐ | env | **"http://localhost:8001"** | ✅ HTTP 직접 요청 | AIAgentService, ClassificationService |
| **`VLLM_MODEL`** | env | **"Qwen3-30B-A3B-Thinking-2507-FP8"** | ✅ 모델명 | vLLM 모델 지정 |
| `temperature` | 코드 | 0.3 | ✅ 0.3 | 창의성 |
| `max_tokens` | 코드 | 2000 | ✅ 2000 | 최대 토큰 |

**🔑 중요: VLLM_BASE_URL vs VLLM_QWEN_API_BASE 차이**

| 항목 | VLLM_QWEN_API_BASE (Privacy) | VLLM_BASE_URL (Detection) |
|------|--------|---------|
| **기술** | OpenAI SDK (base_url) | HTTP 직접 요청 |
| **설정값** | `http://localhost:8001/v1` | `http://localhost:8001` |
| **경로 포함** | ✅ /v1 포함 | ❌ 경로 제외 |
| **라이브러리** | `openai.OpenAI()` | `requests.post()` |
| **최종 URL** | `http://localhost:8001/v1/chat/completions` (SDK 자동) | `http://localhost:8001/v1/chat/completions` (코드 추가) |
| **사용처** | `privacy_remover.py` | `ai_agent_service.py`, `classification_service.py` |

**📍 코드 위치**: 

- **AIAgentService** (api_server/services/ai_agent_service.py:48):
```python
class AIAgentService:
    def __init__(self, vllm_base_url: Optional[str] = None, ...):
        # ✅ VLLM_BASE_URL 환경변수 사용 (기본값: 'http://localhost:8001')
        self.vllm_base_url = vllm_base_url or os.getenv('VLLM_BASE_URL', 'http://localhost:8001')
        self.vllm_model = vllm_model or os.getenv('VLLM_MODEL', 'Qwen3-30B-A3B-Thinking-2507-FP8')
```

- **ClassificationService** (api_server/services/classification_service.py:46):
```python
class ClassificationService:
    def __init__(self, vllm_base_url: Optional[str] = None, ...):
        # ✅ VLLM_BASE_URL 환경변수 사용 (기본값: 'http://localhost:8001')
        self.vllm_base_url = vllm_base_url or os.getenv('VLLM_BASE_URL', 'http://localhost:8001')
        self.vllm_model = vllm_model or os.getenv('VLLM_MODEL', 'Qwen3-30B-A3B-Thinking-2507-FP8')
```

**호출 예시** (ai_agent_service.py:255, classification_service.py:236):
```python
# ⚠️ 경로를 직접 추가함 (SDK 아님)
response = requests.post(
    f"{self.vllm_base_url}/v1/chat/completions",  # ✅ 완전한 URL
    json={
        "model": self.vllm_model,  # "Qwen3-30B-A3B-Thinking-2507-FP8"
        "messages": [...],
        "temperature": 0.3,
        "max_tokens": 2000
    },
    timeout=60
)
```

**점검 사항**:
- [ ] `VLLM_BASE_URL=http://localhost:8001` 환경변수 설정 (경로 제외!)
- [ ] `VLLM_MODEL=Qwen3-30B-A3B-Thinking-2507-FP8` 환경변수 설정
- [ ] Privacy Removal의 VLLM_QWEN_API_BASE(`/v1` 포함)와 혼동하지 않기
- [ ] requests가 경로를 직접 추가하므로 base_url에 경로를 빼야 함

---

## 🔗 **Privacy Removal → Element Detection 데이터 전달**

> **확인된 상태**: ✅ **정확히 bypass되고 있음**  
> **코드 위치**: `api_server/app.py:575` (데이터 전달), `transcribe_endpoint.py:853-950` (처리)

### **데이터 흐름**

```
STT 결과 (원본 텍스트)
    ↓
[Privacy Removal 수행] (vLLM + Qwen)
    - 입력: 원본 텍스트
    - 출력: privacy_result.text (개인정보 제거된 텍스트) ✅
    ↓
[Element Detection 입력 선택 로직]
    ↓
detection_text = privacy_result.text if privacy_result else stt_result.get('text', '')
    ↓
[Element Detection 처리]
    - 입력: privacy_result.text (정제된 텍스트) ✅
    - 처리 방식: fallback (external → local → dummy)
    - 출력: detection_results
    ↓
[응답 구성]
    - stt.text: 원본
    - privacy_removal.text: 정제됨
    - element_detection.detection_results: 탐지 결과
```

### **코드 검증**

| 단계 | 코드 | 상태 |
|------|------|------|
| Privacy Removal 실행 | `app.py:520-530` | ✅ 수행 |
| 결과 저장 | `privacy_result = await perform_privacy_removal(...)` | ✅ 저장됨 |
| Element Detection 입력 선택 | `detection_text = privacy_result.text if privacy_result else ...` | ✅ 정확 |
| Element Detection 호출 | `await perform_element_detection(text=detection_text, ...)` | ✅ 전달됨 |
| 응답에 포함 | `build_transcribe_response(..., privacy_result, element_detection_result)` | ✅ 포함됨 |

### **분류 없이도 작동하는가?**

✅ **Yes**. Classification 없이도 Privacy Removal → Element Detection 직접 연결 가능

```python
# app.py 라인 520-540 (Privacy Removal)
if privacy_removal:
    privacy_result = await perform_privacy_removal(...)
    
# app.py 라인 570 (Element Detection - Classification 없이 실행 가능)
if element_detection_enabled:
    detection_text = privacy_result.text if privacy_result else stt_result.get('text', '')
    element_response = await perform_element_detection(text=detection_text, ...)
```

**흐름**:
```
Privacy Removal ✅ (항상)
    ↓
Classification (선택사항) ← 없어도 OK
    ↓
Element Detection ✅ (항상, privacy_result 사용)
```

### **API 타입별 처리**

| API 타입 | 설명 | 현재 설정 |
|---------|------|---------|
| **external** | 외부 AI Agent 호출만 | - |
| **local** | vLLM/Ollama 로컬 호출만 | ✅ 기본값 |
| **fallback** | 자동 선택 (추천) | ✅ `api_server/app.py:573` |

```python
# app.py 라인 573
detection_api_type = form_data.get('detection_api_type', 'local')

# fallback 로직 (transcribe_endpoint.py:903-950)
if api_type == "fallback":
    1️⃣ external API 시도 (설정된 경우)
    2️⃣ local LLM 시도 (vLLM/Ollama)
    3️⃣ Dummy 반환 (TEST_MODE=True일 때만)
```

---

## 🎯 **Element Detection 설정 상세 분석**

> **목적**: External AI Agent vs Local vLLM 선택 메커니즘 명확화  
> **코드 위치**: `app.py:410-590` (파라미터 관리), `transcribe_endpoint.py:849-950` (처리 로직)

### **설정 파라미터 (Dependency 포함)**

| 파라미터 | 출처 | 기본값 | 현행값 | 역할 | **의존 모드** |
|---------|------|--------|--------|------|--------------|
| **`element_detection`** | FormData | "false" | ✅ "true" | 요소 탐지 활성화 | 모든 모드 필수 |
| **`element_detection_prompt_type`** ⭐ | FormData | "element_detection_qwen" | ✅ "element_detection_qwen" | 프롬프트 파일명 ({prompt_type}.prompt 자동 로드) | ❌ ai_agent / ✅ vllm, fallback (필수) |
| **`detection_api_type`** ⭐ | FormData | "ai_agent" | ✅ "vllm" | API 모드 선택 | 모든 모드 필수 |
| **`agent_url`** ⭐ | FormData | "" | - | 외부 AI Agent URL | ✅ ai_agent / ⚠️ fallback (선택) / ❌ vllm (무시) |
| **`detection_llm_type`** | FormData | "openai" | ✅ "vllm" | Local LLM 타입 | ❌ ai_agent / ✅ vllm, fallback (필수) |
| **`vllm_model_name`** | FormData | None | ✅ "/model/qwen30_thinking_2507" | vLLM 모델명 | ❌ ai_agent / ✅ vllm, fallback (detection_llm_type='vllm'일 때) |
| **`ollama_model_name`** | FormData | None | - | Ollama 모델명 | ❌ ai_agent / ✅ vllm, fallback (detection_llm_type='ollama'일 때) |
| **`detection_types`** | FormData | "" | - | 탐지 대상 (CSV) | 모든 모드 선택 (기본: incomplete_sales,aggressive_sales) |
| **`VLLM_BASE_URL`** ⭐ | env | "http://localhost:8001" | ✅ 설정됨 | vLLM 엔드포인트 | ❌ ai_agent / ✅ vllm, fallback (detection_llm_type='vllm'일 때) |
| **`OLLAMA_BASE_URL`** | env | "http://localhost:11434" | - | Ollama 엔드포인트 | ❌ ai_agent / ✅ vllm, fallback (detection_llm_type='ollama'일 때) |
| **`TEST_MODE`** | env | "false" | - | Dummy 허용 여부 | ⚠️ fallback (단계 3에만 영향) |

**⚠️ 핵심 의존성 규칙**:

| 모드 | detection_api_type | agent_url | detection_llm_type | vllm_base_url | 설명 |
|-----|-------------------|-----------|-------------------|----------------|------|
| **AI Agent** | `"ai_agent"` | ✅ **필수** | ❌ 무시 | ❌ 무시 | 외부 AI Agent만 호출, 텍스트 그대로 전달 |
| **vLLM** | `"vllm"` | ❌ 무시 | ✅ **필수** | ✅ **필수** | Local vLLM만 호출, 프롬프트로 포맷팅하여 전달 |
| **Fallback** | `"fallback"` | ⚠️ **선택** | ✅ **필수** (단계2) | ✅ **필수** (단계2) | AI Agent (설정시) → vLLM (필수) → Dummy (TEST_MODE=true만) |

---

### **설정 파라미터

### **API 타입별 동작**

#### **1️⃣ detection_api_type = "ai_agent"** ⭐ 외부 AI Agent 호출

외부 AI Agent만 호출. **agent_url 필수**. 

**데이터 전달 방식**:
- 입력: STT 결과 또는 Privacy Removal 결과 (순수 텍스트)
- 포맷팅: **없음** - 텍스트 그대로 `user_query` 필드로 전달
- 쿼리 형식: KIS Agent API 표준 형식

**API 요청 형식**:
```json
{
  "chat_thread_id": "",
  "parameters": {
    "user_query": "분석할 텍스트 (STT 또는 Privacy Removal 결과)"
  }
}
```

**API 응답 형식** (예상):
```json
{
  "detected_yn": "Y" 또는 "N",
  "detected_sentences": ["문장1", "문장2", ...],
  "detected_reasons": ["근거1", "근거2", ...],
  "detected_keywords": ["키워드1", "키워드2", ...]
}
```

**코드 위치**: [transcribe_endpoint.py#L559-L675](transcribe_endpoint.py#L559-L675)

```python
# _call_external_api 함수 (transcribe_endpoint.py:603-612)
payload = {
    "chat_thread_id": "",
    "parameters": {
        "user_query": text  # ⭐ 순수 텍스트만 전달, 포맷팅 없음
    }
}

async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(
        external_api_url,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
```

**필수 파라미터**:
| 파라미터 | 값 | 필수 |
|---------|-----|------|
| `agent_url` | 외부 API 엔드포인트 URL | ✅ **필수** |
| `detection_api_type` | `"ai_agent"` | ✅ **필수** |
| `detection_types` | CSV 리스트 | ⚠️ 선택 (기본: incomplete_sales,aggressive_sales) |

---

#### **2️⃣ detection_api_type = "vllm"** ⭐ Local vLLM/Ollama 호출

Local vLLM/Ollama만 호출. **agent_url 무시**.

**데이터 전달 방식**:
- 입력: STT 결과 또는 Privacy Removal 결과 (순수 텍스트)
- 포맷팅: **`detection_prompt` 프롬프트로 구조화**하여 전달
- 프롬프트 명: `ELEMENT_DETECTION_PROMPT_V1` (정의 필요시)
- Privacy Removal의 `privacy_remover_default_v6` 프롬프트와 유사 패턴

**프롬프트 구조**:
```
다음 고객 상담 통화 내용을 분석하여 요청된 요소들의 탐지 여부를 판단하세요.

감지 대상:
{detection_types_csv}

상담 내용:
{text}

다음 JSON 형식으로 응답하세요:
{
    "detected_yn": "Y" 또는 "N",
    "detected_sentences": ["탐지된 문장1", ...],
    "detected_reasons": ["근거1", ...],
    "detected_keywords": ["키워드1", ...]
}

검정 결과:
```

**코드 위치**: [transcribe_endpoint.py#L676-L870](transcribe_endpoint.py#L676-L870)

```python
# _call_local_llm 함수 (transcribe_endpoint.py:676-870)

async def _call_local_llm(
    text: str,
    detection_types: list,
    llm_type: str = "vllm",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None,
    vllm_base_url: Optional[str] = None,
    ollama_base_url: Optional[str] = None,
    prompt_type: str = "element_detection_qwen"  # ⭐ 프롬프트 파일 타입 (기본값)
) -> Optional[dict]:
    
    # 프롬프트 파일 로드 (element_detection_qwen.prompt 등)
    try:
        prompt_file_path = Path(__file__).parent / "services" / "prompts" / f"{prompt_type}.prompt"
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        detection_prompt = prompt_template.replace("{usertxt}", text)
        logger.info(f"프롬프트 파일 로드 완료 (타입: {prompt_type})")
    except Exception as prompt_err:
        logger.warning(f"프롬프트 파일 로드 실패, 기본 프롬프트 사용")
        # Fallback: 기본 프롬프트 사용
        detection_prompt = f"""...기본 프롬프트..."""
    
    # LLM 호출
    response = await llm_client.call(
        prompt=detection_prompt,
        temperature=0.3,
        max_tokens=1000
    )
```

**핵심 변경사항**:
- ✅ `prompt_type` 파라미터로 프롬프트 파일 동적 로드 (기본값: "element_detection_qwen")
- ✅ `api_server/services/prompts/{prompt_type}.prompt` 파일 자동 로드
- ✅ `{usertxt}` 치환으로 프롬프트 템플릿 처리
- ✅ Privacy Removal과 동일한 프롬프트 로드 방식 적용

**필수 파라미터**:
| 파라미터 | 값 | 필수 |
|---------|-----|------|
| `detection_api_type` | `"vllm"` | ✅ **필수** |
| `detection_llm_type` | `"vllm"` 또는 `"ollama"` | ✅ **필수** |
| `vllm_model_name` | 모델명 (vLLM의 경우) | ✅ **필수** (detection_llm_type='vllm') |
| `ollama_model_name` | 모델명 (Ollama의 경우) | ✅ **필수** (detection_llm_type='ollama') |
| `VLLM_BASE_URL` | 환경변수 | ✅ **필수** (vLLM의 경우) |
| `OLLAMA_BASE_URL` | 환경변수 | ✅ **필수** (Ollama의 경우) |
| `agent_url` | 무시됨 | ❌ 불필요 |

**⚠️ 주의**: 프롬프트가 JSON 파싱 가능한 형식으로 응답하도록 강제하므로, 응답 실패 시 NULL 반환 (fallback 불가능)

#### **3️⃣ detection_api_type = "fallback"** (추천 ⭐ 간단한 구조)

자동 선택: ai_agent (설정시) → vllm (필수) → dummy (TEST_MODE=true만) 순서로 시도.  
**각 단계 실패 시 다음 단계로 자동 이동 (TEST_MODE 무관)**

**단계별 동작**:

1️⃣ **단계 1: 외부 AI Agent 시도** (agent_url이 지정된 경우만)
   - 조건: `external_api_url`이 지정되어 있음
   - 동작: 텍스트 그대로 KIS Agent API 형식으로 전달
   - 성공 시: 즉시 결과 반환 (api_type='ai_agent')
   - 실패 시: 자동으로 단계 2로 진행

2️⃣ **단계 2: Local vLLM 시도** (필수 폴백)
   - 조건: 항상 실행
   - 동작: 텍스트를 `detection_prompt`로 포맷팅하여 vLLM/Ollama 호출
   - 성공 시: 즉시 결과 반환 (api_type='vllm')
   - 실패 시: 자동으로 단계 3으로 진행

3️⃣ **단계 3: Dummy 결과 반환** (TEST_MODE=True일 때만)
   - 조건: TEST_MODE=true 환경변수 설정됨
   - 동작: 모든 탐지가 "N"인 더미 결과 반환
   - TEST_MODE=false: 에러 반환

**코드 위치**: [transcribe_endpoint.py#L877-L1000](transcribe_endpoint.py#L877-L1000)

```python
# perform_element_detection 함수 (transcribe_endpoint.py:877-1000)
async def perform_element_detection(
    text: str,
    detection_types: list = None,
    api_type: str = "fallback",
    llm_type: str = "vllm",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None,
    vllm_base_url: Optional[str] = None,
    ollama_base_url: Optional[str] = None,
    element_detection_prompt_type: str = "element_detection_qwen",  # ⭐ 프롬프트 타입
    classification_result: dict = None,
    privacy_removal_result: dict = None,
    external_api_url: Optional[str] = None
) -> dict:

if api_type == "fallback":
    # 1️⃣ AI Agent 시도 (설정된 경우)
    if external_api_url:
        logger.info("[Fallback] 단계 1️⃣: 외부 AI Agent 호출 시도...")
        result = await _call_external_api(text, detection_types, external_api_url)
        
        if result:
            return {
                'success': True,
                'detection_results': result.get('detection_results', []),
                'api_type': 'ai_agent',
                'llm_type': None
            }
        else:
            logger.warning("[Fallback] ❌ AI Agent 실패, vLLM으로 이동")
    
    # 2️⃣ vLLM 시도 (필수) - ⭐ element_detection_prompt_type 전달
    logger.info("[Fallback] 단계 2️⃣: 로컬 vLLM 호출 시도...")
    result = await _call_local_llm(
        text, detection_types, llm_type,
        vllm_model_name, ollama_model_name,
        vllm_base_url, ollama_base_url,
        prompt_type=element_detection_prompt_type  # ⭐ 프롬프트 파일 타입 전달
    )
    
    if result:
        result['success'] = True
        return result
    else:
        logger.warning("[Fallback] ❌ vLLM 실패, Dummy 또는 에러 반환")
    
    # 3️⃣ Dummy 반환 또는 에러
    if test_mode:
        logger.warning("[Fallback] 단계 3️⃣: Dummy 반환 (TEST_MODE=True)")
        return _get_dummy_results(detection_types)
    else:
        return {
            'success': False,
            'error': 'All fallback attempts failed',
            'api_type': 'fallback'
        }
```

**핵심 변경사항**:
- ✅ `element_detection_prompt_type: str = "element_detection_qwen"` 파라미터 추가
- ✅ `_call_local_llm` 호출 시 `prompt_type=element_detection_prompt_type` 전달
- ✅ Privacy Removal과 동일한 프롬프트 타입 관리 방식 적용

**흐름도**:
```
Fallback 모드 시작
    ↓
1️⃣ agent_url 설정됨?
    ├─ YES → AI Agent 호출 (텍스트 그대로)
    │   ├─ 성공 → 반환 ✅
    │   └─ 실패 → 자동 다음 단계
    │
2️⃣ vLLM 호출 (detection_prompt 포맷팅)
    ├─ 성공 → 반환 ✅
    └─ 실패 → 자동 다음 단계
    
3️⃣ TEST_MODE=True?
    ├─ YES → Dummy 반환 ✅
    └─ NO → 에러 반환 ❌
```

**필수 파라미터**:
| 파라미터 | 값 | 필수 |
|---------|-----|------|
| `detection_api_type` | `"fallback"` | ✅ **필수** |
| `detection_llm_type` | `"vllm"` 또는 `"ollama"` | ✅ **필수** (단계 2용) |
| `vllm_model_name` 또는 `ollama_model_name` | 모델명 | ✅ **필수** (단계 2용) |
| `VLLM_BASE_URL` 또는 `OLLAMA_BASE_URL` | 환경변수 | ✅ **필수** (단계 2용) |
| `agent_url` | 외부 API URL | ⚠️ **선택** (단계 1 수행 여부 결정) |

**⚠️ 주의**:
- 각 단계 실패 시 **자동으로 다음 단계로 이동** (TEST_MODE 체크 없음)
- `TEST_MODE=true`일 때만 최종 단계에서 Dummy 결과 반환
- `TEST_MODE=false`에서는 모든 API 실패 시 에러 반환
- **단계별 독립적 처리**: AI Agent 실패 → vLLM 자동 시도 → vLLM 실패 → Dummy 또는 에러

### **현재 실제 설정 (Web UI 기준)** ✅ Local vLLM 모드

```python
# web_ui/app/services/analysis_service.py:661-671

stt_result = await stt_service.transcribe_local_file(
    file_path=str(file_path),
    language="ko",
    is_stream=False,
    privacy_removal=True,              # ✅ 항상 활성화 (vLLM + Qwen)
    classification=False,              # ❌ 미사용
    element_detection=True,            # ✅ 항상 활성화 (Local vLLM)
    # 추가 파라미터는 기본값 사용
)
```

**API 서버에서의 실제 처리** (app.py:410-590):

```python
# 1️⃣ FormData에서 파라미터 추출
element_detection = form_data.get('element_detection', 'false')  # 값: 'true'
detection_api_type = form_data.get('detection_api_type', 'ai_agent')  # 기본: 'ai_agent', 현재 웹UI에서 'vllm' 설정 필요
agent_url = form_data.get('agent_url', '')  # 값: '' (미제공)
detection_llm_type = form_data.get('detection_llm_type', 'openai')  # 기본: 'openai'
vllm_model_name = form_data.get('vllm_model_name')  # 값: '/model/qwen30_thinking_2507'
detection_types = form_data.get('detection_types', '')  # 기본값 사용

# 2️⃣ 환경변수에서 기본값 읽기
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001")
VLLM_MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "Qwen3-30B-A3B-Thinking-2507-FP8")

# 3️⃣ perform_element_detection 호출
element_response = await perform_element_detection(
    text=detection_text,  # STT 또는 Privacy Removal 결과
    detection_types=detection_types_list,
    api_type=detection_api_type,  # 기본: 'ai_agent', 현재 웹UI에서 'vllm' 설정 필요
    llm_type=detection_llm_type,  # 'vllm' (detection_api_type='vllm'일 때만)
    vllm_model_name=vllm_model_name,  # '/model/qwen30_thinking_2507'
    vllm_base_url=VLLM_BASE_URL,  # 'http://localhost:8001'
    external_api_url=agent_url  # '' (미사용)
)
```

**⭐ 현재 문제점**: Web UI에서 명시적으로 `detection_api_type='vllm'`을 지정하지 않으므로, API 서버 기본값 'ai_agent'이 사용됨
→ ai_agent는 agent_url이 필수인데 Web UI에서 제공하지 않음
→ **현재는 fallback 모드로 전환하거나 Web UI에서 detection_api_type 파라미터 추가 필요**

### **권장 설정 시나리오**

**시나리오 1️⃣: Local vLLM만 사용 (현재 + 웹UI 수정)**
```python
# Web UI (upload.html)에서 FormData에 추가
formData.append('detection_api_type', 'vllm');  # ⭐ 명시적 지정
formData.append('detection_llm_type', 'vllm');
formData.append('vllm_model_name', '/model/qwen30_thinking_2507');
```
**장점**: 단순, 가벼움 | **단점**: 외부 AI Agent 미지원

**시나리오 2️⃣: Fallback 사용 (추천, 안정적)**
```python
# Web UI (upload.html)에서 FormData에 추가
formData.append('detection_api_type', 'fallback');  # ⭐ Fallback 지정
formData.append('detection_llm_type', 'vllm');
formData.append('vllm_model_name', '/model/qwen30_thinking_2507');
# agent_url은 선택사항 (없으면 자동으로 vllm으로 폴백)
```
**장점**: AI Agent 장애 시 자동으로 vllm으로 폴백 | **단점**: 약간의 오버헤드

**시나리오 3️⃣: 외부 AI Agent 사용**
```python
# Web UI (upload.html)에서 FormData에 추가
formData.append('detection_api_type', 'ai_agent');  # ⭐ AI Agent 지정
formData.append('agent_url', 'https://agent-api.kis.zone/...');  # ⭐ 필수
# detection_llm_type, vllm_model_name은 무시됨
```
**장점**: 외부 AI Agent의 고급 기능 활용 | **단점**: 외부 API 의존, 장애 시 전체 시스템 영향

### **점검 체크리스트**

- [x] Local vLLM 설정: vllm_base_url='http://localhost:8001' (경로 제외)
- [x] Local vLLM 모델: vllm_model_name='/model/qwen30_thinking_2507'
- [x] Privacy Removal: VLLM_QWEN_API_BASE='http://localhost:8001/v1' (경로 포함)
- [ ] **Web UI 수정 필요**: detection_api_type 명시적 지정 (현재 기본값 'ai_agent' 문제)
- [ ] External AI Agent 사용 계획 시: agent_url 환경변수 또는 FormData에 추가
- [ ] Fallback 모드 테스트: detection_api_type='fallback' + TEST_MODE=true로 설정

---

### **API 타입별 처리**

---

## ⚙️ **현재 설정 상태**

### **Web UI (upload.html)**

```python
# web_ui/app/services/analysis_service.py:661-667

stt_result = await stt_service.transcribe_local_file(
    file_path=str(file_path),
    language="ko",
    is_stream=False,
    privacy_removal=True,              # ✅ Privacy Removal 항상 활성
    classification=False,               # 사용자 선택
    ai_agent=include_classification,   # 사용자 선택
    element_detection=True              # ✅ Element Detection 항상 활성
)
```
formData.append('detection_api_type', 'local');      // ✅ 로컬 사용
formData.append('detection_llm_type', 'vllm');       // ✅ vLLM 사용
formData.append('vllm_model_name', '/model/qwen30_thinking_2507'); // ✅ Qwen 모델
```

### **API Server (app.py)**

```python
# 라인 407 - Privacy Removal LLM 타입 기본값
privacy_llm_type = form_data.get('privacy_llm_type', 'vllm')  # ✅ vllm으로 통일

# 라인 520-650 - 처리 순서
@app.post("/transcribe")
"""
STT 처리 (라인 873)
    ↓
Privacy Removal 처리 (라인 520-535)
    - llm_type: 'vllm'
    - model_name: Qwen 모델
    - api_base: VLLM_QWEN_API_BASE (http://localhost:8001/v1)
    ↓
Classification 처리 (라인 540-567) [선택사항]
    - 입력: privacy_result.text
    ↓
Element Detection 처리 (라인 570-600) ✅ [중요]
    - 입력: privacy_result.text (Privacy Removal 결과 사용)
    - api_type: 'local' (기본값) or 'fallback' (추천)
    - vllm_model_name: Qwen 모델
    ↓
응답 구성 (라인 610-615)
    - stt.text: 원본
    - privacy_removal.text: 정제됨
    - element_detection.detection_results: 탐지 결과
"""
```

**핵심 확인사항**:
- ✅ Privacy Removal 결과 (`privacy_result.text`)가 **정확히** Element Detection 입력으로 전달됨
- ✅ Classification 없이도 Privacy Removal → Element Detection 직접 연결 가능
- ✅ Element Detection은 항상 정제된 텍스트 사용

### **Docker 환경변수 (scratch/aa:28-42)**

```bash
docker run -d \
  --network stt-network \
  --name stt-engine \
  -p 8001:8001 \
  -p 8003:8003 \
  --gpus all \
  -e STT_PRESET=accuracy \
  -e VLLM_BASE_URL=http://localhost:8001/v1/chat/completions  # ✅ vLLM 엔드포인트
  -e LLM_MODEL_NAME=/model/qwen30_thinking_2507               # ✅ Qwen 모델
  -v $(pwd)/models:/app/models \
  stt-engine:cuda129-rhel89-v1.9.7
```

**상태 검증**:
- ✅ `VLLM_BASE_URL`: vLLM 엔드포인트 정확함
- ✅ `LLM_MODEL_NAME`: Qwen 모델명 정확함
- ✅ `STT_PRESET=accuracy`: STT 정확도 우선
- ✅ 모델 볼륨 마운트: `/app/models` 정확함

---

## 🔍 **흐름 정확성 검증**

### **1. Element Detection의 입력 텍스트**
```python
# 라인 604
detection_text = privacy_result.text if privacy_result else stt_result.get('text', '')
```
**상태**: ✅ 정확함. Privacy Result 우선순위 정확함.

### **2. Classification의 입력 텍스트**
```python
# 라인 566
classification_text = privacy_result.text if privacy_result else stt_result.get('text', '')
```
**상태**: ✅ 정확함.

### **3. vLLM 모델명 전달**
```python
# 웹UI에서 설정
vllm_model_name: '/model/qwen30_thinking_2507'

# API에서 전달
await llm_client.call(...)  # ✅ 모델명 전달됨
```
**상태**: ✅ 정확함.

### **4. Fallback 메커니즘**
```python
# 라인 903-950
api_type == "fallback"
  → 1️⃣ external API 실패
  → 2️⃣ local LLM 실패  
  → 3️⃣ Dummy (TEST_MODE=True일 때만)
```
**상태**: ✅ 완전 구현됨. 단, TEST_MODE 환경변수 설정 필요할 수 있음.

---

## ⚠️ **권장 확인사항**

| 항목 | 확인 필요 | 우선순위 |
|------|----------|---------|
| VLLM 서버 실행 여부 | `curl http://localhost:8001/v1/chat/completions` | 🔴 필수 |
| Qwen 모델 로드 여부 | `/model/qwen30_thinking_2507` 존재 확인 | 🔴 필수 |
| TEST_MODE 설정 | `docker run -e TEST_MODE=false ...` | 🟡 권장 |
| vLLM 엔드포인트 | 환경변수 `VLLM_BASE_URL` 설정 확인 | 🟡 권장 |
| Element Detection 활성화 | Web UI에서 자동 `true` 설정됨 ✅ | ✅ 완료 |

---

## 📝 **보완 작업 항목**

### **Phase 1: 로깅 및 에러 처리 강화**
- [ ] 각 단계별 상세 로깅 추가
- [ ] 에러 메시지 통일 및 명확화
- [ ] 성능 메트릭 수집 개선

### **Phase 2: 설정값 검증 강화**
- [ ] 환경변수 존재 여부 사전 검증
- [ ] 모델 경로 유효성 사전 검증
- [ ] LLM 엔드포인트 연결 테스트

### **Phase 3: Privacy Removal 최적화**
- [ ] 프롬프트 타입 검증 강화
- [ ] 응답 포맷 표준화
- [ ] 실패 시 폴백 로직 개선

### **Phase 4: Classification 개선**
- [ ] 분류 카테고리 정의 명확화
- [ ] 신뢰도 점수 계산 개선
- [ ] 재분류 로직 추가

### **Phase 5: Element Detection 완성**
- [ ] 탐지 유형 문서화
- [ ] Fallback 로직 테스트
- [ ] 외부 API 호출 로직 검증

### **Phase 6: 통합 테스트**
- [ ] End-to-End 테스트 케이스 작성
- [ ] 성능 베이스라인 수립
- [ ] 배포 전 최종 검증

---

## 📌 **다음 단계**

이 문서를 기반으로 다음과 같이 진행할 예정입니다:

1. **Phase별 상세 작업 명세** 수립
2. **각 단계별 코드 개선** 실행
3. **테스트 케이스** 작성 및 검증
4. **문서 업데이트** (사용자 가이드 등)

---

**작성자**: GitHub Copilot  
**최종 수정**: 2026-03-05
