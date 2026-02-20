# STT 웹 서비스 (부당권유/불완전판매 탐지) 구현 계획

## 📋 개요

금융상품 판매 녹취 음성을 STT로 변환하고, 부당권유 및 불완전판매 요소를 탐지하는 웹 서비스

**주요 특징:**
- 사번 기반 사용자 인증 및 격리
- 계층적 폴더 구조 (사번 > 날짜/폴더명)
- 비동기 분석 처리
- SQLite 기반 메타데이터 관리
- 실시간 진행 상태 모니터링

---

## 📁 디렉토리 구조

```
scratch/stt-web/
├── backend/                      # FastAPI 백엔드
│   ├── main.py                   # 메인 앱
│   ├── config.py                 # 설정 관리
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── routers/              # API 라우터
│   │   │   ├── auth.py           # 인증 (로그인/검증)
│   │   │   ├── upload.py         # 파일/폴더 업로드
│   │   │   ├── analysis.py       # 분석 시작/상태/결과
│   │   │   └── files.py          # 파일 목록/검색
│   │   ├── models/               # 데이터 모델
│   │   │   ├── schemas.py        # Pydantic 스키마
│   │   │   └── database.py       # SQLAlchemy 모델
│   │   ├── services/             # 비즈니스 로직
│   │   │   ├── auth_service.py   # 사용자 인증
│   │   │   ├── upload_service.py # 파일 업로드 관리
│   │   │   ├── analysis_service.py # 분석 태스크
│   │   │   └── stt_engine_client.py # STT 엔진 연결
│   │   ├── utils/
│   │   │   ├── db.py             # DB 초기화/관리
│   │   │   └── logger.py         # 로깅
│   │   └── tasks/                # 백그라운드 태스크
│   │       └── analysis_worker.py # 비동기 분석 워커
│   └── data/
│       ├── stt_web.db            # SQLite DB
│       └── uploads/              # 파일 저장소
│           └── {사번}/
│               ├── {폴더명}/
│               │   └── *.wav
│               └── {YYYY-MM-DD}/
│                   └── *.wav
│
├── frontend/                     # 정적 파일
│   ├── index.html                # 로그인 페이지
│   ├── upload.html               # 업로드 관리 페이지
│   ├── analysis.html             # 분석 페이지
│   ├── css/
│   │   ├── style.css
│   │   └── responsive.css
│   └── js/
│       ├── common.js             # 공통 함수
│       ├── upload.js             # 업로드 로직
│       └── analysis.js           # 분석 로직
│
└── docs/
    ├── API.md                    # API 명세서
    └── DATABASE.md               # DB 스키마
```

---

## 🔐 인증 시스템

### 1. 로그인 (index.html)
- **입력:** 사번 (직원 ID)
- **검증:** 등록된 사번 확인 또는 LDAP/SSO 연동
- **세션:** JWT 토큰 또는 세션 쿠키로 관리
- **동작:**
  - 사번 입력 → 서버 검증 → 토큰 발급
  - 이후 모든 요청에 토큰 포함
  - 만료 시 재로그인

```python
# 임시 구현: 간단한 사번 검증
ALLOWED_EMPLOYEES = {
    "10001": {"name": "홍길동", "dept": "금융감시팀"},
    "10002": {"name": "이순신", "dept": "법무팀"},
    # ...
}
```

---

## 📤 파일 업로드 (upload.html)

### 2. 업로드 구조

**사용자 격리:**
```
/uploads/{사번}/
├── 2026-02-20/           # 업로드 날짜 기반 폴더 (자동 생성)
│   ├── recording_001.wav
│   └── recording_002.wav
└── 부당권유_검토/        # 사용자 지정 폴더 (upsert)
    ├── case_001.wav
    └── case_002.wav
```

### 3. 업로드 기능

**UI 요소:**
- 드래그 앤 드롭 (파일/폴더)
- 브라우저 파일 선택
- 대상 폴더 선택 또는 신규 폴더 입력
- 진행 상황 표시

**서버 처리:**
```python
# 1. 폴더 선택 여부 확인
if folder_name:
    target_path = f"/uploads/{employee_id}/{folder_name}/"
    # UPSERT: 존재하면 파일 추가, 없으면 생성
else:
    today = datetime.now().strftime("%Y-%m-%d")
    target_path = f"/uploads/{employee_id}/{today}/"
    # 자동 생성

# 2. 파일 저장
for file in uploaded_files:
    save_path = f"{target_path}{file.filename}"
    # 바이너리 저장
    
# 3. DB에 메타데이터 저장
insert_file_metadata(employee_id, folder_path, filename, size, created_at)
```

### 4. 업로드 목록 조회

**표시 정보:**
- 폴더 경로
- 파일 개수
- 총 용량
- 업로드 일시
- 검색 기능 (폴더명/파일명)

**정렬:**
- 최신순
- 이름순
- 크기순

---

## 🔍 분석 (analysis.html)

### 5. 분석 대상 선택

**UI 플로우:**
1. upload.html에서 폴더 선택 → analysis.html로 이동
2. analysis.html에서 폴더 내 파일 목록 표시
3. 분석 옵션 선택:
   - ☐ 부당권유 판매 요소 탐지
   - ☐ 불완전판매 요소 탐지
4. 각 탐지의 AI Agent 설정 (선택사항)
5. 분석 시작 버튼

### 6. 분석 옵션

```python
class AnalysisOption(BaseModel):
    """분석 옵션"""
    employee_id: str
    folder_path: str
    files: List[str]  # 선택된 파일들
    
    # 탐지 옵션
    detect_improper_solicitation: bool = False  # 부당권유
    detect_incomplete_sales: bool = False       # 불완전판매
    
    # Agent 설정
    improper_solicitation_agent_url: Optional[str] = None
    improper_solicitation_agent_format: str = "text_only"
    
    incomplete_sales_agent_url: Optional[str] = None
    incomplete_sales_agent_format: str = "text_only"
```

### 7. 분석 처리 흐름

```
[분석 시작] 
    ↓
[각 파일마다]
    ├─ STT 변환 (STT 엔진 호출)
    ├─ 내용 분류 (선택사항)
    ├─ 부당권유 탐지 (AI Agent 호출, if selected)
    └─ 불완전판매 탐지 (AI Agent 호출, if selected)
    ↓
[결과 저장 및 DB 업데이트]
    ↓
[상태 실시간 전달 (WebSocket/polling)]
```

### 8. 분석 결과 표시

**레이아웃:**
```
[파일 정보]
├─ 파일명
├─ 미디어 플레이어 (브라우저 재생)
└─ 파일 메타정보 (크기, 길이, 업로드 일시)

[STT 결과]
├─ 변환된 텍스트
└─ 처리 시간, 신뢰도

[분석 상태]
├─ ⏳ 대기 중
├─ 🔄 STT 변환 중 → ✅ 완료
├─ 🔄 내용 분류 중 → ✅ 완료
├─ 🔄 부당권유 탐지 중 → ✅ 완료 (if selected)
└─ 🔄 불완전판매 탐지 중 → ✅ 완료 (if selected)

[탐지 결과]
├─ 부당권유 판매 탐지 결과
│   ├─ 탐지 여부
│   ├─ 탐지 항목 목록
│   └─ AI Agent 분석 내용
│
└─ 불완전판매 탐지 결과
    ├─ 탐지 여부
    ├─ 탐지 항목 목록
    └─ AI Agent 분석 내용
```

---

## 🗄️ 데이터베이스 스키마

### 9. SQLite 테이블 설계

```sql
-- 1. 사용자
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    emp_id VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100),
    dept VARCHAR(100),
    created_at TIMESTAMP,
    last_login TIMESTAMP
);

-- 2. 폴더/파일 메타데이터
CREATE TABLE file_uploads (
    id INTEGER PRIMARY KEY,
    emp_id VARCHAR(10) NOT NULL,
    folder_path VARCHAR(500) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_size_mb FLOAT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY(emp_id) REFERENCES employees(emp_id)
);

-- 3. 분석 작업
CREATE TABLE analysis_jobs (
    id INTEGER PRIMARY KEY,
    job_id VARCHAR(50) UNIQUE NOT NULL,
    emp_id VARCHAR(10) NOT NULL,
    folder_path VARCHAR(500) NOT NULL,
    file_ids TEXT,  # JSON list of file IDs
    status VARCHAR(20),  # pending, running, completed, failed
    
    -- 분석 옵션
    detect_improper_solicitation BOOLEAN DEFAULT 0,
    detect_incomplete_sales BOOLEAN DEFAULT 0,
    improper_solicitation_agent_url TEXT,
    incomplete_sales_agent_url TEXT,
    
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY(emp_id) REFERENCES employees(emp_id)
);

-- 4. 파일별 분석 결과
CREATE TABLE analysis_results (
    id INTEGER PRIMARY KEY,
    job_id VARCHAR(50) NOT NULL,
    file_id INTEGER NOT NULL,
    filename VARCHAR(255),
    
    -- STT 결과
    stt_text TEXT,
    stt_duration_sec FLOAT,
    stt_processing_time_sec FLOAT,
    stt_confidence FLOAT,
    
    -- 분석 상태
    status_stt VARCHAR(20),  # pending, processing, done, error
    status_classification VARCHAR(20),
    status_improper_detection VARCHAR(20),
    status_incomplete_detection VARCHAR(20),
    
    -- 분류 결과
    classification_code VARCHAR(10),
    classification_category VARCHAR(100),
    classification_confidence FLOAT,
    classification_reason TEXT,
    
    -- 부당권유 탐지 결과
    improper_solicitation_detected BOOLEAN,
    improper_solicitation_items TEXT,  # JSON
    improper_solicitation_agent_response TEXT,
    
    -- 불완전판매 탐지 결과
    incomplete_sales_detected BOOLEAN,
    incomplete_sales_items TEXT,  # JSON
    incomplete_sales_agent_response TEXT,
    
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES analysis_jobs(job_id),
    FOREIGN KEY(file_id) REFERENCES file_uploads(id)
);

-- 5. 분석 진행 상태 (WebSocket 업데이트용)
CREATE TABLE analysis_progress (
    id INTEGER PRIMARY KEY,
    job_id VARCHAR(50) NOT NULL,
    file_id INTEGER NOT NULL,
    step VARCHAR(50),  # stt, classification, improper, incomplete
    progress_percent INTEGER,  # 0-100
    current_status VARCHAR(50),  # pending, processing, done, error
    message TEXT,
    updated_at TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES analysis_jobs(job_id)
);
```

---

## 🔄 비동기 분석 처리

### 10. 처리 흐름

**큐 기반 시스템:**
```
사용자 [분석 시작 요청]
    ↓
API [AnalysisJob 생성]
    ↓
DB [job status = "pending"]
    ↓
Worker [job 감지]
    ↓
  ┌─ 파일1 처리 ─┐
  │              ├─ API 응답 (job_id 반환, polling 시작)
  ├─ 파일2 처리 ─┤
  │              └─ 백그라운드 처리 계속
  └─ 파일3 처리 ─┘
    ↓
DB [각 단계별 status 업데이트]
    ↓
Frontend [WebSocket/polling으로 실시간 업데이트]
```

### 11. Worker 구현

```python
# tasks/analysis_worker.py

class AnalysisWorker:
    async def process_job(self, job_id):
        """비동기 분석 태스크"""
        job = db.get_analysis_job(job_id)
        
        for file_id in job.file_ids:
            file_info = db.get_file_info(file_id)
            
            try:
                # 1. STT 변환
                update_progress(job_id, file_id, "stt", "processing")
                stt_result = await stt_engine_client.transcribe(file_info.path)
                
                update_progress(job_id, file_id, "stt", "done")
                
                # 2. 내용 분류 (옵션)
                classification_result = await stt_engine_client.classify(stt_result.text)
                
                # 3. 부당권유 탐지 (옵션)
                if job.detect_improper_solicitation:
                    update_progress(job_id, file_id, "improper", "processing")
                    improper_result = await call_ai_agent(
                        agent_url=job.improper_solicitation_agent_url,
                        text=stt_result.text,
                        agent_type="improper_solicitation"
                    )
                    update_progress(job_id, file_id, "improper", "done")
                
                # 4. 불완전판매 탐지 (옵션)
                if job.detect_incomplete_sales:
                    update_progress(job_id, file_id, "incomplete", "processing")
                    incomplete_result = await call_ai_agent(
                        agent_url=job.incomplete_sales_agent_url,
                        text=stt_result.text,
                        agent_type="incomplete_sales"
                    )
                    update_progress(job_id, file_id, "incomplete", "done")
                
                # 결과 저장
                save_result(job_id, file_id, {
                    "stt": stt_result,
                    "classification": classification_result,
                    "improper_solicitation": improper_result if job.detect_improper_solicitation else None,
                    "incomplete_sales": incomplete_result if job.detect_incomplete_sales else None
                })
                
            except Exception as e:
                update_progress(job_id, file_id, "error", str(e))
                log_error(job_id, file_id, e)
        
        # 전체 작업 완료
        db.update_job_status(job_id, "completed")
```

---

## 📡 API 명세서

### 12. 주요 엔드포인트

```
POST /api/auth/login
  요청: {"emp_id": "10001"}
  응답: {"token": "jwt_token", "emp_id": "10001", "name": "홍길동"}

GET /api/files?emp_id={emp_id}&folder={folder_name}
  응답: {
    "folders": [
      {"name": "2026-02-20", "file_count": 3, "total_size_mb": 50},
      {"name": "부당권유_검토", "file_count": 5, "total_size_mb": 100}
    ],
    "files": [
      {"id": 1, "name": "recording_001.wav", "size_mb": 20, "created_at": "2026-02-20T10:30:00"}
    ]
  }

POST /api/upload
  요청: FormData { files: [File], target_folder: "2026-02-20" }
  응답: {"uploaded_count": 3, "total_size_mb": 50}

POST /api/analysis/start
  요청: {
    "emp_id": "10001",
    "folder_path": "/uploads/10001/2026-02-20/",
    "files": ["recording_001.wav", "recording_002.wav"],
    "detect_improper_solicitation": true,
    "detect_incomplete_sales": false,
    "improper_solicitation_agent_url": "http://agent-server:5000/api/detect",
    "improper_solicitation_agent_format": "text_only"
  }
  응답: {"job_id": "job_abc123", "status": "pending"}

GET /api/analysis/{job_id}/progress
  응답: {
    "job_id": "job_abc123",
    "status": "running",
    "files_processed": 2,
    "files_total": 5,
    "progress_percent": 40,
    "current_file": "recording_003.wav",
    "current_step": "improper_detection",
    "file_progress": [
      {
        "filename": "recording_001.wav",
        "status": "completed",
        "steps": {
          "stt": "done",
          "classification": "done",
          "improper_detection": "done"
        }
      }
    ]
  }

GET /api/analysis/{job_id}/results
  응답: {
    "job_id": "job_abc123",
    "status": "completed",
    "results": [
      {
        "filename": "recording_001.wav",
        "stt_text": "...",
        "stt_duration_sec": 120,
        "classification": {"code": "100", "category": "정상판매"},
        "improper_solicitation": {
          "detected": true,
          "items": ["무료 수익 보장", "원금보장"],
          "agent_analysis": "..."
        }
      }
    ]
  }
```

---

## 🛠️ 기술 스택

| 계층 | 기술 |
|------|------|
| **Backend** | FastAPI + Uvicorn |
| **Database** | SQLite + SQLAlchemy |
| **Frontend** | HTML5 + CSS3 + JavaScript (Vanilla) |
| **STT Engine** | 기존 STT API (http://localhost:8003) |
| **Real-time** | WebSocket 또는 Polling |
| **인증** | JWT 토큰 |
| **배포** | Docker |

---

## 📅 구현 단계

### Phase 1: 기초 구축 (1주)
- [ ] FastAPI 프로젝트 구조 생성
- [ ] SQLite DB 초기화 및 테이블 생성
- [ ] 인증 시스템 구현 (로그인 API)
- [ ] 기본 HTML 레이아웃 (index.html)

### Phase 2: 파일 관리 (1주)
- [ ] 파일 업로드 API 구현
- [ ] 폴더 구조 자동 생성
- [ ] 파일 목록 조회 API
- [ ] upload.html UI 구현
- [ ] 파일 검색 기능

### Phase 3: 분석 시스템 (1.5주)
- [ ] Analysis Job 관리 API
- [ ] 비동기 Worker 구현
- [ ] STT Engine 클라이언트
- [ ] AI Agent 클라이언트
- [ ] 결과 저장 및 조회

### Phase 4: 프론트엔드 (1주)
- [ ] analysis.html UI 구현
- [ ] 실시간 진행 상태 표시
- [ ] 결과 표시 페이지
- [ ] 반응형 디자인

### Phase 5: 통합 및 테스트 (0.5주)
- [ ] E2E 테스트
- [ ] 성능 최적화
- [ ] 에러 처리 및 로깅
- [ ] Docker 이미지 빌드

---

## 🔗 외부 인터페이스

### 13. STT 엔진 연동

```python
# STT 엔진 API 호출
async def transcribe_file(file_path: str) -> dict:
    """
    기존 STT 엔진에 요청
    
    Args:
        file_path: /uploads/{emp_id}/{folder}/{filename}
    
    Returns:
        {
            "success": true,
            "text": "변환된 텍스트",
            "duration": 120.5,
            "backend": "faster-whisper"
        }
    """
    async with aiohttp.ClientSession() as session:
        with open(file_path, 'rb') as f:
            form = aiohttp.FormData()
            form.add_field('file', f)
            
            async with session.post(
                f"{STT_ENGINE_URL}/transcribe",
                data=form
            ) as resp:
                return await resp.json()
```

### 14. AI Agent 호출

```python
# AI Agent 호출 (부당권유/불완전판매 탐지)
async def call_detection_agent(
    agent_url: str,
    text: str,
    agent_type: str  # "improper_solicitation" or "incomplete_sales"
) -> dict:
    """
    분석 대상 탐지 AI 호출
    
    Args:
        agent_url: AI Agent 엔드포인트 (사전 정의)
        text: STT 변환 텍스트
        agent_type: 탐지 유형
    
    Returns:
        {
            "detected": true,
            "items": ["항목1", "항목2", ...],
            "analysis": "분석 내용",
            "confidence": 0.95
        }
    """
    payload = {
        "use_streaming": False,
        "chat_thread_id": None,
        "parameters": {
            "user_query": text,
            "analysis_type": agent_type
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(agent_url, json=payload) as resp:
            return await resp.json()
```

---

## 🔒 보안 고려사항

1. **인증:** JWT 토큰 기반 인증
2. **파일 격리:** 사번별 폴더 격리로 데이터 접근 제어
3. **CORS:** 같은 도메인에서만 요청 허용
4. **입력 검증:** 파일명, 폴더명 검증 (경로 traversal 공격 방지)
5. **로깅:** 모든 분석 작업 및 접근 기록
6. **임시 파일:** 분석 완료 후 자동 삭제 (선택사항)

---

## 📊 모니터링 및 로깅

```python
# 로그 포맷
[2026-02-20 10:30:45] [INFO] [emp_id: 10001] POST /api/upload - 3 files uploaded
[2026-02-20 10:31:00] [INFO] [job_id: job_abc123] Analysis started
[2026-02-20 10:31:15] [INFO] [job_id: job_abc123] [file: recording_001.wav] STT completed (120s)
[2026-02-20 10:31:45] [INFO] [job_id: job_abc123] [file: recording_001.wav] Improper detection completed
[2026-02-20 10:32:00] [INFO] [job_id: job_abc123] Analysis completed (5 files)
```

---

## 🚀 배포

### Docker Compose
```yaml
version: '3.8'
services:
  stt-web:
    build: ./scratch/stt-web/backend
    ports:
      - "8200:8000"
    environment:
      STT_ENGINE_URL: "http://stt-engine:8003"
      DATABASE_URL: "sqlite:///data/stt_web.db"
    volumes:
      - ./scratch/stt-web/backend/data:/app/data
    depends_on:
      - stt-engine
```

---

## 📝 추가 고려사항

1. **동시성 제한:** 사용자당 동시 분석 작업 수 제한
2. **저장소 관리:** 오래된 파일 자동 정리 (30일 이상)
3. **성능:** 큰 파일 처리 시 스트리밍 방식
4. **백업:** DB 및 파일 정기 백업
5. **확장성:** 다중 Worker 지원으로 처리량 증가

---

## 📚 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [SQLAlchemy 문서](https://www.sqlalchemy.org/)
- [SQLite 문서](https://www.sqlite.org/docs.html)
- [기존 STT 엔진 API 명세](./API_SERVER_RESTRUCTURING_GUIDE.md)
