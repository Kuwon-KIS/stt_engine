# Database Schema Documentation

## 개요
STT 불완전판매 탐지 시스템의 데이터베이스 스키마 문서입니다.
- **ORM**: SQLAlchemy
- **DB Engine**: SQLite (로컬) / PostgreSQL (서버 가능)
- **스키마 정의**: `app/models/database.py`
- **초기화 스크립트**: `setup_db.py`

## 테이블 구조

### 1. employees (사용자 정보)
직원 정보 및 인증 정보를 관리하는 테이블

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY | 자동 증가 ID |
| emp_id | VARCHAR(10) | UNIQUE, NOT NULL | 사번 (로그인 ID) |
| name | VARCHAR(100) | NOT NULL | 이름 |
| dept | VARCHAR(100) | | 부서명 |
| password | VARCHAR(255) | NOT NULL | bcrypt 해시 비밀번호 |
| is_admin | BOOLEAN | DEFAULT FALSE | 관리자 권한 |
| storage_used | BIGINT | DEFAULT 0 | 사용 중인 저장공간 (bytes) |
| storage_quota | BIGINT | DEFAULT 5GB | 할당된 저장공간 (bytes) |
| created_at | DATETIME | DEFAULT NOW | 생성 시간 |
| last_login | DATETIME | | 마지막 로그인 시간 |

**인덱스**: emp_id (UNIQUE)

---

### 2. file_uploads (파일 업로드 정보)
사용자가 업로드한 파일 메타데이터

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY | 자동 증가 ID |
| emp_id | VARCHAR(10) | FK, NOT NULL, INDEX | 업로드한 사용자 |
| folder_path | VARCHAR(500) | NOT NULL, INDEX | 폴더 경로 |
| filename | VARCHAR(500) | NOT NULL | 파일명 |
| file_size_mb | REAL | | 파일 크기 (MB) |
| uploaded_at | DATETIME | DEFAULT NOW | 업로드 시간 |

**외래키**: emp_id → employees.emp_id
**복합 인덱스**: (emp_id, folder_path)

---

### 3. analysis_jobs (분석 작업)
사용자가 요청한 분석 작업의 메타정보

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY | 자동 증가 ID |
| job_id | VARCHAR(50) | UNIQUE, NOT NULL, INDEX | 작업 고유 ID (job_xxxxx) |
| emp_id | VARCHAR(10) | FK, NOT NULL, INDEX | 요청한 사용자 |
| folder_path | VARCHAR(500) | NOT NULL | 분석 대상 폴더 |
| file_ids | JSON | | 파일 목록 ["file1.wav", "file2.wav"] |
| files_hash | VARCHAR(64) | | 파일 목록 SHA256 해시 (중복 방지) |
| options | JSON | | 분석 옵션 {classification: true, ...} |
| status | VARCHAR(20) | DEFAULT 'pending' | 작업 상태 (pending/processing/completed/failed) |
| created_at | DATETIME | DEFAULT NOW | 작업 생성 시간 |
| started_at | DATETIME | | 분석 시작 시간 |
| completed_at | DATETIME | | 분석 완료 시간 |

**외래키**: emp_id → employees.emp_id
**인덱스**: job_id (UNIQUE), emp_id, (emp_id, folder_path)

---

### 4. analysis_results (분석 결과)
각 파일별 상세 분석 결과

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY | 자동 증가 ID |
| job_id | VARCHAR(50) | FK, NOT NULL, INDEX | 분석 작업 ID |
| file_id | VARCHAR(500) | NOT NULL | 파일명 |
| stt_text | TEXT | | STT 변환 텍스트 |
| stt_metadata | JSON | | STT 메타데이터 {duration, language, backend, confidence} |
| classification_code | VARCHAR(20) | | 분류 코드 (예: "100-100") |
| classification_category | VARCHAR(100) | | 분류 카테고리 (예: "사전판매") |
| classification_confidence | FLOAT | | 분류 신뢰도 (0.0-1.0) |
| **improper_detection_results** | **JSON** | | **부당권유 탐지 결과** (새로 추가) |
| **incomplete_detection_results** | **JSON** | | **불완전판매 탐지 결과** (새로 추가) |
| **status** | **VARCHAR(20)** | **DEFAULT 'pending'** | **분석 상태** (새로 추가) |
| **updated_at** | **DATETIME** | **DEFAULT NOW** | **마지막 업데이트** (새로 추가) |
| created_at | DATETIME | DEFAULT NOW | 생성 시간 |

**외래키**: job_id → analysis_jobs.job_id
**인덱스**: job_id, (job_id, file_id)

#### improper_detection_results / incomplete_detection_results JSON 구조:
```json
{
  "category": "사전판매",
  "detected_yn": "Y",  // "Y" (위반탐지) 또는 "N" (이상없음)
  "detected_sentence": [
    "문장1",
    "문장2"
  ],
  "detected_reason": [
    "단정적판단(부당권유 위배)",
    "온라인가입유도(부당권유 위배)"
  ],
  "detected_keyword": ["보장", "괜찮"]
}
```

---

### 5. analysis_progress (분석 진행 상황)
분석 작업의 실시간 진행 상황 (WebSocket/polling용)

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY | 자동 증가 ID |
| job_id | VARCHAR(50) | UNIQUE, FK, NOT NULL | 분석 작업 ID |
| total_files | INTEGER | DEFAULT 0 | 전체 파일 수 |
| processed_files | INTEGER | DEFAULT 0 | 처리 완료된 파일 수 |
| current_file | VARCHAR(500) | | 현재 처리 중인 파일 |
| status | VARCHAR(20) | DEFAULT 'pending' | 진행 상태 |
| created_at | DATETIME | DEFAULT NOW | 생성 시간 |

**외래키**: job_id → analysis_jobs.job_id

---

## 데이터베이스 초기화

### 로컬 환경
```bash
cd /Users/a114302/Desktop/Github/stt_engine/web_ui
./venv/bin/python setup_db.py
```

### 서버 환경
서버 환경에서도 동일한 스크립트 사용:
```bash
python setup_db.py
```

**주의사항**:
- `setup_db.py`는 SQLAlchemy ORM 모델 (`app/models/database.py`)을 사용
- 로컬과 서버의 스키마가 동일하게 유지됨
- 기존 DB가 있으면 `.backup`으로 백업 후 재생성

---

## 마이그레이션 전략

### 스키마 변경 시 절차
1. `app/models/database.py`에서 ORM 모델 수정
2. 마이그레이션 스크립트 작성 (예: `migrations/add_status_column.py`)
3. 로컬에서 테스트
4. 서버에서 마이그레이션 실행

### 예시: 컬럼 추가
```python
# migrations/add_new_column.py
import sqlite3

conn = sqlite3.connect('app/database.db')
cursor = conn.cursor()

# 컬럼 추가
cursor.execute("ALTER TABLE analysis_results ADD COLUMN new_column VARCHAR(100);")
conn.commit()
conn.close()

print("✅ Migration complete")
```

---

## Dummy 모드 조건

### Dummy 데이터 사용 조건
더미 데이터 (`SAMPLE_DETECTION_RESULTS`)는 **오직 다음 상황에서만 사용**:

1. **STT API 서버 연결 실패**
   - `stt_service.transcribe_local_file()` 실패 시
   - Timeout, ConnectionError, HTTP 4xx/5xx 등

2. **Agent API 연결 실패**
   - `incomplete_elements_check=True`인데 Agent 결과 없음
   - Agent 응답에 `incomplete_elements` 필드 없음

3. **처리 로직**
   ```python
   # 1. Agent 결과 확인
   if include_classification and stt_result.get('incomplete_elements'):
       # Agent 결과 사용
       detection_result = convert_agent_result(...)
   
   # 2. Agent 결과 없으면 더미 데이터 (개발/테스트용)
   else:
       logger.warning("No agent result, using dummy data")
       detection_result = SAMPLE_DETECTION_RESULTS[idx % len(...)]
   ```

### 서버 모드 (프로덕션)
- STT API와 Agent API가 정상 동작하면 **더미 데이터 사용 안 함**
- 실제 API 응답의 `incomplete_elements` 사용
- 로그에 "using dummy data" 경고 메시지 없어야 함

---

## 로컬 vs 서버 차이점

| 구분 | 로컬 (개발) | 서버 (프로덕션) |
|------|------------|----------------|
| DB 경로 | `app/database.db` | `app/database.db` (동일) |
| 스키마 | SQLAlchemy ORM | SQLAlchemy ORM (동일) |
| 초기화 | `setup_db.py` | `setup_db.py` (동일) |
| STT API | http://localhost:8003 | http://stt-api:8003 (Docker) |
| Agent API | 연결 실패 시 더미 | 정상 연결 시 실제 데이터 |
| Dummy 모드 | 자주 사용 (API 없음) | 거의 사용 안 함 (API 정상) |

---

## 체크리스트

### 로컬 → 서버 배포 전 확인사항
- [ ] `setup_db.py`가 최신 ORM 모델 사용하는지 확인
- [ ] `app/models/database.py`의 모든 컬럼이 `setup_db.py`에 반영되었는지 확인
- [ ] 마이그레이션 스크립트 준비 (기존 DB가 있는 경우)
- [ ] 더미 데이터 사용 조건이 "API 연결 실패 시"로 제한되어 있는지 확인
- [ ] 로그에서 "using dummy data" 경고가 프로덕션에서 발생하지 않는지 확인

### 서버 배포 후 확인사항
- [ ] DB 테이블이 모두 생성되었는지 확인 (`PRAGMA table_info`)
- [ ] 분석 실행 시 Agent 결과가 제대로 저장되는지 확인
- [ ] 더미 데이터가 사용되지 않는지 로그 확인

---

## 문제 해결

### 스키마 불일치 (Missing Columns)
```bash
# 현재 스키마 확인
sqlite3 app/database.db "PRAGMA table_info(analysis_results);"

# 재생성 (데이터 손실 주의!)
python setup_db.py
```

### 마이그레이션 필요
```bash
# 백업
cp app/database.db app/database.db.backup

# 마이그레이션 실행
python migrations/your_migration.py

# 확인
sqlite3 app/database.db "PRAGMA table_info(your_table);"
```

---

## 추가 정보
- **ORM 모델**: `app/models/database.py`
- **DB 유틸리티**: `app/utils/db.py`
- **초기화 스크립트**: `setup_db.py`
- **재생성 스크립트**: `recreate_db.py` (개발 전용)
