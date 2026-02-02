# Whisper STT API - 음성 인식 엔진

OpenAI의 Whisper 모델을 사용하여 음성을 텍스트로 변환하는 REST API 서버입니다.

## 🎯 주요 기능

- **Whisper 기반 STT**: OpenAI의 whisper-large-v3-turbo 모델 사용
- **다국어 지원**: 한국어, 영어, 중국어 등 다양한 언어 지원
- **GPU 최적화**: CUDA GPU를 활용한 빠른 처리
- **Docker 환경**: 컨테이너화된 간단한 배포
- **FastAPI 서버**: REST API를 통한 쉬운 접근

**참고**: vLLM 텍스트 처리는 별도로 배포된 서버에서 담당합니다.

## 📋 준비 사항

- Python 3.11+
- CUDA 12.4+ (GPU 사용 시, CUDA 11.8 호환도 가능)
- Docker & Docker Compose
- 최소 4GB VRAM (권장 8GB 이상)

## 🚀 빠른 시작 (Docker)

### 1단계: 이미지 빌드
```bash
docker build -f docker/Dockerfile.gpu -t whisper-stt:latest .
```

### 2단계: 컨테이너 실행
```bash
docker-compose -f docker/docker-compose.yml up -d
```

### 3단계: 상태 확인
```bash
curl http://localhost:8001/health
```

### 4단계: 음성 인식
```bash
curl -X POST -F "file=@audio.wav" -F "language=ko" \
  http://localhost:8001/transcribe
```

## 📡 API 엔드포인트

### 헬스 체크
```bash
curl http://localhost:8001/health
```

### 음성 인식 (STT)
```bash
curl -X POST \
  -F "file=@audio.wav" \
  -F "language=ko" \
  http://localhost:8001/transcribe
```

**응답 예시**:
```json
{
  "success": true,
  "text": "안녕하세요, 저는 인공지능 음성인식 시스템입니다.",
  "language": "ko"
}
```

## 🔄 텍스트 처리 (vLLM)

STT로 변환한 텍스트를 별도로 배포된 vLLM 서버로 보내서 처리합니다:

```bash
# vLLM API 호출 예시
curl -X POST http://your-vllm-server:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-2-7b-hf",
    "prompt": "안녕하세요, 저는 인공지능 음성인식 시스템입니다.",
    "max_tokens": 100
  }'
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
