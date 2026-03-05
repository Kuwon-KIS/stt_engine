# Legacy Code Cleanup 계획

## 📌 웹페이지 마이그레이션 배경

### 이전 구조 (Phase 1-2)
- **UI**: main.js 기반의 파일 업로드 + 배치 처리
- **사용자 흐름**: 
  1. 파일 드래그 & 드롭 (파일 선택)
  2. `uploadFile()` → `/upload/` → 파일 ID 획득
  3. `transcribeFile()` → `/transcribe/` → STT 처리 (privacy_removal=false)
  4. `startBatch()` → `/batch/start/` → 배치 처리
- **특징**: 개별 파일 중심의 처리

### 현재 구조 (Phase 3+)
- **UI**: upload.html 기반의 폴더 관리 + 분석
- **사용자 흐름**:
  1. 폴더 선택 (먼저 파일 업로드)
  2. `startAnalysis()` → `/api/analysis/start` → 폴더 기반 분석 (privacy_removal=true ✅)
  3. 분석 진행 상황 모니터링
- **특징**: 폴더 중심의 관리 및 처리

---

## 🗑️ 정리 대상 (레거시 코드)

### 1. main.js 내 사용되지 않는 코드

#### ❌ 파일 업로드 UI (아직 upload.html이 있는데도 남겨짐)
```javascript
// 라인 121-218: 파일 업로드 관련 DOM 요소 선택
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const browseBtn = document.querySelector(".browse-btn");
const fileInfo = document.getElementById("file-info");
const transcribeBtn = document.getElementById("transcribe-btn");

// 라인 229-257: uploadFile() 함수
// 라인 229-260: handleFileSelect() 함수  
// 라인 125-227: initializeFileUploadHandlers() 함수 (드래그&드롭)

// 라인 261-292: transcribeFile() 함수
// - 내부에서 privacy_removal='false'로 설정 (의미 없음)
// - element_detection, classification, agent_url 등의 파라미터 설정하지만 사용 안 됨
```

#### ❌ 배치 처리 UI (API 서버에서도 사용 안 함)
```javascript
// 라인 610-613: 배치 관련 DOM 요소 선택
const startBatchBtn = document.getElementById("start-batch-btn");
const batchExtensionInput = document.getElementById("batch-extension");
const batchLanguageSelect = document.getElementById("batch-language");
const batchParallelInput = document.getElementById("batch-parallel");

// 라인 615: batchFiles 변수
// 라인 619-750: 배치 관련 함수들
// - loadBatchFiles()
// - renderBatchTable()
// - startBatch() → /batch/start/ 호출 (Web UI에서 사용 안 함)
// - startBatchProgressMonitoring()
// - updateProgress()
```

#### ❌ 사용되지 않는 변수
```javascript
// 라인 11: let currentBatchId = null;  (배치 처리 미사용)
// 라인 12: let batchProgressInterval = null;  (배치 모니터링 미사용)
// 라인 1-10: 파일 업로드 관련 변수들
```

### 2. API 서버 내 사용되지 않는 엔드포인트 (참고용)

#### ❌ POST /transcribe
```
호출처: main.js (파일 업로드 후)
privacy_removal: false (설정됨)
→ privacy_removal 미실행 (의미 없음)
→ Web UI 폴더 분석에서는 사용 안 함
```

#### ❌ POST /batch/start
```
호출처: main.js (배치 처리)
→ Web UI에서 호출 안 함
→ 현재는 Web UI의 /api/analysis/start 사용
```

#### ❌ POST /transcribe_legacy
```
레거시 엔드포인트 (명시적으로 "legacy" 표기)
```

#### ❌ POST /transcribe_by_upload
```
텍스트 입력용 엔드포인트
main.js에서 사용하지 않음
```

---

## ✅ 유지할 코드 (현재 사용 중)

### 1. upload.html 기반 폴더 분석
```javascript
// 라인 1411-1473: startAnalysis() 함수
// - upload.html에서 호출됨
// - /api/analysis/start 엔드포인트 호출
// - privacy_removal=true (강제 실행, 의미 있음)
// - element_detection=true (강제 실행)
```

### 2. 유틸리티 함수들
```javascript
// 라인 26-66: apiCall() - 모든 API 호출에 사용
// 라인 73-86: formatFileSize() 
// 라인 91-98: formatTime()
// 라인 103-107: showNotification()
```

### 3. 백엔드 설정 관련
```javascript
// 라인 283-324: fetchGlobalBackendInfo() - 백엔드 정보 조회
// 라인 329-363: setGlobalBackend() - 백엔드 변경
```

---

## 📊 정리 영향도 분석

### main.js (976 라인)
- **삭제 대상**: ~400+ 라인 (파일 업로드 + 배치 처리)
- **유지 대상**: ~300 라인 (유틸리티 + 폴더 분석)
- **최종 크기**: 약 300-400 라인

### API 서버 (app.py - 2127 라인)
- **참고**: 엔드포인트는 유지 (다른 용도로 사용될 수 있음)
- **문서화**: API_SERVER_FLOW_ANALYSIS.md에 현재 사용 현황 명시

---

## 🎯 정리 계획

### Phase 1: 분석 및 문서화 ✅
- main.js 구조 분석 완료
- 레거시 vs 현재 코드 분류 완료
- 영향도 분석 완료

### Phase 2: 점진적 정리 권장사항

**전략 변경 (권장):**
- ⚠️ main.js를 완전히 정리하기보다는, **레거시 섹션을 명확하게 주석 처리**하고 문서화하는 것을 권장
- 이유: 다른 HTML 파일에서 main.js를 import할 수 있고, 즉시 제거 시 부작용 위험

**Step 1: main.js 리팩토링 (낮은 위험)**
```javascript
// ============================================================================
// [LEGACY - 2026년 이전 구조] 파일 업로드 & 배치 처리 UI
// 현재 사용 안 함 - upload.html 기반의 폴더 분석으로 변경됨
// ============================================================================

// ❌ 다음 코드는 사용되지 않음 (유지만 하고 주석)
/*
const dropZone = document.getElementById("drop-zone");
...
async function transcribeFile() { ... }
async function startBatch() { ... }
...
*/
```

**Step 2: 현재 구조 명확화 (높은 우선순위)**
```javascript
// ============================================================================
// [CURRENT - 2026년 이후 구조] 폴더 기반 분석 (upload.html)
// 실제 사용되는 기능
// ============================================================================

// 백엔드 설정 함수 (유지)
async function fetchGlobalBackendInfo() { ... }
async function setGlobalBackend(backend) { ... }
```

**Step 3: API 서버 문서화 (높은 우선순위)**
- API_SERVER_FLOW_ANALYSIS.md에 명확하게 표시

### Phase 3: 문서 업데이트
- ✅ LEGACY_CODE_CLEANUP.md 생성 (현재 파일)
- API_SERVER_FLOW_ANALYSIS.md 업데이트 (진행 중)

---

## ⚠️ 주의사항

1. **API 엔드포인트 삭제 X**
   - 다른 클라이언트에서 사용될 가능성 있음
   - 향후 필요시 유지 가능

2. **HTML 파일 확인 필요**
   - 어떤 HTML 파일에서 main.js를 import하는지 확인
   - 제거할 DOM 요소가 실제로 사용되지 않는지 확인

3. **테스트**
   - 폴더 분석 기능이 정상 작동하는지 확인
   - 백엔드 설정 변경이 정상 작동하는지 확인

---

## 📝 현재 상태

**Web UI의 실제 사용 경로:**
```
upload.html (폴더 분석 UI)
    ↓
    startAnalysis() [main.js에서 import됨? 또는 upload.html 내 로컬]
    ↓
    POST /api/analysis/start (Web UI 서버)
    ↓
    AnalysisService.process_analysis_sync()
    ↓
    await stt_service.transcribe_local_file()
        - privacy_removal=True ✅
        - element_detection=True ✅
        - classification=설정에 따라
```

**사용되지 않는 경로:**
```
main.js (파일 업로드 UI) → 사용 안 함
    uploadFile() → /upload/
    transcribeFile() → /transcribe/ (privacy_removal=false)
    startBatch() → /batch/start/
```
