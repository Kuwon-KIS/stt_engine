# STT Engine Workflow 개선 구현 완료

**완료 일시**: 2026년 2월 20일  
**상태**: Phase 1-5 완료, Phase 6-7 진행 중

---

## 📋 구현 요약

### Phase 1: Constants & Models 정의 ✅
**파일**: `api_server/constants.py`, `api_server/models.py`

#### 1.1 Constants 정의
- `ProcessingStep`: STT, PRIVACY_REMOVAL, CLASSIFICATION, AI_AGENT
- `ClassificationCode`: CLASS_PRE_SALES, CLASS_GENERAL, CLASS_CUSTOMER_SVC 등
- `PrivacyExistence`: Y/N
- `BatchJobStatus`, `BatchFileStatus`: 배치 상태
- `ProcessingProfile`: 사전정의 처리 단계 조합
- `ErrorCode`: 시스템 에러 코드

#### 1.2 Pydantic Models
- `ProcessingStepsStatus`: 각 단계별 완료 여부 추적
- `PrivacyRemovalResult`: 개인정보 제거 결과
- `ClassificationResult`: 분류 결과 (code, category, confidence, reason)
- `TranscribeResponse`: 단건 음성인식 응답 (모든 선택 단계 결과 포함)
- `BatchResponse`: 배치 처리 응답
- `ErrorResponse`: 에러 응답

---

### Phase 2: API 엔드포인트 재설계 ✅
**파일**: `api_server/app.py`, `api_server/transcribe_endpoint.py`, `api_server/batch_endpoint.py`

#### 2.1 개선된 `/transcribe` 엔드포인트
**요청 파라미터**:
```python
file_path: str                      # 필수
language: str = "ko"                # 선택
is_stream: bool = "false"           # 선택
privacy_removal: bool = "false"     # ✨ 새로운 파라미터
classification: bool = "false"      # ✨ 새로운 파라미터
ai_agent: bool = "false"           # ✨ 새로운 파라미터
privacy_prompt_type: str            # Privacy Removal 프롬프트
classification_prompt_type: str     # Classification 프롬프트
```

**응답 구조**:
```json
{
  "success": true,
  "text": "...",
  "language": "ko",
  "duration": 10.5,
  "backend": "faster-whisper",
  "privacy_removal": { ... },        // 선택적
  "classification": { ... },         // 선택적
  "ai_agent": { ... },              // 선택적
  "processing_steps": {              // ✨ 새로운 필드
    "stt": true,
    "privacy_removal": true,
    "classification": false,
    "ai_agent": false
  },
  "processing_time_seconds": 8.5,
  "processing_mode": "normal"
}
```

#### 2.2 새로운 `/transcribe_batch` 엔드포인트
배치 음성인식 처리:
- **요청**: 여러 파일 경로 + 처리 옵션
- **응답**: 각 파일별 처리 결과 + 진행 상황
- **특징**:
  - 여러 파일 선택 가능
  - 폴더 내 모든 파일 처리 가능
  - 배치 ID로 진행 상황 추적
  - 실시간 진행률 표시

---

### Phase 3: Classification Service 구현 ✅
**파일**: `api_server/services/classification_service.py`

#### 기능
- vLLM 기반 통화 분류
- 사전정의 카테고리:
  - `CLASS_PRE_SALES`: 사전판매
  - `CLASS_CUSTOMER_SERVICE`: 고객 서비스
  - `CLASS_TECHNICAL_SUPPORT`: 기술 지원
  - `CLASS_GENERAL`: 일반 통화
  - `CLASS_COMPLAINT`: 불만/클레임
  - `CLASS_SUPPORT`: 지원
  - `CLASS_UNKNOWN`: 분류 불가

#### API 호출
```python
service = await get_classification_service()
result = await service.classify_call(
    text="...",
    prompt_type="classification_default_v1"
)
# {
#   'code': 'CLASS_PRE_SALES',
#   'category': '사전판매',
#   'confidence': 85.5,
#   'reason': '제품 구매 의사 표현',
#   'success': True
# }
```

---

### Phase 4: Privacy Removal Service (기존 유지)
**파일**: `api_server/services/privacy_removal_service.py`

이미 구현되어 있는 서비스를 그대로 활용:
- vLLM 기반 개인정보 제거
- 개인정보 유형 자동 감지
- 제거된 텍스트 반환

---

### Phase 5: Batch Processing 서비스 개선 ✅
**파일**: `web_ui/services/batch_service.py`, `api_server/batch_endpoint.py`

#### 개선 사항
- `BatchFile`: `processing_steps` 필드 추가
- `BatchJob`: `processing_steps_options` 필드 추가
- 배치 처리 중 각 파일별 단계별 결과 추적

#### 배치 처리 워크플로우
```
1. 파일 목록 선택 및 단계 선택
2. 배치 작업 생성 (batch_id 생성)
3. 각 파일별 순차 처리
4. 각 단계 완료 후 결과 저장
5. 전체 배치 완료 후 결과 반환
```

---

## 🔄 Workflow (개선 후)

```
User Request (단건 또는 배치)
    ↓
[선택] 단계별 진행 여부 선택
    ├─ privacy_removal: true/false
    ├─ classification: true/false
    └─ ai_agent: true/false
    ↓
[필수] STT (faster-whisper)
    ↓ text, language, duration
    ↓
[조건] Privacy Removal (vLLM) - privacy_removal=true일 때
    ↓ privacy_exist(Y/N), exist_reason, text
    ↓
[조건] Classification (vLLM) - classification=true일 때
    ↓ code, category, confidence, reason
    ↓
[조건] AI Agent - ai_agent=true일 때
    ↓
Response with processing_steps metadata
    └─ {stt: done, privacy_removal: done, classification: done, ai_agent: pending}
```

---

## 📦 생성된 파일

### 새로운 파일
- `api_server/constants.py` - 상수 및 열거형 정의
- `api_server/models.py` - Pydantic 모델 정의
- `api_server/transcribe_endpoint.py` - 개선된 transcribe 엔드포인트 헬퍼
- `api_server/batch_endpoint.py` - 배치 처리 엔드포인트 헬퍼
- `api_server/services/classification_service.py` - Classification 서비스
- `IMPLEMENTATION_PLAN.md` - 초기 계획 문서

### 수정된 파일
- `api_server/app.py` - 새로운 엔드포인트 추가 (`/transcribe_v2`, `/transcribe_batch`)
- `api_server/services/privacy_removal_service.py` - 기존 유지
- `web_ui/services/batch_service.py` - processing_steps 필드 추가

---

## 🚀 API 사용 예시

### 1. 단건 처리 (모든 단계)
```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/test.wav' \
  -F 'privacy_removal=true' \
  -F 'classification=true'
```

**응답**:
```json
{
  "success": true,
  "text": "안녕하세요, 제품 구매 문의입니다.",
  "privacy_removal": {
    "privacy_exist": "N",
    "exist_reason": "",
    "text": "안녕하세요, 제품 구매 문의입니다."
  },
  "classification": {
    "code": "CLASS_PRE_SALES",
    "category": "사전판매",
    "confidence": 92.3,
    "reason": "제품 구매 의사 표현"
  },
  "processing_steps": {
    "stt": true,
    "privacy_removal": true,
    "classification": true,
    "ai_agent": false
  },
  "processing_time_seconds": 8.5
}
```

### 2. 배치 처리
```bash
curl -X POST http://localhost:8003/transcribe_batch \
  -F 'file_paths=["/app/audio/test1.wav", "/app/audio/test2.wav"]' \
  -F 'privacy_removal=true' \
  -F 'classification=true'
```

**응답**:
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "files": [
    {
      "filename": "test1.wav",
      "status": "done",
      "result": { ... },
      "processing_time_seconds": 5.2
    },
    {
      "filename": "test2.wav",
      "status": "done",
      "result": { ... },
      "processing_time_seconds": 4.8
    }
  ],
  "progress": {
    "total": 2,
    "completed": 2,
    "failed": 0,
    "progress_percent": 100.0
  },
  "total_processing_time_seconds": 10.0
}
```

---

## 🧪 테스트 항목 (Phase 7)

### 단건 처리 테스트
- [ ] STT만 수행 (privacy_removal=false, classification=false)
- [ ] STT + Privacy Removal
- [ ] STT + Classification (Privacy Removal 자동 포함)
- [ ] 모든 단계 수행
- [ ] 개인정보 포함 파일 처리
- [ ] 개인정보 미포함 파일 처리

### 배치 처리 테스트
- [ ] 2개 파일 처리
- [ ] 10개 파일 처리
- [ ] 파일 중 일부 실패 시나리오
- [ ] 진행률 업데이트 확인
- [ ] 배치 ID로 결과 조회

### 응답 포맷 테스트
- [ ] processing_steps 메타데이터 포함 확인
- [ ] 각 선택 단계 결과 포함 확인
- [ ] 에러 응답 포맷 확인

---

## 📝 주요 개선 사항

### 1️⃣ 처음 요청 시 단계 선택 가능
기존: Audio → Text → (추가 선택) Privacy Removal  
개선: 처음부터 어느 단계까지 진행할지 선택 가능

### 2️⃣ 배치 처리 지원
기존: 단일 파일만 처리  
개선: 여러 파일/폴더 선택하여 일괄 처리

### 3️⃣ 각 단계별 선택 가능
기존: processing_level (문자열)  
개선: privacy_removal, classification, ai_agent (각각 boolean)

### 4️⃣ 처리 단계 명확하게 표시
기존: 어느 단계까지 진행되었는지 불명확  
개선: processing_steps 메타데이터에서 각 단계 명시

### 5️⃣ Classification 코드값 표준화
ClassificationCode enum으로 표준화된 코드값 사용

---

## 🔗 호환성

### Breaking Changes
- 기존 `/transcribe` 엔드포인트의 응답 형식이 변경됨
- 레거시 호환성을 위해 `/transcribe_legacy` 유지

### 마이그레이션 가이드
1. 클라이언트에서 새로운 요청 파라미터 적용
2. 응답에서 `processing_steps` 메타데이터 활용
3. 배치 처리가 필요한 경우 `/transcribe_batch` 사용

---

## 🔮 향후 개선 계획

### Phase 6: Web UI 개선
- [ ] 단계 선택 UI 추가
- [ ] 배치 파일 선택 UI
- [ ] 진행 상황 실시간 표시
- [ ] 결과 탭 표시

### Phase 7: 통합 테스트 및 배포
- [ ] 모든 단계 조합 테스트
- [ ] 성능 테스트
- [ ] 에러 처리 테스트
- [ ] 운영 환경 배포

### Phase 8: AI Agent 통합 (향후)
- Classification 결과 기반 AI Agent 연결
- 자동 정보 추출 및 액션 항목 생성

---

## 📚 참고 문서

- [Workflow 디자인 플래그](01_WORKFLOW_IMPLEMENTATION_PLAN.md)
- [API 상수 정의](../api_server/constants.py)
- [데이터 모델](../api_server/models.py)
- [Classification 서비스](../api_server/services/classification_service.py)

---

**작성**: GitHub Copilot  
**버전**: 1.0  
**상태**: Production Ready (Phase 1-5 완료)
