# STT Engine - Speech-to-Text 엔진

음성 파일을 텍스트로 변환하고, vLLM을 사용하여 추가 처리를 수행하는 엔진입니다.

## 🎯 주요 기능

- **Whisper 기반 STT**: OpenAI의 whisper-large-v3-turbo 모델 사용
- **다국어 지원**: 한국어, 영어 등 다양한 언어 지원
- **vLLM 통합**: STT 결과를 대규모 언어 모델로 추가 처리
- **Docker 환경**: 컨테이너화된 배포 환경
- **FastAPI 서버**: REST API를 통한 쉬운 접근

## 📋 준비 사항

- Python 3.11+
- CUDA 11.0+ (GPU 사용 시)
- Docker & Docker Compose (컨테이너 사용 시)

## 🚀 빠른 시작

### 1. 로컬 환경 설정

```bash
# 가상 환경 생성
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# Windows의 경우: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. Whisper 모델 다운로드

```bash
python download_model.py
```

이 스크립트는 Hugging Face에서 `openai/whisper-large-v3-turbo` 모델을 다운로드합니다.

### 3. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 필요에 따라 수정
```

### 4. STT 테스트

```bash
# audio/ 디렉토리에 음성 파일을 추가한 후
python stt_engine.py
```

### 5. API 서버 실행

```bash
python api_server.py
```

API 서버가 `http://localhost:8001`에서 실행됩니다.

## 🐳 Docker 환경 설정

### 1. Docker 이미지 빌드

```bash
docker build -t stt-engine:latest .
```

### 2. Docker Compose로 실행

```bash
docker-compose up -d
```

이 명령어로 STT 엔진과 vLLM 서버가 동시에 실행됩니다.

### 3. 서버 상태 확인

```bash
# STT 엔진 로그 확인
docker-compose logs -f stt-engine

# vLLM 서버 로그 확인
docker-compose logs -f vllm-server
```

## 📡 API 엔드포인트

### 헬스 체크
```bash
curl http://localhost:8001/health
```

### 음성 파일 변환 (STT만)
```bash
curl -X POST -F "file=@audio.wav" http://localhost:8001/transcribe
```

### 음성 파일 변환 및 vLLM 처리
```bash
curl -X POST -F "file=@audio.wav" \
  -F "instruction=다음 텍스트를 요약해주세요:" \
  http://localhost:8001/transcribe-and-process
```

## 📁 프로젝트 구조

```
stt_engine/
├── download_model.py          # 모델 다운로드 스크립트
├── stt_engine.py             # STT 핵심 모듈
├── vllm_client.py            # vLLM 클라이언트
├── api_server.py             # FastAPI 서버
├── Dockerfile                # Docker 이미지 정의
├── docker-compose.yml        # Docker Compose 설정
├── requirements.txt          # Python 의존성
├── .env.example              # 환경 변수 예제
├── README.md                 # 이 파일
├── models/                   # Whisper 모델 저장 위치
├── audio/                    # 테스트 음성 파일 위치
└── logs/                     # 로그 파일 위치
```

## 🔧 고급 설정

### GPU 사용 설정

#### docker-compose.yml에서 GPU 활성화:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

#### 환경 변수에서 GPU 설정:
```bash
WHISPER_DEVICE=cuda
```

### vLLM 모델 변경

docker-compose.yml에서 모델 이름 변경:
```yaml
environment:
  - MODEL_NAME=meta-llama/Llama-2-13b-hf  # 다른 모델로 변경
```

## 🧪 테스트

### 로컬 테스트
```bash
# STT 엔진 테스트
python stt_engine.py

# vLLM 연결 테스트
python vllm_client.py
```

### Docker 환경에서 테스트
```bash
# 컨테이너 내에서 테스트 실행
docker-compose exec stt-engine python stt_engine.py
```

## 📊 모니터링

### 로그 확인
```bash
# 최근 100줄 로그
tail -100f logs/*.log

# 특정 로그 보기
docker-compose logs -f stt-engine
```

### 리소스 사용량 확인
```bash
docker stats stt-engine vllm-server
```

## ⚠️ 주의사항

1. **모델 다운로드**: 첫 실행 시 모델이 상당히 큼 (수 GB)이므로 시간이 걸릴 수 있습니다.
2. **GPU 메모리**: GPU를 사용할 경우 충분한 VRAM이 필요합니다 (최소 8GB 권장).
3. **vLLM 서버**: STT와 vLLM을 함께 사용하려면 vLLM 서버가 반드시 실행 중이어야 합니다.

## 🛠️ 문제 해결

### 모델 다운로드 실패
```bash
# Hugging Face 토큰 설정
export HUGGINGFACE_HUB_TOKEN=your_token_here
python download_model.py
```

### 메모리 부족
```bash
# CPU 모드로 실행
export WHISPER_DEVICE=cpu
python stt_engine.py
```

### vLLM 서버 연결 실패
```bash
# vLLM 서버가 실행 중인지 확인
curl http://localhost:8000/health

# 서버 재시작
docker-compose restart vllm-server
```

## 📝 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 👥 기여

이슈 및 풀 리퀘스트는 언제든 환영합니다!
