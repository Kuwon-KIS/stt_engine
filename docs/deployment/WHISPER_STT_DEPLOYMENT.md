# Whisper STT API - 배포 가이드

Whisper 모델을 사용한 음성 인식(STT) API 서버를 배포하는 가이드입니다.

## 🔍 faster-whisper와 Whisper 모델의 관계

### 개념 정리

**Whisper Large Turbo v3** (모델)
- OpenAI에서 훈련한 AI 모델 파일
- 약 1.5B 파라미터 (2.7GB 용량)
- `models/openai_whisper-large-v3-turbo/` 디렉토리에 저장

**faster-whisper** (추론 엔진)
- Whisper 모델을 더 빠르게 실행하는 최적화 엔진
- CTranslate2 + ONNX Runtime 기반
- **모델 자동 최적화**: Whisper 모델을 ONNX 형식으로 변환하여 실행

### 실행 구조
```
음성 입력
   ↓
faster-whisper 엔진
   ↓
Whisper Large Turbo v3 모델 (자동 최적화)
   ↓
텍스트 출력
```

### 성능 비교

| 지표 | 기존 OpenAI Whisper | faster-whisper |
|------|---|---|
| 추론 속도 (10초 음성) | ~15-30초 | ~5-7초 (3-4배 빠름) |
| VRAM 사용량 | 4-6GB | 2.5-3.5GB |
| 정확도 | 100% | 100% (동일) |
| 배포 환경 | 제약 있음 | RHEL 8.9에 최적화 |

### 배포 시 자동 최적화
- 첫 실행 시 Whisper 모델이 자동으로 ONNX 형식으로 변환됨
- 변환된 모델은 캐시되어 다음 실행은 더 빠름
- 추가 모델 다운로드 불필요

## 📋 시스템 요구사항

### 필수 사항
- **OS**: RHEL 8.9 (또는 호환 Linux)
- **Python**: 3.11+
- **CUDA**: 12.4+ (GPU 사용 시)
- **Docker & Docker Compose**: 최신 버전
- **메모리**: 최소 8GB RAM, 권장 16GB+
- **VRAM**: 최소 4GB (GPU 메모리)

### 이미 설치된 서비스
- ✅ **vLLM 서버**: 별도로 실행 중 (텍스트 처리 담당)
- ✅ **텍스트 처리**: vLLM에서 담당

## 🚀 배포 방법

### 1단계: 파일 준비

#### 1-1. 배포 패키지 전송
```bash
# macOS에서 Linux 서버로 전송
scp -r deployment_package/ user@your-server:/tmp/

# 또는 tar 파일로 전송
scp stt_engine_deployment_offline_complete.tar.gz user@your-server:/tmp/
```

#### 1-2. 서버에서 추출 및 설정
```bash
# 서버에 접속
ssh user@your-server

# 파일 추출
cd /home/user
tar -xzf /tmp/stt_engine_deployment_offline_complete.tar.gz
cd stt_engine

# 분할된 wheel 파일 재결합 (필요시)
cat deployment_package/wheels/torch-900mb-part{aa,ab,ac} > \
    deployment_package/wheels/torch-2.5.1-cp311-cp311-linux_aarch64.whl
```

### 2단계: 의존성 설치

```bash
# Python 가상환경 생성
python3.11 -m venv venv
source venv/bin/activate

# 오프라인 모드로 wheel 파일 설치
cd deployment_package
pip install wheels/*.whl --no-index --find-links wheels/

# 또는 완전 오프라인 설치
pip install *.whl --no-index --find-links .
```

### 3단계: 모델 다운로드

```bash
# Whisper 모델 다운로드 (인터넷 필요)
# 모델은 ~/.cache/huggingface/ 또는 ./models/ 에 저장됩니다.
python download_model.py
```

**예상 시간**: 5-15분 (인터넷 속도에 따라)

### 4단계: Docker 배포

#### 4-1. Docker 이미지 빌드
```bash
# GPU 버전 (권장)
docker build -f docker/Dockerfile.gpu -t whisper-stt:latest .

# 또는 CPU 버전
docker build -f docker/Dockerfile -t whisper-stt:latest .
```

**예상 시간**: 3-5분

#### 4-2. Docker Compose로 실행
```bash
# 서비스 시작
docker-compose -f docker/docker-compose.yml up -d

# 로그 확인
docker-compose -f docker/docker-compose.yml logs -f whisper-api

# 상태 확인
docker ps
```

### 5단계: 서비스 검증

```bash
# 헬스 체크
curl http://localhost:8003/health

# 응답 예시
# {
#   "status": "ok",
#   "version": "1.0.0",
#   "engine": "faster-whisper"
# }
```

## 📡 API 사용 방법

### 음성 인식 (STT)

#### 요청
```bash
curl -X POST http://localhost:8003/transcribe \
  -F "file=@audio.wav" \
  -F "language=ko"
```

#### 응답
```json
{
  "success": true,
  "text": "안녕하세요, 저는 인공지능 음성인식 시스템입니다.",
  "language": "ko"
}
```

#### 파라미터
- **file** (required): 음성 파일 (WAV, MP3, FLAC, OGG)
- **language** (optional): 언어 코드 ('ko', 'en', 'zh', 등)
  - 미지정: 자동으로 언어 감지

## 🔄 vLLM 텍스트 처리

**참고**: 텍스트 처리는 이미 배포 서버에 있는 vLLM에서 처리합니다.

Whisper STT에서 받은 텍스트를 vLLM API로 보내면 됩니다:

```bash
# 예시: vLLM API로 텍스트 처리
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-2-7b-hf",
    "prompt": "안녕하세요, 저는 인공지능 음성인식 시스템입니다.\n이 문장을 요약하면:",
    "max_tokens": 100
  }'
```

## 🛠️ 문제 해결

### 문제 1: GPU 인식 안 됨
```bash
# GPU 드라이버 확인
nvidia-smi

# Docker GPU 지원 확인
docker run --rm --gpus all nvidia/cuda:12.4.0-runtime-ubuntu20.04 nvidia-smi
```

### 문제 2: 포트 이미 사용 중
```bash
# 점유한 프로세스 확인
sudo lsof -i :8001

# 포트 변경 (docker-compose.yml 수정)
# ports:
#   - "8002:8001"  # 호스트 포트를 8002로 변경
```

### 문제 3: 메모리 부족
```bash
# Docker 메모리 제한 확인
docker stats

# 메모리 설정 (docker-compose.yml)
# deploy:
#   resources:
#     limits:
#       memory: 16G
```

## 📊 성능 지표

| 항목 | 사양 | 비고 |
|------|------|------|
| **모델** | Whisper Large Turbo v3 | 제1.5B 파라미터 |
| **입력 포맷** | WAV, MP3, FLAC, OGG | 다양한 포맷 지원 |
| **동시 처리** | 1개 요청씩 | 순차 처리 |
| **처리 시간** | 1-30초 | 오디오 길이에 따라 |
| **GPU 메모리** | ~4GB | Whisper Large 기준 |
| **포트** | 8001 | 커스터마이징 가능 |

## 📝 로그 확인

```bash
# Docker 컨테이너 로그
docker-compose -f docker/docker-compose.yml logs whisper-api

# 로그 파일 직접 확인
tail -f logs/stt_api.log

# 특정 에러 검색
grep ERROR logs/stt_api.log
```

## 🔒 보안 사항

### 권장사항
- API는 내부 네트워크에서만 접근 가능하도록 제한
- 프로덕션 환경에서는 인증 추가 필요
- HTTPS 적용 권장

### 환경 변수 설정
```bash
# .env 파일 생성
cat > .env << EOF
WHISPER_DEVICE=cuda
SERVER_HOST=0.0.0.0
SERVER_PORT=8001
DEBUG=False
EOF
```

## 🔄 서비스 관리

### 서비스 시작
```bash
docker-compose -f docker/docker-compose.yml up -d
```

### 서비스 중지
```bash
docker-compose -f docker/docker-compose.yml down
```

### 서비스 재시작
```bash
docker-compose -f docker/docker-compose.yml restart whisper-api
```

### 컨테이너 로그 확인
```bash
docker-compose -f docker/docker-compose.yml logs -f
```

## 📦 파일 구조

```
stt_engine/
├── api_server.py              # FastAPI 서버
├── stt_engine.py              # Whisper STT 엔진
├── download_model.py          # 모델 다운로더
├── models/                    # 모델 저장소
├── docker/
│   ├── Dockerfile             # CPU 버전
│   ├── Dockerfile.gpu         # GPU 버전
│   └── docker-compose.yml     # Docker Compose 설정
├── deployment_package/
│   ├── wheels/               # Python wheel 파일 (오프라인 설치용)
│   └── SPLIT_WHEELS_README.md # wheel 설치 가이드
├── docs/
│   └── deployment/           # 배포 문서
├── audio/                    # 오디오 샘플
├── logs/                     # 로그 파일
└── requirements.txt          # Python 의존성
```

## 🚀 빠른 시작 (요약)

```bash
# 1. 파일 추출
tar -xzf stt_engine_deployment_offline_complete.tar.gz
cd stt_engine

# 2. 의존성 설치 (오프라인)
python3.11 -m venv venv
source venv/bin/activate
pip install deployment_package/wheels/*.whl --no-index --find-links deployment_package/wheels/

# 3. 모델 다운로드
python download_model.py

# 4. Docker 빌드 및 실행
docker build -f docker/Dockerfile.gpu -t whisper-stt:latest .
docker-compose -f docker/docker-compose.yml up -d

# 5. 상태 확인
curl http://localhost:8001/health

# 6. 음성 인식 테스트
curl -X POST http://localhost:8001/transcribe \
  -F "file=@audio.wav" \
  -F "language=ko"
```

## 📞 지원

문제 발생 시:
1. 로그 확인: `docker-compose logs whisper-api`
2. 헬스 체크: `curl http://localhost:8001/health`
3. GPU 확인: `nvidia-smi`
4. Docker 확인: `docker ps`

---

**마지막 업데이트**: 2026년 2월 2일
