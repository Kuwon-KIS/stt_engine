# Phase 3: LLM Client Factory Implementation - 완료

**완료일**: 2026년 2월 25일  
**상태**: ✅ 아키텍처 설계 및 기본 구현 완료

---

## 개요

Phase 3에서는 다중 LLM 제공자를 지원하기 위한 LLM Client Factory 패턴을 구현했습니다. vLLM과 Ollama 등 로컬 LLM 제공자에 대한 통일된 인터페이스를 제공합니다.

---

## 구현 내용

### 1. 아키텍처 설계

```
api_server/llm_clients/
├── __init__.py           # 패키지 초기화, 공개 API
├── base.py              # 추상 기본 클래스 (LLMClient)
├── vllm_client.py       # vLLM 로컬 서버 구현
├── ollama_client.py     # Ollama 로컬 서버 구현
└── factory.py           # LLMClientFactory (클라이언트 생성)
```

### 2. 구현된 클래스

#### LLMClient (추상 기본 클래스)
- **위치**: `api_server/llm_clients/base.py`
- **메서드**:
  - `async call()`: LLM 호출 (프롬프트 → 응답)
  - `async is_available()`: 서버 가용성 확인

#### vLLMClient
- **위치**: `api_server/llm_clients/vllm_client.py`
- **특징**:
  - vLLM 로컬 서버 통신 (HTTP API)
  - 기본 URL: `http://localhost:8000`
  - `/v1/completions` 엔드포인트 사용
  - 로컬 LLM 실행 (오프라인)

#### OllamaClient
- **위치**: `api_server/llm_clients/ollama_client.py`
- **특징**:
  - Ollama 로컬 서버 통신 (HTTP API)
  - 기본 URL: `http://localhost:11434`
  - `/api/generate` 엔드포인트 사용
  - 로컬 LLM 실행 (오프라인)

#### LLMClientFactory
- **위치**: `api_server/llm_clients/factory.py`
- **메서드**:
  - `create_client()`: 새 클라이언트 인스턴스 생성 (기본값: vllm)
  - `get_cached_client()`: 캐시된 클라이언트 조회/재사용
- **사용 예**:
  ```python
  # vLLM 클라이언트 생성 (기본값)
  client = LLMClientFactory.create_client(
      model_name="mistral-7b",
      vllm_api_url="http://localhost:8000"
  )
  
  # Ollama 클라이언트 생성
  client = LLMClientFactory.create_client(
      llm_type="ollama",
      model_name="llama2",
      ollama_api_url="http://localhost:11434"
  )
  ```

---

## 통합 구현

### perform_classification() 업데이트

```python
async def perform_classification(
    text: str,
    prompt_type: str,
    llm_type: str = "vllm",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None
) -> Optional[ClassificationResult]:
```

**변경사항**:
- ✅ 더미 구현 → 실제 LLM 호출
- ✅ LLMClientFactory 사용하여 클라이언트 생성
- ✅ 프롬프트 기반 분류 수행
- ✅ JSON 응답 파싱

**지원 분류**:
- TELEMARKETING (텔레마케팅)
- CUSTOMER_SERVICE (고객 서비스)
- SALES (직판 영업)
- SURVEY (설문조사)
- SCAM (사기/불법)
- UNKNOWN (분류 불가)

### perform_element_detection() 업데이트

```python
async def perform_element_detection(
    text: str,
    detection_types: list = None,
    api_type: str = "external",
    llm_type: str = "vllm",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None,
    ...
) -> dict:
```

**변경사항**:
- ✅ api_type="local" 모드 구현 (LLM 기반 탐지)
- ✅ LLMClientFactory 사용
- ✅ 구조화된 JSON 응답 처리
- ✅ 다중 요소 탐지 지원

**동작 모드**:
1. **external**: 외부 API 호출 (기존 더미 구현 유지)
2. **local**: 로컬 LLM 사용 (새로 구현)

---

## 사용 방법

### 1. API 호출 (Privacy Removal + Classification + Detection)

```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=테스트 텍스트입니다' \
  -F 'privacy_removal=true' \
  -F 'privacy_llm_type=vllm' \
  -F 'classification=true' \
  -F 'classification_llm_type=vllm' \
  -F 'classification_prompt_type=classification_default_v1' \
  -F 'element_detection=true' \
  -F 'detection_api_type=local' \
  -F 'detection_llm_type=ollama' \
  -F 'detection_types=incomplete_sales,aggressive_sales'
```

### 2. 다양한 LLM 조합

```bash
# 모든 단계에서 vLLM 사용 (기본값)
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=테스트' \
  -F 'privacy_removal=true' \
  -F 'privacy_llm_type=vllm' \
  -F 'classification=true' \
  -F 'classification_llm_type=vllm' \
  -F 'element_detection=true' \
  -F 'detection_api_type=local' \
  -F 'detection_llm_type=vllm'

# vLLM + Ollama 하이브리드
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=테스트' \
  -F 'privacy_removal=true' \
  -F 'privacy_llm_type=vllm' \
  -F 'vllm_model_name=mistral-7b' \
  -F 'classification=true' \
  -F 'classification_llm_type=ollama' \
  -F 'ollama_model_name=neural-chat'
```

---

## 환경 설정

### vLLM 시작 (로컬)

```bash
# vLLM 서버 시작 (기본 포트: 8000)
python -m vllm.entrypoints.openai.api_server \
  --model mistral-7b-instruct-v0.2 \
  --host 0.0.0.0 \
  --port 8000
```

### Ollama 시작 (로컬)

```bash
# Ollama 시작 (기본 포트: 11434)
ollama serve

# 별도 터미널에서 모델 다운로드
ollama pull neural-chat
ollama pull llama2
```

---

## 프로토콜 상세

### vLLM API
```json
POST http://localhost:8000/v1/completions
{
  "model": "mistral-7b",
  "prompt": "프롬프트",
  "temperature": 0.7,
  "max_tokens": 2000,
  "top_p": 0.95
}
```

### Ollama API
```json
POST http://localhost:11434/api/generate
{
  "model": "neural-chat",
  "prompt": "프롬프트",
  "temperature": 0.7,
  "num_predict": 2000,
  "stream": false
}
```

---

## 응답 형식

### Classification 응답

```json
{
  "success": true,
  "processing_steps": {
    "privacy_removal": true,
    "classification": true,
    "element_detection": false
  },
  "privacy_removal_result": {
    "privacy_exist": "N",
    "text": "정제된 텍스트..."
  },
  "classification_result": {
    "code": "TELEMARKETING",
    "category": "TELEMARKETING",
    "confidence": 0.95,
    "reason": "LLM-based classification"
  },
  "element_detection_result": null
}
```

### Element Detection 응답

```json
{
  "success": true,
  "element_detection_result": {
    "success": true,
    "detection_results": [
      {
        "type": "incomplete_sales",
        "detected": true,
        "confidence": 0.87,
        "details": "발견된 내용: 약관 미설명..."
      },
      {
        "type": "aggressive_sales",
        "detected": false,
        "confidence": 0.2,
        "details": "적대적 판매 행위 감지 안됨"
      }
    ],
    "api_type": "local",
    "llm_type": "ollama"
  }
}
```

---

## 에러 처리

### LLM 서버 연결 실패

```
[OllamaClient] Availability check failed: Connection refused
[LLMClientFactory] Creating OllamaClient failed
Error: Failed to connect to LLM server
```

**해결방법**:
1. 로컬 LLM 서버 실행 확인
2. URL 및 포트 확인
3. 방화벽 설정 확인

### 타임아웃

```
[vLLMClient] Timeout: Request timeout after 300 seconds
```

**해결방법**:
1. 모델 크기 확인 (큰 모델은 오래 걸림)
2. `max_tokens` 감소
3. 타임아웃 값 증가

---

## 테스트

### 단위 테스트 예제

```python
import asyncio
from api_server.llm_clients import LLMClientFactory

async def test_vllm():
    client = LLMClientFactory.create_client(
        llm_type="vllm",
        model_name="mistral-7b"
    )
    response = await client.call(prompt="Hello, how are you?")
    print(f"vLLM: {response}")

async def test_ollama():
    client = LLMClientFactory.create_client(
        llm_type="ollama",
        model_name="neural-chat"
    )
    response = await client.call(prompt="Hello, how are you?")
    print(f"Ollama: {response}")

# 실행
asyncio.run(test_vllm())
asyncio.run(test_ollama())
```

---

## 파일 목록

| 파일 | 설명 | 상태 |
|------|------|------|
| `api_server/llm_clients/__init__.py` | 패키지 초기화 | ✅ |
| `api_server/llm_clients/base.py` | LLMClient 추상 클래스 | ✅ |
| `api_server/llm_clients/vllm_client.py` | vLLM 구현 | ✅ |
| `api_server/llm_clients/ollama_client.py` | Ollama 구현 | ✅ |
| `api_server/llm_clients/factory.py` | LLMClientFactory | ✅ |
| `api_server/transcribe_endpoint.py` | 통합 (perform_classification, perform_element_detection) | ✅ |

---

## 다음 단계

1. **실제 LLM 서버 통합 테스트**
   - vLLM 서버 실행
   - Ollama 서버 실행
   - 각 모드별 테스트

2. **성능 최적화**
   - 캐싱 전략 개선
   - 연결 풀 관리
   - 응답 시간 모니터링

3. **프롬프트 최적화**
   - Classification 프롬프트 개선
   - Detection 프롬프트 개선
   - 응답 정확도 향상

4. **에러 처리 강화**
   - 재시도 로직
   - Fallback 메커니즘
   - 타임아웃 관리

---

## 참고 자료

- **vLLM**: https://docs.vllm.ai/en/latest/
- **Ollama**: https://github.com/ollama/ollama

---

**작성**: GitHub Copilot  
**완료일**: 2026년 2월 25일

---

## 구현 내용

### 1. 아키텍처 설계

```
api_server/llm_clients/
├── __init__.py           # 패키지 초기화, 공개 API
├── base.py              # 추상 기본 클래스 (LLMClient)
├── openai_client.py     # OpenAI API 구현
├── vllm_client.py       # vLLM 로컬 서버 구현
├── ollama_client.py     # Ollama 로컬 서버 구현
└── factory.py           # LLMClientFactory (클라이언트 생성)
```

### 2. 구현된 클래스

#### LLMClient (추상 기본 클래스)
- **위치**: `api_server/llm_clients/base.py`
- **메서드**:
  - `async call()`: LLM 호출 (프롬프트 → 응답)
  - `async is_available()`: 서버 가용성 확인

#### OpenAIClient
- **위치**: `api_server/llm_clients/openai_client.py`
- **특징**:
  - OpenAI API 사용 (gpt-4, gpt-3.5-turbo 등)
  - 환경변수 `OPENAI_API_KEY` 지원
  - Chat completions API 사용
  - 온라인 서비스 (API 호출)

#### vLLMClient
- **위치**: `api_server/llm_clients/vllm_client.py`
- **특징**:
  - vLLM 로컬 서버 통신 (HTTP API)
  - 기본 URL: `http://localhost:8000`
  - `/v1/completions` 엔드포인트 사용
  - 로컬 LLM 실행 (오프라인)

#### OllamaClient
- **위치**: `api_server/llm_clients/ollama_client.py`
- **특징**:
  - Ollama 로컬 서버 통신 (HTTP API)
  - 기본 URL: `http://localhost:11434`
  - `/api/generate` 엔드포인트 사용
  - 로컬 LLM 실행 (오프라인)

#### LLMClientFactory
- **위치**: `api_server/llm_clients/factory.py`
- **메서드**:
  - `create_client()`: 새 클라이언트 인스턴스 생성
  - `get_cached_client()`: 캐시된 클라이언트 조회/재사용
- **사용 예**:
  ```python
  # OpenAI 클라이언트 생성
  client = LLMClientFactory.create_client(
      llm_type="openai",
      model_name="gpt-4"
  )
  
  # vLLM 클라이언트 생성
  client = LLMClientFactory.create_client(
      llm_type="vllm",
      model_name="mistral-7b",
      vllm_api_url="http://localhost:8000"
  )
  
  # Ollama 클라이언트 생성
  client = LLMClientFactory.create_client(
      llm_type="ollama",
      model_name="llama2",
      ollama_api_url="http://localhost:11434"
  )
  ```

---

## 통합 구현

### perform_classification() 업데이트

```python
async def perform_classification(
    text: str,
    prompt_type: str,
    llm_type: str = "vllm",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None
) -> Optional[ClassificationResult]:
```

**변경사항**:
- ✅ 더미 구현 → 실제 LLM 호출
- ✅ LLMClientFactory 사용하여 클라이언트 생성
- ✅ 프롬프트 기반 분류 수행
- ✅ JSON 응답 파싱

**지원 분류**:
- TELEMARKETING (텔레마케팅)
- CUSTOMER_SERVICE (고객 서비스)
- SALES (직판 영업)
- SURVEY (설문조사)
- SCAM (사기/불법)
- UNKNOWN (분류 불가)

### perform_element_detection() 업데이트

```python
async def perform_element_detection(
    text: str,
    detection_types: list = None,
    api_type: str = "external",
    llm_type: str = "vllm",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None,
    ...
) -> dict:
```

**변경사항**:
- ✅ api_type="local" 모드 구현 (LLM 기반 탐지)
- ✅ LLMClientFactory 사용
- ✅ 구조화된 JSON 응답 처리
- ✅ 다중 요소 탐지 지원

**동작 모드**:
1. **external**: 외부 API 호출 (기존 더미 구현 유지)
2. **local**: 로컬 LLM 사용 (vLLM/Ollama)

---

## 사용 방법

### 1. API 호출 (Privacy Removal + Classification + Detection)

```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=테스트 텍스트입니다' \
  -F 'privacy_removal=true' \
  -F 'privacy_llm_type=openai' \
  -F 'classification=true' \
  -F 'classification_llm_type=vllm' \
  -F 'classification_prompt_type=classification_default_v1' \
  -F 'element_detection=true' \
  -F 'detection_api_type=local' \
  -F 'detection_llm_type=ollama' \
  -F 'detection_types=incomplete_sales,aggressive_sales'
```

### 2. 다양한 LLM 조합

```bash
# vLLM만 사용
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=테스트' \
  -F 'classification=true' \
  -F 'classification_llm_type=vllm' \
  -F 'element_detection=true' \
  -F 'detection_api_type=local' \
  -F 'detection_llm_type=vllm'

# vLLM + Ollama 하이브리드
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=테스트' \
  -F 'classification=true' \
  -F 'classification_llm_type=vllm' \
  -F 'vllm_model_name=mistral-7b' \
  -F 'element_detection=true' \
  -F 'detection_api_type=local' \
  -F 'detection_llm_type=ollama' \
  -F 'ollama_model_name=neural-chat'
```

---

## 환경 설정

### vLLM 시작 (로컬)

```bash
# vLLM 서버 시작 (기본 포트: 8000)
python -m vllm.entrypoints.openai.api_server \
  --model mistral-7b-instruct-v0.2 \
  --host 0.0.0.0 \
  --port 8000
```

### Ollama 시작 (로컬)

```bash
# Ollama 시작 (기본 포트: 11434)
ollama serve

# 별도 터미널에서 모델 다운로드
ollama pull neural-chat
ollama pull llama2
```

---

## 프로토콜 상세

### vLLM API
```json
POST http://localhost:8000/v1/completions
{
  "model": "mistral-7b",
  "prompt": "프롬프트",
  "temperature": 0.7,
  "max_tokens": 2000,
  "top_p": 0.95
}
```

### Ollama API
```json
POST http://localhost:11434/api/generate
{
  "model": "neural-chat",
  "prompt": "프롬프트",
  "temperature": 0.7,
  "num_predict": 2000,
  "stream": false
}
```

---

## 응답 형식

### Classification 응답

```json
{
  "success": true,
  "processing_steps": {
    "privacy_removal": true,
    "classification": true,
    "element_detection": false
  },
  "privacy_removal_result": {
    "privacy_exist": "N",
    "text": "정제된 텍스트..."
  },
  "classification_result": {
    "code": "TELEMARKETING",
    "category": "TELEMARKETING",
    "confidence": 0.95,
    "reason": "LLM-based classification"
  },
  "element_detection_result": null
}
```

### Element Detection 응답

```json
{
  "success": true,
  "element_detection_result": {
    "success": true,
    "detection_results": [
      {
        "type": "incomplete_sales",
        "detected": true,
        "confidence": 0.87,
        "details": "발견된 내용: 약관 미설명..."
      },
      {
        "type": "aggressive_sales",
        "detected": false,
        "confidence": 0.2,
        "details": "적대적 판매 행위 감지 안됨"
      }
    ],
    "api_type": "local",
    "llm_type": "ollama"
  }
}
```

---

## 에러 처리

### LLM 서버 연결 실패

```
[OllamaClient] Availability check failed: Connection refused
[LLMClientFactory] Creating OllamaClient failed
Error: Failed to connect to LLM server
```

**해결방법**:
1. 로컬 LLM 서버 실행 확인
2. URL 및 포트 확인
3. 방화벽 설정 확인

### OpenAI API 키 없음

```
[OpenAIClient] OpenAI API key not found
[OpenAIClient] Availability check failed: API key required
```

**해결방법**:
```bash
export OPENAI_API_KEY="sk-..."
```

### 타임아웃

```
[vLLMClient] Timeout: Request timeout after 300 seconds
```

**해결방법**:
1. 모델 크기 확인 (큰 모델은 오래 걸림)
2. `max_tokens` 감소
3. 타임아웃 값 증가

---

## 테스트

### 단위 테스트 예제

```python
import asyncio
from api_server.llm_clients import LLMClientFactory

async def test_openai():
    client = LLMClientFactory.create_client(llm_type="openai")
    response = await client.call(prompt="Hello, how are you?")
    print(f"OpenAI: {response}")

async def test_vllm():
    client = LLMClientFactory.create_client(
        llm_type="vllm",
        model_name="mistral-7b"
    )
    response = await client.call(prompt="Hello, how are you?")
    print(f"vLLM: {response}")

# 실행
asyncio.run(test_openai())
asyncio.run(test_vllm())
```

---

## 파일 목록

| 파일 | 설명 | 상태 |
|------|------|------|
| `api_server/llm_clients/__init__.py` | 패키지 초기화 | ✅ |
| `api_server/llm_clients/base.py` | LLMClient 추상 클래스 | ✅ |
| `api_server/llm_clients/openai_client.py` | OpenAI 구현 | ✅ |
| `api_server/llm_clients/vllm_client.py` | vLLM 구현 | ✅ |
| `api_server/llm_clients/ollama_client.py` | Ollama 구현 | ✅ |
| `api_server/llm_clients/factory.py` | LLMClientFactory | ✅ |
| `api_server/transcribe_endpoint.py` | 통합 (perform_classification, perform_element_detection) | ✅ |

---

## 다음 단계

1. **실제 LLM 서버 통합 테스트**
   - vLLM 서버 실행
   - Ollama 서버 실행
   - 각 모드별 테스트

2. **성능 최적화**
   - 캐싱 전략 개선
   - 연결 풀 관리
   - 응답 시간 모니터링

3. **프롬프트 최적화**
   - Classification 프롬프트 개선
   - Detection 프롬프트 개선
   - 응답 정확도 향상

4. **에러 처리 강화**
   - 재시도 로직
   - Fallback 메커니즘
   - 타임아웃 관리

---

## 참고 자료

- **OpenAI API**: https://platform.openai.com/docs/api-reference
- **vLLM**: https://docs.vllm.ai/en/latest/
- **Ollama**: https://github.com/ollama/ollama

---

**작성**: GitHub Copilot  
**완료일**: 2026년 2월 25일
