# Element Detection 코드 위치 및 참고 자료

## 📂 주요 파일 및 라인 번호

### Web UI 부분

#### 1. **분석 시작 JavaScript**
- **파일**: `web_ui/templates/upload.html`
- **함수**: `startAnalysis()`
- **라인**: ~1402
- **역할**: 사용자가 "분석 시작" 버튼 클릭 → POST /api/analysis/start 호출

```javascript
async function startAnalysis() {
    const data = await apiCall('/api/analysis/start', 'POST', {
        folder_path: currentFolder,
        include_classification: true,
        include_validation: true,
        force_reanalysis: forceReanalysis
    });
}
```

#### 2. **분석 라우터 (백엔드)**
- **파일**: `web_ui/app/routes/analysis.py`
- **함수**: `start_analysis()` (비동기)
- **라인**: ~36
- **역할**: 분석 요청 수신 → job 생성 → 백그라운드 태스크 추가

```python
@router.post("/start", response_model=AnalysisStartResponse, status_code=202)
async def start_analysis(
    request_data: AnalysisStartRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # job_id 생성 및 백그라운드 처리 등록
    response = AnalysisService.start_analysis(emp_id, request_data, db)
    
    # BackgroundTasks에 비동기 처리 추가
    background_tasks.add_task(
        AnalysisService.process_analysis_async,
        response.job_id, emp_id, request_data.folder_path, ...
    )
```

#### 3. **분석 서비스**
- **파일**: `web_ui/app/services/analysis_service.py`
- **클래스**: `AnalysisService`
- **메서드**: 
  - `start_analysis()` - 라인 ~120
  - `process_analysis_async()` - 라인 ~986
- **역할**: 분석 로직 실행, STT 호출, Element Detection 옵션 전달

```python
class AnalysisService:
    @staticmethod
    def start_analysis(emp_id, request, db):
        # job_id 생성, DB 저장
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        analysis_job = AnalysisJob(...)
        db.add(analysis_job)
        db.commit()
        return AnalysisStartResponse(job_id=job_id, ...)
    
    @staticmethod
    async def process_analysis_async(job_id, emp_id, folder_path, ...):
        # 각 파일 순회
        for file_id in file_ids:
            # STT 처리
            stt_result = await stt_service.transcribe_local_file(
                file_path=file_path,
                element_detection=True,  # ✨ 항상 true
                agent_url="",  # 또는 환경변수값
                ...
            )
```

#### 4. **STT 서비스**
- **파일**: `web_ui/app/services/stt_service.py`
- **클래스**: `STTService`
- **메서드**: `transcribe_local_file()`
- **라인**: ~46
- **역할**: API Server로 파일 전달, element_detection + agent_url 파라미터 전송

```python
async def transcribe_local_file(
    self,
    file_path: str,
    element_detection: bool = True,  # ✨
    agent_url: str = "",  # ✨
    agent_request_format: str = "text_only",  # ✨
    ...
) -> dict:
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field("file_path", api_file_path)
        
        # ✨ Element Detection 관련 파라미터
        data.add_field("element_detection", str(element_detection).lower())
        if agent_url:
            data.add_field("agent_url", agent_url)
            data.add_field("agent_request_format", agent_request_format)
        
        async with session.post(
            f"{self.api_url}/transcribe",
            data=data,
            ...
        ) as response:
```

---

### API Server 부분

#### 5. **API 서버 메인**
- **파일**: `api_server/app.py`
- **함수**: `_transcribe_file()` (비동기)
- **라인**: ~480
- **역할**: element_detection 파라미터 확인 → perform_element_detection() 호출

```python
# api_server/app.py line 505-540

# Element Detection 환경변수 설정
vllm_base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1/chat/completions")
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/generate")

# Element Detection 실행
element_response = await perform_element_detection(
    text=detection_text,
    api_type=detection_api_type,  # "external" / "vllm" / "ollama"
    vllm_base_url=vllm_base_url,  # ✨ 환경변수에서 읽음
    ollama_base_url=ollama_base_url,  # ✨ 환경변수에서 읽음
    external_api_url=agent_url,  # ✨ Web UI에서 전달
    ...
)
```

#### 6. **Element Detection 메인 함수**
- **파일**: `api_server/transcribe_endpoint.py`
- **함수**: `perform_element_detection()` (비동기)
- **라인**: ~420
- **역할**: api_type에 따라 외부 API 또는 vLLM 선택 호출

```python
async def perform_element_detection(
    text: str,
    detection_types: list,
    api_type: str,  # "external" / "vllm" / "ollama"
    llm_type: str,
    vllm_model_name: str,
    ollama_model_name: str,
    vllm_base_url: str,  # http://localhost:8001/v1/chat/completions
    ollama_base_url: str,  # http://localhost:11434/api/generate
    classification_result: dict = None,
    privacy_removal_result: dict = None,
    external_api_url: str = None  # https://agent-api.kis.zone/...
) -> dict:
    """
    api_type 판단:
    1. external_api_url 있음 → _call_external_api()
    2. external_api_url 없음 + api_type="vllm" → _call_vllm_api()
    3. external_api_url 없음 + api_type="ollama" → _call_ollama()
    """
    
    if api_type == "external" and external_api_url:
        result = await _call_external_api(text, detection_types, external_api_url)
    elif api_type == "vllm":
        result = await _call_vllm_api(text, vllm_base_url, vllm_model_name)
    elif api_type == "ollama":
        result = await _call_ollama(text, ollama_base_url, ollama_model_name)
```

#### 7. **외부 API 호출**
- **파일**: `api_server/transcribe_endpoint.py`
- **함수**: `_call_external_api()` (비동기)
- **라인**: ~563
- **역할**: KIS Agent API 형식으로 외부 API 호출

```python
async def _call_external_api(
    text: str,
    detection_types: list,
    external_api_url: Optional[str]
) -> Optional[dict]:
    """
    외부 AI Agent 호출 (KIS Agent API 형식)
    
    요청:
    {
        "chat_thread_id": "",
        "parameters": {
            "user_query": "상담 텍스트"
        }
    }
    
    응답:
    {
        "detected_yn": "Y"/"N",
        "detected_sentences": [...],
        "detected_reasons": [...],
        "detected_keywords": [...]
    }
    """
    
    if not external_api_url:
        return None
    
    payload = {
        "chat_thread_id": "",
        "parameters": {
            "user_query": text  # ✨ 순수 텍스트만
        }
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            external_api_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
    
    if response.status_code == 200:
        return {
            'success': True,
            'agent_type': 'external',
            ...
        }
```

#### 8. **vLLM API 호출**
- **파일**: `api_server/transcribe_endpoint.py`
- **함수**: `_call_vllm_api()` (비동기)
- **라인**: ~350
- **역할**: vLLM OpenAI 호환 API 호출

```python
async def _call_vllm_api(
    text: str,
    vllm_base_url: str,
    vllm_model_name: str
) -> Optional[dict]:
    """
    vLLM OpenAI 호환 API 호출
    
    요청:
    {
        "model": "qwen2.5-7b",
        "messages": [
            {"role": "user", "content": "상담 텍스트"}
        ],
        "temperature": 0.3,
        "max_tokens": 1000
    }
    """
    
    payload = {
        "model": vllm_model_name,
        "messages": [
            {"role": "user", "content": text}  # ✨ 순수 텍스트
        ],
        "temperature": 0.3,
        "max_tokens": 1000
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            vllm_base_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
```

---

## 🔍 호출 체인

```
1. upload.html (사용자)
   └─ startAnalysis()
      │
      ├─→ /api/analysis/start (POST)
      │   └─ app/routes/analysis.py: start_analysis()
      │      │
      │      ├─→ AnalysisService.start_analysis()
      │      │   └─ job 생성, DB 저장, job_id 반환
      │      │
      │      └─→ BackgroundTasks.add_task()
      │         └─ AnalysisService.process_analysis_async() [비동기]
      │            │
      │            ├─→ loop: 각 파일 처리
      │            │   │
      │            │   ├─→ STTService.transcribe_local_file()
      │            │   │   │
      │            │   │   └─→ /transcribe (POST to API Server)
      │            │   │      [FormData: file_path, element_detection, agent_url]
      │            │   │      │
      │            │   │      └─ app.py: _transcribe_file()
      │            │   │         │
      │            │   │         ├─→ perform_element_detection()
      │            │   │         │   │
      │            │   │         │   ├─ [api_type="external" && external_api_url]
      │            │   │         │   │  └─ _call_external_api()
      │            │   │         │   │     └─ POST to https://agent-api.kis.zone/...
      │            │   │         │   │
      │            │   │         │   └─ [api_type="vllm" || no external_api_url]
      │            │   │         │      └─ _call_vllm_api()
      │            │   │         │         └─ POST to http://localhost:8001/v1/chat/completions
      │            │   │         │
      │            │   │         └─ 결과 반환
      │            │   │
      │            │   └─← AnalysisResult 저장
      │            │
      │            └─ 모든 파일 완료
      │
      └─ analysis.html
         └─ checkProgress() [2초 주기]
            └─ /api/analysis/progress (GET)
               └─ 진행 상황 표시
```

---

## 🌍 환경변수 설정

### Web UI 환경변수
```bash
# web_ui/config.py 읽음
ELEMENT_DETECTION_AGENT_URL=https://agent-api.kis.zone/v2_2/api/agent_before_check/messages
# 또는
ELEMENT_DETECTION_AGENT_URL=  # 비어있음 (vLLM 사용)
```

### API Server 환경변수
```bash
# api_server/app.py 읽음 (Line 505-540)
VLLM_BASE_URL=http://localhost:8001/v1/chat/completions
VLLM_MODEL_NAME=qwen2.5-7b

# 또는
OLLAMA_BASE_URL=http://localhost:11434/api/generate
OLLAMA_MODEL_NAME=qwen2.5-7b
```

---

## 📊 데이터 구조

### **Web UI → API Server 전달**

```python
# FormData (multipart/form-data)
{
    "file_path": "/app/web_ui/data/uploads/customer_visit/file.wav",
    "element_detection": "true",  # ✨ 항상 true
    "agent_url": "https://agent-api.kis.zone/...",  # 또는 ""
    "agent_request_format": "text_only",
    # ... 기타 파라미터
}
```

### **API Server → 외부 Agent 전달**

```json
{
  "chat_thread_id": "",
  "parameters": {
    "user_query": "고객 상담 텍스트 여기..."
  }
}
```

### **API Server → vLLM 전달**

```json
{
  "model": "qwen2.5-7b",
  "messages": [
    {
      "role": "user",
      "content": "고객 상담 텍스트 여기..."
    }
  ],
  "temperature": 0.3,
  "max_tokens": 1000
}
```

---

## 🔑 핵심 포인트

| 항목 | 값 | 위치 |
|------|-----|------|
| **분석 시작** | upload.html의 startAnalysis() | Line ~1402 |
| **Job 생성** | AnalysisService.start_analysis() | app/services/analysis_service.py:~120 |
| **비동기 처리** | process_analysis_async() | app/services/analysis_service.py:~986 |
| **STT 호출** | STTService.transcribe_local_file() | app/services/stt_service.py:~46 |
| **Element 처리 결정** | api_server/app.py | Line ~505-540 |
| **외부 API 호출** | _call_external_api() | api_server/transcribe_endpoint.py:~563 |
| **vLLM 호출** | _call_vllm_api() | api_server/transcribe_endpoint.py:~350 |

---

## 💡 추적 팁

**문제 발생 시 확인 순서:**

1. ✅ Web UI 환경변수: `ELEMENT_DETECTION_AGENT_URL` 설정 확인
2. ✅ API Server 환경변수: `VLLM_BASE_URL`, `OLLAMA_BASE_URL` 설정 확인
3. ✅ Log 추적: `[STT Service]`, `[API]`, `[Transcribe/ElementDetection]` 키워드
4. ✅ FormData 확인: agent_url이 올바르게 전달되는지 확인
5. ✅ API 응답: 외부 API 또는 vLLM 응답 형식 확인
