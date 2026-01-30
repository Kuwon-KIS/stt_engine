# vLLM Docker 연동 가이드

## 🎯 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  로컬 (macOS) 또는 GPU 서버 (Linux)                              │
│                                                                 │
│  ┌──────────────────────┐          ┌──────────────────────┐   │
│  │   STT Engine         │          │   vLLM Server        │   │
│  │ (Port 8001)          │◄────────►│ (Port 8000)          │   │
│  │                      │          │                      │   │
│  │ • Whisper Model      │  음성    │ • Llama/Mistral      │   │
│  │ • FastAPI Server     │  파일    │ • OpenAI API 호환    │   │
│  │ • Audio Processing   │ ───────► │ • 텍스트 처리/요약    │   │
│  └──────────────────────┘          └──────────────────────┘   │
│                                                                 │
│  플로우:                                                         │
│  음성파일 ──(HTTP POST)──► STT Engine ──(음성 처리)──►          │
│     ▲                                                            │
│     │                                                   ▼        │
│     │                                          텍스트 추출       │
│     │                                                   ▼        │
│     │◄─(결과)─────────(HTTP POST)──(vLLM) ◄──────────         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1️⃣ vLLM Docker 환경 설정

### 1.1 vLLM 컨테이너 시작

#### Option A: 단일 컨테이너로 실행
```bash
# Llama 2 모델 사용
docker run --gpus all \
  -p 8000:8000 \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf \
  --dtype float16 \
  --max-model-len 4096

# 또는 Mistral 모델 사용 (더 빠름)
docker run --gpus all \
  -p 8000:8000 \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model mistralai/Mistral-7B-v0.1 \
  --dtype float16
```

#### Option B: docker-compose 사용
```yaml
# docker-compose.yml 추가
services:
  vllm:
    image: vllm/vllm-openai:latest
    ports:
      - "8000:8000"
    environment:
      - CUDA_VISIBLE_DEVICES=0  # GPU 선택
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface  # 모델 캐시
    command: >
      --model meta-llama/Llama-2-7b-hf
      --dtype float16
      --max-model-len 4096
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### 1.2 vLLM 정상 실행 확인
```bash
# 헬스 체크
curl http://localhost:8000/health

# 응답 예시
# {"model_name":"meta-llama/Llama-2-7b-hf"}
```

---

## 2️⃣ STT Engine에서 vLLM Endpoint 설정

### 2.1 환경 변수 설정 (`.env` 파일)

```dotenv
# vLLM 설정
VLLM_API_URL="http://localhost:8000"      # 로컬 테스트
# VLLM_API_URL="http://vllm:8000"         # Docker Compose 네트워크
# VLLM_API_URL="http://gpu-server:8000"   # 원격 GPU 서버

VLLM_MODEL_NAME="meta-llama/Llama-2-7b-hf"
VLLM_TIMEOUT=60
```

### 2.2 Docker 환경에서의 Endpoint 설정

#### 경우 1: 로컬 테스트 (macOS)
```bash
# 터미널 1: vLLM 실행
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf

# 터미널 2: STT Engine 실행
export VLLM_API_URL="http://localhost:8000"
python api_server.py
```

#### 경우 2: Docker Compose (STT + vLLM 함께)
```yaml
version: '3.8'

services:
  vllm:
    image: vllm/vllm-openai:latest
    ports:
      - "8000:8000"
    environment:
      - CUDA_VISIBLE_DEVICES=0
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    command: >
      --model meta-llama/Llama-2-7b-hf
      --dtype float16
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  whisper-api:
    build:
      context: .
      dockerfile: Dockerfile.gpu
    ports:
      - "8001:8001"
    environment:
      - VLLM_API_URL=http://vllm:8000  # ← Docker 네트워크 사용
      - WHISPER_DEVICE=cuda
    volumes:
      - ./models:/app/models
      - ./audio_samples:/app/audio_samples
    depends_on:
      - vllm
    command: python api_server.py
```

#### 경우 3: 원격 GPU 서버
```bash
# GPU 서버에서 vLLM 실행 (예: 192.168.1.100)
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf

# 로컬에서 STT Engine 설정
export VLLM_API_URL="http://192.168.1.100:8000"
python api_server.py
```

---

## 3️⃣ 음성 파일 처리 플로우

### 3.1 API 엔드포인트 사용

#### 옵션 A: STT만 처리
```bash
# 음성 파일을 텍스트로만 변환
curl -X POST "http://localhost:8001/transcribe" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.mp3" \
  -F "language=ko"

# 응답
{
  "success": true,
  "text": "안녕하세요, 이것은 테스트 음성입니다.",
  "language": "ko",
  "duration": 5.2
}
```

#### 옵션 B: STT + vLLM 처리 (권장)
```bash
# 음성 → 텍스트 → vLLM 처리
curl -X POST "http://localhost:8001/transcribe-and-process" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.mp3" \
  -F "language=ko" \
  -F "instruction=다음 텍스트를 한 문장으로 요약해주세요:"

# 응답
{
  "success": true,
  "stt_result": {
    "success": true,
    "text": "안녕하세요, 이것은 테스트 음성입니다.",
    "language": "ko"
  },
  "vllm_result": {
    "summary": "사용자가 테스트 음성으로 인사를 합니다."
  }
}
```

### 3.2 Python 클라이언트 사용

#### 기본 테스트
```python
import requests

# 헬스 체크
response = requests.get("http://localhost:8001/health")
print(response.json())
# {'status': 'healthy', 'device': 'cuda', 'models_loaded': True}

# STT만 처리
with open("audio.mp3", "rb") as f:
    files = {"file": f}
    data = {"language": "ko"}
    response = requests.post(
        "http://localhost:8001/transcribe",
        files=files,
        data=data
    )
    print(response.json())

# STT + vLLM 처리
with open("audio.mp3", "rb") as f:
    files = {"file": f}
    data = {
        "language": "ko",
        "instruction": "이 문장의 핵심을 3단어로 요약해주세요:"
    }
    response = requests.post(
        "http://localhost:8001/transcribe-and-process",
        files=files,
        data=data
    )
    result = response.json()
    print(f"음성 인식: {result['stt_result']['text']}")
    print(f"vLLM 처리: {result['vllm_result']}")
```

#### 배치 처리
```python
import os
from pathlib import Path
import requests

# audio_samples 폴더의 모든 파일 처리
audio_dir = Path("audio_samples")
for audio_file in audio_dir.glob("*.mp3"):
    with open(audio_file, "rb") as f:
        files = {"file": f}
        data = {
            "language": "ko",
            "instruction": "이 음성의 감정을 분석해주세요:"
        }
        response = requests.post(
            "http://localhost:8001/transcribe-and-process",
            files=files,
            data=data
        )
        result = response.json()
        
        print(f"\n파일: {audio_file.name}")
        print(f"인식: {result['stt_result']['text']}")
        print(f"분석: {result['vllm_result']}")
```

---

## 4️⃣ 코드에서 Endpoint 구성 방식

### 4.1 `vllm_client.py` - 현재 구조

```python
class VLLMConfig(BaseModel):
    """vLLM 서버 설정"""
    api_url: str = os.getenv("VLLM_API_URL", "http://localhost:8000")
    model_name: str = os.getenv("VLLM_MODEL_NAME", "meta-llama/Llama-2-7b-hf")
    timeout: int = 60
    max_tokens: int = 512

class VLLMClient:
    def __init__(self, config: VLLMConfig):
        self.config = config
        self.completion_endpoint = f"{config.api_url}/v1/completions"
        # ↑ 자동으로 구성됨: "http://localhost:8000/v1/completions"
```

### 4.2 `api_server.py` - 서버 초기화

```python
# 자동 로드
vllm_client = VLLMClient(VLLMConfig())  # .env 파일에서 자동 읽음

# 또는 명시적 설정
from vllm_client import VLLMConfig, VLLMClient

config = VLLMConfig(
    api_url="http://gpu-server:8000",
    model_name="mistralai/Mistral-7B-v0.1"
)
vllm_client = VLLMClient(config)
```

---

## 5️⃣ 네트워크 연결 가이드

### 5.1 로컬 개발 (macOS)
```
┌──────────┐         ┌──────────┐
│ STT Port │◄───────►│vLLM Port │
│  8001    │         │  8000    │
└──────────┘         └──────────┘
 localhost           localhost
```

**설정**:
```bash
export VLLM_API_URL="http://localhost:8000"
```

### 5.2 Docker Compose (로컬)
```
┌──────────────────────────────────────┐
│      Docker Network (vllm_net)       │
│                                      │
│  ┌────────────┐      ┌────────────┐ │
│  │ STT        │      │ vLLM       │ │
│  │ Port 8001  │◄────►│ Port 8000  │ │
│  │ Host: stt  │      │ Host: vllm │ │
│  └────────────┘      └────────────┘ │
│                                      │
└──────────────────────────────────────┘
```

**설정**:
```yaml
environment:
  - VLLM_API_URL=http://vllm:8000  # Docker DNS 사용
```

### 5.3 원격 GPU 서버
```
┌──────────────┐                ┌──────────────┐
│ 로컬 (macOS) │                │GPU 서버(Linux)│
│              │                │              │
│STT 8001 ────────(HTTP)───────► vLLM 8000    │
│              │   192.168.1.100│              │
└──────────────┘                └──────────────┘
```

**설정**:
```bash
export VLLM_API_URL="http://192.168.1.100:8000"
```

**GPU 서버에서 vLLM 실행**:
```bash
docker run --gpus all \
  -p 8000:8000 \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf
```

---

## 6️⃣ 문제 해결

### Issue 1: "vLLM 서버 연결 불가"
```bash
# 1단계: vLLM 실행 확인
docker ps | grep vllm

# 2단계: 포트 확인
lsof -i :8000

# 3단계: 헬스 체크
curl http://localhost:8000/health

# 4단계: 방화벽 확인 (원격 서버의 경우)
telnet 192.168.1.100 8000
```

### Issue 2: Docker Compose에서 연결 불가
```bash
# 원인: 네트워크 이름 확인
docker network ls

# STT 컨테이너에서 vLLM 접근 테스트
docker exec whisper-api curl http://vllm:8000/health

# 또는 IP 직접 사용
docker inspect vllm | grep IPAddress
```

### Issue 3: 모델 로드 에러
```bash
# 1단계: 모델 캐시 확인
ls ~/.cache/huggingface/

# 2단계: 볼륨 마운트 확인
docker inspect vllm | grep Mounts

# 3단계: 토큰 설정 (Llama 2의 경우)
huggingface-cli login
```

---

## 7️⃣ 성능 최적화

### 7.1 vLLM 설정 최적화
```bash
docker run --gpus all \
  -p 8000:8000 \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf \
  --dtype float16 \                          # 메모리 절감
  --max-model-len 4096 \                     # 최대 토큰 길이
  --gpu-memory-utilization 0.9 \             # GPU 활용률 높임
  --tensor-parallel-size 1 \                 # GPU 단일 사용
  --max-num-seqs 256                         # 배치 크기
```

### 7.2 STT Engine 설정 최적화
```python
# api_server.py
import torch

# GPU 메모리 정리
torch.cuda.empty_cache()

# 모델 로드 시 메모리 맵
model_kwargs = {
    "torch_dtype": torch.float16,  # 메모리 절감
    "device_map": "auto"           # 자동 할당
}
```

### 7.3 Docker Compose 리소스 설정
```yaml
services:
  vllm:
    # ... 기존 설정 ...
    deploy:
      resources:
        limits:
          cpus: '4'              # CPU 제한
          memory: 32G            # 메모리 제한
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']   # GPU 0번만 사용
              count: 1
              capabilities: [gpu]
```

---

## 8️⃣ 실행 예시

### 로컬 테스트 (권장 순서)

```bash
# 1단계: vLLM 시작 (터미널 1)
docker run --gpus all \
  -p 8000:8000 \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf

# 2단계: STT Engine 시작 (터미널 2)
cd /Users/a113211/workspace/stt_engine
export VLLM_API_URL="http://localhost:8000"
python api_server.py

# 3단계: 테스트 (터미널 3)
python api_client.py --health
python api_client.py --process audio_samples/test.mp3
```

### Docker Compose로 한 번에 (권장)

```bash
# 1단계: docker-compose.yml 업데이트 (위 참고)

# 2단계: 시작
docker-compose up -d

# 3단계: 헬스 체크
curl http://localhost:8001/health

# 4단계: 테스트
curl -X POST "http://localhost:8001/transcribe" \
  -F "file=@audio_samples/test.mp3" \
  -F "language=ko"

# 5단계: 중지
docker-compose down
```

---

## 요약

| 항목 | 값 |
|------|-----|
| **STT Engine Port** | 8001 |
| **vLLM Port** | 8000 |
| **Endpoint 형식** | `http://[host]:[port]/v1/completions` |
| **환경변수** | `VLLM_API_URL` |
| **로컬 (localhost)** | `http://localhost:8000` |
| **Docker Compose** | `http://vllm:8000` |
| **원격 GPU 서버** | `http://[IP]:8000` |

✅ 이제 음성 파일을 STT로 처리하고 vLLM으로 연속 처리할 수 있습니다!
