# Phase 1-2 구현 체크리스트: Web UI 리팩토링

> 📌 **참고 문서**
> - [01_WEB_UI_REFACTOR_PLAN.md](01_WEB_UI_REFACTOR_PLAN.md) - 상세 계획 및 코드 예시
> - [03_WEB_UI_REFACTOR_SUMMARY.md](03_WEB_UI_REFACTOR_SUMMARY.md) - 작업 요약

---

## 📋 Phase 1: 기초 인프라 구축 (인증 & DB)

### 1.1 requirements.txt 업데이트
- [ ] sqlalchemy==2.0.23 추가
- [ ] python-multipart==0.0.6 추가
- [ ] starlette-sessions 확인
- [ ] 기존 의존성 유지
- **파일 위치**: `web_ui/requirements.txt`
- **소요 시간**: 5분

### 1.2 config.py 수정
- [ ] DATABASE_URL 추가 (`sqlite:///./data/stt_web.db`)
- [ ] ALLOWED_EMPLOYEES 사전 추가 (3-5개 테스트 계정)
- [ ] SESSION_SECRET_KEY 추가
- [ ] SESSION_TIMEOUT 추가 (8시간)
- [ ] AI_AGENTS 설정 추가 (URL, timeout)
- [ ] UPLOAD_DIR, MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS 추가
- **파일 위치**: `web_ui/config.py`
- **소요 시간**: 30분
- **코드 참조**: [01_WEB_UI_REFACTOR_PLAN.md#1-configpy-수정](01_WEB_UI_REFACTOR_PLAN.md#1-configpy-수정)

### 1.3 app/models/database.py 생성
- [ ] SQLAlchemy Base 초기화
- [ ] Employee 모델 구현 (emp_id, name, dept, created_at, last_login)
- [ ] FileUpload 모델 구현
- [ ] AnalysisJob 모델 구현
- [ ] AnalysisResult 모델 구현
- [ ] AnalysisProgress 모델 구현
- [ ] 모든 모델에 적절한 관계설정 (ForeignKey)
- **파일 위치**: `web_ui/app/models/database.py` (신규 생성)
- **소요 시간**: 1시간
- **코드 참조**: [01_WEB_UI_REFACTOR_PLAN.md#2-appmodelsdatabasepy-생성](01_WEB_UI_REFACTOR_PLAN.md#2-appmodelsdatabasepy-생성)

### 1.4 app/utils/db.py 생성
- [ ] create_engine 설정 (SQLite용 check_same_thread 옵션)
- [ ] SessionLocal = sessionmaker(...) 설정
- [ ] init_db() 함수 구현 (테이블 생성)
- [ ] get_db() 의존성 함수 구현
- **파일 위치**: `web_ui/app/utils/db.py` (신규 생성)
- **소요 시간**: 30분
- **코드 참조**: [01_WEB_UI_REFACTOR_PLAN.md#3-apputilsdbpy-생성](01_WEB_UI_REFACTOR_PLAN.md#3-apputilsdbpy-생성)

### 1.5 app/services/auth_service.py 생성
- [ ] AuthService 클래스 생성
- [ ] validate_employee() 메서드 (emp_id 검증, DB 기록)
- [ ] get_current_employee() 메서드 (세션에서 정보 조회)
- [ ] 기타 필요한 헬퍼 함수
- **파일 위치**: `web_ui/app/services/auth_service.py` (신규 생성)
- **소요 시간**: 1시간
- **코드 참조**: [01_WEB_UI_REFACTOR_PLAN.md#4-appservicesauth_servicepy-생성](01_WEB_UI_REFACTOR_PLAN.md#4-appservicesauth_servicepy-생성)

### 1.6 app/routes/auth.py 생성
- [ ] APIRouter 생성 (`/api/auth` prefix)
- [ ] LoginRequest Pydantic 모델 정의
- [ ] POST /api/auth/login 엔드포인트
  - [ ] emp_id 검증
  - [ ] 세션 쿠키 설정
  - [ ] 응답: {success, emp_id, name, dept}
- [ ] POST /api/auth/logout 엔드포인트
  - [ ] 세션 삭제
  - [ ] 응답: {message}
- [ ] GET /api/auth/session 엔드포인트
  - [ ] 현재 세션 정보 조회
  - [ ] 응답: {emp_id, name, dept}
- **파일 위치**: `web_ui/app/routes/auth.py` (신규 생성)
- **소요 시간**: 1시간
- **코드 참조**: [01_WEB_UI_REFACTOR_PLAN.md#5-approutesauthpy-생성](01_WEB_UI_REFACTOR_PLAN.md#5-approutesauthpy-생성)

### 1.7 main.py 수정
- [ ] SessionMiddleware 임포트
- [ ] init_db 임포트
- [ ] auth 라우터 임포트
- [ ] SessionMiddleware 등록 (SECRET_KEY 사용)
- [ ] @app.on_event("startup") 에서 init_db() 호출
- [ ] app.include_router(auth.router) 등록
- [ ] 기존 라우트 유지
- **파일 위치**: `web_ui/main.py`
- **소요 시간**: 30분
- **코드 참조**: [01_WEB_UI_REFACTOR_PLAN.md#6-mainpy-수정](01_WEB_UI_REFACTOR_PLAN.md#6-mainpy-수정)

### 1.8 templates/index.html 생성
- [ ] HTML 구조 (로그인 컨테이너)
- [ ] 로그인 폼 (emp_id 입력 필드)
- [ ] 제출 버튼
- [ ] 에러 메시지 표시 영역
- [ ] 테스트 계정 안내
- [ ] JavaScript: 폼 제출 처리
  - [ ] fetch로 /api/auth/login 호출
  - [ ] 성공: upload.html로 리다이렉트 (Phase 2)
  - [ ] 실패: 에러 메시지 표시
- **파일 위치**: `web_ui/templates/index.html`
- **소요 시간**: 1시간
- **코드 참조**: [01_WEB_UI_REFACTOR_PLAN.md#7-templatesindexhtml-생성](01_WEB_UI_REFACTOR_PLAN.md#7-templatesindexhtml-생성)

### 1.9 static/js/common.js 생성
- [ ] checkSession() - 현재 세션 검증
  - [ ] /api/auth/session 호출
  - [ ] 미인증: index.html로 리다이렉트
- [ ] logout() - 로그아웃 함수
- [ ] apiCall() - API 호출 헬퍼
  - [ ] fetch 래퍼
  - [ ] 에러 처리
- [ ] showNotification() - 알림 표시
- [ ] formatFileSize() - 파일 크기 포맷
- [ ] formatDate() - 날짜 포맷
- **파일 위치**: `web_ui/static/js/common.js`
- **소요 시간**: 1시간
- **코드 참조**: [01_WEB_UI_REFACTOR_PLAN.md#8-staticjscommonjs-생성](01_WEB_UI_REFACTOR_PLAN.md#8-staticjscommonjs-생성)

### 1.10 static/css/style.css 생성/개선
- [ ] 로그인 페이지 스타일
  - [ ] .login-page, .login-container, .login-box
  - [ ] 폼 입력 필드
  - [ ] 버튼 스타일
  - [ ] 에러 알림
- [ ] 반응형 디자인 (mobile, tablet, desktop)
- [ ] 색상 스키마 정의
- [ ] 폰트 설정
- [ ] 유틸리티 클래스 (.btn, .alert, .text-muted 등)
- **파일 위치**: `web_ui/static/css/style.css`
- **소요 시간**: 45분

### 1.11 DB 초기화 및 테스트
- [ ] data/ 디렉토리 생성
- [ ] `pip install -r requirements.txt` 실행
- [ ] `python main.py` 실행
- [ ] DB 파일 생성 확인 (`data/stt_web.db`)
- [ ] 테이블 생성 확인 (sqlite3 CLI)
- [ ] 테스트 사번 데이터 생성 (선택사항, init_db 또는 수동)
- **소요 시간**: 30분

### 1.12 로그인 기능 테스트
- [ ] 브라우저: http://localhost:8000/static/index.html
- [ ] 테스트 계정으로 로그인 (10001, 10002, 10003)
- [ ] 성공 시 upload.html로 리다이렉트 (아직 없음, 오류 확인)
- [ ] 잘못된 사번 입력 시 에러 메시지 확인
- [ ] 개발자 도구에서 쿠키 확인 (session 쿠키)
- [ ] `/api/auth/session` 엔드포인트 테스트
- [ ] 로그아웃 테스트 (API 호출)
- **소요 시간**: 30분

---

## 📊 Phase 1 요약

| 항목 | 상태 | 우선순위 | 소요시간 |
|------|------|---------|---------|
| requirements.txt | ⬜ | 🔴 필수 | 5분 |
| config.py | ⬜ | 🔴 필수 | 30분 |
| database.py | ⬜ | 🔴 필수 | 1시간 |
| db.py | ⬜ | 🔴 필수 | 30분 |
| auth_service.py | ⬜ | 🔴 필수 | 1시간 |
| auth.py | ⬜ | 🔴 필수 | 1시간 |
| main.py | ⬜ | 🔴 필수 | 30분 |
| index.html | ⬜ | 🔴 필수 | 1시간 |
| common.js | ⬜ | 🟡 권장 | 1시간 |
| style.css | ⬜ | 🟡 권장 | 45분 |
| DB 테스트 | ⬜ | 🔴 필수 | 30분 |
| 로그인 테스트 | ⬜ | 🔴 필수 | 30분 |
| **합계** | | | **8.5시간** |

---

## 🚀 구현 순서 (권장)

1. **requirements.txt** - 의존성 설치 필요
2. **config.py** - 다른 파일에서 참조
3. **database.py** - ORM 모델 정의
4. **db.py** - 데이터베이스 초기화
5. **auth_service.py** - 비즈니스 로직
6. **auth.py** - API 엔드포인트
7. **main.py** - 라우터 등록
8. **index.html** - 프론트엔드
9. **common.js** - 유틸리티
10. **style.css** - 스타일
11. **테스트** - 모든 기능 검증

---

## ✅ Phase 1 완료 체크리스트

```
Infrastructure
- [x] requirements.txt 업데이트
- [x] config.py 수정
- [x] app/ 디렉토리 구조 생성

Database
- [x] database.py 작성 (5개 모델)
- [x] db.py 작성 (세션 관리)
- [x] init_db() 테스트
- [x] 테이블 생성 확인

Authentication
- [x] auth_service.py 작성
- [x] auth.py 작성 (3개 엔드포인트)
- [x] main.py 미들웨어 등록
- [x] 세션 쿠키 생성 확인

Frontend
- [x] index.html 작성 (로그인 폼)
- [x] common.js 작성 (유틸리티)
- [x] style.css 작성 (스타일)
- [x] 로그인 기능 테스트

Testing
- [x] POST /api/auth/login 테스트
- [x] GET /api/auth/session 테스트
- [x] POST /api/auth/logout 테스트
- [x] DB에 직원 정보 저장 확인
- [x] 에러 처리 테스트
```

---

## 📝 Next Phase (Phase 2)

Phase 1 완료 후 다음 단계:
- **파일 업로드** 기능 구현
- **폴더 관리** UI 추가
- **파일 메타정보** DB 저장
- `/api/files/list`, `/api/files/upload`, `/api/files/delete` 엔드포인트

참고: [01_WEB_UI_REFACTOR_PLAN.md - Phase 2-4](01_WEB_UI_REFACTOR_PLAN.md#phase별-요약)
