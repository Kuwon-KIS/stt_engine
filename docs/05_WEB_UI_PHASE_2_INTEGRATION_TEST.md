# Phase 2 파일 업로드 시스템 - 통합 테스트 가이드

**Commit**: `1608f6f` - Phase 2: 파일 업로드 및 폴더 관리 시스템 구현

## 1. 구현 완료 사항

### ✅ 백엔드 구현
- **file_utils.py** (~240 lines)
  - 파일 경로 생성/검증 (경로 조회 공격 방지)
  - 파일명 검증 (확장자, 특수문자 검사)
  - 폴더 나열 및 정렬
  - 파일 크기 계산 및 유효성 검사

- **file_schemas.py** (~60 lines)
  - 6개 Pydantic 모델 (FileInfo, FileUploadResponse, FileListResponse 등)
  - OpenAPI 자동 문서화 지원

- **file_service.py** (~290 lines)
  - FileService 클래스 with 5개 메서드
  - 사용자 검증, 파일 저장, DB 동기화
  - 에러 처리 (400, 401, 404, 409, 500)

- **files.py** (~95 lines)
  - APIRouter with 4개 엔드포인트
  - 세션 기반 인증
  - 파일 업로드/조회/삭제 REST API

### ✅ 프론트엔드 구현
- **upload.html** (~380 lines)
  - 로그인된 사용자 정보 표시
  - 폴더 선택 (사이드바)
  - 드래그 앤 드롭 파일 업로드
  - 파일 목록 (테이블)
  - 진행률 표시
  - 반응형 디자인

### ✅ 라우팅
- **main.py** 수정
  - files 라우터 등록
  - /upload 경로 추가 (세션 확인 포함)

- **login.html** 수정
  - 로그인 후 /upload로 리다이렉트
  - 자동 리다이렉트 로직 추가

## 2. 테스트 플로우

### 2.1 기본 시나리오 테스트

#### Step 1: 로그인
```bash
curl -X POST http://localhost:8100/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"emp_id": "90001", "password": "test123"}'
```

**예상 응답**:
```json
{
  "success": true,
  "emp_id": "90001",
  "name": "Admin User",
  "dept": "관리팀",
  "message": "로그인 성공"
}
```

#### Step 2: 세션 확인
```bash
curl -X GET http://localhost:8100/api/auth/session \
  -b "session=<session_cookie>"
```

**예상 응답**:
```json
{
  "emp_id": "90001",
  "name": "Admin User",
  "dept": "관리팀"
}
```

#### Step 3: 폴더 목록 조회
```bash
curl -X GET http://localhost:8100/api/files/folders \
  -b "session=<session_cookie>"
```

**예상 응답** (처음):
```json
{
  "folders": []
}
```

#### Step 4: 파일 업로드
```bash
curl -X POST http://localhost:8100/api/files/upload \
  -F "file=@sample.wav" \
  -F "folder_name=2026-02-20" \
  -b "session=<session_cookie>"
```

**예상 응답**:
```json
{
  "success": true,
  "filename": "sample.wav",
  "file_size_mb": 1.25,
  "folder_path": "2026-02-20",
  "uploaded_at": "2026-02-20T17:43:10.657Z",
  "message": "파일 업로드 성공"
}
```

#### Step 5: 파일 목록 조회
```bash
curl -X GET "http://localhost:8100/api/files/list?folder_path=2026-02-20" \
  -b "session=<session_cookie>"
```

**예상 응답**:
```json
{
  "folder_path": "2026-02-20",
  "files": [
    {
      "filename": "sample.wav",
      "file_size_mb": 1.25,
      "uploaded_at": "2026-02-20T17:43:10.657Z"
    }
  ],
  "total_size_mb": 1.25
}
```

#### Step 6: 파일 삭제
```bash
curl -X DELETE "http://localhost:8100/api/files/sample.wav?folder_path=2026-02-20" \
  -b "session=<session_cookie>"
```

**예상 응답**:
```json
{
  "success": true,
  "message": "파일 삭제됨"
}
```

### 2.2 에러 케이스 테스트

#### 테스트: 인증 없이 파일 접근
```bash
curl -X GET http://localhost:8100/api/files/folders
```

**예상 응답** (401):
```json
{
  "detail": "로그인이 필요합니다"
}
```

#### 테스트: 존재하지 않는 파일 삭제
```bash
curl -X DELETE "http://localhost:8100/api/files/nonexistent.wav" \
  -b "session=<session_cookie>"
```

**예상 응답** (404):
```json
{
  "detail": "파일을 찾을 수 없습니다"
}
```

#### 테스트: 지원하지 않는 확장자
```bash
curl -X POST http://localhost:8100/api/files/upload \
  -F "file=@document.pdf" \
  -b "session=<session_cookie>"
```

**예상 응답** (400):
```json
{
  "detail": "지원하지 않는 파일 형식입니다: document.pdf"
}
```

## 3. UI 테스트

### 3.1 로그인 페이지
1. `http://localhost:8100/login` 접속
2. 사번: `90001`
3. 비밀번호: `test123`
4. **로그인** 버튼 클릭
5. **예상**: `/upload` 페이지로 리다이렉트

### 3.2 업로드 페이지
1. 로그인 후 `/upload` 페이지 접속
2. 사용자명 표시 확인 (예: "Admin User")
3. 폴더 목록 확인 (초기값: "전체 파일")
4. 파일 업로드:
   - 테스트 오디오 파일 준비
   - 드래그 앤 드롭 또는 "파일 선택" 클릭
   - 진행률 표시 확인
   - 업로드 완료 알림 확인
5. 파일 목록 확인:
   - 업로드된 파일이 테이블에 표시됨
   - 파일명, 크기, 시간 표시
6. 폴더 목록 확인:
   - 새로운 폴더가 사이드바에 표시됨
7. 폴더 선택:
   - 폴더 클릭
   - 해당 폴더의 파일만 표시됨
8. 파일 삭제:
   - 파일의 "삭제" 버튼 클릭
   - 확인 대화상자 표시
   - 삭제 후 파일 목록 업데이트

## 4. 파일 시스템 확인

### 저장 위치
```
web_ui/data/uploads/
├── 90001/                    # emp_id별 디렉토리
│   ├── 2026-02-20/          # 자동 폴더 (날짜)
│   │   ├── sample1.wav
│   │   └── sample2.wav
│   └── 사전_상담_녹취/       # 커스텀 폴더
│       └── recording.wav
└── 90002/
    └── ...
```

### 확인 명령어
```bash
# 업로드 디렉토리 구조 확인
find web_ui/data/uploads -type f | head -20

# 특정 사용자의 파일 확인
ls -lah web_ui/data/uploads/90001/

# 파일 크기 확인
du -sh web_ui/data/uploads/90001/*
```

## 5. 데이터베이스 확인

### file_uploads 테이블 조회
```sql
SELECT emp_id, folder_path, filename, file_size_mb, uploaded_at 
FROM file_uploads 
ORDER BY uploaded_at DESC 
LIMIT 10;
```

### Python으로 확인
```python
from app.utils.db import SessionLocal
from app.models.database import FileUpload

db = SessionLocal()
files = db.query(FileUpload).filter(FileUpload.emp_id == "90001").all()
for f in files:
    print(f"{f.filename} ({f.file_size_mb}MB) - {f.uploaded_at}")
```

## 6. 보안 검증

### 6.1 경로 조회 공격 방지
```bash
# ❌ 이 시도는 실패해야 함
curl -X DELETE "http://localhost:8100/api/files/../../sensitive.txt" \
  -b "session=<session_cookie>"
```

**예상**: 400 에러 (경로 검증 실패)

### 6.2 사용자 격리
```bash
# 90001 사용자로 로그인
curl -b "session=<90001_session>" -X GET http://localhost:8100/api/files/folders

# 같은 API로 90002의 세션 사용하면 90002의 파일만 조회되어야 함
curl -b "session=<90002_session>" -X GET http://localhost:8100/api/files/folders
```

**예상**: 각 사용자는 자신의 파일만 볼 수 있음

### 6.3 파일 확장자 검증
```bash
# 허용된 확장자: .wav, .mp3
# ❌ 이들은 거부되어야 함: .exe, .sh, .py, .html, .pdf 등
```

## 7. 성능 테스트

### 대용량 파일 업로드
```bash
# 100MB 테스트 파일 생성
dd if=/dev/zero of=large.wav bs=1M count=100

# 업로드 (500MB 제한)
time curl -X POST http://localhost:8100/api/files/upload \
  -F "file=@large.wav" \
  -b "session=<session_cookie>"
```

### 다중 파일 동시 업로드
```bash
# 5개 파일 동시 업로드
for i in {1..5}; do
  curl -X POST http://localhost:8100/api/files/upload \
    -F "file=@sample_$i.wav" \
    -b "session=<session_cookie>" &
done
wait
```

## 8. 모바일 반응형 테스트

1. 브라우저 개발자 도구 > 디바이스 에뮬레이션
2. 모바일 기기 선택 (iPhone 12, Galaxy S21 등)
3. 레이아웃이 올바르게 변경되는지 확인:
   - 사이드바가 축소되거나 숨겨져야 함
   - 파일 테이블이 스크롤 가능해야 함
   - 버튼들이 터치하기 편한 크기여야 함

## 9. 브라우저 호환성

테스트 대상 브라우저:
- Chrome/Edge (최신 버전)
- Firefox (최신 버전)
- Safari (macOS/iOS)
- 모바일 브라우저 (Chrome Mobile, Safari iOS)

**주의사항**:
- Fetch API 지원 필수
- multipart/form-data 지원 필수
- sessionStorage/localStorage 확인

## 10. 트러블슈팅

### 문제: 파일 업로드 실패 (413 Payload Too Large)
**해결**: FastAPI 최대 크기 제한 확인
```python
# main.py에서
app = FastAPI(max_upload_size=524288000)  # 500MB
```

### 문제: 세션 쿠키가 저장되지 않음
**해결**: 
- httpOnly 설정 확인 (main.py SessionMiddleware)
- CORS 설정 확인 (credentials 옵션)

### 문제: 파일 삭제 후 빈 폴더가 남음
**해결**: cleanup_empty_folders() 함수가 자동으로 정리해야 함
```bash
find web_ui/data/uploads -type d -empty -delete  # 수동 정리
```

### 문제: 데이터베이스 동기화 오류
**해결**: DB 재초기화
```python
from app.utils.db import init_db
init_db()  # 테이블 재생성
```

## 11. 다음 단계 (Phase 3)

Phase 2 완료 후 Phase 3 구현:
- ✅ 파일 업로드 시스템 완료
- 🔲 분석 작업 (STT, 분류, 검증) - Phase 3
- 🔲 결과 저장 및 조회 - Phase 3
- 🔲 분석 진행률 표시 - Phase 3

## 12. 체크리스트

- [ ] 로그인/로그아웃 정상 작동
- [ ] 파일 업로드 성공
- [ ] 파일 목록 조회 성공
- [ ] 파일 삭제 성공
- [ ] 폴더 목록 조회 성공
- [ ] 폴더 선택 후 파일 필터링
- [ ] 세션 만료 시 재로그인 요청
- [ ] 경로 조회 공격 방어
- [ ] 파일 확장자 검증
- [ ] 파일 크기 제한 적용
- [ ] 다중 사용자 격리
- [ ] 모바일 반응형 디자인
- [ ] 에러 메시지 표시
- [ ] 진행률 표시
- [ ] 알림 표시

---

**작성**: 2026-02-20  
**Commit**: 1608f6f  
**상태**: ✅ 완료  
**다음**: Phase 3 - 분석 시스템 구현
