# Phase 2-1 상세 계획: 파일 업로드 & 폴더 관리

> 📌 **참고 문서**
> - [01_WEB_UI_REFACTOR_PLAN.md](01_WEB_UI_REFACTOR_PLAN.md) - 전체 기술 명세
> - [PHASE_1_IMPLEMENTATION_COMPLETE.md](PHASE_1_IMPLEMENTATION_COMPLETE.md) - Phase 1 완료 보고서

---

## 📋 Phase 2 개요

### 목표
- ✅ 파일 업로드 시스템 구현
- ✅ 폴더 구조 자동 관리 (emp_id/date or custom)
- ✅ 파일 메타정보 DB 저장
- ✅ 파일 목록 조회 및 폴더 관리 UI

### 범위
- **파일 저장**: `data/uploads/{emp_id}/{folder_path}/{filename}`
- **자동 폴더**: 날짜 (YYYY-MM-DD) 또는 커스텀 폴더명
- **DB**: file_uploads 테이블에 메타정보 저장
- **API**: 4개 엔드포인트 (/upload, /list, /folders, /delete)
- **UI**: upload.html 페이지 작성

---

## 🔄 파일 저장 구조

### 현재 구조 (기존)
```
data/
├── uploads/
├── results/
├── batch_input/
└── db.sqlite
```

### Phase 2 구조 (개선)
```
data/uploads/
├── 10001/                       # 사번 (emp_id)
│   ├── 2026-02-20/             # 날짜 폴더 (자동)
│   │   ├── call_001.wav
│   │   ├── call_002.wav
│   │   └── metadata.json
│   ├── 부당권유_검토/            # 커스텀 폴더
│   │   ├── sample_1.wav
│   │   └── metadata.json
│   └── 불완전판매_사례/
│       └── example.wav
└── 10002/                       # 다른 사용자
    └── 2026-02-20/
        └── ...
```

### 특징
1. **사번별 격리**: 다른 사용자 파일 접근 불가
2. **자동 폴더**: 업로드 시 자동으로 당일 폴더 생성
3. **커스텀 폴더**: 사용자가 다른 폴더명 지정 가능
4. **메타정보**: 각 폴더에 metadata.json 저장

---

## 📊 DB 스키마 확장

### 기존 테이블 (Phase 1)
- `employees` - 직원 정보
- `analysis_jobs` - 분석 작업
- `analysis_results` - 분석 결과
- `analysis_progress` - 진행 상황

### Phase 2 추가
- `file_uploads` - **파일 메타정보** (이미 정의됨)

**file_uploads 상세:**
```sql
CREATE TABLE file_uploads (
    id INTEGER PRIMARY KEY,
    emp_id VARCHAR(10) NOT NULL,        -- 업로드 사용자
    folder_path VARCHAR(500) NOT NULL,   -- 상위 폴더 (2026-02-20)
    filename VARCHAR(500) NOT NULL,      -- 파일명
    file_size_mb FLOAT,                  -- 파일 크기
    uploaded_at TIMESTAMP,               -- 업로드 시간
    FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
);
```

---

## 🔧 구현할 파일 (10개)

### Backend (6개)
| 파일 | 내용 |
|------|------|
| `app/services/file_service.py` | 파일 업로드/삭제 로직 |
| `app/routes/files.py` | 파일 관리 API 엔드포인트 |
| `app/utils/file_utils.py` | 파일 경로, 유효성 검사 |
| `app/schemas/file_schemas.py` | Pydantic 모델 (요청/응답) |
| 수정: `main.py` | 파일 라우터 등록 |
| 수정: `config.py` | 파일 관련 상수 추가 |

### Frontend (3개)
| 파일 | 내용 |
|------|------|
| `templates/upload.html` | 파일 업로드/폴더 관리 페이지 |
| `static/js/upload.js` | 업로드 기능 JavaScript |
| 수정: `static/js/common.js` | 파일 관련 유틸리티 추가 |

### 문서 (1개)
| 파일 | 내용 |
|------|------|
| `04_WEB_UI_PHASE_2_PLAN.md` | Phase 2 상세 계획 (이 파일) |

---

## 📝 세부 구현 계획

### 1. file_service.py 구현
```python
class FileService:
    @staticmethod
    def create_folder_path(emp_id: str, folder_name: str = None) -> str
    # 폴더 경로 생성 (folder_name 없으면 오늘 날짜 사용)
    
    @staticmethod
    def upload_file(emp_id: str, file: UploadFile, folder_name: str = None) -> dict
    # 파일 업로드 및 DB 기록
    
    @staticmethod
    def list_files(emp_id: str, folder_path: str = None) -> list
    # 파일 목록 조회 (특정 폴더 또는 전체)
    
    @staticmethod
    def list_folders(emp_id: str) -> list
    # 폴더 목록 조회
    
    @staticmethod
    def delete_file(emp_id: str, filename: str) -> bool
    # 파일 삭제
```

### 2. files.py 라우터
```
GET    /api/files/folders        - 폴더 목록 조회
GET    /api/files/list           - 파일 목록 조회 (folder 파라미터)
POST   /api/files/upload         - 파일 업로드
DELETE /api/files/{filename}     - 파일 삭제
```

### 3. upload.html (주요 요소)
```html
<!-- 로그인 확인 메시지 -->
<div id="userInfo">김철수님 (영업팀)</div>

<!-- 폴더 선택 -->
<div id="folderSelector">
  <select id="selectedFolder">
    <option>날짜별 (자동)</option>
    <option>부당권유_검토</option>
    <option>불완전판매_사례</option>
    <option>+ 새 폴더 만들기</option>
  </select>
</div>

<!-- 파일 업로드 -->
<div id="uploadArea" (drag&drop)>
  <input type="file" multiple accept=".wav,.mp3,.m4a">
  <p>음성 파일을 드래그 & 드롭하세요</p>
</div>

<!-- 업로드 진행 바 -->
<div id="uploadProgress"></div>

<!-- 파일 목록 -->
<div id="fileList">
  <table>
    <tr>
      <th>파일명</th>
      <th>크기</th>
      <th>업로드 시간</th>
      <th>작업</th>
    </tr>
  </table>
</div>

<!-- 분석 시작 버튼 (Phase 3) -->
<button id="startAnalysisBtn">분석 시작</button>
```

### 4. Pydantic 모델 (file_schemas.py)
```python
class FileUploadRequest(BaseModel):
    folder_name: Optional[str] = None
    # None이면 자동으로 오늘 날짜 사용

class FileUploadResponse(BaseModel):
    success: bool
    filename: str
    file_size_mb: float
    folder_path: str
    uploaded_at: datetime
    message: str

class FileListResponse(BaseModel):
    folder_path: str
    files: List[FileInfo]
    total_size_mb: float

class FileInfo(BaseModel):
    filename: str
    file_size_mb: float
    uploaded_at: datetime

class FolderListResponse(BaseModel):
    folders: List[str]
    # ["2026-02-20", "부당권유_검토", "불완전판매_사례"]
```

---

## 🎯 API 엔드포인트 상세

### 1. GET /api/files/folders
**목적**: 현재 사용자의 폴더 목록 조회

**요청**:
```
GET /api/files/folders HTTP/1.1
Cookie: session=...
```

**응답 (200)**:
```json
{
  "folders": [
    "2026-02-20",
    "부당권유_검토",
    "불완전판매_사례"
  ]
}
```

---

### 2. GET /api/files/list
**목적**: 특정 폴더의 파일 목록 조회

**요청**:
```
GET /api/files/list?folder_path=2026-02-20 HTTP/1.1
Cookie: session=...
```

또는 전체 파일 조회:
```
GET /api/files/list HTTP/1.1
```

**응답 (200)**:
```json
{
  "folder_path": "2026-02-20",
  "files": [
    {
      "filename": "call_001.wav",
      "file_size_mb": 2.5,
      "uploaded_at": "2026-02-20T14:30:00"
    }
  ],
  "total_size_mb": 2.5
}
```

---

### 3. POST /api/files/upload
**목적**: 파일 업로드

**요청**:
```
POST /api/files/upload HTTP/1.1
Content-Type: multipart/form-data
Cookie: session=...

file=@call_001.wav&folder_name=2026-02-20
```

**응답 (201)**:
```json
{
  "success": true,
  "filename": "call_001.wav",
  "file_size_mb": 2.5,
  "folder_path": "2026-02-20",
  "uploaded_at": "2026-02-20T14:30:00",
  "message": "파일 업로드 성공"
}
```

**에러 (400)**:
```json
{
  "detail": "파일 크기 초과 (최대 500MB)"
}
```

---

### 4. DELETE /api/files/{filename}
**목적**: 파일 삭제

**요청**:
```
DELETE /api/files/call_001.wav?folder_path=2026-02-20 HTTP/1.1
Cookie: session=...
```

**응답 (200)**:
```json
{
  "success": true,
  "message": "파일 삭제됨"
}
```

---

## 📋 구현 체크리스트

### Backend 구현
- [ ] file_service.py 작성 (5개 메서드)
- [ ] files.py 라우터 작성 (4개 엔드포인트)
- [ ] file_utils.py 유틸리티 작성
- [ ] file_schemas.py Pydantic 모델
- [ ] main.py 파일 라우터 등록
- [ ] config.py 파일 관련 상수 추가

### Frontend 구현
- [ ] upload.html 작성 (주요 UI)
- [ ] upload.js 작성 (업로드 로직)
- [ ] common.js 확장 (파일 관련 유틸)

### 테스트
- [ ] 파일 업로드 테스트
- [ ] 폴더 목록 조회 테스트
- [ ] 파일 목록 조회 테스트
- [ ] 파일 삭제 테스트
- [ ] 에러 처리 테스트

### 문서
- [ ] Phase 2 계획 문서 작성
- [ ] API 문서 작성
- [ ] 체크리스트 작성

---

## 🔐 보안 고려사항

### 1. 경로 traversal 방지
```python
# ❌ 위험
file_path = f"data/uploads/{emp_id}/{user_input}"

# ✅ 안전
import os
safe_path = os.path.abspath(os.path.join(base_path, emp_id, folder_path))
if not safe_path.startswith(base_path):
    raise ValueError("Invalid path")
```

### 2. 파일 크기 제한
- 최대 파일 크기: 500MB (config.py에서 설정 가능)
- 총 저장 용량: 무제한 (나중에 추가 가능)

### 3. 파일 확장자 검증
- 허용 확장자: .wav, .mp3, .m4a, .ogg, .flac
- MIME 타입 검증 추가 권장

### 4. 사용자 격리
- 모든 파일 접근 시 세션의 emp_id와 검증
- 다른 사용자 파일 접근 불가

---

## 📊 예상 소요 시간

| 항목 | 시간 |
|------|------|
| file_service.py | 1.5시간 |
| files.py (라우터) | 1시간 |
| file_utils.py | 45분 |
| file_schemas.py | 30분 |
| upload.html | 1.5시간 |
| upload.js | 1.5시간 |
| 테스트 및 버그 수정 | 1.5시간 |
| 문서 작성 | 45분 |
| **합계** | **10시간** |

**예상 기간**: 2.5일 (일일 4시간 기준)

---

## 🚀 다음 단계

### Phase 2 구현 순서
1. `file_service.py` - 파일 처리 로직
2. `file_utils.py` - 경로 검증 등
3. `file_schemas.py` - Pydantic 모델
4. `files.py` - API 엔드포인트
5. `main.py` - 라우터 등록
6. `upload.html` - UI
7. `upload.js` - 클라이언트 로직
8. 테스트 및 문서화

### Phase 3 준비 (파일 업로드 후 필요)
- 분석 작업 생성
- 비동기 처리 (STT, 분류, 탐지)
- 진행 상황 실시간 추적

---

## 📌 중요 노트

1. **파일 메타정보**: 각 폴더에 metadata.json으로도 저장 (나중에 빠른 조회용)
2. **자동 폴더 생성**: 오늘 날짜 폴더가 없으면 자동 생성
3. **커스텀 폴더**: 사용자가 원하는 폴더명으로 생성 가능
4. **파일 권한**: 모든 파일은 업로드 사용자(emp_id)만 접근 가능
5. **DELETE 확인**: 파일 삭제 전 사용자 확인 필수

---

**다음 문서**: Phase 2 구현 체크리스트 (04_WEB_UI_PHASE_2_CHECKLIST.md)
