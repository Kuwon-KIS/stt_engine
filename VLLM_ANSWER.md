# vLLM 연동 완벽 가이드 - 최종 요약

## 🎯 당신의 상황

> "vllm을 docker로 띄웠는데, 그러면 여기의 endpoint는 어떻게 설정해야하는거야? 음성 파일을 저기로 보내서 처리하려면 어떤 식으로 해야하는지 알려줘"

## ✅ 답변

### 1️⃣ Endpoint 설정 방법

#### A. 로컬 테스트 (가장 간단)
```bash
# 터미널 1: vLLM 실행
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf

# 터미널 2: STT Engine 설정
export VLLM_API_URL="http://localhost:8000"
python api_server.py

# 결과: 모든 통신이 http://localhost 통해 자동 연결
```

**코드**: `.env` 파일이나 환경 변수로 자동 설정
```env
VLLM_API_URL="http://localhost:8000"
```

---

#### B. Docker Compose (권장)
```bash
# 한 명령으로 모두 시작
docker-compose -f docker-compose.vllm.yml up -d

# 특징:
# - STT + vLLM이 자동으로 연결
# - 내부 Docker 네트워크 사용 (http://vllm:8000)
# - GPU 자동 할당
```

**코드**: 자동으로 `http://vllm:8000`으로 설정됨

---

#### C. 원격 GPU 서버
```bash
# GPU 서버에서
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf

# 로컬에서
export VLLM_API_URL="http://192.168.1.100:8000"
python api_server.py
```

**코드**: `.env` 파일 또는 환경 변수
```env
VLLM_API_URL="http://192.168.1.100:8000"
```

---

### 2️⃣ 음성 파일 처리 방식

#### 방법 A: API 직접 호출 (가장 간단)

**음성 파일 → 텍스트 추출만**:
```bash
curl -X POST "http://localhost:8001/transcribe" \
  -F "file=@audio.mp3" \
  -F "language=ko"
```

**응답**:
```json
{
  "success": true,
  "text": "안녕하세요, 이것은 테스트 음성입니다."
}
```

---

**음성 파일 → 텍스트 → vLLM 처리 (완전 자동)**:
```bash
curl -X POST "http://localhost:8001/transcribe-and-process" \
  -F "file=@audio.mp3" \
  -F "language=ko" \
  -F "instruction=이 텍스트를 요약해주세요:"
```

**응답**:
```json
{
  "success": true,
  "stt_result": {
    "text": "안녕하세요, 이것은 테스트 음성입니다."
  },
  "vllm_result": {
    "summary": "사용자의 간단한 인사말"
  }
}
```

---

#### 방법 B: Python 클라이언트

```python
import requests

# 음성 파일 준비
with open("audio.mp3", "rb") as f:
    files = {"file": f}
    data = {
        "language": "ko",
        "instruction": "이 문장의 감정을 분석해주세요:"
    }
    
    # STT + vLLM 한 번에 처리
    response = requests.post(
        "http://localhost:8001/transcribe-and-process",
        files=files,
        data=data
    )
    
    result = response.json()
    print(f"음성 인식: {result['stt_result']['text']}")
    print(f"vLLM 분석: {result['vllm_result']}")
```

---

### 3️⃣ 흐름 다이어그램

```
┌─────────────┐
│ 음성 파일    │ (audio.mp3)
└──────┬──────┘
       │ (HTTP POST)
       ▼
┌──────────────────────┐
│   STT Engine         │ (Port 8001)
│ • Whisper 모델       │
│ • 음성 → 텍스트      │
└──────┬───────────────┘
       │ (인식된 텍스트)
       ▼
┌──────────────────────┐
│   vLLM Server        │ (Port 8000)
│ • LLM 모델           │
│ • 텍스트 처리/요약   │
└──────┬───────────────┘
       │ (처리 결과)
       ▼
┌─────────────────────────────┐
│ 최종 결과                    │
│ {                           │
│   "text": "...",            │
│   "summary": "...",         │
│   "emotion": "...",         │
│   ...                       │
│ }                           │
└─────────────────────────────┘
```

---

## 🚀 3가지 환경별 설정 가이드

### 환경 1: 로컬 (macOS)
```bash
# 1. vLLM 실행
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf

# 2. STT Engine 실행
export VLLM_API_URL="http://localhost:8000"
python api_server.py

# 3. 테스트
python test_vllm_integration.py --test-vllm audio.mp3
```

**Endpoint**: `http://localhost:8000`

---

### 환경 2: Docker Compose (로컬)
```bash
# 1. 시작
docker-compose -f docker-compose.vllm.yml up -d

# 2. 테스트
curl http://localhost:8001/health
curl http://localhost:8000/health

# 3. 음성 파일 처리
curl -X POST "http://localhost:8001/transcribe-and-process" \
  -F "file=@audio.mp3" \
  -F "language=ko"
```

**Endpoint**: `http://vllm:8000` (자동 설정)

---

### 환경 3: 원격 GPU 서버
```bash
# 서버에서 vLLM 실행
ssh gpu-server
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf

# 로컬에서 STT Engine 설정
export VLLM_API_URL="http://192.168.1.100:8000"
python api_server.py

# 테스트
curl "http://localhost:8001/health"
```

**Endpoint**: `http://192.168.1.100:8000`

---

## 📋 빠른 시작 (선택하세요)

### Option 1️⃣: 가장 빠른 방법 (Docker Compose)
```bash
cd /Users/a113211/workspace/stt_engine

# 1단계: 시작
docker-compose -f docker-compose.vllm.yml up -d

# 2단계: 확인 (30초 대기)
sleep 30
curl http://localhost:8001/health

# 3단계: 테스트
curl -X POST "http://localhost:8001/transcribe-and-process" \
  -F "file=@audio_samples/test.mp3" \
  -F "language=ko"
```

---

### Option 2️⃣: 수동 설정 (더 자세한 제어)
```bash
# 터미널 1: vLLM
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf

# 터미널 2: STT Engine
cd /Users/a113211/workspace/stt_engine
export VLLM_API_URL="http://localhost:8000"
python api_server.py

# 터미널 3: 테스트
python test_vllm_integration.py --test-vllm audio_samples/test.mp3 \
  --instruction "이 음성을 요약해주세요:"
```

---

## 🔧 핵심 설정 파일 3개

### 1. `.env` - 환경 변수
```env
# vLLM 연결 설정
VLLM_API_URL="http://localhost:8000"    # ← 여기만 변경!
VLLM_MODEL_NAME="meta-llama/Llama-2-7b-hf"
VLLM_TIMEOUT=60
```

### 2. `docker-compose.vllm.yml` - 자동 설정
```yaml
services:
  vllm:
    ports: ["8000:8000"]
  
  whisper-api:
    environment:
      - VLLM_API_URL=http://vllm:8000  # ← 자동으로 올바르게 설정
```

### 3. `test_vllm_integration.py` - 통합 테스트
```bash
python test_vllm_integration.py --check-health
python test_vllm_integration.py --test-vllm audio.mp3
```

---

## 📚 상세 문서

- **[VLLM_QUICKSTART.md](VLLM_QUICKSTART.md)** - 5분 시작 가이드 ⭐
- **[VLLM_SETUP.md](VLLM_SETUP.md)** - 완벽한 설정 매뉴얼
- **[docker-compose.vllm.yml](docker-compose.vllm.yml)** - Docker Compose 설정
- **[test_vllm_integration.py](test_vllm_integration.py)** - 통합 테스트 스크립트

---

## ❓ FAQ

### Q1: vLLM endpoint를 바꾸려면?
```bash
export VLLM_API_URL="http://192.168.1.100:8000"
python api_server.py
```

### Q2: Docker Compose에서 자동으로 연결되나요?
네, `VLLM_API_URL=http://vllm:8000`으로 자동 설정됩니다.

### Q3: 원격 GPU 서버에서는?
```bash
export VLLM_API_URL="http://gpu-server-ip:8000"
```

### Q4: 모델 변경하려면?
```bash
# .env 또는 docker-compose.vllm.yml 수정
VLLM_MODEL_NAME="mistralai/Mistral-7B-v0.1"

# 컨테이너 재시작
docker-compose -f docker-compose.vllm.yml restart vllm
```

### Q5: 배치 처리는?
```bash
python test_vllm_integration.py --batch audio_samples/
```

---

## 🎓 작동 원리

```python
# 1. 음성 파일을 받음
# api_server.py의 /transcribe-and-process 엔드포인트

# 2. Whisper로 음성 → 텍스트 변환
stt_result = stt.transcribe("audio.mp3", language="ko")
# "안녕하세요, 이것은 테스트 음성입니다."

# 3. vLLM으로 텍스트 처리
# vllm_client.py의 generate() 메서드
vllm_result = vllm_client.generate(
    prompt="이 텍스트를 요약해주세요: 안녕하세요, 이것은 테스트 음성입니다."
)
# "사용자의 간단한 인사말"

# 4. 최종 결과 반환
return {
    "stt_result": stt_result,
    "vllm_result": vllm_result
}
```

---

## ✅ 완료 체크리스트

- [ ] vLLM Docker 이미지 확인
- [ ] VLLM_API_URL 설정
- [ ] docker-compose.vllm.yml 준비
- [ ] STT Engine 헬스 체크
- [ ] vLLM 헬스 체크
- [ ] 음성 파일 처리 테스트
- [ ] 배치 처리 확인

---

## 🚀 다음 단계

1. **로컬 테스트 완료** → VLLM_QUICKSTART.md 따라하기
2. **원격 서버 배포** → 모델을 GPU 서버로 이전
3. **프로덕션 설정** → vLLM 성능 최적화
4. **모니터링** → 로그 및 메트릭 수집

---

**질문이 있으신가요?** [VLLM_SETUP.md](VLLM_SETUP.md)의 "문제 해결" 섹션을 확인하세요!
