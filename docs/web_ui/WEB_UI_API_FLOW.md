# Web UI → API 호출 흐름 분석

> **작성일**: 2026년 3월 9일  
> **대상**: 개발자, 아키텍처 검토자

---

## 📋 개요

Web UI에서 STT API (`/transcribe` 엔드포인트)로의 호출 흐름을 분석합니다.

**메인 사용자 흐름**:
```
Login (auth.py) 
  ↓
Upload (files.py) 
  ↓
Analysis (analysis.py) 
  ↓
STT API (/transcribe)
```

---

## 🔐 1단계: 로그인 (Login)

### 엔드포인트: `/api/auth/login`

**파일**: [web_ui/app/routes/auth.py](../../web_ui/app/routes/auth.py)

**호출 방식 (HTML)**:
```html
<!-- web_ui/templates/login.html -->
POST /api/auth/login
Content-Type: application/json

{
  "emp_id": "000123"  // 6자리 숫자 사번
}
```

**로직**:
1. 사번 검증
2. DB에 직원 정보 저장 또는 업데이트
3. 세션 생성 (`request.session["emp_id"] = emp_id`)
4. 응답:
```json
{
  "success": true,
  "emp_id": "000123",
  "name": "김철수",
  "dept": "영업팀"
}
```

**세션 정보 저장 위치**:
- 서버 세션에 `emp_id` 저장
- 이후 모든 API 요청에서 사용

---

## 📤 2단계: 파일 업로드 (Upload)

### 엔드포인트: `/api/files/upload`

**파일**: [web_ui/app/routes/files.py](../../web_ui/app/routes/files.py)

**호출 방식 (HTML/JavaScript)**:
```javascript
// web_ui/templates/upload.html (라인 1296 근처)
const xhr = new XMLHttpRequest();
xhr.open('POST', '/api/files/upload');

const formData = new FormData();
formData.append('file', fileInputElement.files[0]);
formData.append('folder_name', currentFolder || 'YYYY-MM-DD');  // 선택: 폴더 이름

xhr.send(formData);
```

**데이터 흐름**:
```
브라우저 파일선택
  ↓
FormData 생성 (file + folder_name)
  ↓
POST /api/files/upload
  ↓
Web UI 서버에서 파일 저장
  /app/web_ui/data/uploads/{emp_id}/{folder_name}/{filename}
  ↓
DB에 FileUpload 레코드 저장
  - emp_id, filename, folder_path, upload_date
```

**저장 위치**:
```
Web UI 컨테이너 내부:
  /app/web_ui/data/uploads/{emp_id}/{folder_date}/{filename}.wav

Docker 볼륨 마운트 (양쪽 컨테이너 접근 가능):
  host:/data/uploads ← shared volume
```

**응답**:
```json
{
  "success": true,
  "filename": "recording_20260309_120000.wav",
  "folder_path": "2026-03-09",
  "file_size_mb": 5.2,
  "upload_date": "2026-03-09 12:00:00"
}
```

---

## 🔍 3단계: 분석 시작 (Analysis)

### 엔드포인트: `/api/analysis/start`

**파일**: [web_ui/app/routes/analysis.py](../../web_ui/app/routes/analysis.py)

**호출 방식 (HTML/JavaScript)**:
```javascript
// web_ui/templates/analysis.html
const startAnalysisBtn = document.getElementById('startAnalysisBtn');
startAnalysisBtn.addEventListener('click', async () => {
  const response = await fetch('/api/analysis/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      folder_path: "2026-03-09",           // 분석할 폴더
      include_classification: true,        // 통화 분류 포함 여부
      include_validation: false            // 유효성 검사 포함 여부
    })
  });
  const response_data = await response.json();
  console.log(`Job ID: ${response_data.job_id}`);
});
```

**데이터 흐름**:
```
1. 사용자가 분석 시작 버튼 클릭
   ↓
2. POST /api/analysis/start
   {
     "folder_path": "2026-03-09",
     "include_classification": true,
     "include_validation": false
   }
   ↓
3. AnalysisService.start_analysis() 호출
   - 폴더 해시 계산
   - 형상 변경 여부 확인
   - AnalysisJob 레코드 생성 (status="processing")
   - job_id 반환
   ↓
4. 백그라운드 작업 등록
   background_tasks.add_task(
     AnalysisService.process_analysis_sync,
     job_id, emp_id, folder_path, file_list, ...
   )
   ↓
5. 응답 (202 Accepted)
   {
     "job_id": "job-uuid-xxxx",
     "status": "processing",
     "file_count": 3,
     "started_at": "2026-03-09 12:05:00"
   }
```

**응답 (202 Accepted)**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "file_count": 3,
  "started_at": "2026-03-09T12:05:00",
  "estimated_time_seconds": 180
}
```

---

## 🚀 4단계: 백그라운드 분석 처리

### 함수: `AnalysisService.process_analysis_sync()`

**파일**: [web_ui/app/services/analysis_service.py](../../web_ui/app/services/analysis_service.py)

**실행 흐름**:
```python
# Step 1: 파일 목록 조회
files = [
  "/app/web_ui/data/uploads/{emp_id}/{folder_date}/file1.wav",
  "/app/web_ui/data/uploads/{emp_id}/{folder_date}/file2.wav"
]

# Step 2: 동시성 제어 (MAX_CONCURRENT_ANALYSIS 설정)
for file in files:
    # Step 3: STT API 호출 (아래 참고)
    result = await stt_service.transcribe_local_file(
        file_path=file,
        language="ko",
        is_stream=False,
        privacy_removal=True,      # 개인정보 제거
        classification=True,       # 통화 분류
        element_detection=True,    # 요소 탐지
        agent_url="<ELEMENT_DETECTION_AGENT_URL>",
        ...
    )
    
    # Step 4: 결과 저장
    if result.get('success'):
        save_analysis_result(result)
    else:
        save_analysis_error(result)

# Step 5: AnalysisJob status 업데이트 (processing → completed)
```

---

## 💫 5단계: STT API 호출 (핵심!)

### 호출 함수: `stt_service.transcribe_local_file()`

**파일**: [web_ui/app/services/stt_service.py](../../web_ui/app/services/stt_service.py)

### FormData 구성 방식

**웹 UI 내부 로직** (라인 80-130):
```python
async def transcribe_local_file(
    self,
    file_path: str,                    # "/app/web_ui/data/uploads/..."
    language: str = "ko",
    is_stream: bool = False,
    privacy_removal: bool = False,
    classification: bool = False,
    element_detection: bool = True,
    agent_url: str = "",
    ...
) -> dict:
    """
    ❌ 파일을 읽어서 업로드하지 않음
    ✅ 파일 경로를 String으로 전달
    """
    
    # Step 1: 파일 경로 변환 (볼륨 마운트 경로 처리)
    if file_path.startswith("/app/data/"):
        api_file_path = file_path.replace("/app/data/", "/app/web_ui/data/")
    else:
        api_file_path = file_path
    
    # Step 2: FormData 구성
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        
        # ⭐ 핵심: 파일 경로 String 전달
        data.add_field("file_path", api_file_path)
        
        # 기본 설정
        data.add_field("language", language)
        data.add_field("is_stream", str(is_stream).lower())
        
        # 처리 옵션
        data.add_field("privacy_removal", str(privacy_removal).lower())
        data.add_field("classification", str(classification).lower())
        data.add_field("element_detection", str(element_detection).lower())
        
        # 추가 정보
        if agent_url:
            data.add_field("agent_url", agent_url)
            data.add_field("agent_request_format", "text_only")
        
        # Step 3: API 호출
        async with session.post(
            f"{self.api_url}/transcribe",
            data=data,
            timeout=aiohttp.ClientTimeout(total=600)  # 10분
        ) as response:
            return await response.json()
```

**API 측에서 받는 내용** (app.py 라인 408+):
```python
@app.post("/transcribe")
async def transcribe(request: Request):
    # 1️⃣ FormData 파싱
    form_data = await request.form()
    
    # 2️⃣ 파라미터 추출 (모두 String)
    file_path = form_data.get('file_path')              # "/app/web_ui/data/uploads/..."
    privacy_removal = form_data.get('privacy_removal', 'false')  # "true" 또는 "false"
    classification = form_data.get('classification', 'false')    # "true" 또는 "false"
    element_detection = form_data.get('element_detection', 'false')  # "true" 또는 "false"
    
    # 3️⃣ String을 Boolean으로 변환
    privacy_removal_enabled = privacy_removal.lower() in ['true', '1', 'yes', 'on']
    classification_enabled = classification.lower() in ['true', '1', 'yes', 'on']
    element_detection_enabled = element_detection.lower() in ['true', '1', 'yes', 'on']
    
    # 4️⃣ 처리
    # ... (이후 Privacy, Classification, Element Detection 처리)
```

---

## 📊 전체 데이터 흐름 (요약)

```
브라우저 (Web UI 프론트엔드)
  │
  ├─ 1️⃣ Login
  │  └─ POST /api/auth/login {"emp_id": "000123"}
  │     └─ Response: {emp_id, name, dept}
  │        └─ Session: emp_id 저장
  │
  ├─ 2️⃣ Upload
  │  └─ POST /api/files/upload (multipart/form-data)
  │     └─ file: <binary audio file>
  │     └─ folder_name: "2026-03-09"
  │        └─ Web UI 서버에서 저장
  │           /app/web_ui/data/uploads/{emp_id}/{folder}/{file}
  │        └─ DB에 FileUpload 레코드
  │
  ├─ 3️⃣ Start Analysis
  │  └─ POST /api/analysis/start (application/json)
  │     └─ {folder_path, include_classification, ...}
  │        └─ Response: {job_id, status}
  │        └─ 백그라운드 처리 시작
  │
  └─ 4️⃣ Background Processing (BackgroundTasks)
     │
     ├─ AnalysisService.process_analysis_sync()
     │  ├─ 파일 목록 조회
     │  └─ for each file in files:
     │     │
     │     └─ 5️⃣ STT API 호출
     │        │
     │        └─ stt_service.transcribe_local_file()
     │           │
     │           └─ POST http://stt-api:8003/transcribe (multipart/form-data)
     │              ├─ file_path: "/app/web_ui/data/uploads/..."
     │              ├─ language: "ko"
     │              ├─ privacy_removal: "true"
     │              ├─ classification: "true"
     │              ├─ element_detection: "true"
     │              └─ agent_url: "https://api.kis.com/v1/detect"
     │                 │
     │                 └─ STT API Server
     │                    ├─ 파일 로드 및 검증
     │                    ├─ STT 처리
     │                    ├─ Privacy Removal (LLM)
     │                    ├─ Classification (LLM)
     │                    ├─ Element Detection (외부 API 또는 LLM)
     │                    └─ Response: {
     │                         text, language, backend,
     │                         privacy_result,
     │                         classification_result,
     │                         element_detection_result,
     │                         processing_time
     │                       }
     │
     └─ DB에 AnalysisResult 저장
        └─ Status 업데이트 (processing → completed)

프론트엔드
  └─ 6️⃣ Progress 조회
     └─ GET /api/analysis/progress/{job_id}
        └─ Response: {current_file, progress_percent, ...}

  └─ 7️⃣ Results 조회
     └─ GET /api/analysis/results/{job_id}
        └─ Response: [{filename, text, classification, validation, ...}]
```

---

## 🌍 Docker 환경에서의 경로 해석

### 볼륨 마운트 구성

```yaml
# docker-compose.yml
services:
  web-ui:
    volumes:
      - /data/uploads:/app/web_ui/data/uploads    # ← 공유 볼륨
  
  stt-api:
    volumes:
      - /data/uploads:/app/web_ui/data/uploads    # ← 같은 경로로 마운트
```

### 경로 변환 로직

**Web UI가 파일 저장**:
```
/app/web_ui/data/uploads/000123/2026-03-09/file.wav
```

**Web UI가 API에 전달**:
```python
file_path = "/app/web_ui/data/uploads/000123/2026-03-09/file.wav"
# (변환 로직이 있으면)
# "/app/data/uploads/..." → "/app/web_ui/data/uploads/..."
```

**API가 파일 접근**:
```python
Path(file_path).read_bytes()
# → /app/web_ui/data/uploads/000123/2026-03-09/file.wav 읽음
```

---

## 🔄 환경변수 흐름

### Web UI 환경변수

**파일**: [web_ui/config.py](../../web_ui/config.py)

```python
STT_API_URL = os.getenv("STT_API_URL", "http://stt-api:8003")
STT_API_TIMEOUT = int(os.getenv("STT_API_TIMEOUT", "600"))  # 10분
MAX_CONCURRENT_ANALYSIS = int(os.getenv("MAX_CONCURRENT_ANALYSIS", "5"))
```

### API 환경변수

**파일**: [api_server/app.py](../../api_server/app.py)

```python
# STT 설정
STT_DEVICE = os.getenv("STT_DEVICE", "auto")
STT_PRESET = os.getenv("STT_PRESET", "accuracy")
STT_BACKEND = os.getenv("STT_BACKEND")

# LLM 설정
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001")
VLLM_MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "qwen30_thinking_2507")

# Element Detection
ELEMENT_DETECTION_API_TYPE = os.getenv("ELEMENT_DETECTION_API_TYPE", "fallback")
ELEMENT_DETECTION_AGENT_URL = os.getenv("ELEMENT_DETECTION_AGENT_URL")  # ai_agent 모드 필수
```

---

## 📝 FormData 파라미터 상세 정의

### Web UI → API 호출 시 전달되는 파라미터

| 파라미터 | 타입 | 설정 위치 | 값 예시 | 비고 |
|---------|------|---------|--------|------|
| **file_path** | string | stt_service.py | `/app/web_ui/data/uploads/000123/2026-03-09/file.wav` | 필수 |
| **language** | string | stt_service.py (기본값) | `ko` | 기본: ko |
| **is_stream** | string | stt_service.py (기본값) | `false` | 기본: false |
| **privacy_removal** | string | stt_service.py (매개변수) | `true` 또는 `false` | 기본: false |
| **classification** | string | stt_service.py (매개변수) | `true` 또는 `false` | 기본: false |
| **element_detection** | string | stt_service.py (하드코딩) | `true` | 항상 true |
| **agent_url** | string | stt_service.py (매개변수) | `https://api.kis.com/v1/detect` | 선택사항 |
| **agent_request_format** | string | stt_service.py (하드코딩) | `text_only` | - |

---

## ⚠️ 현재 상태 & 이슈

### 존재하는 문제들

1. **FormData 파라미터 반복**: 
   - Privacy, Classification, Element Detection 각각에서 LLM 모델명을 반복해서 처리 (라인 415-444)
   - 우선순위 로직 (`or os.getenv('X_MODEL_NAME', os.getenv('VLLM_MODEL_NAME', ...))`)이 반복됨

2. **Boolean 문자열 변환**:
   - FormData는 모두 String으로 전달됨 ("true", "false")
   - 각 처리 단계에서 `.lower() in ['true', '1', 'yes', 'on']`로 변환 (라인 461, 468, 475)

3. **환경변수 우선순위 복잡성**:
   - 3개 LLM 모델명 환경변수 (PRIVACY, CLASSIFICATION, DETECTION) + 공통 (VLLM_MODEL_NAME)
   - 우선순위: 요청 파라미터 > 작업별 환경변수 > 공통 환경변수 > 기본값

4. **Element Detection API URL**:
   - ELEMENT_DETECTION_AGENT_URL로 명확하게 통일 (ai_agent 모드 필수)
   - 우선순위: form_data > ELEMENT_DETECTION_AGENT_URL (환경변수) > 기본값

---

## 🎯 리팩토링 계획

### Phase 1: 환경변수 로더 추상화
- `FormDataConfig` 클래스 생성
- 환경변수 우선순위 통합
- `_normalize_model_name()` 개선

### Phase 2: FormData 처리 표준화
- Boolean String 변환 헬퍼 함수
- FormData 검증 함수

### Phase 3: 설정 객체화
- `TranscribeRequest` Pydantic 모델 (Form 파라미터 자동 검증)
- `STTConfig` 클래스 (환경변수 관리)

---

## 📚 참고 문서

- [docs/api/ENVIRONMENT_VARIABLES.md](../api/ENVIRONMENT_VARIABLES.md) - 환경변수 상세 가이드
- [docs/api/API_REFACTORING_SUMMARY.md](../api/API_REFACTORING_SUMMARY.md) - API 구조
- [web_ui/README.md](../../web_ui/README.md) - Web UI 설치 및 실행

---

**작성자**: GitHub Copilot  
**마지막 수정**: 2026년 3월 9일
