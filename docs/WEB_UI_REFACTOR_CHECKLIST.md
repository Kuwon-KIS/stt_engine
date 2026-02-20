# Web UI 리팩토링 체크리스트

## Phase 1: 기초 인프라

### 1. 데이터베이스 모델 생성
- [ ] `app/models/database.py` 생성
  - [ ] Employee 모델
  - [ ] FileUpload 모델
  - [ ] AnalysisJob 모델
  - [ ] AnalysisResult 모델
  - [ ] AnalysisProgress 모델
  - [ ] init_db() 함수

### 2. 인증 시스템 구현
- [ ] `app/services/auth_service.py` 생성
  - [ ] 세션 쿠키 기반 인증
  - [ ] 직원 검증
  - [ ] 로그인/로그아웃
- [ ] `app/routes/auth.py` 생성
  - [ ] POST /api/auth/login
  - [ ] POST /api/auth/logout
  - [ ] GET /api/auth/session
- [ ] `templates/index.html` 생성
  - [ ] 로그인 폼 UI
  - [ ] 직원 정보 검증
  - [ ] 에러 메시지 표시

### 3. 설정 및 유틸리티
- [ ] `config.py` 업데이트
  - [ ] DATABASE_URL 추가
  - [ ] ALLOWED_EMPLOYEES 추가
  - [ ] SESSION_SECRET_KEY 추가
  - [ ] SESSION_TIMEOUT_HOURS 추가
  - [ ] AI_AGENTS 설정 추가
- [ ] `app/utils/db.py` 생성
  - [ ] get_session() 함수
  - [ ] init_db() 함수
- [ ] `app/utils/logger.py` 생성 (선택사항)

### 4. 프론트엔드 기초
- [ ] `static/js/common.js` 생성
  - [ ] 세션 확인
  - [ ] API 호출 헬퍼
  - [ ] 알림/포맷팅
- [ ] `static/css/style.css` 업데이트
  - [ ] 로그인 페이지 스타일
  - [ ] 반응형 디자인
- [ ] `main.py` 업데이트
  - [ ] SessionMiddleware 추가
  - [ ] DB 초기화
  - [ ] auth 라우터 등록
  - [ ] 정적 파일 마운트 (templates)

### 5. 의존성 업데이트
- [ ] `requirements.txt` 업데이트
  - [ ] sqlalchemy 추가
  - [ ] python-multipart 추가
  - [ ] 기타 필요한 패키지

---

## Phase 2: 파일 관리

### 1. 업로드 서비스 개선
- [ ] `app/services/upload_service.py` 생성
  - [ ] 사번별 폴더 격리
  - [ ] 날짜/커스텀 폴더 자동 생성
  - [ ] 파일 메타데이터 저장
  - [ ] 파일 검증 (확장자, 크기)

### 2. 파일 관리 라우터
- [ ] `app/routes/upload.py` 생성
  - [ ] POST /api/upload
  - [ ] GET /api/uploads/{emp_id}
  - [ ] POST /api/uploads/folder
- [ ] `app/routes/files.py` 생성
  - [ ] GET /api/files/{emp_id}
  - [ ] GET /api/files/search
  - [ ] DELETE /api/files/{file_id}

### 3. 업로드 UI
- [ ] `templates/upload.html` 생성
  - [ ] 드래그앤드롭
  - [ ] 폴더 목록 표시
  - [ ] 파일 목록 표시
  - [ ] 폴더 검색
  - [ ] 폴더 선택 후 분석 페이지 이동

### 4. 업로드 JavaScript
- [ ] `static/js/upload.js` 생성
  - [ ] 드래그앤드롭 처리
  - [ ] 파일 업로드
  - [ ] 진행 상황 표시
  - [ ] 폴더 목록 새로고침

---

## Phase 3: 분석 시스템

### 1. 분석 서비스 생성
- [ ] `app/services/analysis_service.py` 생성
  - [ ] AnalysisJob 생성/조회
  - [ ] 분석 시작
  - [ ] 진행 상태 업데이트
  - [ ] 결과 저장

### 2. 분석 라우터
- [ ] `app/routes/analysis.py` 생성
  - [ ] POST /api/analysis/start
  - [ ] GET /api/analysis/{job_id}/progress
  - [ ] GET /api/analysis/{job_id}/results
  - [ ] GET /api/analysis/{job_id}/status

### 3. 비동기 워커
- [ ] `app/tasks/analysis_worker.py` 생성
  - [ ] 백그라운드 분석 처리
  - [ ] STT 엔진 호출
  - [ ] 분류 처리
  - [ ] AI Agent 호출 (부당권유/불완전판매)
  - [ ] 결과 저장
  - [ ] 진행 상태 업데이트

### 4. 분석 페이지 개선
- [ ] `templates/analysis.html` 개선
  - [ ] 분석 옵션 선택 UI (부당권유, 불완전판매)
  - [ ] AI Agent URL 입력 (선택사항)
  - [ ] 분석 시작 버튼
  - [ ] 실시간 진행 상황 표시
  - [ ] 파일별 상태 표시
  - [ ] 미디어 플레이어
  - [ ] STT 결과 표시
  - [ ] 분석 결과 표시 (부당권유/불완전판매)

### 5. 분석 JavaScript
- [ ] `static/js/analysis.js` 개선
  - [ ] 옵션 선택 처리
  - [ ] 분석 시작 요청
  - [ ] 진행 상황 polling/WebSocket
  - [ ] 결과 표시
  - [ ] 다시 분석 버튼

### 6. 스키마 업데이트
- [ ] `app/models/schemas.py` 업데이트
  - [ ] 분석 옵션 스키마 추가
  - [ ] 분석 결과 스키마 개선
  - [ ] 진행 상황 스키마 추가

### 7. 기존 서비스 업데이트
- [ ] `services/stt_service.py` 개선
  - [ ] 부당권유 탐지 옵션 추가
  - [ ] 불완전판매 탐지 옵션 추가
  - [ ] AI Agent 호출 로직 추가

---

## Phase 4: 통합 및 최적화

### 1. 워크플로우 통합
- [ ] index.html → upload.html → analysis.html 흐름 확인
- [ ] 세션 유지 검증
- [ ] 에러 처리
- [ ] 로깅 추가

### 2. 성능 최적화
- [ ] 대용량 파일 처리 (streaming)
- [ ] 동시 분석 제한
- [ ] 캐싱 전략
- [ ] DB 인덱스 추가

### 3. 테스트
- [ ] 단위 테스트 작성
- [ ] 통합 테스트
- [ ] 성능 테스트
- [ ] 사용자 테스트

### 4. 배포 준비
- [ ] Docker 이미지 업데이트
- [ ] 환경 변수 설정
- [ ] 마이그레이션 스크립트
- [ ] 배포 가이드 작성

---

## 🎯 우선순위

### 필수 (Phase 1)
1. 데이터베이스 모델
2. 세션 기반 인증
3. 로그인 페이지
4. main.py 업데이트

### 중요 (Phase 2-3)
5. 파일 업로드/관리
6. 분석 기능
7. 부당권유/불완전판매 탐지

### 선택사항
- 성능 최적화
- 고급 기능 (WebSocket 등)
- 추가 테스트

---

## 📝 진행 상황

### Phase 1
- [x] 작업 계획 수립
- [ ] 구현 시작

### Phase 2
- [ ] 구현 예정

### Phase 3
- [ ] 구현 예정

### Phase 4
- [ ] 구현 예정
