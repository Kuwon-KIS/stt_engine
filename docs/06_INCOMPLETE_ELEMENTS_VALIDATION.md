# 불완전판매요소 검증 가이드

## 개요

STT Engine에 불완전판매요소(Incomplete Sales Elements) 검증 기능을 추가했습니다. 통화 기록을 분석하여 완료되지 않은 판매 단계를 식별합니다.

**불완전판매요소:**
- ❌ 고객 요구사항 미확인 - 고객의 실제 필요를 파악하지 못함
- ❌ 제안 부족 - 명확한 솔루션/제안을 제시하지 않음
- ❌ 가격 협상 미완료 - 가격 결정이나 협상이 이루어지지 않음
- ❌ 다음 단계 미정 - 후속 조치가 명확하지 않음
- ❌ 계약 미완료 - 최종 계약이나 서명이 없음

---

## 아키텍처

### 계층 구조

```
┌─────────────────────────────────────────────────────┐
│           Transcribe Endpoint                        │
│     (incomplete_elements_check=true)                 │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│   IncompleteElementsValidator                        │
│   (비즈니스 로직 - 불완전판매요소 검증)              │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│        AgentBackend                                  │
│   (Agent 호출 추상화 - URL + request_format)        │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┴───────────┐
        ▼                        ▼
    ┌─────────┐          ┌─────────────┐
    │ 외부    │          │ vLLM        │
    │ Agent   │          │ /v1/chat    │
    └─────────┘          └─────────────┘
```

### Request Format 선택

| 형식 | 사용처 | 특징 |
|------|--------|------|
| `text_only` | 외부 Agent | 텍스트만 전송 |
| `prompt_based` | vLLM | 프롬프트 템플릿으로 구성 |

---

## API 엔드포인트

### 1. 불완전판매요소 검증 (`POST /ai-agent/incomplete-elements`)

통화 기록에서 불완전판매요소를 검증합니다.

**Request:**
```bash
curl -X POST "http://localhost:8003/ai-agent/incomplete-elements" \
-H "Content-Type: application/json" \
-d '{
    "call_transcript": "안녕하세요... (통화 전사)",
    "agent_url": "http://your-agent:8000",
    "request_format": "text_only",
    "timeout": 30
}'
```

**Parameters:**
- `call_transcript` (required): 통화 전사 텍스트
- `agent_url` (required): Agent 서버 URL
- `request_format` (default: "text_only"): 요청 형식
  - `text_only`: 외부 Agent 
  - `prompt_based`: vLLM
- `timeout` (default: 30): 요청 타임아웃 (초)

**Response:**
```json
{
    "success": true,
    "incomplete_elements": {
        "customer_requirements_not_confirmed": true,
        "proposal_not_made": false,
        "price_negotiation_incomplete": true,
        "next_steps_not_defined": true,
        "contract_not_completed": false,
        "summary": "상세 분석 내용..."
    },
    "analysis": "AI Agent의 상세 분석 텍스트",
    "agent_type": "external",
    "processing_time_sec": 2.5
}
```

**Response Fields:**
- `success`: 검증 성공 여부
- `incomplete_elements`: 불완전판매요소 구조
  - `customer_requirements_not_confirmed`: 고객 요구사항 미확인 여부
  - `proposal_not_made`: 제안 부족 여부
  - `price_negotiation_incomplete`: 가격 협상 미완료 여부
  - `next_steps_not_defined`: 다음 단계 미정 여부
  - `contract_not_completed`: 계약 미완료 여부
  - `summary`: 종합 분석 요약
- `analysis`: Agent의 상세 분석 결과
- `agent_type`: 사용된 Agent 타입 (external 또는 vllm)
- `processing_time_sec`: 처리 시간

---

### 2. 제네릭 Agent 호출 (`POST /ai-agent/process`)

일반적인 텍스트를 Agent로 처리합니다.

**Request:**
```bash
curl -X POST "http://localhost:8003/ai-agent/process" \
-H "Content-Type: application/json" \
-d '{
    "user_query": "처리할 텍스트",
    "agent_url": "http://your-agent:8000",
    "request_format": "text_only",
    "use_streaming": false,
    "chat_thread_id": null,
    "timeout": 30
}'
```

**Parameters:**
- `user_query` (required): 처리할 텍스트
- `agent_url` (required): Agent 서버 URL
- `request_format` (default: "text_only"): 요청 형식
- `use_streaming` (default: false): 스트리밍 모드
- `chat_thread_id` (optional): 대화 연속성을 위한 스레드 ID
- `timeout` (default: 30): 타임아웃 (초)

**Response:**
```json
{
    "success": true,
    "response": "Agent의 응답 텍스트",
    "agent_type": "external",
    "chat_thread_id": "thread_123",
    "processing_time_sec": 2.5
}
```

---

## Transcribe 엔드포인트 통합

### Form Parameters

```bash
curl -X POST "http://localhost:8003/transcribe" \
-F "file_path=/app/audio/call.wav" \
-F "privacy_removal=true" \
-F "classification=true" \
-F "incomplete_elements_check=true" \
-F "agent_url=http://your-agent:8000" \
-F "agent_request_format=text_only"
```

**Parameters:**
- `incomplete_elements_check` (default: false): 불완전판매요소 검증 활성화
- `agent_url`: Agent 서버 URL
- `agent_request_format` (default: text_only): 요청 형식

### Response Structure

```json
{
    "success": true,
    "text": "STT 결과 텍스트",
    "privacy_removal": { /* 개인정보 제거 결과 */ },
    "classification": { /* 통화 분류 결과 */ },
    "incomplete_elements": {
        "customer_requirements_not_confirmed": true,
        "proposal_not_made": false,
        "price_negotiation_incomplete": true,
        "next_steps_not_defined": true,
        "contract_not_completed": false,
        "summary": "..."
    },
    "agent_analysis": "상세 분석 텍스트",
    "agent_type": "external",
    "processing_time_seconds": 15.2
}
```

---

## AgentBackend 구조

Agent 호출을 추상화한 `AgentBackend` 클래스:

```python
agent_backend = get_agent_backend()

result = await agent_backend.call(
    request_text="통화 기록",
    url="http://agent:8000",
    request_format="text_only",  # text_only 또는 prompt_based
    timeout=30
)
```

### Request Format 처리

**text_only (외부 Agent):**
```json
{
    "use_streaming": false,
    "chat_thread_id": null,
    "parameters": {
        "user_query": "텍스트"
    }
}
```

**prompt_based (vLLM):**
```json
{
    "model": "gpt-3.5-turbo",
    "messages": [
        {
            "role": "user",
            "content": "프롬프트 템플릿 + 텍스트"
        }
    ],
    "temperature": 0.7,
    "max_tokens": 2048
}
```

---

## 프롬프트 템플릿

### 불완전판매요소 검증 프롬프트 (prompt_based)

```
당신은 판매 컨설턴트입니다. 다음 통화 기록을 분석하여 불완전판매요소를 식별하세요.

불완전판매요소는:
1. 고객 요구사항 미확인 - 고객의 실제 필요를 파악하지 못함
2. 제안 부족 - 명확한 솔루션/제안을 제시하지 않음
3. 가격 협상 미완료 - 가격 결정이나 협상이 이루어지지 않음
4. 다음 단계 미정 - 후속 조치가 명확하지 않음
5. 계약 미완료 - 최종 계약이나 서명이 없음

통화 내용:
{transcript}

분석 결과를 다음 형식으로 제시하세요:
- 고객 요구사항 확인 여부: [확인됨/미확인]
- 제안 제시 여부: [제시됨/미제시]
- 가격 협상 상태: [완료/진행중/미완료]
- 다음 단계: [명확함/불명확]
- 계약 상태: [완료/미완료]
- 종합 분석: [주요 문제점과 개선 사항]
```

---

## Fallback 체계

Agent 호출 실패 시 자동으로 Dummy Agent로 Fallback:

```
Agent 호출 시도
    │
    ├─ 성공 → 응답 반환
    │
    └─ 실패 (TimeoutError, ConnectionError 등)
       │
       └─ Dummy Agent로 Fallback
          │
          └─ 기본 응답 생성
```

---

## 사용 예시

### 예시 1: Transcribe 엔드포인트에서 불완전판매요소 검증

```bash
curl -X POST "http://localhost:8003/transcribe" \
  -F "file_path=/app/audio/sales_call.wav" \
  -F "language=ko" \
  -F "privacy_removal=true" \
  -F "classification=true" \
  -F "incomplete_elements_check=true" \
  -F "agent_url=http://my-ai-agent:8000" \
  -F "agent_request_format=text_only" | jq '.incomplete_elements'
```

**응답:**
```json
{
    "customer_requirements_not_confirmed": true,
    "proposal_not_made": false,
    "price_negotiation_incomplete": true,
    "next_steps_not_defined": true,
    "contract_not_completed": false,
    "summary": "고객의 예산 범위를 확인하지 않았으며, 다음 미팅 일정이 정해지지 않음..."
}
```

### 예시 2: 직접 불완전판매요소 검증 API 호출

```bash
curl -X POST "http://localhost:8003/ai-agent/incomplete-elements" \
  -H "Content-Type: application/json" \
  -d '{
    "call_transcript": "고객: 이 솔루션이 우리 환경에 맞나요? 판매자: 네, 기본적으로는 맞을 것 같습니다. 고객: 비용은 어느 정도인가요? 판매자: 자세한 견적은 추후에 보내드리겠습니다.",
    "agent_url": "http://my-ai-agent:8000",
    "request_format": "text_only"
  }' | jq '.'
```

**응답:**
```json
{
    "success": true,
    "incomplete_elements": {
        "customer_requirements_not_confirmed": true,
        "proposal_not_made": true,
        "price_negotiation_incomplete": true,
        "next_steps_not_defined": true,
        "contract_not_completed": true,
        "summary": "모든 불완전판매요소가 존재합니다. 고객의 요구사항 확인, 명확한 제안, 가격 협상, 다음 단계 정의가 필요합니다."
    },
    "analysis": "...",
    "agent_type": "external",
    "processing_time_sec": 3.2
}
```

### 예시 3: vLLM을 사용한 검증

```bash
curl -X POST "http://localhost:8003/ai-agent/incomplete-elements" \
  -H "Content-Type: application/json" \
  -d '{
    "call_transcript": "...",
    "agent_url": "http://vllm-server:8001/v1/chat/completions",
    "request_format": "prompt_based"
  }'
```

---

## 환경 변수

필요한 환경 변수는 없습니다. 모든 설정은 요청 시점에 지정합니다.

---

## 문제 해결

### Agent 연결 실패

**증상:** "Connection refused" 또는 "Timeout"

**해결:**
1. Agent 서버가 실행 중인지 확인
2. `agent_url`이 정확한지 확인
3. 네트워크 연결 확인
4. Dummy Agent로 Fallback됨 (기본 응답)

### vLLM 포맷 오류

**증상:** "Invalid JSON" 또는 "400 Bad Request"

**확인:**
- vLLM `/v1/chat/completions` 엔드포인트 지원 여부
- 모델 이름이 올바른지 확인

### 프롬프트 관련 오류

**증상:** Agent가 예상치 못한 응답 반환

**개선:**
- 프롬프트 템플릿 조정
- Agent의 시스템 프롬프트 설정 확인
- Temperature 값 조정 (0.7 기본값)

---

## 베스트 프랙티스

1. **외부 Agent 우선**: `request_format=text_only`로 외부 Agent 사용
2. **vLLM Fallback**: 외부 Agent가 없을 때만 `prompt_based` 사용
3. **타임아웃 설정**: 네트워크 상태에 따라 타임아웃 조정
4. **프롬프트 최적화**: 비즈니스 요구에 맞게 프롬프트 템플릿 커스터마이징

---

## 마이그레이션 가이드 (이전 AI Agent 구조에서)

### 이전 방식 (Deprecated)

```bash
# agent_type으로 구분
curl -X POST "http://localhost:8003/transcribe" \
  -F "ai_agent=true" \
  -F "ai_agent_type=external"
```

### 새로운 방식 (권장)

```bash
# URL과 request_format으로 구분
curl -X POST "http://localhost:8003/transcribe" \
  -F "incomplete_elements_check=true" \
  -F "agent_url=http://your-agent:8000" \
  -F "agent_request_format=text_only"
```

---

## 관련 문서

- [API 서버 아키텍처](./05_API_SERVER_RESTRUCTURING_GUIDE.md)
- [Privacy Removal 가이드](./PRIVACY_REMOVAL_GUIDE.md)
- [Classification 가이드](./docs/classification_guide.md)
