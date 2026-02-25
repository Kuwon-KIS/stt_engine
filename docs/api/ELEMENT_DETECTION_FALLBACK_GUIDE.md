# 요소 탐지 (Element Detection) Fallback 메커니즘 가이드

**작성일**: 2026년 2월 25일  
**버전**: v1.0  
**상태**: ✅ 구현 완료

---

## 개요

요소 탐지 (불완전판매, 부당권유 등) 기능에서 **자동 Fallback 메커니즘**을 통해 높은 가용성을 제공합니다.

**핵심 특징**:
- 🔄 3단계 자동 Fallback
- 🚀 빠른 장애 대응
- 💪 신뢰성 향상
- 📊 상세한 동작 로깅

---

## Fallback 흐름도

```
요소 탐지 요청
     │
     ├─ api_type = "fallback" ?
     │   │
     │   ├─ YES
     │   │   │
     │   │   ├─ 1️⃣ 외부 AI Agent 호출
     │   │   │   ├─ 성공 → 결과 반환 (api_type='external')
     │   │   │   └─ 실패 ↓
     │   │   │
     │   │   ├─ 2️⃣ 로컬 vLLM/Ollama 호출
     │   │   │   ├─ 성공 → 결과 반환 (api_type='local')
     │   │   │   └─ 실패 ↓
     │   │   │
     │   │   └─ 3️⃣ Dummy 결과 반환
     │   │       └─ 결과 반환 (api_type='dummy')
     │   │
     │   └─ NO → 지정된 api_type 사용
     │       ├─ "external" → 외부 API만 호출
     │       └─ "local" → 로컬 LLM만 호출
     │
     └─ 응답 반환
```

---

## API 타입 설명

### 1. `api_type="fallback"` (추천 ⭐)

**특징**: 
- 가장 신뢰성 높은 방식
- 자동으로 최적의 방법 선택
- 모든 방법이 실패해도 dummy 결과 반환

**동작 흐름**:
1. 외부 AI Agent 시도 (빠름, 정확함)
2. 실패 → 로컬 vLLM/Ollama 시도 (느림, 항상 가능)
3. 실패 → Dummy 결과 반환 (모든 요소 미탐지)

**언제 사용?**
- 운영 환경 (프로덕션)
- 높은 가용성이 필요한 경우
- 정확성과 빠른 응답 모두 원할 때

**응답 예시**:
```json
{
  "success": true,
  "detection_results": [
    {
      "type": "incomplete_sales",
      "detected": true,
      "confidence": 0.92,
      "details": "판매 절차 미흡 감지"
    }
  ],
  "api_type": "external",  // 실제로 사용된 방식
  "llm_type": null,
  "fallback_chain": ["external_api"]  // 시도 내역
}
```

---

### 2. `api_type="external"` (외부 API만)

**특징**:
- 외부 AI Agent 만 호출
- Fallback 없음
- API 응답 실패 시 바로 에러 반환

**언제 사용?**
- 외부 AI Agent가 항상 가용할 때
- 빠른 응답이 중요할 때
- 로컬 리소스가 제한적일 때

**응답 예시** (실패 시):
```json
{
  "success": false,
  "error": "External API call failed",
  "api_type": "external"
}
```

---

### 3. `api_type="local"` (로컬 LLM만)

**특징**:
- vLLM 또는 Ollama 사용
- 외부 의존성 없음
- 높은 응답 시간

**언제 사용?**
- 폐쇄망 환경
- 외부 API 불가능할 때
- 완전한 프라이버시 필요할 때

**응답 예시**:
```json
{
  "success": true,
  "detection_results": [...],
  "api_type": "local",
  "llm_type": "vllm"
}
```

---

## API 호출 예제

### 1. Fallback 모드 (추천)

```bash
curl -X POST http://localhost:8003/transcribe \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'file_path=/app/audio/samples/test.wav' \
  -d 'incomplete_elements_check=true' \
  -d 'incomplete_elements_llm_type=fallback' \
  -d 'agent_url=http://your-agent:8080/api/detect'
```

**Python 예제**:
```python
import httpx
import json

async def detect_elements_with_fallback():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8003/transcribe",
            data={
                "file_path": "/app/audio/samples/test.wav",
                "incomplete_elements_check": "true",
                "incomplete_elements_llm_type": "fallback",
                "agent_url": "http://your-agent:8080/api/detect"
            }
        )
        result = response.json()
        
        # fallback_chain으로 사용된 방법 확인
        if 'fallback_chain' in result:
            print(f"Tried methods: {result['fallback_chain']}")
            print(f"Used API type: {result['api_type']}")
```

---

### 2. 외부 API만 사용

```bash
curl -X POST http://localhost:8003/transcribe \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'file_path=/app/audio/samples/test.wav' \
  -d 'incomplete_elements_check=true' \
  -d 'incomplete_elements_llm_type=external' \
  -d 'agent_url=http://your-agent:8080/api/detect'
```

---

### 3. 로컬 LLM만 사용

```bash
curl -X POST http://localhost:8003/transcribe \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'file_path=/app/audio/samples/test.wav' \
  -d 'incomplete_elements_check=true' \
  -d 'incomplete_elements_llm_type=local' \
  -d 'element_detection_llm_type=vllm'
```

---

## 응답 필드 설명

### 기본 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `success` | bool | 전체 작업 성공 여부 |
| `detection_results` | list | 탐지된 요소 목록 |
| `api_type` | str | 실제 사용된 API 방식 (`external`/`local`/`dummy`) |
| `error` | str | 에러 메시지 (실패 시) |

### Fallback 관련 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `fallback_chain` | list | 시도한 방법들의 목록 |
| `llm_type` | str | 사용된 LLM 타입 (`vllm`/`ollama`) |

### 탐지 결과 필드

```json
{
  "type": "incomplete_sales",     // 탐지 요소 타입
  "detected": true,                // 탐지 여부
  "confidence": 0.92,              // 신뢰도 (0.0 ~ 1.0)
  "details": "판매 절차 미흡 감지" // 상세 정보
}
```

---

## Fallback 로직 상세 분석

### 호출 순서와 타임아웃

```
요청 → Fallback 메커니즘
     │
     ├─ [1] 외부 API 호출 (타임아웃: 30초)
     │   ├─ 성공 (HTTP 200) → 결과 반환 ✅
     │   ├─ 타임아웃 → [2]로 이동
     │   ├─ HTTP 에러 → [2]로 이동
     │   └─ 연결 에러 → [2]로 이동
     │
     ├─ [2] 로컬 LLM 호출 (타임아웃: 무제한)
     │   ├─ 성공 → 결과 반환 ✅
     │   ├─ JSON 파싱 실패 → [3]으로 이동
     │   └─ 서버 에러 → [3]으로 이동
     │
     └─ [3] Dummy 결과 반환 (항상 성공)
         └─ api_type='dummy' ✅
```

---

## 로깅 및 모니터링

### 로그 레벨별 정보

```python
# INFO 레벨
[Transcribe/ElementDetection] [Fallback] 단계 1️⃣: 외부 AI Agent 호출 시도...
[Transcribe/ElementDetection] [Fallback] ✅ 단계 1️⃣ 성공 (외부 API 사용)

# WARNING 레벨
[Transcribe/ElementDetection] 외부 API URL이 지정되지 않음
[Transcribe/ElementDetection] 외부 API 호출 실패 (status=500)
[Transcribe/ElementDetection] [Fallback] 단계 3️⃣: 모든 방법 실패, 더미 결과 반환

# ERROR 레벨
[Transcribe/ElementDetection] 요소 탐지 중 오류: ValueError: ...
```

### Fallback 진행 상황 추적

응답에서 `fallback_chain` 필드를 확인하면 어떤 방법들이 시도되었는지 알 수 있습니다:

```json
{
  "fallback_chain": [
    "external_api",     // 1번 시도
    "local_llm(vllm)"   // 2번 시도 (성공)
  ],
  "api_type": "local"
}
```

---

## 성능 고려사항

### 응답 시간 비교

| 방식 | 평균 응답 시간 | 특징 |
|------|----------------|------|
| 외부 API | 1-3초 | 빠름, 외부 의존 |
| vLLM | 5-15초 | 중간, 로컬 실행 |
| Ollama | 10-30초 | 느림, 최대 호환성 |
| Dummy | <100ms | 매우 빠름, 가짜 결과 |

### 네트워크 고려사항

**외부 API 호출 시**:
- 네트워크 지연 발생
- 외부 서비스 가용성 의존
- 방화벽 규칙 필요

**로컬 LLM 사용 시**:
- 네트워크 지연 없음
- GPU/CPU 리소스 소비
- 완전 자율 운영 가능

---

## 운영 권장사항

### 1. 프로덕션 환경

```python
# 추천: Fallback 모드 사용
api_type = "fallback"
external_api_url = "https://your-ai-agent.com/api/detect"
llm_type = "vllm"  # 2단계 Fallback용
```

**이점**:
- ✅ 높은 가용성
- ✅ 자동 장애 대응
- ✅ 운영 부담 감소

---

### 2. 개발/테스트 환경

```python
# 선택 1: 로컬만 사용 (빠른 개발)
api_type = "local"
llm_type = "ollama"  # 작은 모델 사용

# 선택 2: 외부만 사용 (외부 서비스 테스트)
api_type = "external"
external_api_url = "http://localhost:8080/api/detect"
```

---

### 3. 모니터링

```bash
# 로그에서 fallback_chain 분석
grep -i "fallback_chain" /var/log/stt-engine.log | tail -20

# 성공율 통계
grep -c "✅ 단계 1" /var/log/stt-engine.log  # 외부 API 성공
grep -c "✅ 단계 2" /var/log/stt-engine.log  # LLM 성공
grep -c "단계 3" /var/log/stt-engine.log    # Dummy 반환
```

---

## 문제 해결

### 외부 API 계속 실패하는 경우

```
증상: fallback_chain이 항상 ["external_api", "local_llm(vllm)"]
해결:
1. 외부 API 엔드포인트 확인
   curl http://your-agent:8080/api/detect
2. 네트워크 연결 테스트
   ping your-agent
3. 방화벽 규칙 확인
   sudo iptables -L | grep 8080
```

### 로컬 LLM 응답 파싱 실패

```
증상: fallback_chain이 3단계까지 진행 (더미 반환)
로그: "LLM 응답 파싱 실패"
해결:
1. LLM 응답 확인
   curl http://localhost:8000/v1/completions -X POST
2. JSON 형식 검증
3. 모델 업그레이드 확인
```

---

## 기술 상세

### 내부 구현

```python
# 주요 헬퍼 함수들

async def _call_external_api(text, detection_types, external_api_url):
    """외부 API 호출 (실패 시 None 반환)"""
    
async def _call_local_llm(text, detection_types, llm_type, ...):
    """로컬 LLM 호출 (실패 시 None 반환)"""
    
def _get_dummy_results(detection_types):
    """더미 결과 생성 (모든 요소 미탐지)"""
    
async def perform_element_detection(...):
    """메인 함수 (fallback 로직 조율)"""
```

---

## 차이점 정리

### 이전 버전 (Fallback 없음)
```
요청 → API 선택 → 호출 → 실패 → 에러 반환 ❌
```

### 현재 버전 (Fallback 있음)
```
요청 → API 선택
  ├─ fallback: 외부 → LLM → Dummy 자동 시도 ✅
  ├─ external: 외부만 호출
  └─ local: LLM만 호출
```

---

## 추가 리소스

- [LLM Client Factory 문서](./PHASE3_LLM_CLIENT_IMPLEMENTATION.md)
- [API 테스트 가이드](./API_TESTING_GUIDE.md)
- [Docker 배포 가이드](./DOCKER_DEPLOYMENT_GUIDE.md)

---

**작성자**: STT Engine Development Team  
**마지막 수정**: 2026년 2월 25일
