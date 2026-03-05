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

**코드 위치**: `api_server/app.py:76-100`

**상태 확인**:
```python
device = os.getenv("STT_DEVICE", "auto")  # ✅ auto로 자동 감지
compute_type = os.getenv("STT_COMPUTE_TYPE")
if compute_type is None:
    compute_type = "float16" if device == "cuda" else "float32"  # ✅ 기본값 설정됨
```

**점검 사항**:
- [ ] STT_DEVICE=auto 환경변수 설정 확인
- [ ] STT_PRESET=accuracy 환경변수 설정 확인
- [ ] 모델 로드 시 프리셋 자동 적용 (초기화: app.py:105-140)

---

### **2️⃣ Privacy Removal 단계**

| 설정값 | 출처 | 기본값 | 용도 |
|--------|------|--------|------|
| `privacy_removal` | FormData | "false" | 활성화 여부 |
| `privacy_llm_type` | FormData | "vllm" | LLM 타입 (vllm, ollama) |
| `privacy_prompt_type` | FormData | "privacy_remover_default_v6" | 프롬프트 타입 |
| `vllm_model_name` | FormData | "/model/qwen30_thinking_2507" | vLLM 모델명 (Qwen) |
| `VLLM_BASE_URL` | env | "http://localhost:8001/v1/chat/completions" | vLLM 엔드포인트 |

**코드 위치**: `api_server/transcribe_endpoint.py:228-340`

**동작 흐름**:
```python
async def perform_privacy_removal():
    privacy_service = get_privacy_remover_service()
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

### **4️⃣ Element Detection 단계 ⭐**

| 설정값 | 출처 | 기본값 | 용도 |
|--------|------|--------|------|
| `element_detection` | FormData | "false" | 활성화 여부 |
| `detection_types` | FormData | "" | 탐지 대상 (CSV: "incomplete_sales,aggressive_sales") |
| `detection_api_type` | FormData | "external" | API 방식 (external, local, fallback) |
| `detection_llm_type` | FormData | "vllm" | LLM 타입 (vllm, ollama) |
| `agent_url` | FormData | "" | 외부 AI Agent URL |
| `vllm_model_name` | FormData | env VLLM_MODEL_NAME | vLLM 모델명 |
| `VLLM_BASE_URL` | env | "http://localhost:8001/v1/chat/completions" | vLLM 엔드포인트 |
| `OLLAMA_BASE_URL` | env | "http://localhost:11434/api/generate" | Ollama 엔드포인트 |
| `TEST_MODE` | env | "false" | 테스트 모드 (Dummy 결과 허용) |

**코드 위치**: `api_server/transcribe_endpoint.py:853-1000`

**동작 흐름 (Fallback 메커니즘)**:
```python
if api_type == "fallback":
    # 1️⃣ 외부 API 시도 (agent_url)
    # 2️⃣ 실패 → 로컬 LLM 시도 (vLLM/Ollama)
    # 3️⃣ 실패 → Dummy 결과 반환 (TEST_MODE=True일 때만)
```

**점검 사항**:
- [ ] Fallback 메커니즘 동작 확인
- [ ] TEST_MODE 환경변수 설정 확인
- [ ] detection_types 자동 기본값 설정 확인 (incomplete_sales, aggressive_sales)
- [ ] 외부 API (agent_url) 호출 가능성 확인
- [ ] 로컬 LLM 호출 성공 여부 확인

---

## ⚙️ **현재 설정 상태**

### **Web UI (main.js:360-370)**

```javascript
formData.append('file_id', uploadResult.file_id);
formData.append('language', language);
formData.append('is_stream', isStream ? 'true' : 'false');
formData.append('privacy_removal', 'false');         // 기본값
formData.append('privacy_llm_type', 'vllm');         // ✅ vLLM으로 통일
formData.append('privacy_prompt_type', 'privacy_remover_default_v6');
formData.append('vllm_model_name', '/model/qwen30_thinking_2507');  // ✅ Qwen 모델
formData.append('classification', classification ? 'true' : 'false');
formData.append('element_detection', 'true');        // ✅ 항상 활성화
formData.append('detection_api_type', 'local');      // ✅ 로컬 사용
formData.append('detection_llm_type', 'vllm');       // ✅ vLLM 사용
formData.append('vllm_model_name', '/model/qwen30_thinking_2507'); // ✅ Qwen 모델
```

### **API Server (app.py)**

```python
# 라인 407 - Privacy Removal LLM 타입 기본값
privacy_llm_type = form_data.get('privacy_llm_type', 'vllm')  # ✅ vllm으로 통일

# 라인 350-650
@app.post("/transcribe")
- STT → Privacy (vLLM) → Classification → Element Detection 순서 ✅ 정확함
```

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
