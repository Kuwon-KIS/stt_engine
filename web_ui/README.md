# STT Web UI

FastAPI 기반 Speech-to-Text (STT) 웹 인터페이스입니다. 음성 파일을 업로드하여 텍스트로 변환하거나, 서버 디렉토리의 파일들을 배치 처리할 수 있습니다.

## 🚀 빠른 시작

### Option A: 로컬에서 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정 (선택)
export STT_API_URL=http://localhost:8003
export WEB_PORT=8001

# 서버 시작
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

브라우저에서 `http://localhost:8001` 접속

### Option B: Docker Compose로 실행 (권장)

```bash
# 웹 UI + STT API 함께 시작
docker-compose -f docker/docker-compose.yml up

# 또는 백그라운드 실행
docker-compose -f docker/docker-compose.yml up -d
```

접속 주소:
- 웹 UI: http://localhost:8001
- STT API: http://localhost:8003

### Option C: 개별 Docker 실행

```bash
# 웹 UI만 실행 (STT API는 외부 서버 연결)
docker build -f docker/Dockerfile.web_ui -t stt-web-ui .
docker run -p 8001:8001 \
  -e STT_API_URL=http://your-api-server:8003 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  stt-web-ui
```

---

## 📋 주요 기능

### 1. 파일 업로드 & STT 처리

- 드래그 & 드롭 지원
- 지원 형식: `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`
- 최대 크기: 100MB
- 언어 선택: 한국어, 영어, 일본어, 중국어

**처리 흐름:**
```
파일 선택 → 업로드 → STT 변환 → 결과 표시 → 다운로드
```

### 2. 배치 처리

여러 파일을 자동으로 일괄 처리합니다.

**설정:**
- 입력 디렉토리: `./data/batch_input`
- 파일 확장자 필터
- 언어 선택
- 병렬 처리 수 (1-8)

**모니터링:**
- 실시간 진행 상황 표시
- 파일별 처리 상태
- 처리 시간 및 성공/실패 통계
- 예상 남은 시간

### 3. 결과 관리

- 처리 결과 저장 (자동)
- 다운로드: TXT, JSON 포맷
- 결과 조회 및 복사
- 메타데이터: 지속시간, 처리시간, 백엔드 정보

---

## 🏗️ 디렉토리 구조

```
web_ui/
├── main.py                 # FastAPI 메인 앱
├── config.py              # 설정
├── requirements.txt       # Python 의존성
├── run.sh                 # 실행 스크립트
│
├── routes/                # API 라우트 (선택)
├── services/              # 비즈니스 로직
│   ├── stt_service.py     # STT API 통신
│   ├── file_service.py    # 파일 관리
│   └── batch_service.py   # 배치 처리
│
├── models/
│   └── schemas.py         # Pydantic 모델
│
├── utils/
│   └── logger.py          # 로깅 설정
│
├── static/
│   ├── css/
│   │   └── style.css      # 스타일시트
│   └── js/
│       └── main.js        # 프론트엔드 로직
│
├── templates/
│   └── index.html         # HTML 템플릿
│
├── data/
│   ├── uploads/           # 업로드 파일
│   ├── results/           # 처리 결과
│   ├── batch_input/       # 배치 입력
│   └── db.sqlite          # SQLite DB (선택)
│
├── docker/
│   ├── Dockerfile.web_ui  # Docker 이미지
│   └── docker-compose.yml # Docker Compose
│
└── logs/                  # 로그 파일
```

---

## 🔌 API 명세

### 기본 요청/응답

#### 1. 파일 업로드
```
POST /api/upload/
Content-Type: multipart/form-data

파라미터:
  - file: 오디오 파일

응답:
{
  "success": true,
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "audio.wav",
  "file_size_mb": 15.5,
  "upload_time_sec": 2.3
}
```

#### 2. STT 처리
```
POST /api/transcribe/
Content-Type: application/json

Body:
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "language": "ko"
}

응답:
{
  "success": true,
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "audio.wav",
  "text": "안녕하세요. 이것은 변환된 텍스트입니다.",
  "language": "ko",
  "duration_sec": 45.2,
  "processing_time_sec": 15.8,
  "backend": "faster-whisper"
}
```

#### 3. 배치 파일 목록
```
GET /api/batch/files?extension=.wav

응답:
{
  "total": 5,
  "files": [
    {
      "name": "file1.wav",
      "path": "./data/batch_input/file1.wav",
      "size_mb": 10.5,
      "modified": "2026-02-11T10:30:00",
      "status": "pending"
    }
  ]
}
```

#### 4. 배치 처리 시작
```
POST /api/batch/start/
Content-Type: application/json

Body:
{
  "path": "./data/batch_input",
  "extension": ".wav",
  "language": "ko",
  "parallel_count": 2
}

응답:
{
  "batch_id": "batch-550e8400-e29b-41d4",
  "total_files": 5,
  "status": "started"
}
```

#### 5. 배치 진행 상황
```
GET /api/batch/progress/{batch_id}

응답:
{
  "batch_id": "batch-550e8400-e29b-41d4",
  "total": 5,
  "completed": 2,
  "failed": 0,
  "in_progress": 1,
  "estimated_remaining_sec": 120,
  "files": [
    {
      "name": "file1.wav",
      "status": "done",
      "processing_time_sec": 15.5
    }
  ]
}
```

#### 6. 결과 조회
```
GET /api/results/{file_id}

응답:
{
  "success": true,
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "변환된 텍스트..."
}
```

#### 7. 결과 다운로드
```
GET /api/results/{file_id}/export?format=txt|json

응답: 파일 (텍스트 또는 JSON)
```

#### 8. 헬스 체크
```
GET /health

응답:
{
  "status": "healthy",
  "stt_api": "ok"
}
```

---

## ⚙️ 환경 변수

```bash
# 웹 서버
WEB_HOST=0.0.0.0           # 바인드 주소
WEB_PORT=8001              # 포트

# STT API
STT_API_URL=http://localhost:8003  # STT API 주소
STT_API_TIMEOUT=300        # 타임아웃 (초)

# 파일 설정
MAX_UPLOAD_SIZE_MB=100     # 최대 업로드 크기
ALLOWED_EXTENSIONS=.wav,.mp3,.m4a,.flac,.ogg

# 배치 처리
BATCH_PARALLEL_COUNT=2     # 동시 처리 수
BATCH_CHECK_INTERVAL=5     # 상태 확인 간격 (초)

# 기타
LOG_LEVEL=INFO             # 로그 레벨
DEFAULT_LANGUAGE=ko        # 기본 언어
CORS_ORIGINS=*             # CORS 설정
```

---

## 🔧 troubleshooting

### 문제: STT API 연결 실패

```
❌ STT API 연결 실패
```

**해결:**
1. STT API 서버가 실행 중인지 확인
2. `STT_API_URL` 환경변수 확인
3. 네트워크 연결 확인

```bash
# STT API 헬스 체크
curl http://localhost:8003/health

# Docker Compose 사용 시, 서비스 상태 확인
docker-compose -f docker/docker-compose.yml ps
```

### 문제: 파일 업로드 실패

**해결:**
- 파일 크기 확인 (최대 100MB)
- 파일 형식 확인 (.wav, .mp3 등)
- 디스크 용량 확인

### 문제: 배치 처리 진행 안 됨

**해결:**
1. `./data/batch_input` 디렉토리에 파일 확인
2. 파일 확장자 필터 확인
3. 로그 확인

```bash
# 로그 확인
tail -f logs/web_ui.log
```

---

## 📊 성능 최적화

### 배치 처리 병렬화

```python
# docker-compose.yml에서 조정
environment:
  BATCH_PARALLEL_COUNT=4  # CPU 코어 수에 따라
```

### 파일 크기 제한

```python
# config.py
MAX_UPLOAD_SIZE_MB = 100  # 필요시 조정
```

### 메모리 사용량

- 각 병렬 처리: ~2GB (faster-whisper)
- 4개 병렬: 최소 8GB RAM 필요

---

## 🔒 보안

1. **파일 검증**
   - 확장자 화이트리스트
   - 크기 제한
   - MIME type 검증

2. **경로 보안**
   - 배치 경로는 프리셋된 디렉토리만 사용
   - 상위 디렉토리 접근 방지

3. **Rate Limiting**
   - 동시 업로드 제한
   - 배치 작업 수 제한

---

## 🧪 테스트

### 단위 테스트 (예제)

```bash
# 서버 헬스 체크
curl http://localhost:8001/health

# 파일 업로드 테스트
curl -X POST http://localhost:8001/api/upload/ \
  -F "file=@test_audio.wav"

# STT 처리 테스트
curl -X POST http://localhost:8001/api/transcribe/ \
  -H "Content-Type: application/json" \
  -d '{"file_id": "test-id", "language": "ko"}'
```

---

## 📚 참고

- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [STT Engine API](../api_server.py)
- [아키텍처 디자인](../WEB_UI_ARCHITECTURE.md)

---

## 📝 라이선스

MIT License

---

## 💬 피드백

버그 리포트 및 기능 요청은 이슈로 등록해주세요.
