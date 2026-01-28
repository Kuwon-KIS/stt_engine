# 🚀 STT Engine - 빠른 시작 가이드

## 🎯 프로젝트 개요

**STT Engine**은 OpenAI의 Whisper 모델을 사용하여 음성을 텍스트로 변환하고, vLLM을 통해 추가 처리를 수행하는 완전한 STT 솔루션입니다.

### 주요 특징
- ✅ Whisper Large v3 Turbo 모델 기반 고정밀 STT
- ✅ 다국어 지원 (한국어, 영어 등)
- ✅ vLLM 통합으로 자동 요약/분석 가능
- ✅ Docker/Docker Compose 지원
- ✅ GPU 최적화 (CUDA 11.0+)
- ✅ FastAPI REST API 제공
- ✅ Linux 서버 배포 완벽 가이드

---

## 📦 설치 및 실행

### Option 1️⃣ : 로컬 개발 환경 (macOS/Linux)

#### Step 1: 자동 설정 스크립트 실행
```bash
chmod +x setup.sh
./setup.sh
```

#### Step 2: Whisper 모델 다운로드
```bash
source venv/bin/activate
python download_model.py
```

> **⏱️ 예상 시간**: 10-20분 (인터넷 속도에 따라 변함)
> **💾 필요 용량**: 약 3GB

#### Step 3: 음성 파일 준비
```bash
# audio/ 디렉토리에 WAV, MP3, FLAC 또는 OGG 파일 추가
cp /path/to/your/audio.wav audio/
```

#### Step 4: STT 테스트
```bash
python stt_engine.py
```

#### Step 5: API 서버 실행 (별도 터미널)
```bash
python api_server.py
```

API가 `http://localhost:8001`에서 실행됩니다.

---

### Option 2️⃣ : Docker 환경 (권장)

#### Step 1: Docker 이미지 빌드
```bash
# 기본 CPU 버전
docker build -t stt-engine:latest .

# GPU 지원 버전 (CUDA 포함)
docker build -t stt-engine:gpu -f Dockerfile.gpu .
```

#### Step 2: Docker Compose로 실행
```bash
# 환경 파일 생성
cp .env.example .env

# 서비스 시작 (STT 엔진 + vLLM 서버)
docker-compose up -d

# 상태 확인
docker-compose ps
docker-compose logs -f
```

#### Step 3: 서버 상태 확인
```bash
curl http://localhost:8001/health
```

---

## 🎤 사용 방법

### Python API 클라이언트 사용

#### 1. STT만 수행
```python
from stt_engine import WhisperSTT

stt = WhisperSTT("models/openai_whisper-large-v3-turbo")
result = stt.transcribe("audio/sample.wav", language="ko")
print(result["text"])
```

#### 2. vLLM과 함께 사용
```python
from stt_engine import WhisperSTT
from vllm_client import VLLMClient, VLLMConfig

stt = WhisperSTT("models/openai_whisper-large-v3-turbo")
vllm = VLLMClient(VLLMConfig())

# STT 처리
stt_result = stt.transcribe("audio/sample.wav", language="ko")

# vLLM으로 추가 처리
llm_result = vllm.generate(
    f"다음 텍스트를 요약해주세요:\n{stt_result['text']}"
)
print(llm_result)
```

---

### CLI 클라이언트 사용

#### 1. 헬스 체크
```bash
python api_client.py --health
```

#### 2. 단일 파일 변환
```bash
python api_client.py --transcribe audio/sample.wav --language ko
```

#### 3. 변환 + vLLM 처리
```bash
python api_client.py --process audio/sample.wav \
    --instruction "다음 내용을 3줄로 요약해주세요:" \
    --language ko
```

#### 4. 배치 처리
```bash
python api_client.py --batch audio/ --json
```

---

### REST API 사용

#### 1. 헬스 체크
```bash
curl http://localhost:8001/health
```

#### 2. STT 변환
```bash
curl -X POST \
  -F "file=@audio/sample.wav" \
  -F "language=ko" \
  http://localhost:8001/transcribe | jq
```

#### 3. STT + vLLM 처리
```bash
curl -X POST \
  -F "file=@audio/sample.wav" \
  -F "language=ko" \
  -F "instruction=다음 텍스트를 요약해주세요:" \
  http://localhost:8001/transcribe-and-process | jq
```

---

## 🖥️ Linux 서버 배포

자세한 배포 가이드는 [DEPLOYMENT.md](DEPLOYMENT.md)를 참고하세요.

### 빠른 배포 (Docker Compose)
```bash
# 저장소 클론
git clone https://github.com/Kuwon-KIS/stt_engine.git
cd stt_engine

# 환경 설정
cp .env.example .env
# nano .env  # 필요시 수정

# 서비스 시작
docker-compose up -d

# 상태 확인
docker-compose ps
docker-compose logs -f stt-engine
```

### 자동 재시작 설정 (Systemd)
```bash
# DEPLOYMENT.md의 "자동 재시작 설정" 섹션 참고
```

---

## 📊 성능 지표

| 항목 | 값 |
|-----|-----|
| 모델 크기 | ~3GB |
| 초기 로드 시간 | ~5초 |
| 1시간 음성 처리 시간 | CPU: ~30분 / GPU: ~2분 |
| 메모리 사용 (CPU) | ~2-3GB |
| 메모리 사용 (GPU) | ~8GB |

---

## 🔧 설정 및 커스터마이징

### 환경 변수 (.env)
```bash
# Whisper 설정
WHISPER_MODEL="openai/whisper-large-v3-turbo"
WHISPER_DEVICE="cpu"  # cpu 또는 cuda

# vLLM 설정
VLLM_API_URL="http://localhost:8000"
VLLM_MODEL_NAME="meta-llama/Llama-2-7b-hf"

# 서버 설정
SERVER_HOST="0.0.0.0"
SERVER_PORT=8001
DEBUG=True
```

### 모델 변경
다른 Whisper 모델을 사용하려면:
```bash
# download_model.py에서 model_id 변경
# - openai/whisper-base
# - openai/whisper-small
# - openai/whisper-medium
# - openai/whisper-large
# - openai/whisper-large-v3-turbo
```

---

## 🚨 문제 해결

### Q: 모델 다운로드가 안 됨
**A**: Hugging Face 토큰 설정
```bash
export HUGGINGFACE_HUB_TOKEN=your_token_here
python download_model.py
```

### Q: GPU가 인식되지 않음
**A**: GPU 드라이버 확인
```bash
nvidia-smi
docker run --gpus all nvidia/cuda:11.0-runtime nvidia-smi
```

### Q: 메모리 부족
**A**: Swap 추가 또는 CPU 모드 사용
```bash
# CPU 모드 실행
export WHISPER_DEVICE=cpu
python stt_engine.py

# Swap 추가 (Linux)
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Q: vLLM 연결 실패
**A**: vLLM 서버 상태 확인
```bash
curl http://localhost:8000/health
docker-compose restart vllm-server
```

---

## 📚 주요 파일 설명

| 파일 | 설명 |
|------|------|
| `download_model.py` | Hugging Face에서 Whisper 모델 다운로드 |
| `stt_engine.py` | Whisper STT 핵심 모듈 |
| `vllm_client.py` | vLLM 서버 통신 클라이언트 |
| `api_server.py` | FastAPI REST API 서버 |
| `api_client.py` | CLI 테스트 클라이언트 |
| `Dockerfile` | 기본 Docker 이미지 (CPU) |
| `Dockerfile.gpu` | GPU 최적화 Docker 이미지 |
| `docker-compose.yml` | Docker Compose 설정 |
| `setup.sh` | 로컬 환경 자동 설정 |
| `DEPLOYMENT.md` | Linux 서버 배포 완벽 가이드 |

---

## 🤝 기여 및 지원

- **이슈 보고**: GitHub Issues에서 문제 보고
- **기여**: Pull Request 환영
- **문의**: 토론 게시판 활용

---

## 📝 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 🎓 학습 자료

- [Whisper 공식 문서](https://github.com/openai/whisper)
- [vLLM 공식 문서](https://docs.vllm.ai/)
- [FastAPI 튜토리얼](https://fastapi.tiangolo.com/)
- [Docker 공식 문서](https://docs.docker.com/)

---

**🎉 프로젝트 설정이 완료되었습니다!**

다음 단계:
1. ✅ 프로젝트 구조 생성 완료
2. ✅ 모델 다운로드 스크립트 준비 완료
3. ✅ Docker 환경 설정 완료
4. ✅ vLLM 통합 완료
5. 📌 **다음**: 음성 파일 준비 및 첫 테스트 수행

**시작하기**:
```bash
# 로컬 테스트
source venv/bin/activate
python download_model.py
python api_server.py

# 또는 Docker
docker-compose up -d
```
