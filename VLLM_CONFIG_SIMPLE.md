# 📌 vLLM 연동 설정 - 핵심 요약

당신의 질문: "vllm을 docker로 띄웠는데, endpoint는 어떻게 설정하고, 음성 파일을 처리하려면?"

---

## ⭐ 핵심 답변 (3줄)

1. **Endpoint 설정**: 환경변수 `VLLM_API_URL="http://localhost:8000"` 설정
2. **자동 연결**: `.env` 파일에서 자동으로 읽고 vLLM 클라이언트가 연결
3. **음성 처리**: HTTP POST로 `/transcribe-and-process` 엔드포인트 호출

---

## 🎯 세 가지 상황별 설정

### 상황 1: 로컬 개발 (macOS)
```bash
# 1단계: vLLM Docker 실행
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf

# 2단계: STT Engine에서 endpoint 설정
export VLLM_API_URL="http://localhost:8000"
python api_server.py

# 3단계: 음성 파일 처리
python test_vllm_integration.py --test-vllm audio.mp3
```

---

### 상황 2: Docker Compose (STT + vLLM 함께)
```bash
# 1단계: 시작 (자동으로 모든 설정 완료)
docker-compose -f docker-compose.vllm.yml up -d

# 2단계: 음성 파일 처리
curl -X POST "http://localhost:8001/transcribe-and-process" \
  -F "file=@audio.mp3" \
  -F "language=ko"

# 장점: VLLM_API_URL이 자동으로 http://vllm:8000 설정됨
```

---

### 상황 3: 원격 GPU 서버
```bash
# GPU 서버에서 vLLM 실행
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf

# 로컬에서 endpoint 설정
export VLLM_API_URL="http://192.168.1.100:8000"
python api_server.py
```

---

## 🔌 Endpoint 설정 3가지 방법

### 방법 1: 환경 변수 (간단)
```bash
export VLLM_API_URL="http://localhost:8000"
python api_server.py
```

### 방법 2: .env 파일 (권장)
```env
VLLM_API_URL="http://localhost:8000"
```

### 방법 3: Docker Compose (자동)
```yaml
environment:
  - VLLM_API_URL=http://vllm:8000
```

---

## 🎙️ 음성 파일 처리 방식

### API 호출 (가장 간단)

**Curl 예제**:
```bash
# 음성 → 텍스트 → vLLM 처리 (한 번에)
curl -X POST "http://localhost:8001/transcribe-and-process" \
  -F "file=@audio.mp3" \
  -F "language=ko" \
  -F "instruction=이 음성을 요약해주세요:"
```

**응답**:
```json
{
  "success": true,
  "stt_result": {
    "text": "안녕하세요, 이것은 테스트 음성입니다."
  },
  "vllm_result": {
    "summary": "사용자의 인사말"
  }
}
```

---

### Python 예제

```python
import requests

with open("audio.mp3", "rb") as f:
    files = {"file": f}
    data = {
        "language": "ko",
        "instruction": "감정 분석"
    }
    
    response = requests.post(
        "http://localhost:8001/transcribe-and-process",
        files=files,
        data=data
    )
    
    result = response.json()
    print(f"음성 인식: {result['stt_result']['text']}")
    print(f"vLLM 결과: {result['vllm_result']}")
```

---

## 📊 처리 흐름

```
음성 파일 (audio.mp3)
       ↓
STT Engine (Port 8001)
  ├─ Whisper 모델로 음성 인식
  ├─ 결과: "안녕하세요..."
       ↓
vLLM Server (Port 8000) ← VLLM_API_URL로 자동 연결
  ├─ LLM 모델로 텍스트 처리
  ├─ 결과: "요약/분석/감정분석..."
       ↓
최종 응답 (JSON)
```

---

## 📁 생성된 파일

| 파일 | 목적 |
|------|------|
| **VLLM_ANSWER.md** | ← 당신의 질문에 대한 완벽한 답변 |
| **VLLM_QUICKSTART.md** | 5분 빠른 시작 가이드 |
| **VLLM_SETUP.md** | 완벽한 설정 매뉴얼 |
| **docker-compose.vllm.yml** | STT + vLLM Docker Compose 설정 |
| **test_vllm_integration.py** | 통합 테스트 스크립트 |
| **.env** | 환경 변수 설정 |

---

## ⚡ 가장 빠른 실행 (30초)

```bash
# 1. Docker Compose로 시작
docker-compose -f docker-compose.vllm.yml up -d

# 2. 30초 대기
sleep 30

# 3. 테스트
curl -X POST "http://localhost:8001/transcribe-and-process" \
  -F "file=@audio_samples/test.mp3" \
  -F "language=ko"

# 끝! 🎉
```

---

## 🔍 endpoint 확인 체크리스트

- [ ] vLLM Docker 실행 중? → `curl http://localhost:8000/health`
- [ ] STT Engine 실행 중? → `curl http://localhost:8001/health`
- [ ] VLLM_API_URL 설정됨? → `echo $VLLM_API_URL`
- [ ] 음성 파일 존재? → `ls audio_samples/`
- [ ] 통합 테스트 성공? → `python test_vllm_integration.py --test-vllm`

---

## 💡 주요 포인트

1. **Port 8000**: vLLM 서버
2. **Port 8001**: STT Engine
3. **VLLM_API_URL**: 연결 통로 (로컬: localhost, Docker: vllm, 원격: IP)
4. **자동 연결**: 환경변수만 설정하면 모든 통신 자동
5. **음성 처리**: HTTP POST로 음성 파일 전송

---

## 🚀 다음 단계

1. ✅ VLLM_QUICKSTART.md 따라서 로컬 테스트
2. ✅ docker-compose.vllm.yml로 Docker Compose 테스트
3. ✅ test_vllm_integration.py로 통합 검증
4. ✅ GPU 서버로 배포

**모든 상세 내용은 VLLM_ANSWER.md를 참고하세요!**
