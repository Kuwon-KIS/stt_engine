# 환경변수 및 서비스 Alignment 분석 보고서
**작성일**: 2026년 3월 9일  
**대상**: commit 0037892 이후 작업 검토  
**범위**: 환경변수 표준화, 레거시 제거, web_ui ↔ API 흐름 정렬

---

## 1. 작업 요약

### 1.1 주요 커밋 (8개)

| 커밋 | 제목 | 변경 영역 |
|------|------|---------|
| 117705d | docs: Add comprehensive API flow analysis documentation | 문서 |
| 07732d1 | refactor: Implement FormDataConfig abstraction layer | API Config |
| edb38d8 | docs: Update environment variable references | 문서 |
| b86179e | refactor: Remove redundant 'fast' preset | Performance |
| 87eae2f | perf: Optimize transformers backend with num_beams=2 | STT Engine |
| f5317c4 | fix: Restore missing get_device() method | Bug Fix |
| 040b400 | refactor: Standardize privacy removal naming | Service |
| 6b288c7 | chore: Remove old privacy_remover.py file | Cleanup |
| 3dd8cff | refactor: Load vLLM prompts from files | Prompt Loading |

### 1.2 작업 분류

| 카테고리 | 항목 수 | 우선순위 |
|---------|--------|---------|
| 환경변수 표준화 | 3건 | 🔴 높음 |
| 서비스 아키텍처 | 3건 | 🔴 높음 |
| 레거시 제거 | 2건 | 🟡 중간 |
| 성능 최적화 | 2건 | 🟢 낮음 |

---

## 2. 환경변수 Alignment 현황

### 2.1 표준화된 환경변수 명명 규칙

```
[TASK]_[COMPONENT]_[PROPERTY]

예:
- PRIVACY_REMOVAL_VLLM_MODEL_NAME      (vLLM 모델)
- CLASSIFICATION_VLLM_MODEL_NAME        (vLLM 모델)
- ELEMENT_DETECTION_AGENT_URL          (AI Agent URL)
- ELEMENT_DETECTION_VLLM_MODEL_NAME    (vLLM 모델)
```

### 2.2 Task별 환경변수 매핑

#### Privacy Removal
```
우선순위: FormData → 작업별 환경변수 → 공용 환경변수 → 기본값

설정 항목:
1. ✅ PRIVACY_REMOVAL_VLLM_MODEL_NAME
   - FormData: privacy_vllm_model_name
   - Default: VLLM_MODEL_NAME → qwen30_thinking_2507

2. ✅ PRIVACY_REMOVAL_VLLM_API_BASE
   - FormData: privacy_vllm_api_base
   - Default: config.get_vllm_api_base('privacy_removal') → http://localhost:8001/v1

3. ✅ PRIVACY_REMOVAL_PROMPT_TYPE
   - FormData: privacy_prompt_type
   - Default: privacy_remover_default_v6
```

#### Classification
```
설정 항목:
1. ✅ CLASSIFICATION_VLLM_MODEL_NAME
   - FormData: classification_vllm_model_name
   - Default: VLLM_MODEL_NAME

2. ✅ CLASSIFICATION_VLLM_API_BASE
   - FormData: classification_vllm_api_base
   - Default: config.get_vllm_api_base('classification')

3. ✅ CLASSIFICATION_PROMPT_TYPE
   - FormData: classification_prompt_type
   - Default: classification_default_v1
```

#### Element Detection
```
설정 항목:
1. ✅ ELEMENT_DETECTION_AGENT_URL
   - FormData: agent_url
   - Default: EXTERNAL_API_URL → ""

2. ✅ ELEMENT_DETECTION_VLLM_MODEL_NAME
   - FormData: detection_vllm_model_name
   - Default: VLLM_MODEL_NAME

3. ✅ ELEMENT_DETECTION_VLLM_API_BASE
   - FormData: detection_vllm_api_base
   - Default: config.get_vllm_api_base('element_detection')

4. ✅ ELEMENT_DETECTION_API_TYPE
   - FormData: detection_api_type
   - Default: "ai_agent" (AI Agent 우선)
```

### 2.3 환경변수 설정 검증

#### ✅ 잘 정렬된 부분
- [x] 작업별 환경변수 명명 규칙 통일
- [x] FormDataConfig에서 우선순위 명확히 정의
- [x] 각 task별로 vLLM model/API base 분리 설정 가능
- [x] Fallback 체인 구현 (FormData → Env → Defaults)

#### ⚠️ 개선 필요 부분
- [ ] 문서에서 `EXTERNAL_API_URL` 참조가 완전히 제거되었는지 확인 필요
- [ ] 환경변수 검증 로직 추가 필요 (optional validation)

---

## 3. 서비스 아키텍처 Alignment

### 3.1 Service Singleton 패턴 통일

모든 3개 서비스가 동일한 구조로 통일됨:

```python
# 구조
class [Task]Service:
    def __init__(self)
    async def initialize(model_name, api_base)     # LLM 클라이언트 초기화
    async def process_[task](params)               # 메인 처리 메서드
    _llm_clients_cache = {}                        # 모델별 캐싱

def get_[task]_service() -> Service:               # Singleton 반환
async def _async_get_[task]_service() -> Service:  # FastAPI Depends 호환
```

### 3.2 각 Task별 서비스 상태

| Task | 서비스 클래스 | 상태 | 구현 위치 |
|------|-------------|------|---------|
| Privacy Removal | PrivacyRemovalService | ✅ 완료 | services/privacy_removal.py |
| Classification | ClassificationService | ✅ 완료 | services/classification.py |
| Element Detection | ElementDetectionService | ✅ 완료 | services/element_detection.py |

### 3.3 서비스 초기화 흐름

```
API 요청 수신
  ↓
FormDataConfig에서 파라미터 추출
  ↓
perform_[task]() 함수 호출
  ↓
get_[task]_service() → Singleton 인스턴스 반환
  ↓
service.initialize(model_name, api_base)
  ↓
service.process_[task](...) 실행
  ↓
결과 반환
```

### 3.4 서비스별 LLM 클라이언트 캐싱

✅ 각 서비스가 모델별(`model_name:api_base`) 클라이언트 캐시 관리
- 중복 초기화 방지
- 메모리 효율성 개선
- 응답 시간 단축

---

## 4. Web UI ↔ API 흐름 검증

### 4.1 FormData 파라미터 매핑

#### Privacy Removal
```javascript
// web_ui/static/js/main.js - Line 403
formData.append('privacy_removal', 'false');  // 기능 비활성화
formData.append('privacy_llm_type', 'vllm');  // LLM 타입
formData.append('privacy_prompt_type', 'privacy_remover_default_v6');
formData.append('vllm_model_name', '/model/qwen30_thinking_2507');
```

↓ 서버에서 수신 (app.py)

```python
# API 엔드포인트
config = FormDataConfig(form_data)
privacy_vllm_model_name = config.get_vllm_model_name('privacy_removal')
privacy_vllm_api_base = config.get_vllm_api_base('privacy_removal')
```

#### ✅ 검증 결과
- [x] 파라미터 이름 일치
- [x] 환경변수 fallback 체인 연결
- [x] 기본값 설정

### 4.2 Classification
```javascript
formData.append('classification', true);  // 활성화 여부
formData.append('classification_prompt_type', 'classification_default_v1');
```

#### ✅ 상태: 구현 완료

### 4.3 Element Detection
```javascript
formData.append('element_detection', true);  // 항상 활성화
formData.append('agent_url', agentUrl);     // AI Agent URL (선택)
formData.append('detection_api_type', 'ai_agent');  // 기본: AI Agent
```

#### ✅ 상태: 구현 완료

---

## 5. 레거시 제거 현황

### 5.1 정리된 파일/기능

| 항목 | 상태 | 설명 |
|------|------|------|
| privacy_remover.py | ✅ 삭제 | 중복 파일 제거 |
| PrivacyRemover → PrivacyRemoval | ✅ 명명 변경 | 클래스명 표준화 |
| _call_external_api → _call_agent_api | ✅ 리네임 | 메서드명 명확화 |
| _call_local_llm → _call_vllm_service | ✅ 리네임 | 메서드명 표준화 |
| 'fast' preset | ✅ 제거 | 성능 프리셋 정리 |

### 5.2 코드 크기 감소

```
api_server/transcribe_endpoint.py
Before: 959 lines
After:  589 lines
Reduction: 38.7% ⬇️
```

---

## 6. Alignment 점검 결과

### 6.1 종합 평가: ✅ 전반적으로 양호

#### 🟢 우수한 부분 (10항목)
1. ✅ 환경변수 명명 규칙 통일
2. ✅ 작업별 환경변수 분리 설정 가능
3. ✅ FormDataConfig 우선순위 명확화
4. ✅ Service Singleton 패턴 통일
5. ✅ 모든 서비스에 LLM 클라이언트 캐싱
6. ✅ Element Detection API 타입 기본값 설정 (ai_agent 우선)
7. ✅ 프롬프트 파일 기반 로딩 구현
8. ✅ 레거시 파일/함수 제거 완료
9. ✅ 코드 크기 대폭 감소
10. ✅ Web UI FormData ↔ API 매핑 일치

#### 🟡 개선 가능 영역 (3항목)

1. **문서 최신화**
   - [ ] EXTERNAL_API_URL → ELEMENT_DETECTION_AGENT_URL 모든 참조 확인
   - [ ] 환경변수 설정 가이드 문서 필요

2. **환경변수 검증**
   - [ ] 필수 환경변수 검증 로직 추가
   - [ ] 설정 로드 시 유효성 검사

3. **API 문서**
   - [ ] FormData 파라미터 스키마 문서화
   - [ ] 우선순위 명명 규칙 문서화

---

## 7. 체크리스트

### 7.1 환경변수
- [x] Task별 환경변수 명명 규칙 통일
- [x] FormData ↔ 환경변수 매핑 완료
- [x] Fallback 체인 구현
- [x] 기본값 설정 완료
- [ ] 환경변수 필수/선택 명시 필요

### 7.2 서비스
- [x] 3개 서비스 모두 Singleton 패턴 적용
- [x] LLM 클라이언트 캐싱 구현
- [x] 메서드명 표준화
- [x] 프롬프트 파일 로딩 구현
- [ ] 서비스 초기화 에러 처리 강화 가능

### 7.3 웹UI ↔ API
- [x] FormData 파라미터 매핑 완료
- [x] 환경변수 연결 완료
- [x] 기본값 설정 완료
- [ ] API 스키마 문서 필요
- [ ] 오류 처리 문서 필요

---

## 8. 권장사항

### 우선순위 순서

**🔴 즉시 처리 (1주일 내)**
1. EXTERNAL_API_URL 모든 참조 제거 확인
2. 환경변수 필수/선택 명시 문서 작성
3. API FormData 파라미터 스키마 문서화

**🟡 단기 처리 (2주일 내)**
1. 환경변수 검증 로직 추가 (config.py)
2. 서비스 초기화 에러 메시지 개선
3. Docker 환경변수 설정 가이드 검토

**🟢 장기 개선 (1개월 내)**
1. 자동 환경변수 검증 테스트 추가
2. API 문서 자동 생성 (OpenAPI/Swagger)
3. 모니터링 대시보드 환경변수 설정 추가

---

## 9. 결론

**현재 상태: ✅ Alignment 매우 양호**

- 환경변수 명명 규칙 통일되고 명확함
- Web UI ↔ API 흐름이 일관되게 구현됨
- 서비스 아키텍처가 통일되고 확장성이 좋음
- 레거시 제거로 코드 품질 개선됨

**다음 단계:**
1. 문서 최신화 (1주일)
2. 환경변수 검증 강화 (2주일)
3. 모니터링 강화 (진행 중)

---

## 부록 A: 환경변수 참고표

### 모든 환경변수 (Docker env)

```bash
# 공용 설정
VLLM_MODEL_NAME=qwen30_thinking_2507
VLLM_API_BASE=http://localhost:8001/v1

# Privacy Removal (선택)
PRIVACY_REMOVAL_VLLM_MODEL_NAME=...
PRIVACY_REMOVAL_VLLM_API_BASE=...
PRIVACY_REMOVAL_PROMPT_TYPE=privacy_remover_default_v6

# Classification (선택)
CLASSIFICATION_VLLM_MODEL_NAME=...
CLASSIFICATION_VLLM_API_BASE=...
CLASSIFICATION_PROMPT_TYPE=classification_default_v1

# Element Detection (선택)
ELEMENT_DETECTION_AGENT_URL=https://api.kis.com/v1/detect
ELEMENT_DETECTION_VLLM_MODEL_NAME=...
ELEMENT_DETECTION_VLLM_API_BASE=...
ELEMENT_DETECTION_API_TYPE=ai_agent  # 기본값

# STT 엔진 설정
STT_BACKEND=transformers
STT_PRESET=accuracy  # performance/accuracy

# 기타
DEBUG=false
LOG_LEVEL=INFO
```

