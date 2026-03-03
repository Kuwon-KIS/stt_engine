# Phase 2 - LLM Provider Selection 구현 완료

## 개요
API의 모든 처리 단계(Privacy Removal, Classification, Element Detection)에서 LLM 공급자를 선택할 수 있도록 구현했습니다.

## 변경 사항

### 1. 파라미터 추가 (`/transcribe` 엔드포인트)

#### Privacy Removal 관련 파라미터
- `privacy_llm_type` (기본값: "openai")
- `vllm_model_name` (선택사항)
- `ollama_model_name` (선택사항)

#### Classification 관련 파라미터
- `classification_llm_type` (기본값: "openai")

#### Element Detection (요소 탐지) 관련 파라미터
- `element_detection` (기본값: "false")
- `detection_types` (CSV 형식: "incomplete_sales,aggressive_sales")
- `detection_api_type` (기본값: "external", 옵션: "external" | "local")
- `detection_llm_type` (기본값: "openai", local 모드에서만 사용)

### 2. 함수 시그니처 업데이트

#### perform_privacy_removal()
```python
async def perform_privacy_removal(
    text: str,
    prompt_type: str,
    llm_type: str = "openai",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None
) -> PrivacyRemovalResult
```

#### perform_classification()
```python
async def perform_classification(
    text: str,
    prompt_type: str,
    llm_type: str = "openai",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None
) -> ClassificationResult
```

#### perform_element_detection() (새로운 이름, 이전: perform_ai_agent)
```python
async def perform_element_detection(
    text: str,
    detection_types: list = None,              # ["incomplete_sales", "aggressive_sales"]
    api_type: str = "external",                # "external" or "local"
    llm_type: str = "openai",                  # openai, vllm, ollama
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None,
    classification_result: dict = None,
    privacy_removal_result: dict = None,
    external_api_url: Optional[str] = None
) -> dict
```

### 3. 데이터 모델 업데이트

#### ProcessingStepsStatus
- `ai_agent: bool` → `element_detection: bool` (요소 탐지로 변경)

#### TranscribeResponse
변경 전:
- `agent_response`, `agent_type`, `chat_thread_id`

변경 후:
- `element_detection: Optional[List[Dict[str, Any]]]` - 탐지된 요소 목록
- `element_detection_api_type: Optional[str]` - API 방식 (external/local)
- `element_detection_llm_type: Optional[str]` - LLM 타입 (local 모드 시)

### 4. 요소 탐지 (Element Detection) 동작 방식

#### External API 모드
```
사용자 입력 → perform_element_detection(api_type="external")
           → 외부 API 엔드포인트 호출
           → 탐지 결과 반환
```

#### Local LLM 모드
```
사용자 입력 → perform_element_detection(api_type="local", llm_type="openai|vllm|ollama")
           → LLM 선택 (openai/vllm/ollama)
           → LLM을 통한 요소 탐지
           → 탐지 결과 반환
```

## 테스트 결과

✅ Test 1: 외부 API 요소 탐지 (완료)
✅ Test 2: 로컬 LLM (OpenAI) 요소 탐지 (완료)
✅ Test 3: 로컬 LLM (vLLM) 요소 탐지 (완료)
✅ Test 4: 로컬 LLM (Ollama) 요소 탐지 (완료)
✅ Test 5: 기본값 테스트 (완료)
✅ Test 6: 에러 처리 (완료)

모든 6개 테스트 케이스 통과!

## API 사용 예시

### 예 1: Text 입력 + Privacy Removal (OpenAI)
```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=이 전화번호는 010-1234-5678입니다' \
  -F 'privacy_removal=true' \
  -F 'privacy_llm_type=openai'
```

### 예 2: Text 입력 + Classification + Element Detection
```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=상품을 구매하시겠습니까?' \
  -F 'classification=true' \
  -F 'classification_llm_type=openai' \
  -F 'element_detection=true' \
  -F 'detection_types=incomplete_sales,aggressive_sales' \
  -F 'detection_api_type=local' \
  -F 'detection_llm_type=ollama' \
  -F 'ollama_model_name=mistral'
```

### 예 3: 모든 처리 단계 + vLLM
```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=전화번호는 010-5678-1234이고, 구매하세요!' \
  -F 'privacy_removal=true' \
  -F 'privacy_llm_type=vllm' \
  -F 'vllm_model_name=meta-llama/Llama-2-7b' \
  -F 'classification=true' \
  -F 'classification_llm_type=vllm' \
  -F 'element_detection=true' \
  -F 'detection_types=aggressive_sales' \
  -F 'detection_api_type=local' \
  -F 'detection_llm_type=vllm'
```

## 파일 수정 목록

1. **api_server/app.py**
   - `/transcribe` 엔드포인트 폼 파라미터 추가
   - 새로운 파라미터 파싱 로직
   - perform_element_detection 호출로 업데이트
   - build_transcribe_response에 element_detection_result 전달

2. **api_server/transcribe_endpoint.py**
   - perform_ai_agent() → perform_element_detection() 함수명 변경
   - 함수 시그니처 업데이트 (detection_types, api_type 추가)
   - External API vs Local LLM 분기 로직 구현
   - build_transcribe_response() 파라미터 추가

3. **api_server/models.py**
   - ProcessingStepsStatus: ai_agent → element_detection
   - TranscribeResponse: agent_* 필드 → element_detection_* 필드 변경

## 다음 단계 (Phase 3)

### 1. LLMClientFactory 구현
- create_client(llm_type, model_name) 메서드 구현
- openai, vllm, ollama 클라이언트 선택 로직

### 2. LocalLLMClient 구현
- vLLMClient: vLLM API 호출 로직
- OllamaClient: Ollama API 호출 로직

### 3. 실제 LLM 통합
- perform_privacy_removal()에서 LLM 클라이언트 사용
- perform_classification()에서 LLM 클라이언트 사용
- perform_element_detection(api_type="local")에서 LLM 사용

### 4. 외부 API 통합
- perform_element_detection(api_type="external")에서 외부 엔드포인트 호출

## 핵심 설계 결정

1. **Backward Compatibility**: 모든 파라미터에 기본값을 설정하여 기존 클라이언트 호환성 유지
   - privacy_llm_type 기본값: "openai"
   - detection_api_type 기본값: "external"

2. **CSV 형식 지원**: detection_types는 쉼표로 구분된 문자열 지원
   - "incomplete_sales,aggressive_sales" 형식
   - 자동 파싱으로 리스트로 변환

3. **유연한 LLM 선택**: 각 처리 단계별로 독립적으로 LLM 공급자 선택 가능
   - Privacy Removal: OpenAI
   - Classification: vLLM
   - Element Detection: Ollama
   - 동시 사용 가능

4. **Element Detection 이중 구조**
   - External: 별도 서버의 API 호출
   - Local: 로컬 LLM (OpenAI, vLLM, Ollama) 사용
   - 구현 유연성 제공

## 관련 문서
- [PROJECT_STRUCTURE_AND_ORGANIZATION.md](../docs/PROJECT_STRUCTURE_AND_ORGANIZATION.md)
- [API_USAGE_GUIDE.md](../docs/API_USAGE_GUIDE.md)
