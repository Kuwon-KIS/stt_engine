# STT Web UI - 설정 및 실행 가이드

## 📦 프로젝트 구조

```
stt_engine/
├── api_server.py                 ✅ STT Engine API (기존)
├── stt_engine.py                 ✅ WhisperSTT 모델 (기존)
├── main.py                       ✅ 메인 진입점 (기존)
├── build/                        📦 빌드 산출물
│   ├── models/                   ✅ 모델 파일들
│   └── output/                   📁 기타 출력
├── 
├── web_ui/                       🆕 웹 UI 서버 (신규)
│   ├── main.py                   # FastAPI 메인 앱
│   ├── config.py                 # 환경 설정
│   ├── requirements.txt           # Python 의존성
│   ├── run.sh                    # 실행 스크립트
│   │
│   ├── services/                 # 비즈니스 로직
│   │   ├── stt_service.py        # STT API 통신
│   │   ├── file_service.py       # 파일 관리
│   │   └── batch_service.py      # 배치 처리
│   │
│   ├── models/
│   │   └── schemas.py            # Pydantic 스키마
│   │
│   ├── static/
│   │   ├── css/style.css         # 스타일시트
│   │   └── js/main.js            # 프론트엔드 로직
│   │
│   ├── templates/
│   │   └── index.html            # HTML UI
│   │
│   ├── data/
│   │   ├── uploads/              # 업로드 파일
│   │   ├── results/              # 처리 결과
│   │   ├── batch_input/          # 배치 입력
│   │   └── logs/                 # 로그
│   │
│   ├── docker/
│   │   ├── Dockerfile.web_ui     # 웹 UI 컨테이너
│   │   └── docker-compose.yml    # 통합 Compose
│   │
│   └── README.md                 # 웹 UI 사용 설명서
│
├── WEB_UI_ARCHITECTURE.md         # 아키텍처 문서
├── SETUP_WEB_UI.md                # 이 파일 (설정 가이드)
└── [기타 파일...]
```

---

## 🚀 빠른 시작 (3가지 방법)

### 방법 1: 로컬 개발 환경 (추천)

```bash
# 1단계: 웹 UI 디렉토리로 이동
cd /Users/a113211/workspace/stt_engine/web_ui

# 2단계: 의존성 설치
pip install -r requirements.txt

# 3단계: 환경 변수 설정 (선택)
export STT_API_URL=http://localhost:8003
export WEB_PORT=8001

# 4단계: 웹 UI 서버 시작
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**접속:**
```
http://localhost:8001
```

**특징:**
- 자동 재로드 (--reload)
- 디버깅 용이
- 로그 실시간 확인

---

### 방법 2: Docker Compose (권장 - 배포용)

#### 2-1. STT API와 Web UI 함께 실행

```bash
# 웹 UI 디렉토리의 Docker Compose 사용
cd /Users/a113211/workspace/stt_engine/web_ui/docker

docker-compose -f docker-compose.yml up
```

**또는 백그라운드:**
```bash
docker-compose -f docker-compose.yml up -d
```

**종료:**
```bash
docker-compose -f docker-compose.yml down
```

**상태 확인:**
```bash
docker-compose -f docker-compose.yml ps
```

**접속:**
- 웹 UI: http://localhost:8001
- STT API: http://localhost:8003

**특징:**
- STT API와 Web UI 자동 통합
- 독립적인 환경 (컨테이너)
- 쉬운 배포

#### 2-2. 로그 확인

```bash
# 모든 서비스 로그
docker-compose -f docker-compose.yml logs -f

# 특정 서비스만
docker-compose -f docker-compose.yml logs -f stt-api
docker-compose -f docker-compose.yml logs -f web-ui
```

---

### 방법 3: 개별 Docker (고급)

#### 3-1. Web UI만 Docker로 실행 (STT API는 외부)

```bash
cd /Users/a113211/workspace/stt_engine

# 이미지 빌드
docker build -f web_ui/docker/Dockerfile.web_ui -t stt-web-ui .

# 컨테이너 실행
docker run -p 8001:8001 \
  -e STT_API_URL=http://host.docker.internal:8003 \
  -v $(pwd)/web_ui/data:/app/data \
  -v $(pwd)/web_ui/logs:/app/logs \
  stt-web-ui
```

**Mac에서 호스트 접근:**
```bash
-e STT_API_URL=http://host.docker.internal:8003
```

**Linux에서 호스트 접근:**
```bash
--network host
-e STT_API_URL=http://localhost:8003
```

---

## ⚙️ 환경 설정

### 환경 변수 설정

#### 방법 1: 쉘 환경변수

```bash
# 임시 (현재 세션만)
export WEB_PORT=8001
export STT_API_URL=http://localhost:8003

# 또는 python 실행 전 한 줄로
STT_API_URL=http://localhost:8003 python -m uvicorn main:app
```

#### 방법 2: .env 파일 (선택)

```bash
# web_ui/.env 파일 생성
cat > web_ui/.env << EOF
WEB_HOST=0.0.0.0
WEB_PORT=8001
STT_API_URL=http://localhost:8003
STT_API_TIMEOUT=300
MAX_UPLOAD_SIZE_MB=100
BATCH_PARALLEL_COUNT=2
LOG_LEVEL=INFO
DEFAULT_LANGUAGE=ko
EOF
```

**python-dotenv로 로드:**
```python
from dotenv import load_dotenv
load_dotenv()
```

#### 방법 3: Docker에서 환경변수

```bash
# docker-compose.yml
environment:
  - WEB_PORT=8001
  - STT_API_URL=http://stt-api:8003
  - LOG_LEVEL=INFO
```

---

## 📊 환경별 설정 예시

### 개발 환경 (로컬)

```bash
export LOG_LEVEL=DEBUG
export WEB_PORT=8001
export STT_API_URL=http://localhost:8003
export MAX_UPLOAD_SIZE_MB=100
export BATCH_PARALLEL_COUNT=1  # 단일 처리
```

### 테스트 환경 (Docker Compose)

```yaml
# docker-compose.yml
environment:
  - LOG_LEVEL=INFO
  - WEB_PORT=8001
  - STT_API_URL=http://stt-api:8003
  - BATCH_PARALLEL_COUNT=2
```

### 프로덕션 환경

```bash
# 보안 강화
export LOG_LEVEL=WARNING
export MAX_UPLOAD_SIZE_MB=50  # 더 작게
export BATCH_PARALLEL_COUNT=4  # CPU 코어 수
export CORS_ORIGINS=https://yourdomain.com  # 특정 도메인만
```

---

## 🔄 서비스 시작 순서

### 시나리오: 로컬 개발 (2개 터미널)

**터미널 1 - STT API:**
```bash
cd /Users/a113211/workspace/stt_engine
python api_server.py
# STT API 시작: http://localhost:8003
```

**터미널 2 - Web UI:**
```bash
cd /Users/a113211/workspace/stt_engine/web_ui
python -m uvicorn main:app --port 8001 --reload
# Web UI 시작: http://localhost:8001
```

### 시나리오: Docker Compose (한 번에)

```bash
cd /Users/a113211/workspace/stt_engine/web_ui/docker
docker-compose up
# 자동으로 STT API (8003) + Web UI (8001) 시작
```

---

## 🧪 기본 테스트

### 1. 헬스 체크

```bash
# Web UI
curl http://localhost:8001/health

# STT API
curl http://localhost:8003/health
```

**예상 응답:**
```json
{
  "status": "healthy",
  "stt_api": "ok"
}
```

### 2. 파일 업로드 테스트

```bash
# 테스트 파일 준비
curl -X POST http://localhost:8001/api/upload/ \
  -F "file=@/Users/a113211/workspace/stt_engine/audio/samples/test_ko_1min.wav"
```

**예상 응답:**
```json
{
  "success": true,
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "test_ko_1min.wav",
  "file_size_mb": 15.5,
  "upload_time_sec": 2.3
}
```

### 3. STT 처리 테스트

```bash
curl -X POST http://localhost:8001/api/transcribe/ \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "550e8400-e29b-41d4-a716-446655440000",
    "language": "ko"
  }'
```

### 4. 배치 파일 목록

```bash
curl http://localhost:8001/api/batch/files
```

---

## 📁 데이터 디렉토리 구조

```
web_ui/data/
├── uploads/           # 업로드된 파일
│   ├── 550e8400-....wav
│   └── a1b2c3d4-....wav
│
├── results/           # 처리 결과 (자동 저장)
│   ├── 550e8400-....txt
│   └── a1b2c3d4-....txt
│
├── batch_input/       # 배치 처리할 파일 입력
│   ├── file1.wav
│   ├── file2.wav
│   └── file3.wav
│
└── db.sqlite          # 데이터베이스 (선택)
```

**중요:** `batch_input` 디렉토리에 파일을 넣고 "파일 목록 로드" 버튼을 클릭하면 자동으로 목록이 표시됩니다.

---

## 🔍 문제 해결

### 문제 1: STT API 연결 실패

```
❌ STT API 연결 실패
```

**원인:** STT API 서버가 실행 중이 아니거나 주소가 잘못됨

**해결:**

```bash
# 1. STT API 실행 확인
curl http://localhost:8003/health

# 2. 만약 실행 안 됨:
cd /Users/a113211/workspace/stt_engine
python api_server.py

# 3. 환경변수 재확인
echo $STT_API_URL  # http://localhost:8003 확인

# 4. Docker Compose 사용 시:
docker-compose -f web_ui/docker/docker-compose.yml logs stt-api
```

### 문제 2: 포트 이미 사용 중

```
Address already in use
```

**해결:**

```bash
# 포트 확인
lsof -i :8001
lsof -i :8003

# 기존 프로세스 종료
kill -9 <PID>

# 또는 다른 포트 사용
export WEB_PORT=8002
python -m uvicorn main:app --port 8002
```

### 문제 3: 파일 업로드 실패

**원인:** 파일 크기 초과 또는 형식 오류

**확인:**

```bash
# 파일 크기 확인 (MB 단위)
du -m /path/to/file

# 지원 형식 확인: .wav, .mp3, .m4a, .flac, .ogg
file test.wav
```

### 문제 4: 배치 파일 목록에 아무것도 없음

**원인:** batch_input 디렉토리에 파일이 없거나 확장자 필터가 맞지 않음

**확인:**

```bash
# 파일 확인
ls -la web_ui/data/batch_input/

# 확장자 확인
file web_ui/data/batch_input/*

# 파일 추가 (테스트용)
cp audio/samples/test_ko_1min.wav web_ui/data/batch_input/
```

### 문제 5: 로그 확인

```bash
# 로컬 실행 시
tail -f web_ui/logs/web_ui.log

# Docker Compose 시
docker-compose -f web_ui/docker/docker-compose.yml logs -f web-ui
```

---

## 🚀 프로덕션 배포

### EC2에 배포 (Docker Compose)

```bash
# 1. 저장소 클론
git clone <repo> /opt/stt_engine
cd /opt/stt_engine

# 2. 환경 설정
cat > web_ui/docker/.env << EOF
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE_MB=100
BATCH_PARALLEL_COUNT=4
EOF

# 3. Docker Compose 실행
cd web_ui/docker
docker-compose up -d

# 4. 상태 확인
docker-compose ps
docker-compose logs -f
```

### Nginx 리버스 프록시 (선택)

```nginx
server {
    listen 80;
    server_name stt.example.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📈 성능 최적화

### 메모리 설정

```bash
# 병렬 처리 수 조정 (CPU 코어 수에 따라)
export BATCH_PARALLEL_COUNT=4  # CPU 4코어 권장

# Docker Compose에서:
# memory_limit 설정 (선택)
```

### 타임아웃 조정

```bash
# 큰 파일 처리 시
export STT_API_TIMEOUT=600  # 10분
```

---

## 📚 다음 단계

1. **[웹 UI 사용 설명서](web_ui/README.md)** - 사용자 가이드
2. **[아키텍처 문서](WEB_UI_ARCHITECTURE.md)** - 시스템 설계
3. **api_server.py** - STT Engine API 정보
4. **GitHub** - 코드 변경사항 확인

---

## 💡 팁

### 개발 중 자동 재로드
```bash
# --reload 플래그 사용
python -m uvicorn main:app --reload
```

### 데이터베이스 초기화 (필요시)
```bash
rm web_ui/data/db.sqlite
```

### 로그 레벨 변경
```bash
export LOG_LEVEL=DEBUG
python -m uvicorn main:app
```

### CORS 설정 (프론트엔드가 다른 포트에 있을 때)
```bash
export CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

---

## ✅ 체크리스트

배포 전 확인사항:

- [ ] STT API 실행 중 확인
- [ ] Web UI 실행 중 확인
- [ ] 헬스 체크 성공
- [ ] 파일 업로드 테스트 성공
- [ ] STT 처리 테스트 성공
- [ ] 배치 파일 목록 로드 성공
- [ ] 결과 다운로드 확인
- [ ] 로그 저장 확인

---

## 📞 지원

문제가 발생하면:

1. **로그 확인:**
   ```bash
   tail -f web_ui/logs/web_ui.log
   ```

2. **STT API 상태 확인:**
   ```bash
   curl http://localhost:8003/health
   ```

3. **GitHub 이슈** - 문제 보고

---

마지막 업데이트: 2026-02-11
작성자: STT Engine Team
