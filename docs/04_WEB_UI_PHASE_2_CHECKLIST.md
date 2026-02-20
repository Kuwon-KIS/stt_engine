# Phase 2-2 체크리스트: 파일 업로드 & 폴더 관리

> 📌 **참고 문서**
> - [04_WEB_UI_PHASE_2_PLAN.md](04_WEB_UI_PHASE_2_PLAN.md) - Phase 2 상세 계획

---

## 🎯 Phase 2 체크리스트

### 2.1 Backend 서비스 구현

#### 2.1.1 file_utils.py 생성
**목적**: 파일 경로 검증, 폴더 생성 등 유틸리티

- [ ] 모듈 임포트 (os, pathlib, datetime)
- [ ] `create_folder_path()` 함수
  - [ ] emp_id 검증
  - [ ] folder_name 없으면 오늘 날짜 사용 (YYYY-MM-DD)
  - [ ] 폴더 자동 생성 (존재하지 않으면)
  - [ ] 반환: `"2026-02-20"` 또는 `"커스텀폴더명"`
- [ ] `validate_file_path()` 함수
  - [ ] 경로 traversal 공격 방지
  - [ ] 안전한 절대 경로 생성
  - [ ] 범위 체크 (base_dir 내에 있는지)
- [ ] `validate_filename()` 함수
  - [ ] 허용 확장자 검사
  - [ ] 파일명 길이 검사
  - [ ] 특수 문자 제거/검증
- [ ] `get_file_size()` 함수
  - [ ] 파일 크기를 MB 단위로 반환
- [ ] 상수 정의
  - [ ] ALLOWED_EXTENSIONS = {".wav", ".mp3", ...}
  - [ ] MAX_FILE_SIZE_MB = 500

**파일 위치**: `web_ui/app/utils/file_utils.py`  
**소요 시간**: 45분

---

#### 2.1.2 file_schemas.py 생성
**목적**: 파일 업로드 관련 Pydantic 모델

- [ ] 요청 모델
  - [ ] `FileUploadRequest`
    - [ ] folder_name: Optional[str]
  - [ ] 폼 데이터 처리용 (파일 + folder_name)
- [ ] 응답 모델
  - [ ] `FileUploadResponse`
    - [ ] success: bool
    - [ ] filename: str
    - [ ] file_size_mb: float
    - [ ] folder_path: str
    - [ ] uploaded_at: datetime
    - [ ] message: str
  - [ ] `FileInfo`
    - [ ] filename: str
    - [ ] file_size_mb: float
    - [ ] uploaded_at: datetime
  - [ ] `FileListResponse`
    - [ ] folder_path: str
    - [ ] files: List[FileInfo]
    - [ ] total_size_mb: float
  - [ ] `FolderListResponse`
    - [ ] folders: List[str]
  - [ ] `FileDeleteResponse`
    - [ ] success: bool
    - [ ] message: str

**파일 위치**: `web_ui/app/models/file_schemas.py` (또는 별도)  
**소요 시간**: 30분

---

#### 2.1.3 file_service.py 생성
**목적**: 파일 업로드/삭제/조회 비즈니스 로직

- [ ] 임포트 및 설정
  - [ ] os, pathlib, datetime
  - [ ] FastAPI UploadFile
  - [ ] SQLAlchemy Session
  - [ ] database models (Employee, FileUpload)
  - [ ] file_utils 함수들
  - [ ] config (UPLOAD_DIR, MAX_FILE_SIZE_MB)

- [ ] `FileService` 클래스
  - [ ] `upload_file(emp_id, file, folder_name, db)` → FileUploadResponse
    - [ ] 사용자(emp_id) 검증
    - [ ] 파일명/크기 검증
    - [ ] 파일 저장 (data/uploads/{emp_id}/{folder_path}/{filename})
    - [ ] DB에 FileUpload 레코드 생성
    - [ ] 에러 처리
  
  - [ ] `list_files(emp_id, folder_path, db)` → FileListResponse
    - [ ] 사용자(emp_id) 검증
    - [ ] 폴더 또는 모든 파일 조회
    - [ ] DB에서 파일 목록 검색
    - [ ] 폴더별 총 크기 계산
    - [ ] 반환: 파일 목록 + 총 크기
  
  - [ ] `list_folders(emp_id, db)` → FolderListResponse
    - [ ] 사용자(emp_id) 검증
    - [ ] data/uploads/{emp_id}의 폴더 목록 조회
    - [ ] DB와 파일 시스템 동기화
    - [ ] 반환: 폴더명 목록 정렬
  
  - [ ] `delete_file(emp_id, filename, folder_path, db)` → FileDeleteResponse
    - [ ] 사용자(emp_id) 검증
    - [ ] 파일 경로 검증 (traversal 방지)
    - [ ] 파일 시스템에서 삭제
    - [ ] DB 레코드 삭제
    - [ ] 폴더 비었으면 폴더도 삭제 (선택사항)

- [ ] 에러 처리
  - [ ] HTTPException (400, 401, 404, 413 등)
  - [ ] 자세한 에러 메시지

**파일 위치**: `web_ui/app/services/file_service.py`  
**소요 시간**: 1.5시간

---

#### 2.1.4 files.py 라우터 생성
**목적**: 파일 관련 API 엔드포인트 4개

- [ ] 임포트
  - [ ] FastAPI, UploadFile, File, HTTPException
  - [ ] Request, Depends
  - [ ] SessionLocal, get_db
  - [ ] FileService
  - [ ] file_schemas (Pydantic 모델들)

- [ ] `APIRouter` 생성
  - [ ] prefix: "/api/files"
  - [ ] tags: ["files"]

- [ ] `GET /folders` - 폴더 목록 조회
  - [ ] 세션 검증 (emp_id 추출)
  - [ ] FileService.list_folders() 호출
  - [ ] 응답: FolderListResponse
  - [ ] 에러 처리

- [ ] `GET /list` - 파일 목록 조회
  - [ ] 쿼리 파라미터: folder_path (선택)
  - [ ] 세션 검증
  - [ ] FileService.list_files() 호출
  - [ ] 응답: FileListResponse
  - [ ] 에러 처리

- [ ] `POST /upload` - 파일 업로드
  - [ ] 폼 데이터: file (파일), folder_name (선택)
  - [ ] 세션 검증
  - [ ] FileService.upload_file() 호출
  - [ ] 응답: FileUploadResponse (201)
  - [ ] 에러 처리 (파일 크기 초과 등)

- [ ] `DELETE /{filename}` - 파일 삭제
  - [ ] 경로 파라미터: filename
  - [ ] 쿼리 파라미터: folder_path
  - [ ] 세션 검증
  - [ ] FileService.delete_file() 호출
  - [ ] 응답: FileDeleteResponse
  - [ ] 에러 처리

**파일 위치**: `web_ui/app/routes/files.py`  
**소요 시간**: 1시간

---

### 2.2 Backend 통합

#### 2.2.1 main.py 수정
- [ ] 임포트 추가
  - [ ] `from app.routes import files`
- [ ] 라우터 등록
  - [ ] `app.include_router(files.router)`
- [ ] 위치: SessionMiddleware 등록 다음, 기타 라우터 등록 이전

**소요 시간**: 15분

---

#### 2.2.2 config.py 수정
- [ ] 파일 관련 상수 추가 (이미 있을 수 있음)
  - [ ] ALLOWED_EXTENSIONS (있으면 유지)
  - [ ] MAX_UPLOAD_SIZE_MB (있으면 유지)
  - [ ] 필요시 path 최적화

**소요 시간**: 10분

---

### 2.3 Frontend 구현

#### 2.3.1 upload.html 생성
**목적**: 파일 업로드 및 폴더 관리 UI

- [ ] HTML 구조
  - [ ] 헤더 (로그인 정보, 로그아웃 버튼)
  - [ ] 폴더 선택 (드롭다운 또는 라디오)
  - [ ] 파일 업로드 영역 (drag & drop)
  - [ ] 진행 바 (업로드 중)
  - [ ] 파일 목록 (테이블)
  - [ ] 분석 시작 버튼 (Phase 3용)

- [ ] CSS 스타일
  - [ ] 반응형 레이아웃
  - [ ] 로그인 정보 표시
  - [ ] 폴더 선택 스타일
  - [ ] 파일 목록 테이블
  - [ ] 진행 바 애니메이션
  - [ ] 버튼 스타일

- [ ] JavaScript 연결
  - [ ] common.js import
  - [ ] upload.js import
  - [ ] 초기 로딩 시 세션 확인

**파일 위치**: `web_ui/templates/upload.html`  
**소요 시간**: 1.5시간

---

#### 2.3.2 upload.js 생성
**목적**: 파일 업로드 및 폴더 관리 클라이언트 로직

- [ ] 초기화
  - [ ] 페이지 로드 시 세션 확인 (없으면 로그인으로)
  - [ ] 폴더 목록 로드
  - [ ] 파일 목록 로드

- [ ] 폴더 관련 함수
  - [ ] `loadFolders()` - 폴더 목록 조회
  - [ ] `onFolderChange()` - 선택 폴더 변경 시 파일 목록 새로고침
  - [ ] `createNewFolder()` - 새 폴더 생성 (폼 + API)

- [ ] 파일 업로드
  - [ ] `setupDragDrop()` - drag & drop 설정
  - [ ] `onFileSelected()` - 파일 선택 시 처리
  - [ ] `uploadFiles()` - 파일 업로드 (FormData)
  - [ ] `updateUploadProgress()` - 진행 바 업데이트
  - [ ] 에러 처리 (파일 크기, 형식 등)

- [ ] 파일 목록
  - [ ] `loadFiles()` - 파일 목록 조회
  - [ ] `displayFiles()` - 테이블에 파일 표시
  - [ ] 파일명, 크기, 업로드 시간 표시
  - [ ] 삭제 버튼

- [ ] 파일 삭제
  - [ ] `deleteFile()` - 파일 삭제 API 호출
  - [ ] 확인 다이얼로그
  - [ ] 삭제 후 목록 새로고침

- [ ] 분석 시작 (Phase 3 준비)
  - [ ] `startAnalysis()` - 선택된 폴더로 분석 작업 생성
  - [ ] analysis.html로 이동

**파일 위치**: `web_ui/static/js/upload.js`  
**소요 시간**: 1.5시간

---

#### 2.3.3 common.js 확장
- [ ] 파일 관련 유틸리티 추가
  - [ ] `formatBytes()` - 이미 있을 수 있음
  - [ ] `formatDate()` - 이미 있을 수 있음
  - [ ] `createFileIcon()` - 파일 타입별 아이콘
  - [ ] `validateFile()` - 파일 유효성 검사

**소요 시간**: 20분

---

### 2.4 테스트

#### 2.4.1 API 테스트
- [ ] 폴더 목록 조회
  - [ ] GET /api/files/folders → 200
  - [ ] 폴더 배열 반환 확인

- [ ] 파일 목록 조회
  - [ ] GET /api/files/list → 200
  - [ ] 파일 배열 반환 확인
  - [ ] 폴더별 조회

- [ ] 파일 업로드
  - [ ] POST /api/files/upload (단일 파일) → 201
  - [ ] POST /api/files/upload (폴더명 지정) → 201
  - [ ] 파일 시스템 확인
  - [ ] DB 확인
  - [ ] 파일 크기 초과 → 413
  - [ ] 허용되지 않는 확장자 → 400

- [ ] 파일 삭제
  - [ ] DELETE /api/files/{filename} → 200
  - [ ] 파일 시스템 확인
  - [ ] DB 확인
  - [ ] 존재하지 않는 파일 → 404

#### 2.4.2 UI 테스트
- [ ] 페이지 로드 확인
- [ ] 로그인 정보 표시 확인
- [ ] 폴더 목록 로드 확인
- [ ] 파일 업로드 UI 작동 확인
- [ ] Drag & drop 작동 확인
- [ ] 진행 바 표시 확인
- [ ] 파일 목록 표시 확인
- [ ] 삭제 버튼 작동 확인

#### 2.4.3 보안 테스트
- [ ] 경로 traversal 공격 방지 확인
  - [ ] `GET /api/files/list?folder_path=../../../`
- [ ] 다른 사용자 파일 접근 불가 확인
- [ ] 미인증 사용자 접근 불가 확인

**소요 시간**: 1.5시간

---

### 2.5 문서화

#### 2.5.1 API 문서 작성
- [ ] OpenAPI/Swagger 주석 추가 (FastAPI 자동 생성)
- [ ] 각 엔드포인트 docstring 작성
- [ ] 요청/응답 예시 포함

#### 2.5.2 체크리스트 검토
- [ ] 모든 항목 완료 확인
- [ ] 버그/이슈 정리

**소요 시간**: 45분

---

## 📊 진행 상황 추적

| 항목 | 상태 | 예상 시간 | 실제 시간 |
|------|------|---------|---------|
| file_utils.py | ⬜ | 45분 | |
| file_schemas.py | ⬜ | 30분 | |
| file_service.py | ⬜ | 1.5시간 | |
| files.py | ⬜ | 1시간 | |
| main.py 수정 | ⬜ | 15분 | |
| config.py 수정 | ⬜ | 10분 | |
| upload.html | ⬜ | 1.5시간 | |
| upload.js | ⬜ | 1.5시간 | |
| common.js 확장 | ⬜ | 20분 | |
| 테스트 | ⬜ | 1.5시간 | |
| 문서화 | ⬜ | 45분 | |
| **합계** | | **10시간** | |

---

## 🎯 다음 단계

✅ Phase 2 체크리스트 완료 시:
1. 모든 변경사항 git commit
2. Phase 3 계획 시작 (분석 시스템)
3. Phase 2-3 통합 테스트

---

## 📌 중요 노트

1. **파일 경로 검증**: 반드시 traversal 공격 방지
2. **사용자 격리**: 모든 파일 접근 시 emp_id 검증
3. **에러 처리**: 명확한 에러 메시지 제공
4. **DB 동기화**: 파일 시스템과 DB 항상 동기화
5. **테스트 우선**: 구현 후 충분한 테스트

---

**이전 단계**: Phase 1 - 인증 & DB (✅ 완료)  
**현재 단계**: Phase 2 - 파일 업로드 & 폴더 관리  
**다음 단계**: Phase 3 - 분석 시스템 (분석 작업, 비동기 처리, 결과 저장)
