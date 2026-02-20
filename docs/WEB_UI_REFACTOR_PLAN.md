# Web UI 개선 계획 (부당권유/불완전판매 탐지 기능)

## 📋 개요

기존 web_ui를 개선하여 다음 기능을 추가:
- **사용자 인증**: 사번 기반 로그인 (세션 기반)
- **파일 관리**: 사번별 폴더 격리, 날짜/커스텀 폴더 구조
- **향상된 분석**: 부당권유/불완전판매 탐지 옵션
- **DB 메타데이터**: SQLite 기반 사용자/파일/분석 결과 관리

---

## 🗂️ 현재 구조 vs 개선 구조

### 현재 web_ui 구조
```
web_ui/
├── main.py                # FastAPI 앱
├── config.py              # 설정
├── requirements.txt
├── models/
│   └── schemas.py         # Pydantic 모델
├── services/
│   ├── stt_service.py     # STT 엔진 호출
│   ├── file_service.py    # 파일 관리
│   └── batch_service.py   # 배치 처리
├── routes/                # API 라우터
├── templates/
│   └── index.html         # 단일 페이지 (로그인 없음)
├── static/
│   ├── css/
│   ├── js/
│   └── ...
└── data/                  # 파일 저장소
```

### 개선 구조
```
web_ui/
├── main.py                # FastAPI 앱 (인증 미들웨어 추가)
├── config.py              # 설정 (DB URL, 임직원 목록 등)
├── requirements.txt       # 의존성
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py    # SQLAlchemy ORM 모델
│   │   └── schemas.py     # Pydantic 스키마
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py    # 인증 (세션/쿠키)
│   │   ├── stt_service.py     # STT 호출 (기존 개선)
│   │   ├── file_service.py    # 파일 관리 (사번 격리 추가)
│   │   ├── analysis_service.py # 분석 작업 관리 (NEW)
│   │   └── upload_service.py  # 업로드 관리 (NEW)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py            # 인증 엔드포인트 (NEW)
│   │   ├── files.py           # 파일 목록/검색 (NEW)
│   │   ├── upload.py          # 파일 업로드 (NEW)
│   │   ├── analysis.py        # 분석 시작/상태/결과 (NEW)
│   │   └── transcribe.py      # STT 변환 (기존)
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── db.py              # DB 세션, 초기화
│   │   └── logger.py          # 로깅
│   └── tasks/
│       ├── __init__.py
│       └── analysis_worker.py # 비동기 분석 워커 (NEW)
├── templates/
│   ├── index.html         # 로그인 페이지 (NEW)
│   ├── upload.html        # 파일 업로드/관리 (NEW)
│   └── analysis.html      # 분석 (기존 개선)
├── static/
│   ├── css/
│   │   ├── style.css      # 기본 스타일 (개선)
│   │   └── responsive.css # 반응형 (NEW)
│   └── js/
│       ├── common.js      # 공통 함수 (NEW)
│       ├── upload.js      # 업로드 로직 (NEW)
│       ├── analysis.js    # 분석 로직 (개선)
│       └── main.js        # 메인 (기존 개선)
├── data/
│   ├── stt_web.db         # SQLite DB (NEW)
│   └── uploads/           # 파일 저장소 (구조 개선)
│       └── {emp_id}/
│           ├── {YYYY-MM-DD}/
│           └── {폴더명}/
└── logs/                  # 로그 디렉토리
```

---

## 🔄 개선 단계

### Phase 1: 기초 인프라 (1주)

#### 1-1. 데이터베이스 모델 추가
- `app/models/database.py` 생성
  - Employee (직원 정보)
  - FileUpload (파일 메타데이터)
  - AnalysisJob (분석 작업)
  - AnalysisResult (분석 결과)
  - AnalysisProgress (진행 상태)

#### 1-2. 인증 시스템 추가 (세션 기반)
- `app/services/auth_service.py` 생성
  - 세션 쿠키 기반 인증 (JWT 제외)
  - 직원 목록 검증
- `app/routes/auth.py` 생성
  - POST /api/auth/login - 로그인
  - POST /api/auth/logout - 로그아웃
  - GET /api/auth/session - 세션 확인
- `templates/index.html` 생성
  - 로그인 페이지 UI

#### 1-3. 설정 및 유틸리티
- `config.py` 업데이트
  - DATABASE_URL 추가
  - ALLOWED_EMPLOYEES 추가 (임시)
  - 세션 설정
- `app/utils/db.py` 생성
  - DB 세션 관리
  - DB 초기화

#### 1-4. 프론트엔드 기반 구성
- `static/js/common.js` 생성
  - 세션 확인, 로그아웃
  - API 호출 헬퍼
  - 알림/포맷팅 유틸
- `static/css/style.css` 개선
  - 로그인 페이지 스타일
  - 반응형 디자인

---

### Phase 2: 파일 관리 (1주)

#### 2-1. 업로드 서비스 개선
- `app/services/upload_service.py` 생성
  - 사번별 폴더 격리
  - 날짜/커스텀 폴더 자동 생성
  - 파일 메타데이터 저장
- `app/routes/upload.py` 생성
  - POST /api/upload - 파일 업로드
  - GET /api/uploads/{emp_id} - 업로드 목록
  - POST /api/uploads/folder - 폴더 생성

#### 2-2. 파일 관리 라우터
- `app/routes/files.py` 생성
  - GET /api/files/{emp_id} - 폴더/파일 목록
  - GET /api/files/search - 검색
  - DELETE /api/files/{file_id} - 삭제

#### 2-3. 업로드 UI 개선
- `templates/upload.html` 생성
  - 드래그앤드롭 업로드
  - 폴더 목록 + 파일 목록
  - 검색 기능
  - 폴더 선택 후 analysis.html로 이동

---

### Phase 3: 분석 시스템 (1.5주)

#### 3-1. 분석 서비스 생성
- `app/services/analysis_service.py` 생성
  - AnalysisJob 관리
  - 파일 목록에서 분석 시작
  - 진행 상태 업데이트
  
#### 3-2. 분석 라우터
- `app/routes/analysis.py` 생성
  - POST /api/analysis/start - 분석 시작
  - GET /api/analysis/{job_id}/progress - 진행 상황
  - GET /api/analysis/{job_id}/results - 결과 조회

#### 3-3. 비동기 워커
- `app/tasks/analysis_worker.py` 생성
  - 백그라운드 분석 처리
  - STT → 분류 → 부당권유 탐지 → 불완전판매 탐지
  - AI Agent 호출

#### 3-4. 분석 UI 개선
- `templates/analysis.html` 개선
  - 분석 옵션 선택 (부당권유, 불완전판매)
  - AI Agent URL 설정 (선택사항)
  - 실시간 진행 상황 표시
  - 분석 결과 표시
  - 미디어 플레이어 (브라우저 재생)

---

### Phase 4: 통합 및 테스트 (1주)

#### 4-1. 전체 워크플로우 통합
- index.html → upload.html → analysis.html 흐름
- 세션 기반 인증 유지
- 에러 처리 및 로깅

#### 4-2. 성능 최적화
- 대용량 파일 처리 (streaming)
- 동시 분석 제한
- 캐싱 전략

#### 4-3. 테스트
- 단위 테스트
- 통합 테스트
- 성능 테스트

---

## 🗄️ 필수 변경 사항

### config.py 업데이트
```python
# 데이터베이스
DATABASE_URL = "sqlite:///data/stt_web.db"

# 임직원 (임시, 추후 DB 이동)
ALLOWED_EMPLOYEES = {
    "10001": {"name": "홍길동", "dept": "금융감시팀"},
    "10002": {"name": "이순신", "dept": "법무팀"},
}

# 세션 설정
SESSION_SECRET_KEY = "your-secret-key"
SESSION_TIMEOUT_HOURS = 8

# AI Agent (사전 정의)
AI_AGENTS = {
    "improper_solicitation": {
        "url": "http://localhost:5000/api/detect",
        "format": "text_only"
    },
    "incomplete_sales": {
        "url": "http://localhost:5001/api/detect",
        "format": "text_only"
    }
}
```

### main.py 업데이트
```python
# 세션 미들웨어 추가
from fastapi.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# DB 초기화
from app.utils.db import init_db
init_db()

# 라우터 등록
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(upload.router)
app.include_router(analysis.router)
```

### 파일 저장 구조
```
data/uploads/
├── 10001/
│   ├── 2026-02-20/
│   │   ├── recording_001.wav
│   │   └── recording_002.wav
│   └── 부당권유_검토/
│       ├── case_001.wav
│       └── case_002.wav
└── 10002/
    ├── 2026-02-20/
    │   └── recording_001.wav
    └── 정상판매_사례/
        └── case_001.wav
```

---

## 📊 DB 스키마

### Employees 테이블
```sql
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    emp_id VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100),
    dept VARCHAR(100),
    created_at TIMESTAMP,
    last_login TIMESTAMP
);
```

### FileUploads 테이블
```sql
CREATE TABLE file_uploads (
    id INTEGER PRIMARY KEY,
    emp_id VARCHAR(10) NOT NULL,
    folder_path VARCHAR(500) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_size_mb FLOAT,
    created_at TIMESTAMP,
    FOREIGN KEY(emp_id) REFERENCES employees(emp_id)
);
```

### AnalysisJobs 테이블
```sql
CREATE TABLE analysis_jobs (
    id INTEGER PRIMARY KEY,
    job_id VARCHAR(50) UNIQUE NOT NULL,
    emp_id VARCHAR(10) NOT NULL,
    folder_path VARCHAR(500) NOT NULL,
    file_ids TEXT,
    status VARCHAR(20),  -- pending, running, completed, failed
    detect_improper_solicitation BOOLEAN DEFAULT 0,
    detect_incomplete_sales BOOLEAN DEFAULT 0,
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY(emp_id) REFERENCES employees(emp_id)
);
```

### AnalysisResults 테이블
```sql
CREATE TABLE analysis_results (
    id INTEGER PRIMARY KEY,
    job_id VARCHAR(50) NOT NULL,
    file_id INTEGER NOT NULL,
    filename VARCHAR(255),
    
    -- STT 결과
    stt_text TEXT,
    stt_duration_sec FLOAT,
    stt_processing_time_sec FLOAT,
    
    -- 분석 상태
    status_stt VARCHAR(20),
    status_classification VARCHAR(20),
    status_improper_detection VARCHAR(20),
    status_incomplete_detection VARCHAR(20),
    
    -- 분류 결과
    classification_code VARCHAR(10),
    classification_category VARCHAR(100),
    
    -- 부당권유 탐지 결과
    improper_solicitation_detected BOOLEAN,
    improper_solicitation_items TEXT,
    improper_solicitation_agent_response TEXT,
    
    -- 불완전판매 탐지 결과
    incomplete_sales_detected BOOLEAN,
    incomplete_sales_items TEXT,
    incomplete_sales_agent_response TEXT,
    
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES analysis_jobs(job_id)
);
```

---

## 🔐 세션 기반 인증 (JWT 제외)

### 로그인 흐름
```
1. index.html에서 사번 입력
2. POST /api/auth/login으로 전송
3. 서버에서 사번 검증 (ALLOWED_EMPLOYEES)
4. 세션 쿠키 발급 (httpOnly, Secure)
5. upload.html로 리다이렉트
6. 이후 요청에서 쿠키로 자동 인증
```

### 세션 만료
- 로그아웃 시: 세션 삭제
- 8시간 타임아웃: 자동 로그인 만료
- 재로그인 필요

---

## 📁 생성/수정 파일 목록

### 생성할 파일
- [ ] app/models/database.py
- [ ] app/models/schemas.py (기존 개선)
- [ ] app/services/auth_service.py
- [ ] app/services/analysis_service.py
- [ ] app/services/upload_service.py
- [ ] app/routes/auth.py
- [ ] app/routes/files.py
- [ ] app/routes/upload.py
- [ ] app/routes/analysis.py
- [ ] app/utils/db.py
- [ ] app/utils/logger.py
- [ ] app/tasks/analysis_worker.py
- [ ] templates/index.html (로그인)
- [ ] templates/upload.html (파일 관리)
- [ ] templates/analysis.html (개선)
- [ ] static/js/common.js
- [ ] static/js/upload.js
- [ ] static/js/analysis.js
- [ ] static/css/responsive.css

### 수정할 파일
- [ ] config.py (DB URL, 세션 설정 추가)
- [ ] main.py (미들웨어, 라우터, DB 초기화)
- [ ] requirements.txt (sqlalchemy, python-multipart)
- [ ] services/stt_service.py (부당권유 탐지 옵션 추가)

---

## ⏱️ 예상 소요 시간

| Phase | 내용 | 기간 |
|-------|------|------|
| Phase 1 | 기초 인프라 (인증, DB, 로그인 UI) | 1주 |
| Phase 2 | 파일 관리 (업로드, 폴더 구조, 목록) | 1주 |
| Phase 3 | 분석 시스템 (부당권유/불완전판매 탐지) | 1.5주 |
| Phase 4 | 통합, 테스트, 배포 | 1주 |
| **총계** | | **4.5주** |

---

## 🚀 다음 단계

1. **Phase 1 시작**: 데이터베이스 모델 + 세션 기반 인증 + 로그인 UI
2. **Phase 2 시작**: 파일 업로드 및 관리 (사번별 격리)
3. **Phase 3 시작**: 분석 시스템 (부당권유/불완전판매 탐지)
4. **Phase 4**: 통합 테스트 및 배포
