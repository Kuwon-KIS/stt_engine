# Web UI 파일 구조 및 용도

## 📁 현재 Web UI 구성

### 1️⃣ **index.html** - 레거시 UI (아직 활용 중)

**위치**: `web_ui/templates/index.html`

**용도**:
- 파일 업로드 기반 STT 변환
- 배치 파일 처리

**사용 스크립트**:
- `/static/js/main.js` - 파일 업로드, 배치 처리 로직
- `/static/js/batch_performance.js` - 배치 성능 통계

**기능**:
- ✅ 파일 드래그 & 드롭 업로드
- ✅ 개별 파일 STT 변환
- ✅ 일괄 배치 처리
- ❌ Privacy Removal (항상 false - 미실행)
- ⚠️ Element Detection (설정하지만 /transcribe/에서 미사용)

**엔드포인트**: `/transcribe/` (API 서버, 포트 8003)

---

### 2️⃣ **upload.html** - 현재 UI (폴더 분석)

**위치**: `web_ui/templates/upload.html`

**용도**:
- 폴더 기반 파일 관리
- 다중 파일 STT 변환 및 분석

**사용 스크립트**:
- `/static/js/common.js` - 공용 유틸리티 (API 호출, 세션 관리)
- 로컬 함수: `startAnalysis()` (upload.html 내 정의)

**기능**:
- ✅ 폴더 선택 및 파일 관리
- ✅ STT 변환
- ✅ Privacy Removal (항상 true - vLLM 자동 실행) ✅
- ✅ Element Detection (항상 true)
- ✅ Classification (선택사항)
- ✅ 분석 이력 추적
- ✅ 결과 데이터베이스 저장

**엔드포인트**: `/api/analysis/start` (Web UI 서버, 포트 8100)

---

### 3️⃣ **login.html** - 로그인 페이지

**위치**: `web_ui/templates/login.html`

**용도**: 사용자 인증

**사용 스크립트**: common.js

---

### 4️⃣ **analysis.html** - 분석 결과 페이지

**위치**: `web_ui/templates/analysis.html`

**용도**: 분석 결과 표시 및 조회

**사용 스크립트**: common.js

---

## 🔄 사용 흐름도

### 사용자 흐름

```
옵션 A: 파일 업로드 변환 (index.html)
    http://localhost:8100/
        ↓
    index.html 로드
        ↓
    main.js (uploadFile, transcribeFile) [LEGACY]
        ↓
    POST /transcribe/ → API 서버
        ├─ privacy_removal='false' ❌ (hard-coded)
        ├─ element_detection 설정 (무시됨)
        └─ 결과 표시 (index.html)

옵션 B: 폴더 분석 (upload.html) ✅ RECOMMENDED
    http://localhost:8100/
        ↓
    upload.html 로드
        ↓
    common.js + startAnalysis()
        ↓
    POST /api/analysis/start (privacy_removal=true, element_detection=true)
        ↓
    Web UI Server → AnalysisService.process_analysis_sync()
        ├─ for each file:
        │   └─ stt_service.transcribe_local_file(
        │       privacy_removal=True ✅
        │       element_detection=True ✅
        │     )
        │
        └─ POST /transcribe/ → API 서버
            ├─ privacy_removal="true" (문자열 → True boolean 변환)
            ├─ element_detection="true"
            └─ 개인정보 제거 (vLLM + Qwen)
                
        DB 저장 + analysis.html (결과 조회)
```

---

## 📊 비교 표

| 기능 | index.html | upload.html |
|------|-----------|-----------|
| **UI 타입** | 파일 업로드 | 폴더 관리 |
| **Privacy Removal** | ❌ false (hard-coded) | ✅ True (항상 활성) |
| **LLM 타입** | ⚠️ vllm (설정만) | ✅ vllm (실제 호출) |
| **동시 처리** | ❌ 1개 | ✅ 최대 2개 |
| **이력 추적** | ❌ 없음 | ✅ DB 저장 |
| **Element Detection** | ⚠️ 설정만 무시 | ✅ 자동 실행 |
| **Fallback** | - | ✅ Regex (vLLM 실패 시) |
| **추천도** | 🔴 deprecated | 🟢 권장 |

---

## 🔐 Privacy Removal 호출 비교

### index.html (/transcribe/) - ❌ 개인정보 미보호

**코드** (web_ui/static/js/main.js:387):
```javascript
formData.append('privacy_removal', 'false');  // ❌ Hard-coded false
formData.append('privacy_llm_type', 'vllm');  // 설정만 함 (무시됨)
```

**API 서버 처리** (api_server/transcribe_endpoint.py:58):
```python
self.privacy_removal = privacy_removal.lower() in ['true', '1', 'yes', 'on']
# 'false' → False
# → perform_privacy_removal() 호출 안 됨
```

**처리 흐름**:
```
STT 완료 → [Privacy Removal 단계 스킵] → Element Detection → 완료
          ❌ 개인정보 제거 안 됨
```

---

### upload.html (/api/analysis/start) - ✅ 개인정보 보호

**코드** (web_ui/app/services/analysis_service.py:661):
```python
stt_result = await stt_service.transcribe_local_file(
    privacy_removal=True,  # ✅ Python boolean (True)
    element_detection=True
)
```

**FormData 변환** (web_ui/app/services/stt_service.py:141):
```python
data.add_field("privacy_removal", str(privacy_removal).lower())
# True → "true" (문자열)
```

**API 서버 파싱** (api_server/transcribe_endpoint.py:58):
```python
self.privacy_removal = privacy_removal.lower() in ['true', '1', 'yes', 'on']
# "true" → True
# → perform_privacy_removal() 호출됨 ✅
```

**처리 흐름**:
```
STT 완료 
    ↓
Privacy Removal (vLLM + Qwen)
    ├─ LLM 호출 성공 → JSON 파싱 → 개인정보 제거 ✅
    └─ LLM 호출 실패 → Regex Fallback → 기본 패턴 제거 ✅
    ↓
Element Detection → Classification (선택) → 완료
```

**vLLM 설정값** (api_server/transcribe_endpoint.py:228-273):
```python
async def perform_privacy_removal(
    text: str,
    prompt_type: str = "privacy_remover_default_v6",
    llm_type: str = "vllm",  # ✅ 기본값
    vllm_model_name: Optional[str] = None  # ✅ "/model/qwen30_thinking_2507" 전달됨
):
    # LLMClientFactory → QwenClient 라우팅 ✅
    # vLLM API: http://localhost:8001/v1 ✅
    # Temperature: 0.3, Max tokens: 32768 ✅
    # Fallback: Regex (LLM 실패 시) ✅
```
)
```

**결과**: 개인정보가 **vLLM + Qwen으로 자동 제거** ✅

---

## 🔜 향후 계획

### 단기 (1개월 이내)
- [ ] index.html ← upload.html로 통합 고려
- [ ] main.js의 미사용 함수 완전 제거 또는 보관 (별도 파일)

### 중기 (3-6개월)
- [ ] API 서버의 `/transcribe/` 엔드포인트 deprecated 표시
- [ ] 사용자 가이드 전환 (index.html → upload.html)

### 장기
- [ ] `/transcribe/` 엔드포인트 제거 (다른 클라이언트 확인 후)

---

## 📝 레거시 코드 상태

**main.js의 레거시 섹션** (라인 수):
- 글로벌 변수: 4라인
- 파일 업로드 이벤트: 100+ 라인
- 파일 선택 처리: 10라인
- 파일 업로드: 25라인
- 백엔드 설정: 60라인
- STT 처리: 100+ 라인
- 결과 표시: 200+ 라인
- 배치 처리: 150+ 라인

**총**: 약 650라인 (main.js 전체 976라인 중 ~67%)

---

## 📖 관련 문서

- [WEB_UI_MIGRATION_SUMMARY.md](./WEB_UI_MIGRATION_SUMMARY.md) - 마이그레이션 보고서
- [LEGACY_CODE_CLEANUP.md](./LEGACY_CODE_CLEANUP.md) - 정리 계획
- [API_SERVER_FLOW_ANALYSIS.md](./API_SERVER_FLOW_ANALYSIS.md) - API 흐름 분석
