# STT Engine Web UI 아키텍처 디자인

## 📋 프로젝트 개요

기존 FastAPI 기반 STT Engine API를 프론트엔드화하는 웹 UI 프로젝트입니다.

### 주요 기능
1. **파일 업로드 모드**: 웹에서 오디오 파일 업로드 → 즉시 처리
2. **배치 처리 모드**: 서버 특정 경로의 파일들을 일괄 처리
3. **결과 관리**: 처리 결과 저장 및 조회

---

## 🏗️ 시스템 아키텍처

### 전체 구조

```
┌─────────────────────────────────────────────────────────┐
│                   Client (Browser)                      │
│                   - HTML/CSS/JavaScript                 │
│                   - Drag & Drop Upload                  │
│                   - Batch Management UI                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTP/REST
                     ↓
┌─────────────────────────────────────────────────────────┐
│              Web UI Server (FastAPI)                     │
│  Port: 8001 (Web UI) / 8002 (WebSocket for streaming)   │
│                                                          │
│  ├─ /                      (Dashboard)                   │
│  ├─ /upload/               (파일 업로드)                 │
│  ├─ /files/                (배치 파일 목록)              │
│  ├─ /process_local/        (배치 처리)                   │
│  ├─ /results/              (결과 조회)                   │
│  ├─ /ws/stream/            (스트리밍 결과)               │
│  └─ /static/               (정적 파일)                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTP (Python requests)
                     ↓
┌─────────────────────────────────────────────────────────┐
│        STT Engine API Server (FastAPI)                   │
│              Port: 8003 (이미 구현됨)                    │
│                                                          │
│  ├─ /transcribe            (일반 처리)                   │
│  ├─ /transcribe_by_upload  (파일 업로드)                 │
│  ├─ /export/               (결과 다운로드)               │
│  └─ /health/               (헬스체크)                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
        ┌──────────────────────────┐
        │   WhisperSTT Engine      │
        │  (faster-whisper, etc.)  │
        └──────────────────────────┘
```

---

## 📂 디렉토리 구조

```
stt_engine/
├── api_server.py              (기존 STT Engine API)
├── stt_engine.py              (기존 모델 로직)
├── 
├── web_ui/                    (새로운 웹 UI 서버)
│   ├── __init__.py
│   ├── main.py                (FastAPI 앱 진입점)
│   ├── config.py              (설정 - 포트, 경로 등)
│   ├── 
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── dashboard.py       (대시보드 라우트)
│   │   ├── upload.py          (파일 업로드)
│   │   ├── batch.py           (배치 처리)
│   │   ├── results.py         (결과 조회/다운로드)
│   │   └── stream.py          (WebSocket 스트리밍)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── stt_service.py     (STT API 통신)
│   │   ├── file_service.py    (파일 관리)
│   │   ├── batch_service.py   (배치 처리 로직)
│   │   └── cache_service.py   (결과 캐싱)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py         (Pydantic 모델)
│   │   └── database.py        (SQLite DB 모델)
│   │
│   ├── static/
│   │   ├── css/
│   │   │   ├── style.css      (전체 스타일)
│   │   │   └── theme.css      (다크/라이트 모드)
│   │   ├── js/
│   │   │   ├── main.js        (메인 로직)
│   │   │   ├── upload.js      (업로드 로직)
│   │   │   ├── batch.js       (배치 관리)
│   │   │   └── utils.js       (공통 유틸)
│   │   ├── images/
│   │   └── fonts/
│   │
│   ├── templates/
│   │   ├── base.html          (기본 템플릿)
│   │   ├── index.html         (대시보드)
│   │   ├── upload.html        (업로드 페이지)
│   │   ├── batch.html         (배치 페이지)
│   │   ├── results.html       (결과 페이지)
│   │   └── components/
│   │       ├── navbar.html
│   │       ├── footer.html
│   │       └── loader.html
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py          (로깅)
│   │   ├── validators.py      (검증)
│   │   └── helpers.py         (헬퍼 함수)
│   │
│   ├── data/
│   │   ├── uploads/           (업로드 파일)
│   │   ├── results/           (처리 결과)
│   │   ├── cache/             (캐시 데이터)
│   │   └── db.sqlite          (SQLite DB)
│   │
│   ├── requirements.txt        (의존성)
│   ├── run.py                 (실행 스크립트)
│   ├── docker/
│   │   ├── Dockerfile.web_ui  (Web UI Docker)
│   │   └── docker-compose.yml (전체 Compose)
│   │
│   └── README.md              (Web UI 사용 가이드)
│
└── [기존 파일들...]
```

---

## 🔌 API 명세

### Web UI Server Routes

#### 1. Dashboard
```
GET /
  - 응답: HTML (대시보드)
```

#### 2. 파일 업로드
```
POST /api/upload/
  - Content-Type: multipart/form-data
  - Body: { file: File }
  - 응답: {
      "success": bool,
      "file_id": string,
      "filename": string,
      "file_size_mb": float,
      "upload_time_sec": float
    }
```

#### 3. STT 처리 (업로드한 파일)
```
POST /api/transcribe/
  - Content-Type: application/json
  - Body: { "file_id": string, "language": string }
  - 응답: {
      "success": bool,
      "file_id": string,
      "text": string,
      "language": string,
      "duration_sec": float,
      "processing_time_sec": float,
      "backend": string
    }
```

#### 4. 배치 파일 목록
```
GET /api/batch/files/
  - Query: { 
      "path": string (optional, 기본: ./data/batch_input),
      "extension": string (기본: .wav)
    }
  - 응답: {
      "total": int,
      "files": [
        {
          "name": string,
          "path": string,
          "size_mb": float,
          "modified": datetime,
          "status": "pending|processing|done|error"
        }
      ]
    }
```

#### 5. 배치 처리 시작
```
POST /api/batch/start/
  - Content-Type: application/json
  - Body: {
      "path": string,
      "extension": string,
      "language": string,
      "parallel_count": int (기본: 2)
    }
  - 응답: {
      "batch_id": string,
      "total_files": int,
      "status": "started"
    }
```

#### 6. 배치 진행 상황
```
GET /api/batch/progress/{batch_id}/
  - 응답: {
      "batch_id": string,
      "total": int,
      "completed": int,
      "failed": int,
      "current_file": string,
      "estimated_remaining_sec": float,
      "files": [
        {
          "name": string,
          "status": "pending|processing|done|error",
          "processing_time_sec": float
        }
      ]
    }
```

#### 7. 결과 조회
```
GET /api/results/{file_id}/
  - 응답: {
      "file_id": string,
      "filename": string,
      "text": string,
      "language": string,
      "duration_sec": float,
      "processing_time_sec": float,
      "created_at": datetime,
      "backend": string
    }
```

#### 8. 결과 다운로드
```
GET /api/results/{file_id}/export/?format=txt|json
  - 응답: File (text/plain 또는 application/json)
```

#### 9. WebSocket 스트리밍
```
WS /ws/stream/{file_id}/
  - 메시지 형식:
    {
      "type": "progress|result|error",
      "data": {...}
    }
```

---

## 🛠️ 기술 스택

### Backend
- **Framework**: FastAPI 0.109.0
- **Server**: Uvicorn
- **Database**: SQLite + SQLAlchemy
- **WebSocket**: Python WebSockets
- **HTTP Client**: aiohttp (비동기)
- **Logging**: Python logging

### Frontend
- **Markup**: Jinja2 Templates + HTML5
- **Styling**: CSS3 (Flexbox, Grid)
- **JavaScript**: Vanilla JS (ES6+)
- **File Upload**: Fetch API + Drag & Drop
- **Real-time**: WebSocket + Progress EventSource

### Deployment
- **Docker**: Multi-container setup
- **Compose**: Docker Compose
- **Port Mapping**: 
  - Web UI: 8001
  - STT API: 8003 (내부 연결)

---

## 🚀 배포 옵션

### Option A: Standalone FastAPI (개발/테스트)
```bash
cd web_ui
python run.py
# http://localhost:8001
```

### Option B: Docker Compose (권장)
```bash
docker-compose -f web_ui/docker/docker-compose.yml up
# 자동으로 Web UI (8001) + STT API (8003) 실행
```

### Option C: Kubernetes (확장용)
- 별도 Helm Chart 작성 가능

---

## 🔄 데이터 흐름

### 파일 업로드 → 처리 흐름

```
User uploads file
    ↓
Web UI validates & saves to /uploads/
    ↓
User clicks "Process"
    ↓
Web UI → STT API (/transcribe)
    ↓
STT Engine processes
    ↓
Result stored in SQLite + /results/
    ↓
Web UI displays result
    ↓
User can download (txt/json)
```

### 배치 처리 흐름

```
Admin: Load files from ./batch_input/
    ↓
Web UI: GET /api/batch/files/
    ↓
Display file list in table
    ↓
Admin: Click "Start Batch"
    ↓
Web UI: POST /api/batch/start/
    ↓
Background: Process files (parallel, configurable)
    ↓
WS: Push progress updates
    ↓
Frontend: Update UI in real-time
    ↓
Store results in /results/
    ↓
Completion notification
```

---

## 💾 데이터베이스 스키마

### SQLite 구조

```sql
-- 처리 결과 저장
CREATE TABLE transcriptions (
    id INTEGER PRIMARY KEY,
    file_id TEXT UNIQUE,
    filename TEXT,
    original_filename TEXT,
    language TEXT DEFAULT 'auto',
    text TEXT,
    duration_sec FLOAT,
    processing_time_sec FLOAT,
    backend TEXT,
    file_size_mb FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'done',
    error_message TEXT
);

-- 배치 작업 추적
CREATE TABLE batch_jobs (
    id INTEGER PRIMARY KEY,
    batch_id TEXT UNIQUE,
    status TEXT DEFAULT 'pending',
    total_files INTEGER,
    processed_files INTEGER,
    failed_files INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 배치 파일 상태
CREATE TABLE batch_files (
    id INTEGER PRIMARY KEY,
    batch_id TEXT,
    file_id TEXT,
    filename TEXT,
    path TEXT,
    status TEXT DEFAULT 'pending',
    processing_time_sec FLOAT,
    error_message TEXT,
    FOREIGN KEY(batch_id) REFERENCES batch_jobs(batch_id)
);
```

---

## 🔒 보안 고려사항

1. **파일 검증**
   - 파일 크기 제한 (100MB 이상 차단)
   - 파일 확장자 검증 (.wav, .mp3, .m4a만)
   - MIME type 검증

2. **경로 보안**
   - 배치 경로는 whitelist 기반
   - 상위 디렉토리 접근 방지

3. **Rate Limiting**
   - 동시 업로드 제한
   - API 호출 제한

4. **CORS 설정**
   - 필요시만 활성화

---

## 📊 모니터링 & 로깅

### 로깅 레벨
- DEBUG: 개발 중 상세 정보
- INFO: 일반 동작 정보
- WARNING: 경고 메시지
- ERROR: 에러 정보

### 메트릭
- 처리된 파일 수
- 평균 처리 시간
- 에러율
- 시스템 리소스 사용량

---

## 📝 구현 우선순위

### Phase 1 (필수)
- [x] Web UI 서버 구조
- [x] 파일 업로드 기능
- [x] STT API 통신
- [x] 기본 UI (Dashboard)
- [x] 결과 저장 및 조회

### Phase 2 (권장)
- [ ] 배치 처리 기능
- [ ] 배치 진행 상황 실시간 표시
- [ ] 결과 다운로드 (txt/json)
- [ ] 히스토리 관리

### Phase 3 (선택)
- [ ] WebSocket 스트리밍
- [ ] 다크 모드
- [ ] 사용자 계정 시스템
- [ ] 고급 검색 필터

---

## 🐛 테스트 전략

### Unit Tests
```bash
pytest web_ui/tests/
```

### Integration Tests
- Web UI + STT API 연동 테스트
- Docker Compose 환경 테스트

### UI Tests
- 업로드 기능
- 배치 처리
- 결과 다운로드

---

## 📚 참고 자료

- 기존 프로젝트: `/Users/a113211/workspace/kis_stt_main`
- STT API: `/Users/a113211/workspace/stt_engine/api_server.py`
- FastAPI 문서: https://fastapi.tiangolo.com/
- Docker Compose: https://docs.docker.com/compose/

