# Web UI 리팩토링 - 작업 진행 요약

## 📌 작업 방향

**목표**: 현재 web_ui를 개선하여 다음 기능 추가
- 사용자 인증 (사번 기반, 세션 방식)
- 파일 업로드 관리 (사번별 격리, 날짜/폴더 구조)
- 분석 기능 강화 (부당권유/불완전판매 탐지)
- 메타데이터 관리 (SQLite DB)

---

## 📚 작성된 계획 문서

### 1. **WEB_UI_REFACTOR_PLAN.md**
- 현재 구조 vs 개선 구조 비교
- 4단계 Phase별 상세 계획
- 데이터베이스 스키마 정의
- 파일 저장 구조 명세
- 세션 기반 인증 방식

### 2. **WEB_UI_REFACTOR_CHECKLIST.md**
- Phase별 체크리스트
- 생성/수정할 파일 목록
- 우선순위 정의
- 진행 상황 추적

### 3. **STT_WEB_SERVICE_IMPLEMENTATION_PLAN.md** (참고용)
- scratch/stt-web의 전체 설계
- 앞의 두 계획 문서는 이것을 기반으로 web_ui 중심으로 재정리

---

## 🎯 다음 스텝

### Phase 1: 기초 인프라 구축 (권장 1주)

**우선순위 순서:**

1. **config.py 업데이트** (30분)
   - DATABASE_URL 추가
   - ALLOWED_EMPLOYEES 추가
   - SESSION_SECRET_KEY 추가
   - requirements.txt 의존성 확인

2. **app/models/database.py 생성** (1시간)
   - SQLAlchemy 모델 5개 정의
   - init_db() 함수 구현

3. **app/utils/db.py 생성** (30분)
   - DB 세션 관리
   - get_session() 함수

4. **app/services/auth_service.py 생성** (1시간)
   - 세션 쿠키 검증
   - 로그인/로그아웃 처리

5. **app/routes/auth.py 생성** (1시간)
   - /api/auth/login
   - /api/auth/logout
   - /api/auth/session

6. **main.py 업데이트** (30분)
   - SessionMiddleware 추가
   - init_db() 호출
   - auth 라우터 등록

7. **templates/index.html 생성** (1시간)
   - 로그인 폼 UI
   - JavaScript 로그인 처리

8. **static/js/common.js 생성** (1시간)
   - 세션 관리 함수
   - API 호출 헬퍼
   - 유틸리티 함수

---

## ✅ 변경 사항 요약

### JWT 제외 (세션 방식으로 변경)
- JWT 토큰 대신 세션 쿠키 사용
- httpOnly 보안 옵션
- 8시간 타임아웃

### 파일 저장 구조 개선
```
data/uploads/
├── 10001/                  # 사번으로 격리
│   ├── 2026-02-20/        # 날짜 폴더 (자동 생성)
│   └── 부당권유_검토/      # 커스텀 폴더 (사용자 지정)
└── 10002/
```

### DB 기반 메타데이터 관리
- 사용자 정보
- 파일 메타정보
- 분석 작업 추적
- 결과 저장

---

## 📊 예상 소요 시간

| Phase | 내용 | 예상 기간 |
|-------|------|---------|
| 계획 수립 | 계획 문서 작성 | ✅ 완료 |
| Phase 1 | 기초 인프라 (인증, DB) | 1주 |
| Phase 2 | 파일 관리 (업로드) | 1주 |
| Phase 3 | 분석 시스템 | 1.5주 |
| Phase 4 | 통합 및 테스트 | 1주 |
| **총계** | | **4.5주** |

---

## 🚀 시작하기

### 준비 단계
1. 계획 문서 검토 (WEB_UI_REFACTOR_PLAN.md)
2. 체크리스트 확인 (WEB_UI_REFACTOR_CHECKLIST.md)
3. Phase 1 우선순위 항목부터 구현 시작

### 구현 순서
```
config.py → database.py → db.py → auth_service.py 
→ auth.py → main.py → index.html → common.js
```

### 테스트 방법
```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. DB 초기화 (main.py 실행 시 자동)
python main.py

# 3. 로그인 테스트
# http://localhost:8000/static/index.html
# 사번 입력: 10001, 10002, 10003

# 4. 업로드 페이지 접근
# http://localhost:8000/static/upload.html
```

---

## 💡 주요 결정사항

1. **인증 방식**: JWT → 세션 쿠키 (간단함)
2. **DB**: SQLite (단일 서버, 개발 용이)
3. **비동기**: 백그라운드 태스크 (분석 대기시간 제거)
4. **폴더 구조**: 사번 > 날짜/폴더명 (사용자 격리)
5. **AI Agent**: URL 사전 정의 (설정 파일에서 관리)

---

## 📝 문서 위치

```
docs/
├── WEB_UI_REFACTOR_PLAN.md       # 상세 계획
├── WEB_UI_REFACTOR_CHECKLIST.md  # 체크리스트
├── STT_WEB_SERVICE_IMPLEMENTATION_PLAN.md  # 전체 설계 (참고)
└── ...
```

---

## ❓ 질문/검토 사항

이 계획에 대해 질문이 있거나 조정이 필요한 부분이 있으면 알려주세요:

- [ ] Phase별 일정 조정 필요?
- [ ] 추가 기능 요청?
- [ ] 기술 스택 변경?
- [ ] 우선순위 변경?

---

**다음 단계**: Phase 1 구현 시작 (config.py 업데이트부터)
