# Web UI에서 분석 시작 시 Element Detection 흐름

## 📱 전체 프로세스 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                  Web UI (upload.html)                            │
│          "분석 시작" 버튼 클릭                                      │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  JavaScript: startAnalysis()                                    │
│  - POST /api/analysis/start                                     │
│  - Body:                                                        │
│    {                                                            │
│      "folder_path": "customer_visit",                           │
│      "include_classification": true,                            │
│      "include_validation": true,                                │
│      "force_reanalysis": false                                  │
│    }                                                            │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Web UI Backend (app/routes/analysis.py)                        │
│  POST /api/analysis/start                                       │
│  - session에서 emp_id 추출                                       │
│  - 폴더 내 파일 목록 확인                                         │
│  - 파일 해시 계산 (중복 방지)                                     │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  AnalysisService.start_analysis()                               │
│  - job_id 생성 (job_bc9beaa1bf7a 형식)                          │
│  - 옵션 저장:                                                     │
│    {                                                            │
│      "include_classification": true,                            │
│      "include_validation": true                                 │
│    }                                                            │
│  - DB에 AnalysisJob 저장 (status: pending)                       │
│  - BackgroundTasks에 process_analysis_async() 추가             │
│  - 클라이언트에 job_id 반환 (status 202)                         │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ├─ [동기 응답] job_id 클라이언트 반환
               │
               ▼ [비동기 백그라운드 처리]
┌─────────────────────────────────────────────────────────────────┐
│  AnalysisService.process_analysis_async()                       │
│  - 폴더 내 모든 파일 순회                                         │
│  - 각 파일마다:                                                   │
│    1. STT 처리                                                   │
│    2. Privacy Removal (개인정보 제거)                            │
│    3. Classification (통화 분류)                                 │
│    4. ✨ Element Detection (요소 탐지) ← 핵심!                   │
│    5. DB에 AnalysisResult 저장                                   │
│    6. 진행 상태 업데이트                                          │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
       ┌───────────────────────────────────────────────────┐
       │  ✨ ELEMENT DETECTION 상세 흐름 ✨                │
       │  (Step 4 확대)                                    │
       └───────────────┬─────────────────────────────────┘
                       │
                       ▼
       ┌───────────────────────────────────────────────────┐
       │  API Server 호출                                  │
       │  STTService.transcribe_local_file()               │
       │                                                  │
       │  FormData 파라미터:                               │
       │  - file_path                                     │
       │  - element_detection: true (항상 enabled)       │
       │  - agent_url: (외부 API URL 또는 empty)         │
       │  - agent_request_format: "text_only"            │
       └───────────────┬─────────────────────────────────┘
                       │
                       ▼
       ┌───────────────────────────────────────────────────┐
       │  API Server (transcribe_endpoint.py)              │
       │                                                  │
       │  처리 단계:                                        │
       │  1. STT (faster-whisper)                         │
       │  2. Privacy Removal                             │
       │  3. Classification                              │
       │  4. ⭐ perform_element_detection()              │
       └───────────────┬─────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
    ┌──────────────┐        ┌──────────────────┐
    │ 외부 Agent   │        │ vLLM/Ollama      │
    │ 호출 여부    │        │ 호출 여부        │
    └──────┬───────┘        └────────┬─────────┘
           │                         │
      [외부 URL 있음]         [외부 URL 없음]
           │                         │
           ▼                         ▼
   ┌────────────────────┐   ┌────────────────┐
   │ _call_external_api │   │ _call_vllm_api │
   │                    │   │ 또는           │
   │ POST 요청:         │   │ _call_ollama   │
   │ {                  │   │                │
   │  "chat_thread_id": │   │ (OpenAI 호환   │
   │  "",               │   │  형식)         │
   │  "parameters": {   │   └────────┬───────┘
   │   "user_query":    │            │
   │    "상담 텍스트"   │            ▼
   │  }                 │    성공/실패 응답
   │ }                  │
   │                    │
   │ 응답 형식:         │
   │ {                  │
   │  "detected_yn":    │
   │  "Y"/"N",          │
   │  "detected_...":   │
   │  [...]             │
   │ }                  │
   └──────┬─────────────┘
          │
          └──────────────┬─────────────────┐
                         │                 │
                         ▼                 ▼
                  [성공 케이스]    [실패 케이스]
                         │                 │
                    element_response      폴백
                    (api_type="external") (더미 응답)
```

---

## 🔄 시간 흐름 (Timeline)

### 1️⃣ **Web UI - 사용자 인터랙션** (동기)
```
t=0.0s  | 사용자가 "분석 시작" 버튼 클릭
        |
t=0.1s  | JavaScript POST /api/analysis/start 발송
        |
t=0.2s  | Web UI 백엔드에서 job_id 생성 및 DB 저장
        | 상태: pending
        |
t=0.3s  | 클라이언트에 job_id 반환 (상태 202 Accepted)
        | 📊 analysis.html 페이지로 이동 (with job_id)
```

### 2️⃣ **백그라운드 분석 처리** (비동기)
```
t=1.0s  | process_analysis_async() 시작
        | 상태 변경: pending → processing
        |
t=1.5s  | 첫번째 파일 처리 시작
        | [파일1: customer_visit_001.wav]
        |
        ├─ t=1.7s   | STT 완료 (text 획득)
        ├─ t=3.5s   | Privacy Removal 완료 (민감 정보 제거)
        ├─ t=4.2s   | Classification 완료 (통화 분류)
        │
        ▼ [Element Detection 시작]
        ├─ t=4.5s   | Agent URL 확인
        │           | - 없음: vLLM 호출
        │           | - 있음: 외부 Agent 호출
        │
        ├─ t=4.6s   | API 요청 전송
        │           | (외부: KIS Agent 형식)
        │           | (vLLM: OpenAI 호환 형식)
        │
        ├─ t=5.8s   | API 응답 수신
        │           | (element_detection 결과 획득)
        │
        └─ t=6.0s   | AnalysisResult DB 저장
                    | 상태: processing
                    |
t=6.5s  | 두번째 파일 처리 시작...
        | (같은 프로세스 반복)
        |
t=N.0s  | 모든 파일 처리 완료
        | 상태 변경: processing → completed
```

### 3️⃣ **클라이언트 진행 상황 확인** (Polling)
```
t=0.5s  | analysis.html 페이지 로드
        | interval 설정: 2초마다 진행 상황 확인
        |
t=2.5s  | GET /api/analysis/progress 요청
        | 응답: {"status": "processing", "progress": 15%}
        |
t=4.5s  | GET /api/analysis/progress 요청
        | 응답: {"status": "processing", "progress": 30%}
        |
t=6.5s  | GET /api/analysis/progress 요청
        | 응답: {"status": "processing", "progress": 50%}
        |
...     | (계속 polling)
        |
t=N.5s  | GET /api/analysis/progress 요청
        | 응답: {"status": "completed", "progress": 100%}
        | 🎉 완료 상태 표시
```

---

## 🎯 Element Detection 상세 분석

### **호출 지점 1: Web UI → API Server**

```python
# web_ui/app/services/stt_service.py - transcribe_local_file()
# Line: 100-112, 250-260

async with aiohttp.ClientSession() as session:
    data = aiohttp.FormData()
    data.add_field("file_path", api_file_path)
    data.add_field("element_detection", "true")  # ✨ 항상 전달
    
    if agent_url:  # element_detection과 무관하게 전달
        data.add_field("agent_url", agent_url)
        data.add_field("agent_request_format", "text_only")
    
    async with session.post(
        f"{self.api_url}/transcribe",  # API Server 호출
        data=data,
        timeout=aiohttp.ClientTimeout(total=estimated_timeout)
    ) as response:
        result = await response.json()
```

**흐름:**
- ✅ `element_detection=true` **항상 전달** (옵션 아님)
- ✅ `agent_url` **있을 때만 전달**
  - 있음 → 외부 API 사용
  - 없음 → vLLM 사용 (또는 Ollama)

---

### **호출 지점 2: API Server 내부 처리**

```python
# api_server/app.py - /transcribe 엔드포인트
# Line: 480-550

# 1. 파라미터 확인
element_detection_enabled = element_detection.lower() in ['true', '1', 'yes', 'on']

if element_detection_enabled:
    # 2. 환경변수 읽기
    import os
    vllm_base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1/chat/completions")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/generate")
    
    # 3. perform_element_detection() 호출
    element_response = await perform_element_detection(
        text=detection_text,
        detection_types=detection_types_list,
        api_type=detection_api_type,        # "external" 또는 "vllm" 또는 "ollama"
        llm_type=detection_llm_type,
        vllm_model_name=vllm_model_name,
        ollama_model_name=ollama_model_name,
        vllm_base_url=vllm_base_url,        # ✨ 환경변수에서 읽음
        ollama_base_url=ollama_base_url,    # ✨ 환경변수에서 읽음
        external_api_url=agent_url          # ✨ Web UI에서 전달
    )
```

**중요:**
- `api_type`: external/vllm/ollama 중 선택
- `external_api_url`: Web UI에서 받은 agent_url
- `vllm_base_url/ollama_base_url`: 환경변수에서 읽음

---

### **호출 지점 3: External API 또는 vLLM/Ollama 호출**

#### **A. 외부 Agent 호출** (external_api_url 있을 때)

```python
# api_server/transcribe_endpoint.py - _call_external_api()
# Line: 563-635

async def _call_external_api(text, detection_types, external_api_url):
    """
    외부 AI Agent API 호출 (KIS Agent 형식)
    """
    if not external_api_url:
        return None
    
    # 1. 요청 본문 구성
    payload = {
        "chat_thread_id": "",
        "parameters": {
            "user_query": text  # ✨ 순수 텍스트만 (프롬프트 없음)
        }
    }
    
    # 2. API 호출
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            external_api_url,  # https://agent-api.kis.zone/v2_2/...
            json=payload,
            headers={"Content-Type": "application/json"}
        )
    
    # 3. 응답 처리
    if response.status_code == 200:
        result = response.json()
        # 응답 형식:
        # {
        #   "detected_yn": "Y" or "N",
        #   "detected_sentences": [...],
        #   "detected_reasons": [...],
        #   "detected_keywords": [...]
        # }
        
        return {
            'success': True,
            'agent_type': 'external',
            'incomplete_elements': {...},
            'processing_time_sec': elapsed_time
        }
    else:
        return None  # 폴백: vLLM 사용
```

**요청 형식 (KIS Agent):**
```json
{
  "chat_thread_id": "",
  "parameters": {
    "user_query": "상담 내용 텍스트"
  }
}
```

#### **B. vLLM 호출** (external_api_url 없을 때 또는 외부 실패 시)

```python
# api_server/transcribe_endpoint.py - _call_vllm_api()

async def _call_vllm_api(text, vllm_base_url, vllm_model_name):
    """
    vLLM OpenAI 호환 API 호출
    """
    # 1. 요청 본문 구성
    payload = {
        "model": vllm_model_name,  # "qwen2.5-7b"
        "messages": [
            {
                "role": "user",
                "content": text  # ✨ 순수 텍스트만
            }
        ],
        "temperature": 0.3,
        "max_tokens": 1000
    }
    
    # 2. API 호출
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            vllm_base_url,  # http://localhost:8001/v1/chat/completions
            json=payload,
            headers={"Content-Type": "application/json"}
        )
    
    # 3. 응답 처리
    if response.status_code == 200:
        result = response.json()
        # 응답 형식: {"choices": [{"message": {"content": "분석 결과"}}]}
        
        return {
            'success': True,
            'agent_type': 'vllm',
            'incomplete_elements': {...},
            'processing_time_sec': elapsed_time
        }
```

**요청 형식 (OpenAI 호환):**
```json
{
  "model": "qwen2.5-7b",
  "messages": [
    {
      "role": "user",
      "content": "상담 내용 텍스트"
    }
  ],
  "temperature": 0.3,
  "max_tokens": 1000
}
```

---

## 🌍 환경 설정

### **Web UI (docker-compose 또는 환경변수)**

```bash
# 예시 1: 외부 Agent 사용
ELEMENT_DETECTION_AGENT_URL=https://agent-api.kis.zone/v2_2/api/agent_before_check/messages

# 예시 2: vLLM 사용 (로컬)
ELEMENT_DETECTION_AGENT_URL=  # 비어있음 → vLLM 자동 선택

# 예시 3: vLLM 사용 (원격)
ELEMENT_DETECTION_AGENT_URL=  # 비어있음
VLLM_BASE_URL=http://vllm-server:8001/v1/chat/completions
```

### **API Server (docker-compose 또는 환경변수)**

```bash
# vLLM 설정
VLLM_BASE_URL=http://localhost:8001/v1/chat/completions
VLLM_MODEL_NAME=qwen2.5-7b

# Ollama 설정 (대체)
OLLAMA_BASE_URL=http://localhost:11434/api/generate
OLLAMA_MODEL_NAME=qwen2.5-7b

# 외부 Agent 설정 (Web UI에서 전달됨)
# ELEMENT_DETECTION_AGENT_URL은 Web UI → API로 전달
```

---

## 📊 데이터 흐름 요약

```
┌──────────────────────────┐
│   Web UI Form            │
│ (분석 시작 버튼)         │
└────────────┬─────────────┘
             │ POST /api/analysis/start
             │ {folder_path, options}
             ▼
┌──────────────────────────┐
│ Analysis Backend         │
│ (job_id 생성, DB 저장)   │
└────────────┬─────────────┘
             │ BackgroundTasks
             │ process_analysis_async()
             ▼
┌──────────────────────────┐
│ Loop: 파일 순회          │
│ 1. STT                   │
│ 2. Privacy Removal       │
│ 3. Classification        │
│ 4. Element Detection ⭐ │
└────────────┬─────────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌─────────────┐   ┌──────────────┐
│ 외부 Agent  │   │ vLLM/Ollama  │
│             │   │              │
│ KIS Agent   │   │ OpenAI 호환  │
│ API 형식    │   │ 형식         │
└─────────────┘   └──────────────┘
    │                 │
    └────────┬────────┘
             │ 응답 통합
             ▼
┌──────────────────────────┐
│ AnalysisResult DB 저장   │
│ - stt_text               │
│ - element_detection      │
│ - analysis_metadata      │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ analysis.html 페이지    │
│ (Polling으로 결과 확인) │
│ GET /api/analysis/progress
└──────────────────────────┘
```

---

## ✨ 핵심 차이점: 외부 Agent vs vLLM

| 항목 | 외부 Agent (KIS) | vLLM |
|------|----------------|------|
| **호출 조건** | `agent_url` 설정됨 | `agent_url` 없음 |
| **URL** | https://agent-api.kis.zone/... | http://localhost:8001/v1/chat/completions |
| **요청 형식** | `{"chat_thread_id": "", "parameters": {"user_query": "..."}}` | `{"model": "...", "messages": [...]}` |
| **응답 형식** | `{"detected_yn": "Y/N", "detected_sentences": [...]}` | `{"choices": [{"message": {"content": "..."}}]}` |
| **처리 시간** | ~1-2s (네트워크 + 원격 처리) | ~0.5-1s (로컬 처리) |
| **환경변수** | `ELEMENT_DETECTION_AGENT_URL` | `VLLM_BASE_URL`, `VLLM_MODEL_NAME` |
| **실패 시 폴백** | vLLM으로 자동 재시도 | 더미 응답 또는 에러 |

---

## 📝 결론

**"분석 시작" 버튼 클릭 후 element_detection 처리:**

1. ✅ Web UI에서 `/api/analysis/start` API 호출
2. ✅ 백엔드에서 job 생성 후 비동기 처리 시작
3. ✅ 각 파일마다 STT → Privacy → Classification → **Element Detection**
4. ✅ Element Detection:
   - 외부 Agent 설정 있음 → KIS Agent API 호출
   - 없음 → vLLM OpenAI 호환 API 호출
5. ✅ 결과 DB 저장 및 진행 상황 업데이트
6. ✅ 클라이언트는 2초 주기로 진행 상황 polling
