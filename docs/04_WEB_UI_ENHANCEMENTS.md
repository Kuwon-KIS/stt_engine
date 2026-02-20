# Web UI 개선 사항 - 처리 옵션 & 로깅 강화

## 개요

Web UI를 새로운 STT 엔진 API와 동기화하고, 여러 API 호출로 인한 응답 실패에 더 견고하게 대응하도록 개선했습니다.

**주요 개선 사항:**
1. 처리 단계 선택 옵션 (Privacy Removal, Classification, AI Agent)
2. 통합 로깅 시스템 강화
3. 에러 처리 및 재시도 로직
4. 결과 섹션 구분화 및 확장
5. 배치 처리 진행 모니터링 개선

---

## 1. 처리 옵션 선택 (NEW)

### 화면 요소 추가

**위치:** `web_ui/templates/index.html` - 업로드 섹션

**추가된 체크박스:**
```html
<!-- 처리 단계 선택 -->
<div class="form-group">
    <label class="checkbox-label">
        <input type="checkbox" id="privacy-removal-checkbox">
        🔐 개인정보 제거
    </label>
</div>

<div class="form-group">
    <label class="checkbox-label">
        <input type="checkbox" id="classification-checkbox">
        📊 통화 분류
    </label>
</div>

<div class="form-group">
    <label class="checkbox-label">
        <input type="checkbox" id="ai-agent-checkbox">
        🤖 AI Agent 처리
    </label>
</div>
```

### API 전달

**단일 파일 처리:**
```javascript
const result = await apiCall("/transcribe/", "POST", {
    file_id: uploadResult.file_id,
    language: language,
    backend: backend,
    is_stream: isStream,
    privacy_removal: privacyRemoval,      // NEW
    classification: classification,        // NEW
    ai_agent: aiAgent                     // NEW
});
```

**배치 처리:**
```javascript
const result = await apiCall("/batch/start/", "POST", {
    extension: batchExtensionInput.value || ".wav",
    language: batchLanguageSelect.value,
    parallel_count: parseInt(batchParallelInput.value) || 2,
    privacy_removal: privacyRemoval,     // NEW
    classification: classification,       // NEW
    ai_agent: aiAgent                    // NEW
});
```

---

## 2. 처리 단계 표시 결과

### 새로운 결과 섹션

**처리 단계 현황:**
```html
<div id="processing-steps-section" class="result-card" style="display: none;">
    <h3>✅ 처리 단계 현황</h3>
    <div id="processing-steps-content" style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;"></div>
</div>
```

**표시 형식:**
- ✅ STT 변환 (초록색)
- ❌ STT 변환 (빨간색)
- 각 처리 단계별로 완료/미완료 상태 표시

### JavaScript 함수

```javascript
function displayProcessingSteps(steps) {
    // steps.stt
    // steps.privacy_removal
    // steps.classification
    // steps.ai_agent
    
    // 각각 boolean으로 성공 여부 표시
    // 초록색 배경: 성공
    // 빨간색 배경: 미실행/실패
}
```

---

## 3. Privacy Removal 결과

### 결과 섹션

```html
<div id="privacy-result-section" class="result-card" style="display: none;">
    <h3>🔐 개인정보 제거 결과</h3>
    <div>
        <p><strong>개인정보 존재:</strong> <span id="privacy-exist">-</span></p>
        <p><strong>개인정보 유형:</strong> <span id="privacy-reason">-</span></p>
        <p><strong>처리된 텍스트:</strong></p>
        <div id="privacy-text" style="..."></div>
    </div>
</div>
```

### 데이터 매핑

```javascript
function displayPrivacyResults(privacy) {
    // privacy.exist: 개인정보 포함 여부
    // privacy.reason: 감지된 개인정보 유형
    // privacy.processed_text: 마스킹된 텍스트
}
```

---

## 4. Classification 결과

### 결과 섹션

```html
<div id="classification-result-section" class="result-card" style="display: none;">
    <h3>📊 통화 분류 결과</h3>
    <div>
        <p><strong>분류 코드:</strong> <span id="class-code">-</span></p>
        <p><strong>분류 카테고리:</strong> <span id="class-category">-</span></p>
        <p><strong>신뢰도:</strong> <span id="class-confidence">-</span></p>
        <p><strong>분류 사유:</strong> <span id="class-reason">-</span></p>
    </div>
</div>
```

### 데이터 매핑

```javascript
function displayClassificationResults(classification) {
    // classification.code: 분류 코드
    // classification.category: 분류 카테고리명
    // classification.confidence: 신뢰도 (0-1)
    // classification.reason: 분류 사유
}
```

---

## 5. 통합 로깅 시스템

### 로깅 카테고리

| 카테고리 | 용도 | 예시 |
|---------|------|------|
| `[API]` | API 호출 요청 | `[API] POST /transcribe/` |
| `[API Response]` | API 응답 상태 | `[API Response] /transcribe/: 200 OK` |
| `[API Error]` | API 에러 | `[API Error] /transcribe/ (ERROR_CODE): 메시지` |
| `[API Success]` | API 성공 | `[API Success] /transcribe/: {...}` |
| `[Transcribe]` | 단일 파일 처리 | `[Transcribe] 처리 옵션: {...}` |
| `[배치]` | 배치 처리 | `[배치] 처리 옵션: {...}` |
| `[배치진행]` | 배치 진행상황 | `[배치진행] 진행률: 10/20 (50%)` |
| `[배치실패]` | 배치 실패 파일 | `[배치실패] file.wav: 에러메시지` |
| `[배치조회실패]` | 진행상황 조회 실패 | `[배치조회실패] 시도 1: ...` |
| `[배치완료]` | 배치 완료 | `[배치완료] 배치 처리 완료: 18성공, 2실패` |
| `[Result]` | 결과 수신 | `[Result] Processing Steps: {...}` |
| `[다운로드]` | 파일 다운로드 | `[다운로드] TXT 파일 다운로드 시작` |
| `[다운로드실패]` | 다운로드 실패 | `[다운로드실패] 에러정보` |
| `[Privacy Results]` | 개인정보 결과 | `[Privacy Results] 표시됨` |
| `[Classification Results]` | 분류 결과 | `[Classification Results] 표시됨` |

### 사용 패턴

```javascript
// 1. API 호출 시작
console.log(`[API] ${method} ${endpoint}`, data);

// 2. 응답 받음
console.log(`[API Response] ${endpoint}: ${response.status}`);

// 3. 성공
console.log(`[API Success] ${endpoint}:`, json);

// 4. 에러
console.error(`[API Error] ${endpoint} (${errorCode}):`, errorMessage);

// 5. 비즈니스 로직
console.log("[Transcribe] 처리 옵션:", {...});
console.log("[Result] Processing Steps:", {...});
```

---

## 6. 에러 처리 강화

### API 호출 에러 처리

**기존 방식:**
```javascript
// Simple error message
throw new Error("요청 실패");
```

**개선된 방식:**
```javascript
// Error code + detailed message
const errorCode = json.error_code || "UNKNOWN";
const errorMessage = json.error || json.detail || json.error_code || "요청 실패";
throw new Error(`[${errorCode}] ${errorMessage}`);
```

### 배치 진행 모니터링 재시도

```javascript
// 연속 3회 실패 시 모니터링 중단
if (consoleErrorCount >= 3) {
    console.error("[배치조회] 연속 3회 실패로 모니터링 중단");
    clearInterval(batchProgressInterval);
    showNotification("배치 진행상황 조회 실패...", "error");
}
```

### 결과 조회 에러

```javascript
try {
    const data = await apiCall(`/results/${currentFileId}/export?format=json`);
    // 다운로드 처리
} catch (error) {
    console.error("[다운로드실패]", error);
    showNotification(`다운로드 실패: ${error.message}`, "error");
}
```

---

## 7. 파일 변경 사항

### Python 백엔드

1. **web_ui/models/schemas.py**
   - NEW: `ProcessingStepsStatus` 모델 (4개 boolean 필드)
   - MODIFIED: `TranscribeRequest` - 3개 처리 옵션 추가
   - MODIFIED: `TranscribeResponse` - processing_steps, privacy_removal, classification 추가

2. **web_ui/services/stt_service.py**
   - MODIFIED: `transcribe_local_file()` - 처리 옵션 파라미터 추가
   - MODIFIED: 구조화된 로깅 추가 ([STT Service] 프리픽스)
   - MODIFIED: 에러 처리 개선 (error_code 필드)

3. **web_ui/main.py**
   - MODIFIED: `/api/transcribe/` 엔드포인트 - 처리 옵션 처리
   - MODIFIED: `/api/batch/start/` 엔드포인트 - 처리 옵션 처리
   - MODIFIED: 모든 엔드포인트에 구조화된 로깅 추가

### JavaScript 프론트엔드

1. **web_ui/static/js/main.js**
   - ENHANCED: `apiCall()` - 상세 로깅 및 에러 코드 처리
   - MODIFIED: `transcribeFile()` - 처리 옵션 체크박스 읽기
   - NEW: `displayProcessingSteps()` - 처리 단계 표시
   - NEW: `displayPrivacyResults()` - 개인정보 결과 표시
   - NEW: `displayClassificationResults()` - 분류 결과 표시
   - ENHANCED: `displayResult()` - 결과 섹션 구분화
   - ENHANCED: `startBatchProgressMonitoring()` - 재시도 로직 추가
   - MODIFIED: 다운로드 함수 - 로깅 추가

### HTML 템플릿

1. **web_ui/templates/index.html**
   - NEW: 처리 단계 선택 체크박스 섹션
   - NEW: 처리 단계 현황 표시 섹션
   - NEW: Privacy Removal 결과 표시 섹션
   - NEW: Classification 결과 표시 섹션

---

## 8. 테스트 시나리오

### 시나리오 1: Privacy Removal 활성화
```
1. 체크박스: Privacy Removal 활성화
2. 파일 업로드 및 처리
3. 예상 결과:
   - Processing Steps: privacy_removal = true
   - Privacy Result 섹션 표시
   - 개인정보 제거된 텍스트 표시
```

### 시나리오 2: Classification + Privacy Removal
```
1. 체크박스: Classification, Privacy Removal 모두 활성화
2. 파일 업로드 및 처리
3. 예상 결과:
   - Processing Steps: classification = true, privacy_removal = true
   - Privacy Result 섹션 표시
   - Classification Result 섹션 표시
```

### 시나리오 3: 배치 처리 옵션
```
1. 배치 파일 로드
2. Processing Options 체크박스 활성화
3. 배치 시작
4. 진행상황 모니터링 (5초 간격)
5. 완료 시 결과 표시
```

### 시나리오 4: API 실패 처리
```
1. 네트워크 끊김 시뮬레이션
2. 예상 로그:
   - [API Response] 500 Internal Server Error
   - [API Error] /transcribe/ (INTERNAL_ERROR): 메시지
   - 사용자 알림: "[에러 코드] 메시지"
3. 배치 진행 조회 연속 실패 시:
   - [배치조회실패] 시도 1/2/3
   - 3회 실패 후 모니터링 중단
   - 사용자 알림: "배치 진행상황 조회 실패..."
```

---

## 9. 브라우저 콘솔 로그 예시

### 정상 처리
```
[API] POST /transcribe/ {file_id: "...", privacy_removal: true, ...}
[API Response] /transcribe/: 200 OK
[Transcribe] 처리 옵션: {privacy_removal: true, classification: false, ai_agent: false}
[API Success] /transcribe/: {text: "...", processing_steps: {...}, privacy_removal: {...}}
[Result] Processing Steps: {stt: true, privacy_removal: true, classification: false, ai_agent: false}
[Result] Privacy Removal: {exist: true, reason: "phone_number", processed_text: "..."}
[Privacy Results] 표시됨
```

### 배치 처리
```
[API] POST /batch/start/ {...}
[배치] 처리 옵션: {privacy_removal: true, classification: true, ai_agent: false}
[API Response] /batch/start/: 200 OK
[배치진행] 진행상황 조회: batch_123
[배치진행] 진행률: 5/20 (25%)
[배치실패] failed_file.wav: Connection timeout
[배치진행] 진행률: 18/20 (90%)
[배치완료] 배치 처리 완료: 18성공, 2실패
```

### 에러 처리
```
[API] POST /transcribe/ {...}
[API Response] /transcribe/: 500 Internal Server Error
[API Error] /transcribe/ (INTERNAL_ERROR): Server error occurred
[API Call Failed] /transcribe/: [INTERNAL_ERROR] Server error occurred
[Transcribe Error] Error: [INTERNAL_ERROR] Server error occurred
```

---

## 10. 배포 체크리스트

- [ ] Python 백엔드 파일 문법 검사 완료
- [ ] JavaScript 파일 로딩 확인
- [ ] 브라우저 콘솔에서 에러 없음 확인
- [ ] 처리 옵션 체크박스 표시 확인
- [ ] API 호출 시 파라미터 전달 확인 (콘솔 로그)
- [ ] 결과 섹션 표시 확인
- [ ] 배치 처리 옵션 전달 확인
- [ ] 네트워크 장애 시뮬레이션 테스트
- [ ] 재시도 로직 동작 확인

---

## 11. 추가 개선 사항 (향후)

1. **로그 저장:** 브라우저 로컬스토리지에 로그 저장
2. **진행 상황 WebSocket:** 실시간 배치 진행 업데이트
3. **재시도 자동화:** 실패 시 자동 재시도 (지수 백오프)
4. **타임아웃 설정:** 사용자 정의 가능한 타임아웃
5. **결과 캐싱:** 동일 파일 재처리 시 캐시 활용
6. **상세 에러 표시:** 에러별 해결 방법 제시

---

**작성일:** 2025년 현재
**버전:** 1.0
**상태:** 배포 준비 완료
