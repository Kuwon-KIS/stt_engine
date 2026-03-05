# Web UI 마이그레이션 완료 보고서

> **날짜**: 2026년 3월 5일  
> **변경 사항**: 파일 업로드 기반 → 폴더 기반 분석으로 마이그레이션  
> **상태**: ✅ 구조 변경 완료, ⚠️ 레거시 코드 정리 예정

---

## 📋 Executive Summary

### 변경 전
- **UI**: main.js - 개별 파일 드래그 & 드롭 업로드
- **처리**: `/transcribe/` 엔드포인트 호출
- **Privacy Removal**: 항상 false (미실행)
- **특징**: 일회성 분석

### 변경 후
- **UI**: upload.html - 폴더 선택 및 다중 파일 관리
- **처리**: `/api/analysis/start` 엔드포인트 호출 (Web UI 서버)
- **Privacy Removal**: 항상 true (vLLM + Qwen 사용)
- **특징**: 폴더 중심의 지속적 관리 및 분석 이력 추적

---

## 🏗️ 시스템 아키텍처

### Docker 구성

```
┌──────────────────────────────────────────────────────┐
│ Docker Container 1: STT API 서버                     │
│ stt-engine:cuda129-rhel89-v1.9.7                    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ 포트: 8001 (vLLM), 8003 (STT API)                    │
│ 역할: STT, Privacy Removal, Element Detection        │
│ 환경변수:                                             │
│   - STT_PRESET=accuracy                             │
│   - QWEN_API_BASE=http://localhost:8001/v1          │
│   - VLLM_BASE_URL=http://localhost:8001/v1/...      │
│   - LLM_MODEL_NAME=/model/qwen30_thinking_2507      │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ Docker Container 2: Web UI 서버                      │
│ stt-web-ui:cuda129-rhel89-v1.2.7                    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ 포트: 8100 (Web UI)                                  │
│ 역할: 폴더 기반 분석 관리, 사용자 인증, 파일 업로드 │
│ 서비스:                                              │
│   - auth.router: 사용자 인증                        │
│   - files.router: 파일 관리                         │
│   - analysis.router: 분석 작업 관리 ✅              │
│   - storage.router: 저장소 관리                     │
└──────────────────────────────────────────────────────┘
```

---

## 🔄 사용자 흐름

### 현재 (2026년 이후) ✅

```
1. Web UI (http://localhost:8100) 접속
    ↓
2. upload.html 페이지 로드
    - 폴더 선택
    - 파일 업로드 (드래그 & 드롭)
    ↓
3. "분석 시작" 버튼 클릭
    └─ startAnalysis() [upload.html 내 로컬 함수]
    ↓
4. POST /api/analysis/start (Web UI 서버 포트 8100)
    └─ AnalysisService.process_analysis_sync()
    ↓
5. 백그라운드 동시 처리 (최대 2개 파일)
    ├─ await stt_service.transcribe_local_file()
    │   ├─ privacy_removal=True ✅ (vLLM + Qwen)
    │   ├─ element_detection=True ✅
    │   └─ classification=user_option
    ├─ 결과 DB 저장
    └─ 진행률 업데이트
    ↓
6. 분석 결과 페이지 표시
    - 음성 인식 결과
    - 개인정보 제거 결과 (Privacy Removal)
    - 불완전판매 요소 탐지 (Element Detection)
    - 분류 결과 (Classification, 선택사항)
```

### 이전 (2026년 이전) ❌

```
1. Web UI (main.js) - main.js 기반 UI
    ↓
2. 파일 선택 (드래그 & 드롭)
    ↓
3. "분석" 버튼 클릭
    └─ transcribeFile() [main.js]
    ↓
4. POST /transcribe/ (API 서버 포트 8003)
    ├─ privacy_removal='false' ❌ (미실행)
    ├─ element_detection, classification (설정 무시)
    ↓
5. 결과 표시
    - 음성 인식 결과만 표시
    - Privacy Removal 미실행
```

---

## 📊 현재 사용 중인 엔드포인트

### Web UI 서버 (포트 8100)
| 경로 | 메서드 | 용도 | 상태 |
|------|--------|------|------|
| `/api/analysis/start` | POST | 폴더 기반 분석 시작 | ✅ 현재 사용 |
| `/api/analysis/progress/{job_id}` | GET | 분석 진행률 조회 | ✅ 현재 사용 |
| `/api/analysis/results/{job_id}` | GET | 분석 결과 조회 | ✅ 현재 사용 |

### API 서버 (포트 8003)
| 경로 | 메서드 | 용도 | 상태 |
|------|--------|------|------|
| `POST /transcribe` | POST | 파일 분석 | ❌ Web UI에서 미사용 |
| `/batch/start` | POST | 배치 처리 | ❌ 미사용 |
| `/transcribe_legacy` | POST | 레거시 | ❌ 미사용 |
| `/transcribe_by_upload` | POST | 텍스트 입력 | ❌ 미사용 |

---

## 🔐 Privacy Removal 구현

### 현재 상태 ✅

**설정**:
- LLM: vLLM (로컬 서버)
- 모델: Qwen 30B (thinking) - `/model/qwen30_thinking_2507`
- API 엔드포인트: `http://localhost:8001/v1`
- 항상 실행: Yes (폴더 분석 시)
- 폴백 메커니즘: Regex (vLLM 불가용 시)

**🔄 현행 호출 경로** (upload.html):

```
Web UI (upload.html)
    ↓
startAnalysis() → POST /api/analysis/start (privacy_removal=true, element_detection=true)
    ↓
Web UI Server: AnalysisService.process_analysis_sync()
    ├─ for each file:
    │   ├─ stt_service.transcribe_local_file(
    │   │   file_path="/app/data/uploads/...",
    │   │   privacy_removal=True,        ✅ 항상 True
    │   │   element_detection=True,      ✅ 항상 True
    │   │   classification=user_choice
    │   │ )
    │   └─ await stt_service.transcribe_local_file()
    │
    └─ STT API Server (포트 8003): POST /transcribe
         ├─ file_path → FormData
         ├─ privacy_removal → "true" (문자열)
         │   ↓
         │   TranscribeRequest.__init__()
         │   → self.privacy_removal = "true".lower() in ['true', '1', 'yes', 'on']
         │   → True (boolean 변환) ✅
         │
         └─ perform_privacy_removal()
             ├─ llm_type="vllm" (기본값)
             ├─ vllm_model_name="/model/qwen30_thinking_2507"
             ├─ prompt_type="privacy_remover_default_v6"
             └─ PrivacyRemoverService.process_text()
                 ├─ LLMClientFactory.create_client("Qwen...") 
                 │   → 모델명에 'qwen' 감지
                 │   → return QwenClient(model_name)  ✅
                 │
                 └─ await QwenClient.generate_response()
                     ├─ api_base = "http://localhost:8001/v1" ✅
                     ├─ model = "Qwen3-30B-A3B-Thinking-2507-FP8"
                     ├─ temperature = 0.3
                     ├─ max_tokens = 32768
                     └─ response = await self.client.chat.completions.create(...)
                         ├─ 성공: JSON 파싱 → privacy_removal 결과 ✅
                         ├─ JSON 파싱 실패: Regex fallback → 기본 패턴으로 제거 ✅
                         └─ LLM 연결 실패: RuntimeError → Regex fallback ✅
```

**파라미터 명세** (현행 호출값):

| 항목 | 설정값 | 위치 | 비고 |
|------|--------|------|------|
| privacy_removal | **True** (boolean) | analysis_service.py:661 | ✅ 항상 활성화 |
| privacy_removal (API 입력) | **"true"** (문자열) | stt_service.py:141 | FormData로 변환 |
| llm_type | **"vllm"** | transcribe_endpoint.py:232 | 기본값 |
| vllm_model_name | **/model/qwen30_thinking_2507** | analysis_service.py:667 | Qwen 모델 |
| api_base | **http://localhost:8001/v1** | privacy_remover.py:306 | vLLM 엔드포인트 |
| temperature | **0.3** | transcribe_endpoint.py:272 | 낮은 변동성 |
| max_tokens | **32768** | transcribe_endpoint.py:271 | 충분한 토큰 |
| prompt_type | **privacy_remover_default_v6** | transcribe_endpoint.py:268 | 기본 프롬프트 |

**폴백 체인**:
```python
try:
    # 1️⃣ vLLM API 호출
    response = await QwenClient.generate_response(...)
except (RuntimeError, ConnectionError, TimeoutError) as e:
    # 2️⃣ LLM 호출 실패 → Regex 자동 전환
    logger.warning("[PrivacyRemover] Regex fallback으로 전환")
    try:
        fallback_result = self._regex_fallback(usertxt)  # 기본 패턴 적용
        return {
            'success': False,
            'privacy_exist': fallback_result['privacy_exist'],
            'exist_reason': f"[Fallback] {str(e)[:50]}",
            'privacy_rm_usertxt': fallback_result['privacy_rm_usertxt']
        }
    except Exception as fallback_error:
        # 3️⃣ Regex도 실패 → 원본 반환
        logger.error("[PrivacyRemover] Regex fallback도 실패")
        return {
            'success': False,
            'privacy_exist': 'N',
            'exist_reason': f"[Error] {str(e)[:40]}",
            'privacy_rm_usertxt': usertxt  # 원본 반환
        }
```

**환경 상황별 동작**:
| 환경 | vLLM 서버 | Privacy Removal | 폴백 | 결과 |
|------|---------|-----------------|------|------|
| 운영 (EC2) | ✅ 실행 중 | ✅ vLLM + Qwen | - | 개인정보 제거 ✅ |
| 개발 (MacBook) | ❌ 미실행 | ⚠️ Regex | success=False | 기본 패턴 제거 |
| EC2 빌드 | ❌ 불가용 | ⚠️ Regex | success=False | 기본 패턴 제거 |

---

## 🗑️ 레거시 코드 현황

### main.js (1054 라인) - 파일 업로드 기반 UI

**레거시 파라미터** (호출되지 않음):
- `privacy_removal: 'false'` (라인 387) ❌ 항상 비활성화
- `privacy_llm_type: 'vllm'` (라인 388) - 설정해도 privacy_removal=false이므로 무시
- `privacy_prompt_type: 'privacy_remover_default_v6'` - 무시됨

**레거시 섹션** (사용 안 함):
- 글로벌 변수: `selectedFile`, `currentFileId`, `currentBatchId`, `batchProgressInterval`
- DOM 요소: `dropZone`, `fileInput`, `browseBtn`, `fileInfo`, `transcribeBtn`, `languageSelect`, `backendSelect`, `streamingCheckbox`, `setGlobalBackendCheckbox`
- 함수:
  - `initializeFileUploadHandlers()` - [LEGACY] 드래그 & 드롭 이벤트
  - `handleFileSelect()` - [LEGACY] 파일 선택 처리
  - `uploadFile()` - [LEGACY] 파일 업로드
  - `transcribeFile()` - [LEGACY] STT 처리 (privacy_removal='false') ⚠️ **개인정보 미보호**
  - `displayResult()`, `displayProcessingSteps()` - [LEGACY] 결과 표시
  - 배치 처리: `loadBatchFiles()`, `renderBatchTable()`, `startBatch()` - [LEGACY] 비작동

**유지 섹션** (계속 사용):
- 유틸리티: `apiCall()`, `formatFileSize()`, `formatTime()`, `showNotification()`
- 백엔드 설정: `fetchGlobalBackendInfo()`, `setGlobalBackend()`

**상태**: [LEGACY] - 마이그레이션 경고 추가됨 (라인 1-20)
- ⚠️ 어떤 HTML에서 main.js를 import하는지 확인 필요
- 📝 정리 권장사항: 주석 처리 후 문서화 (즉시 삭제보다 안전)

---

## ✅ 확인 체크리스트

### 배포 전 확인사항

- [x] STT_DEVICE=auto 환경변수 설정
- [x] STT_PRESET=accuracy 환경변수 설정
- [x] privacy_llm_type 기본값: "vllm" ✅
- [x] vllm_model_name: "/model/qwen30_thinking_2507" ✅
- [x] QWEN_API_BASE 환경변수 설정
- [x] VLLM_BASE_URL 환경변수 설정
- [ ] vLLM 서버 실행 (port 8001)
- [ ] Web UI 서버 실행 (port 8100)
- [ ] API 서버 실행 (port 8003)
- [ ] 폴더 기반 분석 기능 테스트
- [ ] privacy_removal 정상 작동 확인 (vLLM)
- [ ] 폴백 메커니즘 확인 (vLLM 미실행 시)

---

## 📝 정리 예정 사항

### 우선순위: 높음
1. **API 엔드포인트 상태 명시** ✅ (현재 문서에서 수행)
   - 사용 중: `/api/analysis/start` (Web UI)
   - 미사용: `/transcribe/`, `/batch/start/` (main.js)

2. **문서화** ✅
   - LEGACY_CODE_CLEANUP.md 작성
   - API_SERVER_FLOW_ANALYSIS.md 업데이트
   - WEB_UI_MIGRATION_SUMMARY.md 작성 (현재 파일)

### 우선순위: 중간
1. **main.js 레거시 섹션 주석 처리**
   - 레거시 코드를 명확하게 표시
   - 교체 대상 코드 명시

2. **HTML 파일 정리**
   - main.js를 import하는 HTML 파일 확인
   - 불필요한 UI 제거

### 우선순위: 낮음
1. **API 엔드포인트 정리** (다른 클라이언트 확인 후)
   - `/transcribe/` 유지 또는 제거
   - `/batch/start/` 유지 또는 제거

---

## 🔗 관련 문서

- [API_SERVER_FLOW_ANALYSIS.md](./API_SERVER_FLOW_ANALYSIS.md) - 상세 API 흐름 분석
- [LEGACY_CODE_CLEANUP.md](./LEGACY_CODE_CLEANUP.md) - 레거시 코드 정리 계획
- [BACKEND_SETTINGS_GUIDE.md](./BACKEND_SETTINGS_GUIDE.md) - 백엔드 설정 가이드

---

## 📞 문의 사항

- vLLM 서버 연결 문제: QWEN_API_BASE, VLLM_BASE_URL 환경변수 확인
- Privacy Removal 미작동: vLLM 서버 상태 확인 (port 8001)
- 폴더 분석 실패: Web UI 서버 로그 확인 (port 8100)
