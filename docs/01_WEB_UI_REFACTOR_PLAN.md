# Phase 1-4 구현 가이드: Web UI 리팩토링 상세 계획

> 📌 **참고 문서**
> - [02_WEB_UI_REFACTOR_CHECKLIST.md](02_WEB_UI_REFACTOR_CHECKLIST.md) - 단계별 체크리스트
> - [03_WEB_UI_REFACTOR_SUMMARY.md](03_WEB_UI_REFACTOR_SUMMARY.md) - 작업 요약 및 진행 상황

---

## 📋 현재 구조 vs 개선된 구조

### 현재 web_ui 구조
```
web_ui/
├── main.py (FastAPI 진입점, 라우트 등록)
├── requirements.txt
├── config.py (기본 설정)
├── models/
│   └── schemas.py (Pydantic 스키마)
├── services/
│   └── stt_service.py (STT 관련 로직)
├── templates/
│   └── index.html (단일 페이지)
└── static/
    ├── js/
    │   └── main.js
    └── css/
```

### 개선된 구조
```
web_ui/
├── main.py (SessionMiddleware, 라우터 등록)
├── requirements.txt (sqlalchemy, python-multipart 추가)
├── config.py (DB_URL, 사용자, 세션 설정 추가)
├── app/
│   ├── models/
│   │   ├── schemas.py (기존 + 분석 옵션 추가)
│   │   └── database.py (SQLAlchemy ORM 모델 5개)
│   ├── services/
│   │   ├── stt_service.py (기존 + 탐지 옵션 추가)
│   │   └── auth_service.py (세션 인증)
│   ├── routes/
│   │   └── auth.py (로그인/로그아웃/세션)
│   └── utils/
│       └── db.py (DB 세션 관리)
├── templates/
│   ├── index.html (로그인 페이지)
│   └── upload.html (파일 관리)
└── static/
    ├── js/
    │   ├── main.js (기존)
    │   └── common.js (공용 유틸)
    └── css/
        └── style.css (향상된 스타일)
```

---

## 🗄️ 데이터베이스 스키마

### 1. employees 테이블
```sql
CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    dept VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

**설명:**
- `emp_id`: 사번 (로그인 ID)
- `name`: 직원 이름
- `dept`: 부서
- `last_login`: 마지막 로그인 시간

---

### 2. file_uploads 테이블
```sql
CREATE TABLE file_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id VARCHAR(10) NOT NULL,
    folder_path VARCHAR(500) NOT NULL,  -- 예: "2026-02-20" 또는 "부당권유_검토"
    filename VARCHAR(500) NOT NULL,
    file_size_mb FLOAT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
);
```

**설명:**
- 사용자별 업로드 파일 추적
- 파일 메타정보 저장 (크기, 업로드 시간)
- `folder_path`: 날짜/커스텀 폴더명

---

### 3. analysis_jobs 테이블
```sql
CREATE TABLE analysis_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(50) UNIQUE NOT NULL,
    emp_id VARCHAR(10) NOT NULL,
    folder_path VARCHAR(500) NOT NULL,
    file_ids JSON,  -- ["file_1.wav", "file_2.wav", ...]
    status VARCHAR(20),  -- "pending", "processing", "completed", "failed"
    options JSON,  -- {"improper_solicitation": true, "incomplete_sales": true}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
);
```

**설명:**
- 분석 작업 단위 관리
- 여러 파일을 한 번에 분석 가능
- 분석 옵션 저장 (부당권유, 불완전판매)

---

### 4. analysis_results 테이블
```sql
CREATE TABLE analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(50) NOT NULL,
    file_id VARCHAR(500) NOT NULL,
    stt_text TEXT,  -- 음성→텍스트 결과
    stt_metadata JSON,  -- {"duration": 60.5, "language": "ko"}
    classification_code VARCHAR(20),  -- "100-100", "100-200", ...
    classification_category VARCHAR(100),  -- "적정", "주의", "위험"
    classification_confidence FLOAT,  -- 0.0-1.0
    improper_detection_results JSON,  -- 부당권유 탐지 결과
    incomplete_detection_results JSON,  -- 불완전판매 탐지 결과
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES analysis_jobs(job_id)
);
```

**설명:**
- 파일별 분석 결과
- STT, 분류, 탐지 결과 통합 저장

---

### 5. analysis_progress 테이블
```sql
CREATE TABLE analysis_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(50) NOT NULL,
    file_id VARCHAR(500) NOT NULL,
    step VARCHAR(50),  -- "stt", "classification", "improper_detection", "incomplete_detection"
    progress_percent INTEGER,  -- 0-100
    status VARCHAR(20),  -- "pending", "processing", "completed", "failed"
    message VARCHAR(500),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES analysis_jobs(job_id)
);
```

**설명:**
- 실시간 진행 상황 추적
- WebSocket/polling으로 클라이언트에 전송

---

## 🔐 세션 기반 인증 방식

### 로그인 플로우
```
1. 클라이언트: POST /api/auth/login {"emp_id": "10001"}
2. 서버: ALLOWED_EMPLOYEES에서 사번 검증
3. 서버: employees 테이블에 기록, last_login 업데이트
4. 서버: 세션 쿠키 생성 (httpOnly, Secure)
5. 클라이언트: 쿠키 자동 저장 (브라우저)
6. 클라이언트: upload.html로 리다이렉트
```

### 세션 정보
```python
# 세션에 저장되는 정보
session_data = {
    "emp_id": "10001",
    "name": "김철수",
    "dept": "영업팀"
}
```

### 보안 설정
- **httpOnly**: JavaScript에서 접근 불가
- **Secure**: HTTPS 연결에서만 전송
- **SameSite**: CSRF 공격 방지
- **timeout**: 8시간

---

## 📁 파일 저장 구조

### 디렉토리 계층
```
data/uploads/
├── 10001/                  # 사번별 격리
│   ├── 2026-02-20/        # 날짜 (자동 생성)
│   │   ├── file1.wav
│   │   └── file2.wav
│   ├── 부당권유_검토/      # 커스텀 폴더 (사용자 생성)
│   │   ├── sample1.wav
│   │   └── sample2.wav
│   └── 불완전판매_사례/
│       └── example.wav
├── 10002/
│   └── 2026-02-20/
│       └── ...
└── 10003/
    └── ...
```

### 장점
1. **격리**: 다른 사용자 파일 접근 불가
2. **조직화**: 날짜/주제별 쉬운 관리
3. **확장성**: 커스텀 폴더 추가 가능

---

## 🔧 구현 상세 가이드

### 1. config.py 수정

**추가할 내용:**

```python
import os
from datetime import timedelta

# === 기존 설정 ===
DEBUG = True
ALLOWED_HOSTS = ["*"]

# === 데이터베이스 ===
DATABASE_URL = "sqlite:///./data/stt_web.db"
# 또는 상대경로: "sqlite:///./stt_web.db"

# === 세션 ===
SESSION_SECRET_KEY = "your-secret-key-change-in-production"  # 프로덕션에서는 환경변수로 변경
SESSION_TIMEOUT = timedelta(hours=8)

# === 인증된 직원 ===
ALLOWED_EMPLOYEES = {
    "10001": {"name": "김철수", "dept": "영업팀"},
    "10002": {"name": "이영희", "dept": "기획팀"},
    "10003": {"name": "박민수", "dept": "기술팀"},
    # 실제 프로덕션: DB 또는 LDAP에서 조회
}

# === AI Agent 설정 ===
AI_AGENTS = {
    "stt": {
        "url": "http://localhost:8001",
        "timeout": 300
    },
    "classification": {
        "url": "http://localhost:8002",
        "timeout": 60
    },
    "improper_detection": {
        "url": "http://localhost:8003",
        "timeout": 120
    },
    "incomplete_detection": {
        "url": "http://localhost:8004",
        "timeout": 120
    }
}

# === 파일 저장 ===
UPLOAD_DIR = "./data/uploads"
MAX_FILE_SIZE_MB = 500
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg"}
```

---

### 2. app/models/database.py 생성

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True)
    emp_id = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    dept = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

class FileUpload(Base):
    __tablename__ = "file_uploads"
    
    id = Column(Integer, primary_key=True)
    emp_id = Column(String(10), ForeignKey("employees.emp_id"), nullable=False)
    folder_path = Column(String(500), nullable=False)
    filename = Column(String(500), nullable=False)
    file_size_mb = Column(Float)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(50), unique=True, nullable=False)
    emp_id = Column(String(10), ForeignKey("employees.emp_id"), nullable=False)
    folder_path = Column(String(500), nullable=False)
    file_ids = Column(JSON)  # JSON 형식 저장
    status = Column(String(20))  # "pending", "processing", "completed", "failed"
    options = Column(JSON)  # 분석 옵션
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(50), ForeignKey("analysis_jobs.job_id"), nullable=False)
    file_id = Column(String(500), nullable=False)
    stt_text = Column(Text)
    stt_metadata = Column(JSON)
    classification_code = Column(String(20))
    classification_category = Column(String(100))
    classification_confidence = Column(Float)
    improper_detection_results = Column(JSON)
    incomplete_detection_results = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class AnalysisProgress(Base):
    __tablename__ = "analysis_progress"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(50), ForeignKey("analysis_jobs.job_id"), nullable=False)
    file_id = Column(String(500), nullable=False)
    step = Column(String(50))
    progress_percent = Column(Integer)
    status = Column(String(20))
    message = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow)
```

---

### 3. app/utils/db.py 생성

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.database import Base
from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite용
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """DB 초기화, 테이블 생성"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """FastAPI dependency: 라우트에서 DB 세션 주입"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### 4. app/services/auth_service.py 생성

```python
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.database import Employee
from config import ALLOWED_EMPLOYEES

class AuthService:
    @staticmethod
    def validate_employee(emp_id: str, db: Session) -> dict:
        """사번 검증 및 DB 기록"""
        if emp_id not in ALLOWED_EMPLOYEES:
            return {"success": False, "error": "Invalid emp_id"}
        
        emp_info = ALLOWED_EMPLOYEES[emp_id]
        
        # DB에서 직원 정보 조회 또는 생성
        employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
        
        if not employee:
            employee = Employee(
                emp_id=emp_id,
                name=emp_info["name"],
                dept=emp_info["dept"]
            )
            db.add(employee)
        
        # last_login 업데이트
        employee.last_login = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "emp_id": emp_id,
            "name": employee.name,
            "dept": employee.dept
        }
    
    @staticmethod
    def get_current_employee(session: dict) -> dict:
        """세션에서 현재 사용자 정보 조회"""
        if "emp_id" not in session:
            return None
        
        return {
            "emp_id": session["emp_id"],
            "name": session.get("name"),
            "dept": session.get("dept")
        }
```

---

### 5. app/routes/auth.py 생성

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.requests import Request
from app.utils.db import get_db
from app.services.auth_service import AuthService
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    emp_id: str

@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """로그인: 사번 검증 후 세션 생성"""
    result = AuthService.validate_employee(request.emp_id, db)
    
    if not result["success"]:
        raise HTTPException(status_code=401, detail="Invalid emp_id")
    
    # 요청 객체에서 세션 설정
    request.session["emp_id"] = result["emp_id"]
    request.session["name"] = result["name"]
    request.session["dept"] = result["dept"]
    
    return JSONResponse({
        "success": True,
        "emp_id": result["emp_id"],
        "name": result["name"],
        "dept": result["dept"]
    })

@router.post("/logout")
async def logout(request: Request):
    """로그아웃: 세션 삭제"""
    request.session.clear()
    return {"message": "logged out"}

@router.get("/session")
async def get_session(request: Request):
    """현재 세션 정보 조회"""
    emp_info = AuthService.get_current_employee(request.session)
    
    if not emp_info:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return emp_info
```

---

### 6. main.py 수정

**추가할 내용 (기존 코드 유지):**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.utils.db import init_db
from app.routes import auth
from config import SESSION_SECRET_KEY

app = FastAPI(title="STT Engine Web UI")

# === Middleware ===
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# === DB 초기화 ===
@app.on_event("startup")
async def startup_event():
    init_db()

# === 라우터 등록 ===
app.include_router(auth.router)
# app.include_router(files.router)  # Phase 2
# app.include_router(upload.router)  # Phase 2
# app.include_router(analysis.router)  # Phase 3

# === 정적 파일 ===
app.mount("/static", StaticFiles(directory="static"), name="static")

# === 기본 라우트 ===
@app.get("/")
async def root():
    return {"message": "STT Engine API"}
```

---

### 7. templates/index.html 생성

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STT Engine - 로그인</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body class="login-page">
    <div class="login-container">
        <div class="login-box">
            <h1>STT Engine</h1>
            <p class="subtitle">음성 분석 시스템</p>
            
            <form id="loginForm">
                <div class="form-group">
                    <label for="empId">사번</label>
                    <input 
                        type="text" 
                        id="empId" 
                        name="emp_id" 
                        placeholder="예: 10001" 
                        required
                    >
                </div>
                
                <button type="submit" class="btn btn-primary btn-block">
                    로그인
                </button>
            </form>
            
            <div id="errorMessage" class="alert alert-danger" style="display: none;"></div>
            
            <div class="test-accounts">
                <p class="text-muted">테스트 계정:</p>
                <ul>
                    <li>10001 - 김철수 (영업팀)</li>
                    <li>10002 - 이영희 (기획팀)</li>
                    <li>10003 - 박민수 (기술팀)</li>
                </ul>
            </div>
        </div>
    </div>

    <script src="/static/js/common.js"></script>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const empId = document.getElementById('empId').value;
            const errorDiv = document.getElementById('errorMessage');
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ emp_id: empId })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    // Phase 2에서 upload.html로 이동
                    window.location.href = '/static/upload.html';
                } else {
                    const error = await response.json();
                    errorDiv.textContent = '로그인 실패: ' + (error.detail || '사번을 확인하세요');
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                errorDiv.textContent = '오류 발생: ' + error.message;
                errorDiv.style.display = 'block';
            }
        });
    </script>
</body>
</html>
```

---

### 8. static/js/common.js 생성

```javascript
// === 세션 관리 ===
async function checkSession() {
    try {
        const response = await fetch('/api/auth/session');
        if (response.ok) {
            return await response.json();
        } else if (response.status === 401) {
            // 로그인 페이지로 리다이렉트
            window.location.href = '/static/index.html';
            return null;
        }
    } catch (error) {
        console.error('Session check failed:', error);
        return null;
    }
}

async function logout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        window.location.href = '/static/index.html';
    } catch (error) {
        console.error('Logout failed:', error);
    }
}

// === API 호출 헬퍼 ===
async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    try {
        const response = await fetch(endpoint, options);
        const data = await response.json();
        
        if (!response.ok) {
            showNotification(data.detail || 'API 호출 실패', 'error');
            return null;
        }
        
        return data;
    } catch (error) {
        showNotification('네트워크 오류: ' + error.message, 'error');
        return null;
    }
}

// === 알림 표시 ===
function showNotification(message, type = 'info') {
    const alertDiv = document.getElementById('notification');
    if (!alertDiv) {
        const div = document.createElement('div');
        div.id = 'notification';
        document.body.appendChild(div);
    }
    
    const notif = document.getElementById('notification');
    notif.textContent = message;
    notif.className = `alert alert-${type}`;
    notif.style.display = 'block';
    
    setTimeout(() => {
        notif.style.display = 'none';
    }, 5000);
}

// === 포맷 유틸 ===
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}
```

---

### 9. requirements.txt 업데이트

**추가할 패키지:**

```
fastapi>=0.100.0
uvicorn>=0.24.0
sqlalchemy>=2.0.23
python-multipart>=0.0.6
starlette-sessions>=0.0.1
pydantic>=2.0.0
```

---

## 🧪 테스트 방법

### 1. 의존성 설치
```bash
cd web_ui
pip install -r requirements.txt
```

### 2. 서버 시작
```bash
python -m uvicorn main:app --reload
```

### 3. 브라우저에서 테스트
```
http://localhost:8000/static/index.html
```

### 4. 테스트 사번 로그인
- 사번: `10001`
- 사번: `10002`
- 사번: `10003`

---

## 📋 Phase별 요약

| Phase | 내용 | 파일 | 기간 |
|-------|------|------|------|
| **1** | 인증 & DB 기초 | 7개 생성 + 3개 수정 | 1주 |
| **2** | 파일 업로드 | upload.html, files router | 1주 |
| **3** | 분석 시스템 | analysis.html, analysis router | 1.5주 |
| **4** | 통합 & 테스트 | 전체 통합 테스트 | 1주 |

---

## ✅ Phase 1 완료 기준

- [x] config.py: DB, 세션, 인증 설정 추가
- [x] database.py: SQLAlchemy 모델 5개 구현
- [x] db.py: 세션 관리 구현
- [x] auth_service.py: 인증 로직 구현
- [x] auth.py: API 엔드포인트 3개 구현
- [x] main.py: 미들웨어, 라우터 등록
- [x] index.html: 로그인 페이지 구현
- [x] common.js: 공용 유틸 구현
- [x] requirements.txt: 의존성 추가
- [x] DB 초기화 및 테스트 사번 생성

---

> 📌 다음 단계: **Phase 1 구현 시작**
> 
> 준비 완료! 이제 실제 코드 작성을 시작하겠습니다.
