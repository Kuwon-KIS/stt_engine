# Phase 0: 작업 요약 및 진행 상황

> 📌 **관련 문서**
> - [01_WEB_UI_REFACTOR_PLAN.md](01_WEB_UI_REFACTOR_PLAN.md) - 상세 기술 명세서
> - [02_WEB_UI_REFACTOR_CHECKLIST.md](02_WEB_UI_REFACTOR_CHECKLIST.md) - Phase별 체크리스트

---

## 🎯 프로젝트 개요

### 목표
기존 web_ui 리팩토링 후 다음 기능 추가:
- ✅ **사용자 인증** (사번 기반 로그인, 세션 방식)
- 🔲 **파일 관리** (사번별 격리, 날짜/폴더 구조)
- 🔲 **분석 시스템** (부당권유, 불완전판매 탐지)
- 🔲 **결과 저장** (메타데이터, 진행 상황, 결과)

### 범위
- **web_ui만** 수정 (scratch/stt-web은 참고용)
- **세션 기반 인증** (JWT는 불필요)
- **SQLite** 데이터베이스
- **FastAPI** 기반 REST API

---

## 📚 문서 계층 구조

```
03_WEB_UI_REFACTOR_SUMMARY.md (이 파일)
├── 작업 개요, 진행 상황, 예상 기간
├── 참고
└── 다음 단계

01_WEB_UI_REFACTOR_PLAN.md
├── 상세 기술 명세
├── 데이터베이스 스키마
├── 세션 인증 방식
├── 코드 예시 (복사 가능)
└── Phase 1-4 상세 설명

02_WEB_UI_REFACTOR_CHECKLIST.md
├── Phase별 체크리스트
├── 각 파일별 작업 항목
├── 소요 시간
├── 완료 기준
└── 다음 Phase 링크
```

**사용 방법:**
1. 이 파일 (요약) 읽기 - 전체 그림 파악
2. [01_WEB_UI_REFACTOR_PLAN.md](01_WEB_UI_REFACTOR_PLAN.md) - 세부 명세 참고
3. [02_WEB_UI_REFACTOR_CHECKLIST.md](02_WEB_UI_REFACTOR_CHECKLIST.md) - 체크리스트로 진행 추적

---

## 📊 작업 진행 상황

### Phase 별 완료도

| Phase | 내용 | 상태 | 예상 기간 |
|-------|------|------|---------|
| **0** | 계획 및 문서 작성 | ✅ **완료** | 2일 |
| **1** | 기초 인프라 (인증, DB) | 🔲 **시작 예정** | 1주 |
| **2** | 파일 업로드 관리 | 🔲 **준비 중** | 1주 |
| **3** | 분석 시스템 통합 | 🔲 **예정** | 1.5주 |
| **4** | 통합 및 테스트 | 🔲 **예정** | 1주 |
| **합계** | | | **4.5주** |

### Phase 0 완료 항목
- ✅ [01_WEB_UI_REFACTOR_PLAN.md](01_WEB_UI_REFACTOR_PLAN.md) 작성 (~400 lines)
  - 현재 vs 개선 구조 비교
  - DB 스키마 정의 (5개 테이블)
  - 세션 인증 플로우
  - 코드 예시 및 상세 가이드

- ✅ [02_WEB_UI_REFACTOR_CHECKLIST.md](02_WEB_UI_REFACTOR_CHECKLIST.md) 작성
  - 50+ 개별 작업 항목
  - 우선순위 표시
  - 소요 시간 예측

- ✅ [03_WEB_UI_REFACTOR_SUMMARY.md](03_WEB_UI_REFACTOR_SUMMARY.md) 작성
  - 이 파일 (진행 상황 요약)

- ✅ 기술 결정사항 확정
  - 인증: 세션 쿠키 (JWT 제외)
  - DB: SQLite + SQLAlchemy
  - 파일 구조: emp_id/date 계층
  - 비동기: 백그라운드 태스크

---

## 🔧 기술 스택

### Backend
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0.23
- **Database**: SQLite
- **Auth**: Starlette SessionMiddleware (httpOnly cookies)
- **Upload**: python-multipart

### Frontend
- **HTML5**: 시맨틱 구조
- **CSS3**: 반응형 디자인
- **JavaScript**: Vanilla JS (프레임워크 없음)
- **Storage**: 로컬 스토리지 (선택사항)

### DevOps
- **Runtime**: Python 3.9+
- **Package Manager**: pip
- **Version Control**: Git

---

## 📁 파일 저장 구조

```
data/uploads/                          # 모든 파일의 루트
├── 10001/                             # 사번별 격리 (사용자 A)
│   ├── 2026-02-20/                   # 날짜 폴더 (자동 생성)
│   │   ├── file1.wav
│   │   ├── file2.wav
│   │   └── ...
│   ├── 부당권유_검토/                 # 커스텀 폴더 (사용자 생성)
│   │   ├── sample1.wav
│   │   └── ...
│   └── 불완전판매_사례/
│       └── ...
├── 10002/                             # 사번별 격리 (사용자 B)
│   └── ...
└── 10003/                             # 사번별 격리 (사용자 C)
    └── ...
```

**장점:**
1. **격리**: 다른 사용자 파일 완전 격리
2. **조직화**: 날짜/주제별 자동/수동 분류
3. **확장성**: 새로운 폴더/파일 추가 용이

---

## 💾 데이터베이스 스키마

### 5개 테이블
1. **employees** - 직원 정보
2. **file_uploads** - 업로드된 파일 메타정보
3. **analysis_jobs** - 분석 작업 정보
4. **analysis_results** - 분석 결과 저장
5. **analysis_progress** - 실시간 진행 상황

**관계도:**
```
employees (1) ──┬─→ (N) file_uploads
                ├─→ (N) analysis_jobs
                │
analysis_jobs (1) ──→ (N) analysis_results
                  ──→ (N) analysis_progress
```

세부 사항: [01_WEB_UI_REFACTOR_PLAN.md - DB 스키마](01_WEB_UI_REFACTOR_PLAN.md#-데이터베이스-스키마)

---

## 🔐 인증 방식

### 세션 기반 (선택된 방식)
```
사용자 입력 사번 (10001)
        ↓
/api/auth/login (POST)
        ↓
ALLOWED_EMPLOYEES에서 검증
        ↓
DB에 기록 + last_login 업데이트
        ↓
세션 쿠키 생성 (httpOnly)
        ↓
브라우저에 저장 (자동)
        ↓
다음 요청부터 쿠키 자동 전송
```

**보안 설정:**
- `httpOnly`: JavaScript 접근 불가
- `Secure`: HTTPS 연결에서만 전송
- `SameSite=Lax`: CSRF 공격 방지
- **timeout**: 8시간

**vs JWT (제외한 이유):**
- ❌ JWT는 추가 로직 필요 (발급, 검증, 갱신)
- ✅ 세션은 브라우저가 자동 처리 (간단함)
- ✅ 서버 세션 강제 로그아웃 가능

---

## 📋 Phase 1: 기초 인프라 (예정)

### 생성할 파일 (7개)
1. `app/models/database.py` - SQLAlchemy 모델
2. `app/utils/db.py` - DB 세션 관리
3. `app/services/auth_service.py` - 인증 로직
4. `app/routes/auth.py` - API 엔드포인트
5. `templates/index.html` - 로그인 페이지
6. `static/js/common.js` - 공용 함수
7. `static/css/style.css` - 스타일

### 수정할 파일 (3개)
1. `config.py` - DB, 세션, AI_AGENTS 설정
2. `main.py` - SessionMiddleware, 라우터 등록
3. `requirements.txt` - 의존성 추가

### 예상 일정
- **총 시간**: 8.5시간
- **구현 기간**: 2-3일 (일일 4시간 기준)
- **테스트 포함**: 총 1주

---

## ✅ Phase 1 완료 기준

| 항목 | 기준 |
|------|------|
| **config.py** | DATABASE_URL, ALLOWED_EMPLOYEES, SESSION_SECRET_KEY 추가 |
| **database.py** | 5개 모델 정의, ForeignKey 관계 설정 |
| **db.py** | init_db() 함수, get_db() 의존성 구현 |
| **auth_service.py** | validate_employee(), get_current_employee() 구현 |
| **auth.py** | /login, /logout, /session 엔드포인트 구현 |
| **main.py** | SessionMiddleware, init_db() 호출, auth 라우터 등록 |
| **index.html** | 로그인 폼, JavaScript 폼 제출 처리 |
| **common.js** | checkSession(), apiCall(), showNotification() 함수 |
| **DB 테스트** | data/stt_web.db 생성 확인, 테이블 생성 확인 |
| **로그인 테스트** | 테스트 계정(10001-10003)으로 로그인 성공 |
| **세션 테스트** | /api/auth/session 엔드포인트에서 사용자 정보 조회 |
| **에러 처리** | 잘못된 사번 입력 시 에러 메시지 표시 |

---

## 🚀 다음 단계 (Phase 1 시작)

### 즉시 실행
1. **requirements.txt 업데이트**
   - sqlalchemy, python-multipart 추가

2. **config.py 수정**
   - DB, 세션, 인증 설정 추가
   - 코드: [01_WEB_UI_REFACTOR_PLAN.md#1-configpy-수정](01_WEB_UI_REFACTOR_PLAN.md#1-configpy-수정)

3. **database.py 생성**
   - SQLAlchemy 모델 5개
   - 코드: [01_WEB_UI_REFACTOR_PLAN.md#2-appmodelsdatabasepy-생성](01_WEB_UI_REFACTOR_PLAN.md#2-appmodelsdatabasepy-생성)

4. **나머지 파일들 순차 구현**
   - 체크리스트: [02_WEB_UI_REFACTOR_CHECKLIST.md](02_WEB_UI_REFACTOR_CHECKLIST.md)

---

## 💡 주요 결정사항

| 항목 | 결정 | 이유 |
|------|------|------|
| **인증** | 세션 쿠키 | JWT보다 간단, 브라우저 자동 처리 |
| **DB** | SQLite | 단일 서버, 개발 용이, 배포 간단 |
| **파일 구조** | emp_id/date | 사용자 격리 + 조직화 |
| **비동기** | 백그라운드 태스크 | 대기 시간 없는 UX |
| **Frontend** | Vanilla JS | 프레임워크 오버헤드 제거 |

---

## 📊 예상 소요 시간

| 항목 | 시간 | 시작 예정 |
|------|------|---------|
| Phase 1 (기초) | 1주 | 2026-02-20 |
| Phase 2 (파일) | 1주 | 2026-02-27 |
| Phase 3 (분석) | 1.5주 | 2026-03-06 |
| Phase 4 (통합) | 1주 | 2026-03-17 |
| **총계** | **4.5주** | |

---

## 📞 질문/변경 사항

변경이 필요하면 다음을 확인하세요:

- ❓ 추가 기능 요청?
  → [01_WEB_UI_REFACTOR_PLAN.md](01_WEB_UI_REFACTOR_PLAN.md)에 명세 추가

- ❓ 기술 스택 변경?
  → Phase 1 시작 전에 논의 후 변경

- ❓ 일정 조정?
  → Phase별 영향도 평가 후 조정

- ❓ Phase 우선순위 변경?
  → 체크리스트 재정렬 및 의존성 확인

---

## 📌 중요 노트

1. **scratch/stt-web**: 참고용만, 수정 불필요
2. **web_ui**: 이 디렉토리만 실제 구현
3. **기존 기능**: 유지보수 (STT, API 등)
4. **DB 초기화**: 필요시 `rm data/stt_web.db && python main.py`
5. **테스트 계정**: config.py에서 관리

---

> 🚀 **준비 완료!**
> 
> Phase 1 구현 시작: 다음 문서 참고
> - 상세 코드: [01_WEB_UI_REFACTOR_PLAN.md](01_WEB_UI_REFACTOR_PLAN.md)
> - 체크리스트: [02_WEB_UI_REFACTOR_CHECKLIST.md](02_WEB_UI_REFACTOR_CHECKLIST.md)
