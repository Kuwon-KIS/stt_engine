# Element Detection 호출 흐름 최종 정리

## 🎯 한눈에 보기

```
사용자가 "분석 시작" 클릭
        ↓
Web UI: /api/analysis/start
        ↓
Job 생성 + 백그라운드 처리 시작
        ↓
각 파일마다:
  1. STT (faster-whisper)
  2. Privacy Removal (민감정보 제거)
  3. Classification (통화 분류)
  4. ⭐ Element Detection
        ↓
Element Detection 선택:
        ↓
  ┌─────────────────────────────┐
  │ 외부 Agent URL 있음?        │
  └─────────────────────────────┘
        ↓              ↓
      YES            NO
        ↓              ↓
   외부 API      vLLM/Ollama
   (KIS Agent)   (OpenAI호환)
        ↓              ↓
   POST 요청    POST 요청
        ↓              ↓
  응답 수신    응답 수신
        ↓              ↓
        └──────┬───────┘
               ↓
          결과 통합
               ↓
          DB 저장
               ↓
        진행 상황 업데이트
```

---

## 📍 주요 의사결정 포인트

### **1. 언제 Element Detection이 호출되나?**
✅ **항상!** 각 파일 처리 시 필수 단계

- Web UI에서 분석 시작 → 각 파일마다 자동으로 element_detection 처리
- `element_detection` 파라미터: 항상 `true`
- 비활성화 불가능 (요소 탐지는 필수)

### **2. 외부 Agent vs vLLM 선택 기준**

```python
# api_server/app.py (Line 505-540)

if element_detection_enabled:  # 항상 true
    # 환경변수에서 vLLM/Ollama URL 읽기
    vllm_base_url = os.getenv("VLLM_BASE_URL", "...")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "...")
    
    # perform_element_detection() 호출
    # ↓ 내부에서 판단:
    # - external_api_url 있음 → 외부 API 호출
    # - external_api_url 없음 → vLLM 호출
```

**판단 로직:**
```python
# api_server/transcribe_endpoint.py

if api_type == "external" and external_api_url:
    # ✨ 외부 Agent 우선 사용
    result = await _call_external_api(...)
else:
    # ✨ vLLM/Ollama 사용
    result = await _call_vllm_api(...) 
    # 또는
    result = await _call_ollama(...)
```

### **3. 외부 API URL은 어디서 오나?**

```
경로 1: Web UI 환경변수
├─ 파일: web_ui/config.py
├─ 변수: ELEMENT_DETECTION_AGENT_URL
└─ 예: https://agent-api.kis.zone/v2_2/api/agent_before_check/messages

경로 2: Web UI → API Server로 전달
├─ 파일: web_ui/app/services/stt_service.py
├─ 전달: agent_url (FormData)
└─ 수신: api_server/app.py 의 external_api_url
```

**구체적인 전달:**
```python
# web_ui/app/services/stt_service.py (Line 100-112)
if agent_url:  # 외부 URL 있으면 전달
    data.add_field("agent_url", agent_url)
    data.add_field("agent_request_format", "text_only")

# api_server/app.py (Line 505-540)
element_response = await perform_element_detection(
    ...
    external_api_url=agent_url  # ✨ 전달받은 값
)
```

---

## 🌐 API 호출 상세

### **외부 Agent (KIS Agent)**

**호출 위치:** `api_server/transcribe_endpoint.py` → `_call_external_api()`

**요청:**
```http
POST https://agent-api.kis.zone/v2_2/api/agent_before_check/messages
Content-Type: application/json

{
  "chat_thread_id": "",
  "parameters": {
    "user_query": "고객과 판매원의 상담 내용 텍스트..."
  }
}
```

**응답:**
```json
{
  "detected_yn": "Y" or "N",
  "detected_sentences": [
    "불완전판매 요소가 포함된 문장 1",
    "불완전판매 요소가 포함된 문장 2"
  ],
  "detected_reasons": [
    "이유 1",
    "이유 2"
  ],
  "detected_keywords": []
}
```

**코드:**
```python
# Line 563-635 in transcribe_endpoint.py

async def _call_external_api(
    text: str,
    detection_types: list,
    external_api_url: Optional[str]
) -> Optional[dict]:
    
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
        result = response.json()
        
        # 응답 형식 처리
        if "detected_yn" in result:
            detection_data = result
        elif "message" in result:
            try:
                detection_data = json.loads(result.get("message", "{}"))
            except:
                detection_data = result
        
        # 표준 형식으로 변환
        return {
            'success': True,
            'agent_type': 'external',
            'incomplete_elements': {
                'detected': detection_data.get('detected_yn') == 'Y',
                'sentences': detection_data.get('detected_sentences', []),
                'reasons': detection_data.get('detected_reasons', []),
                'keywords': detection_data.get('detected_keywords', [])
            },
            'processing_time_sec': elapsed_time
        }
```

---

### **vLLM (OpenAI 호환)**

**호출 위치:** `api_server/transcribe_endpoint.py` → `_call_vllm_api()`

**요청:**
```http
POST http://localhost:8001/v1/chat/completions
Content-Type: application/json

{
  "model": "qwen2.5-7b",
  "messages": [
    {
      "role": "user",
      "content": "고객과 판매원의 상담 내용 텍스트..."
    }
  ],
  "temperature": 0.3,
  "max_tokens": 1000
}
```

**응답:**
```json
{
  "choices": [
    {
      "message": {
        "content": "분석 결과 텍스트...\n불완전판매 요소 탐지: Y\n..."
      }
    }
  ]
}
```

**코드:**
```python
# Line 350 onwards in transcribe_endpoint.py

async def _call_vllm_api(
    text: str,
    vllm_base_url: str,
    vllm_model_name: str
) -> Optional[dict]:
    
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
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            vllm_base_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
    
    if response.status_code == 200:
        result = response.json()
        message = result['choices'][0]['message']['content']
        
        # 응답 파싱
        return {
            'success': True,
            'agent_type': 'vllm',
            'incomplete_elements': parse_vllm_response(message),
            'processing_time_sec': elapsed_time
        }
```

---

## 🔄 시간 흐름 (Timing)

```
t=0s    | 사용자 "분석 시작" 버튼 클릭
        |
t=0.1s  | POST /api/analysis/start 발송
        |
t=0.2s  | job_id 생성, DB 저장 (상태: pending)
        | 응답 202 Accepted 반환
        |
t=0.3s  | analysis.html 페이지 로드
        | → job_id를 쿼리 파라미터로 전달
        |
t=0.5s  | 백그라운드 처리 시작
        | process_analysis_async() 시작
        |
t=1.0s  | 파일1 처리 시작
        | 상태: processing
        |
t=1.5s  | STT 완료
        | (text 획득)
        |
t=2.5s  | Privacy Removal 완료
        | (민감정보 제거)
        |
t=3.0s  | Classification 완료
        | (통화 분류)
        |
t=3.5s  | ⭐ Element Detection 시작
        |
        ├─ [외부 Agent인 경우]
        │  t=3.6s  | POST to https://agent-api.kis.zone/...
        │  t=4.8s  | 응답 수신 (네트워크 지연 고려)
        │
        └─ [vLLM인 경우]
           t=3.6s  | POST to http://localhost:8001/v1/chat/completions
           t=4.2s  | 응답 수신 (로컬 처리)
        |
t=5.0s  | AnalysisResult DB 저장
        |
t=5.5s  | 파일2 처리 시작 (위 반복)
        |
...     | (계속)
        |
t=N.0s  | 모든 파일 처리 완료
        | 상태: completed
```

**클라이언트 측 (Polling):**
```
t=0.5s  | analysis.html에서 2초 주기 polling 시작
t=2.5s  | GET /api/analysis/progress → {progress: 10%}
t=4.5s  | GET /api/analysis/progress → {progress: 30%}
t=6.5s  | GET /api/analysis/progress → {progress: 50%}
...     | (계속)
t=N.5s  | GET /api/analysis/progress → {progress: 100%, status: completed}
        | 🎉 완료 화면 표시
```

---

## 🛠️ 요청/응답 매핑

### **1단계: Web UI → API Server**

```
FormData 형식:
├─ file_path: "/app/web_ui/data/uploads/customer_visit/audio.wav"
├─ element_detection: "true"  ✨ 항상 true
├─ agent_url: "https://agent-api.kis.zone/..."  ✨ 또는 ""
├─ agent_request_format: "text_only"
└─ ... 기타 파라미터

↓ (API Server 수신)

api_server/app.py에서:
├─ element_detection 파라미터 파싱: "true" → True
├─ agent_url 파라미터 추출
├─ VLLM_BASE_URL 환경변수 읽음
├─ OLLAMA_BASE_URL 환경변수 읽음
└─ perform_element_detection() 호출
```

### **2단계: API Server 내부 처리**

```
perform_element_detection() 함수:

┌─ external_api_url 확인
│  ├─ 있음 + api_type=="external"
│  │  └─ _call_external_api() 호출
│  │     └─ POST to 외부 Agent
│  │
│  └─ 없음 + api_type=="vllm"
│     └─ _call_vllm_api() 호출
│        └─ POST to vLLM
```

### **3단계: 외부 API 요청/응답**

```
요청:
POST https://agent-api.kis.zone/v2_2/api/agent_before_check/messages
{
  "chat_thread_id": "",
  "parameters": {
    "user_query": "...상담 텍스트..."
  }
}

응답:
{
  "detected_yn": "Y",
  "detected_sentences": [...],
  "detected_reasons": [...],
  "detected_keywords": [...]
}
```

### **4단계: vLLM 요청/응답**

```
요청:
POST http://localhost:8001/v1/chat/completions
{
  "model": "qwen2.5-7b",
  "messages": [
    {"role": "user", "content": "...상담 텍스트..."}
  ],
  "temperature": 0.3,
  "max_tokens": 1000
}

응답:
{
  "choices": [
    {
      "message": {
        "content": "분석 결과..."
      }
    }
  ]
}
```

---

## 📋 체크리스트

### **배포 전 확인사항**

- [ ] **Web UI 환경변수**
  - [ ] `ELEMENT_DETECTION_AGENT_URL` 설정 확인 (있으면 외부 API, 없으면 vLLM)
  
- [ ] **API Server 환경변수**
  - [ ] `VLLM_BASE_URL` 설정 (기본값: http://localhost:8001/v1/chat/completions)
  - [ ] `VLLM_MODEL_NAME` 설정 (기본값: qwen2.5-7b)
  - [ ] `OLLAMA_BASE_URL` 설정 (기본값: http://localhost:11434/api/generate)
  - [ ] `OLLAMA_MODEL_NAME` 설정

- [ ] **외부 Agent 설정** (사용할 경우)
  - [ ] API URL 정확성 확인
  - [ ] 인증 토큰 필요 여부 확인
  - [ ] 요청/응답 형식 확인

- [ ] **vLLM 설정** (로컬 사용할 경우)
  - [ ] vLLM 서버 실행 중 확인
  - [ ] 모델 로드 완료 확인
  - [ ] 포트 바인딩 확인

- [ ] **코드 변경사항**
  - [ ] `api_server/transcribe_endpoint.py` (_call_external_api 함수)
  - [ ] `api_server/app.py` (환경변수 읽기)
  - [ ] `web_ui/app/services/stt_service.py` (FormData 전달)

---

## 📚 참고 문서

- 전체 흐름: `ANALYSIS_FLOW_WITH_ELEMENT_DETECTION.md`
- 코드 위치: `ELEMENT_DETECTION_CODE_REFERENCE.md`
- 환경 설정: `docker-compose.yml` 또는 `.env` 파일
- API 명세: API Server 주석 코드 참고

---

## 🚀 배포 명령어

### Git 커밋
```bash
cd /Users/a113211/workspace/stt_engine
git add -A
git commit -m "feat: Element Detection 호출 로직 개선

- 외부 Agent (KIS Agent) 형식 지원
- vLLM/Ollama 환경변수 기반 호출
- 순수 텍스트 전달 (프롬프트 제거)
- 응답 형식 통합 처리"
```

### 원격 배포 (SSH + docker cp)
```bash
# 파일 복사
scp -i "aws-stt-build.pem" \
  /Users/a113211/workspace/stt_engine/api_server/transcribe_endpoint.py \
  ec2-user@ec2-15-165-159-23.ap-northeast-2.compute.amazonaws.com:~/stt_engine/api_server/

scp -i "aws-stt-build.pem" \
  /Users/a113211/workspace/stt_engine/api_server/app.py \
  ec2-user@ec2-15-165-159-23.ap-northeast-2.compute.amazonaws.com:~/stt_engine/api_server/

# 원격 서버에서 Docker 컨테이너로 복사
ssh -i "aws-stt-build.pem" ec2-user@ec2-15-165-159-23.ap-northeast-2.compute.amazonaws.com \
  "docker cp ~/stt_engine/api_server/transcribe_endpoint.py stt-engine:/app/api_server/ && \
   docker cp ~/stt_engine/api_server/app.py stt-engine:/app/api_server/ && \
   docker restart stt-engine"
```

### 로그 확인
```bash
# 로컬
docker logs stt-engine | grep -i "element\|agent" | tail -20

# 원격
ssh -i "aws-stt-build.pem" ec2-user@ec2-15-165-159-23.ap-northeast-2.compute.amazonaws.com \
  "docker logs stt-engine | grep -i element | tail -20"
```

---

## 📞 추가 질문?

이 문서가 충분하지 않다면, 다음을 확인하세요:

1. **환경변수 확인**: Docker logs에서 `VLLM_BASE_URL`, `ELEMENT_DETECTION_AGENT_URL` 값 확인
2. **API 연결성**: 외부 Agent 또는 vLLM 서버로 curl 테스트
3. **로그 추적**: `[STT Service]`, `[API]`, `[Transcribe/ElementDetection]` 키워드로 grep
4. **코드 검증**: 각 파일의 라인 번호에서 코드 확인
