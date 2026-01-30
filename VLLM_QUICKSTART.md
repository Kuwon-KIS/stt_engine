# vLLM 연동 빠른 시작 (5분)

## 🚀 30초 요약

```bash
# 1. vLLM 실행
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf

# 2. STT Engine 실행 (다른 터미널)
export VLLM_API_URL="http://localhost:8000"
python api_server.py

# 3. 테스트
python test_vllm_integration.py --test-vllm audio_samples/test.mp3
```

---

## 🛠️ 로컬 환경 설정 (macOS)

### 1단계: vLLM Docker 이미지 준비
```bash
# GPU가 없는 경우 (CPU)
docker run -p 8000:8000 vllm/vllm-openai:latest \
  --model mistralai/Mistral-7B-v0.1

# GPU가 있는 경우 (권장)
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf --dtype float16
```

✅ 확인: `curl http://localhost:8000/health`

### 2단계: STT Engine 설정
```bash
# 환경 변수 설정
cp .env.example .env

# 필요시 수정
vim .env
# VLLM_API_URL="http://localhost:8000"
```

### 3단계: STT Engine 실행
```bash
# 터미널 2에서
python api_server.py
```

✅ 확인: `curl http://localhost:8001/health`

### 4단계: 통합 테스트
```bash
# 터미널 3에서
python test_vllm_integration.py --check-health

# STT만 테스트
python test_vllm_integration.py --test-stt audio_samples/test.mp3

# STT + vLLM 테스트
python test_vllm_integration.py --test-vllm audio_samples/test.mp3 \
  --instruction "이 텍스트의 감정을 분석해주세요:"
```

---

## 🐳 Docker Compose로 한 번에 (권장)

### 1단계: 설정 파일 확인
```bash
# docker-compose.vllm.yml 파일 확인
ls -la docker-compose.vllm.yml
```

### 2단계: 모델 캐시 준비 (선택)
```bash
# Hugging Face 모델 미리 다운로드 (선택사항)
huggingface-cli download meta-llama/Llama-2-7b-hf
```

### 3단계: 시작
```bash
# STT + vLLM 함께 시작
docker-compose -f docker-compose.vllm.yml up -d

# 로그 확인
docker-compose -f docker-compose.vllm.yml logs -f

# 정상 시작 확인 (30-40초 대기)
sleep 40
curl http://localhost:8000/health  # vLLM
curl http://localhost:8001/health  # STT
```

### 4단계: 테스트
```bash
# 컨테이너 내부에서 테스트
docker-compose -f docker-compose.vllm.yml exec whisper-api \
  python test_vllm_integration.py --check-health

# 또는 호스트에서 테스트
curl -X POST "http://localhost:8001/transcribe" \
  -F "file=@audio_samples/test.mp3" \
  -F "language=ko"
```

### 5단계: 중지
```bash
docker-compose -f docker-compose.vllm.yml down

# 컨테이너 삭제
docker-compose -f docker-compose.vllm.yml down -v
```

---

## 🔌 Endpoint 설정 (환경별)

### 로컬 개발 (macOS)
```env
VLLM_API_URL="http://localhost:8000"
```

```bash
# vLLM 실행
docker run -p 8000:8000 vllm/vllm-openai:latest --model mistralai/Mistral-7B-v0.1
```

### Docker Compose (로컬)
```env
VLLM_API_URL="http://vllm:8000"
```

```bash
# 시작
docker-compose -f docker-compose.vllm.yml up -d
```

### 원격 GPU 서버
```env
VLLM_API_URL="http://192.168.1.100:8000"
```

```bash
# 서버에서 vLLM 실행
ssh gpu-server
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf
```

---

## 📝 음성 파일 처리 방식

### API 사용 (권장)

**1. 텍스트만 추출**
```bash
curl -X POST "http://localhost:8001/transcribe" \
  -F "file=@audio.mp3" \
  -F "language=ko" | jq
```

**응답**:
```json
{
  "success": true,
  "text": "안녕하세요, 이것은 테스트 음성입니다.",
  "language": "ko",
  "duration": 5.2
}
```

**2. 텍스트 + vLLM 처리 (권장)**
```bash
curl -X POST "http://localhost:8001/transcribe-and-process" \
  -F "file=@audio.mp3" \
  -F "language=ko" \
  -F "instruction=이 텍스트를 요약해주세요:" | jq
```

**응답**:
```json
{
  "success": true,
  "stt_result": {
    "success": true,
    "text": "안녕하세요, 이것은 테스트 음성입니다.",
    "language": "ko"
  },
  "vllm_result": {
    "summary": "사용자의 간단한 인사말"
  }
}
```

### Python 사용
```python
import requests

# STT + vLLM
with open("audio.mp3", "rb") as f:
    files = {"file": f}
    data = {
        "language": "ko",
        "instruction": "감정을 분석해주세요:"
    }
    response = requests.post(
        "http://localhost:8001/transcribe-and-process",
        files=files,
        data=data
    )
    result = response.json()
    print(f"인식: {result['stt_result']['text']}")
    print(f"분석: {result['vllm_result']}")
```

---

## ⚙️ vLLM 모델 선택 가이드

| 모델 | 크기 | 속도 | 품질 | 추천 환경 |
|------|------|------|------|----------|
| Mistral 7B | 15GB | ⚡⚡⚡ | ⭐⭐⭐ | 로컬 / 서버 |
| Llama 2 7B | 16GB | ⚡⚡ | ⭐⭐⭐⭐ | 서버 |
| Llama 2 13B | 26GB | ⚡ | ⭐⭐⭐⭐⭐ | 고성능 서버 |
| Phi 2 | 6GB | ⚡⚡⚡⚡ | ⭐⭐⭐ | 로컬 |

### 모델 변경 방법

```bash
# 1. .env 파일 수정
VLLM_MODEL_NAME="mistralai/Mistral-7B-v0.1"

# 2. vLLM 컨테이너 재시작
docker-compose -f docker-compose.vllm.yml restart vllm
```

---

## 🔍 문제 해결

### vLLM 서버 연결 불가
```bash
# 1. vLLM 실행 확인
docker ps | grep vllm

# 2. 포트 확인
lsof -i :8000

# 3. 헬스 체크
curl -v http://localhost:8000/health

# 4. 로그 확인
docker logs vllm-server
```

### GPU 메모리 부족
```bash
# 방법 1: 더 작은 모델 사용
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model mistralai/Mistral-7B-v0.1

# 방법 2: 메모리 제한 조정
--gpu-memory-utilization 0.7  # 기본값 0.9 → 0.7로 감소

# 방법 3: 토큰 길이 제한
--max-model-len 2048  # 기본값 4096 → 2048로 감소
```

### Hugging Face 인증 필요
```bash
# 토큰 설정 (Llama 2의 경우)
huggingface-cli login
# 토큰 입력: hf_xxxxxxxxxxxxx

# 또는 환경 변수
export HF_TOKEN=hf_xxxxxxxxxxxxx
```

### Docker Compose 네트워크 문제
```bash
# 컨테이너 간 연결 테스트
docker-compose -f docker-compose.vllm.yml exec whisper-api \
  curl http://vllm:8000/health

# 네트워크 확인
docker network ls
docker network inspect stt_engine_stt_network
```

---

## 📊 성능 최적화

### GPU 설정
```yaml
# docker-compose.vllm.yml에서
command: >
  --model meta-llama/Llama-2-7b-hf
  --dtype float16
  --gpu-memory-utilization 0.9
  --max-num-seqs 256
```

### 동시 요청 처리
```python
# 여러 요청 동시 처리
import asyncio
import aiohttp

async def process_multiple(audio_files):
    async with aiohttp.ClientSession() as session:
        tasks = [
            post_request(session, f)
            for f in audio_files
        ]
        return await asyncio.gather(*tasks)
```

---

## ✅ 체크리스트

- [ ] vLLM Docker 이미지 다운로드
- [ ] `VLLM_API_URL` 환경 변수 설정
- [ ] STT Engine 실행 확인
- [ ] vLLM 헬스 체크 (`curl http://localhost:8000/health`)
- [ ] STT 헬스 체크 (`curl http://localhost:8001/health`)
- [ ] 테스트 음성 파일 준비
- [ ] 통합 테스트 수행 (`test_vllm_integration.py`)
- [ ] 배치 처리 테스트 (선택)

---

## 📚 관련 파일

- [VLLM_SETUP.md](VLLM_SETUP.md) - 상세 설정 가이드
- [docker-compose.vllm.yml](docker-compose.vllm.yml) - Docker Compose 설정
- [test_vllm_integration.py](test_vllm_integration.py) - 통합 테스트 스크립트
- [.env](`.env`) - 환경 변수

---

## 💡 다음 단계

1. ✅ 로컬에서 성공적으로 테스트
2. ✅ GPU 서버로 모델 이전
3. ✅ 원격 vLLM과 연동
4. ✅ 프로덕션 배포

VLLM_SETUP.md에서 더 자세한 내용을 확인하세요!
