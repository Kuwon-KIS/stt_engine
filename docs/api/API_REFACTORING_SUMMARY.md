# API 리팩토링 및 요소 탐지 구현 완료

**작성일**: 2026년 2월 25일  
**버전**: Phase 2 완료  
**상태**: ✅ 구현 완료 및 테스트 통과

---

## 1. 주요 변경사항

### 1.1 함수명 및 구조 정리

#### ❌ 제거된 항목
- `transcribe_v2()` → `transcribe()` (함수명 정리)
- `perform_ai_agent()` → `perform_element_detection()` (용도 명확화)
- `ai_agent_enabled` → `element_detection_enabled`
- `ai_agent_type` → `detection_api_type`
- `ai_agent_llm_type` → `detection_llm_type`

#### ✅ 추가된 항목
- `element_detection` 파라미터 (기본값: "false")
- `detection_types` 파라미터 (CSV 형식: "incomplete_sales,aggressive_sales")
- `detection_api_type` 파라미터 (값: "external" | "local")
- `detection_llm_type` 파라미터 (값: "openai" | "vllm" | "ollama")

### 1.2 엔드포인트 구조

```
POST /transcribe
├─ 입력
│  ├─ file_path (파일 경로) OR stt_text (텍스트 입력)
│  ├─ privacy_removal (bool) + privacy_llm_type
│  ├─ classification (bool) + classification_llm_type
│  └─ element_detection (bool) + detection_types + detection_api_type + detection_llm_type
│
├─ 처리
│  ├─ 1단계: STT (조건: file_path만 실행)
│  ├─ 2단계: Privacy Removal (선택: privacy_removal=true)
│  ├─ 3단계: Classification (선택: classification=true)
│  └─ 4단계: Element Detection (선택: element_detection=true)
│
└─ 출력
   ├─ stt_text, stt_language, stt_backend, stt_metadata
   ├─ privacy_removal (개인정보 제거 여부)
   ├─ classification (분류: 코드, 카테고리, 신뢰도)
   ├─ element_detection (탐지: 요소 목록, api_type, llm_type)
   └─ processing_steps (각 단계별 완료 상태)
```

---

## 2. 요소 탐지 (Element Detection) 상세

### 2.1 두 가지 운영 방식

#### 방식 1: 외부 API
```python
element_detection=true
detection_types=incomplete_sales,aggressive_sales
detection_api_type=external
external_api_url=http://external-service/detect  # 옵션
```

**동작**:
- 외부 API 엔드포인트 호출
- 탐지 유형별 결과 수신
- 더미 구현 → 실제 통합 필요

#### 방식 2: 로컬 LLM
```python
element_detection=true
detection_types=incomplete_sales,aggressive_sales
detection_api_type=local
detection_llm_type=openai|vllm|ollama
vllm_model_name=meta-llama/Llama-2-7b  # vllm 모드 시
ollama_model_name=mistral               # ollama 모드 시
```

**동작**:
- LLM 클라이언트 선택 (openai/vllm/ollama)
- 텍스트 기반 요소 탐지
- 더미 구현 → Phase 3에서 실제 LLM 통합

### 2.2 응답 형식

```json
{
  "element_detection": [
    {
      "type": "incomplete_sales",
      "detected": false,
      "confidence": 0.0,
      "details": "불완전판매 탐지 대기 중"
    },
    {
      "type": "aggressive_sales",
      "detected": false,
      "confidence": 0.0,
      "details": "부당권유 판매 탐지 대기 중"
    }
  ],
  "element_detection_api_type": "local",
  "element_detection_llm_type": "openai"
}
```

---

## 3. 파라미터 정리

### 3.1 LLM 공급자 선택

| 처리 단계 | 파라미터 | 기본값 | 옵션 |
|---------|---------|-------|------|
| Privacy Removal | `privacy_llm_type` | openai | openai, vllm, ollama |
| Classification | `classification_llm_type` | openai | openai, vllm, ollama |
| Element Detection | `detection_llm_type` | openai | openai, vllm, ollama |

### 3.2 모델명 파라미터

| 파라미터 | 용도 | 예시 |
|---------|------|------|
| `vllm_model_name` | vLLM 모델 지정 | meta-llama/Llama-2-7b |
| `ollama_model_name` | Ollama 모델 지정 | mistral, llama2 |

**사용 방식**:
```bash
# vLLM 사용 시
-F 'privacy_llm_type=vllm' \
-F 'vllm_model_name=meta-llama/Llama-2-7b'

# Ollama 사용 시
-F 'detection_llm_type=ollama' \
-F 'ollama_model_name=mistral'
```

---

## 4. 코드 조직

### 4.1 파일 구조

```
api_server/
├── app.py                      # Main endpoint (transcribe_v2 → transcribe)
├── models.py                   # Pydantic models
│   ├── TranscribeResponse      # element_detection_* 필드 추가
│   ├── ProcessingStepsStatus   # ai_agent → element_detection
│   └── ...
└── transcribe_endpoint.py      # Business logic
    ├── perform_element_detection()  # 요소 탐지 (이전: perform_ai_agent)
    ├── perform_privacy_removal()    # llm_type 파라미터 추가
    ├── perform_classification()     # llm_type 파라미터 추가
    └── build_transcribe_response()  # element_detection_result 파라미터 추가
```

### 4.2 주요 함수 시그니처

**perform_element_detection**
```python
async def perform_element_detection(
    text: str,
    detection_types: list = None,
    api_type: str = "external",
    llm_type: str = "openai",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None,
    classification_result: dict = None,
    privacy_removal_result: dict = None,
    external_api_url: Optional[str] = None
) -> dict
```

**perform_privacy_removal**
```python
async def perform_privacy_removal(
    text: str,
    prompt_type: str,
    llm_type: str = "openai",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None
) -> PrivacyRemovalResult
```

**perform_classification**
```python
async def perform_classification(
    text: str,
    prompt_type: str,
    llm_type: str = "openai",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None
) -> ClassificationResult
```

---

## 5. 테스트 현황

### 5.1 테스트 케이스 (모두 통과 ✅)

| # | 테스트 | 상태 |
|---|--------|------|
| 1 | 외부 API 요소 탐지 | ✅ |
| 2 | 로컬 LLM (OpenAI) 탐지 | ✅ |
| 3 | 로컬 LLM (vLLM) 탐지 | ✅ |
| 4 | 로컬 LLM (Ollama) 탐지 | ✅ |
| 5 | 기본값 테스트 | ✅ |
| 6 | 에러 처리 | ✅ |

**테스트 위치**: `scripts/test_element_detection.py`

### 5.2 실행 방법

```bash
cd /Users/a113211/workspace/stt_engine
python scripts/test_element_detection.py
```

---

## 6. API 사용 예시

### 예 1: 텍스트 입력 + Privacy Removal (OpenAI)

```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=이 전화번호는 010-1234-5678입니다' \
  -F 'privacy_removal=true' \
  -F 'privacy_llm_type=openai'
```

### 예 2: 텍스트 입력 + 모든 처리 (vLLM)

```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=상품을 구매하시겠습니까?' \
  -F 'privacy_removal=true' \
  -F 'privacy_llm_type=vllm' \
  -F 'vllm_model_name=meta-llama/Llama-2-7b' \
  -F 'classification=true' \
  -F 'classification_llm_type=vllm' \
  -F 'element_detection=true' \
  -F 'detection_types=incomplete_sales,aggressive_sales' \
  -F 'detection_api_type=local' \
  -F 'detection_llm_type=vllm'
```

### 예 3: 외부 API 요소 탐지

```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=부당한 권유로 보입니다' \
  -F 'element_detection=true' \
  -F 'detection_types=aggressive_sales' \
  -F 'detection_api_type=external' \
  -F 'external_api_url=http://external-service/detect'
```

---

## 7. 다음 단계 (Phase 3)

### 7.1 LLMClientFactory 구현
- [ ] 추상 클래스: `LLMClient`
- [ ] 구현체: `OpenAIClient`, `vLLMClient`, `OllamaClient`
- [ ] 팩토리: `LLMClientFactory.create_client(llm_type, model_name)`

### 7.2 실제 LLM 통합
- [ ] `perform_privacy_removal()`: LLM 클라이언트 활용
- [ ] `perform_classification()`: LLM 클라이언트 활용
- [ ] `perform_element_detection()`: LLM 클라이언트 활용

### 7.3 외부 API 통합
- [ ] `perform_element_detection(api_type="external")`: HTTP 요청 구현
- [ ] 에러 처리 및 타임아웃 설정
- [ ] 재시도 로직

---

## 8. 주요 설계 결정

### 8.1 후방 호환성 (Backward Compatibility)

모든 새 파라미터에 기본값 설정:
- `privacy_llm_type="openai"` (변경 없음)
- `classification_llm_type="openai"` (변경 없음)
- `element_detection=false` (새 기능 비활성화)
- `detection_api_type="external"` (기존 방식 유지)

기존 클라이언트는 새 파라미터 없이도 정상 작동 ✅

### 8.2 CSV 형식 지원

```python
detection_types = "incomplete_sales,aggressive_sales"
# 자동으로 ["incomplete_sales", "aggressive_sales"]로 파싱
```

### 8.3 이중 구조: External vs Local

- **External**: 별도 서버의 API 호출 (높은 정확도)
- **Local**: 로컬 LLM 활용 (빠른 처리, 개인정보 보호)

---

## 9. 알려진 제한사항

### 현재 구현 (더미)
- `perform_element_detection()`: 더미 응답 반환
- `perform_privacy_removal()`: LLM 선택 인식하나 실제 호출 안 함
- `perform_classification()`: LLM 선택 인식하나 실제 호출 안 함

### Phase 3에서 해결
- LLMClientFactory 구현
- vLLM 클라이언트 (HTTP 요청)
- Ollama 클라이언트 (HTTP 요청)
- 외부 API 통합

---

## 10. 모니터링 및 로깅

### 로그 메시지

```python
# 요소 탐지 시작
logger.info("[Transcribe/ElementDetection] 요소 탐지 시작 (api_type=local, llm_type=openai, ...)")

# 외부 API 호출
logger.info("[Transcribe/ElementDetection] 외부 API 호출 시작 (url=...)")

# 로컬 LLM 사용
logger.info("[Transcribe/ElementDetection] 로컬 LLM 요소 탐지 시작 (llm_type=vllm)")

# 완료
logger.info("[Transcribe/ElementDetection] ✅ 로컬 LLM 처리 완료 (llm_type=vllm, 결과_수=2)")
```

---

## 문서 참고

- [PHASE2_COMPLETION.md](./PHASE2_COMPLETION.md) - Phase 2 상세 완료 보고
- [docs/API_USAGE_GUIDE.md](../API_USAGE_GUIDE.md) - API 사용 가이드

---

**작성자**: AI Assistant  
**최종 수정**: 2026년 2월 25일  
**상태**: Phase 2 완료 → Phase 3 대기
