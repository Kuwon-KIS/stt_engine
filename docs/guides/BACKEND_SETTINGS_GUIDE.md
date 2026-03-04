# STT 백엔드 설정 가이드

> **빠른 시작**: 정확도를 우선으로 하려면 다음 API를 호출하세요!
```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "accuracy"}'
```

---

## 📋 백엔드 비교표

| 항목 | faster-whisper (int8) | faster-whisper (float16) | transformers | openai-whisper |
|------|----------------------|--------------------------|--------------|----------------|
| **속도** | ⚡⚡⚡ 매우 빠름 | ⚡⚡ 빠름 | ⚡ 중간 | ⚡ 중간 |
| **정확도** | 🎯 좋음 | 🎯🎯 매우 좋음 | 🎯🎯 매우 좋음 | 🎯🎯 매우 좋음 |
| **메모리** | 💾 매우 적음 | 💾 적음 | 💾💾 많음 | 💾💾 많음 |
| **정밀도** | int8 양자화 | float16 반정밀도 | float32 전정밀도 | float32 전정밀도 |
| **반복 문제** | ⚠️ 가능 | ✅ 없음 | ✅ 없음 | ✅ 없음 |
| **권장 용도** | 실시간 처리 | 균형잡힌 처리 | **정확도 중시** ⭐ | 호환성 |

---

## 🎯 프리셋 모드 (권장)

### 1️⃣ 정확도 우선 (ACCURACY) ⭐ 권장
**가장 정확한 결과** (반복 문제 없음)

```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "accuracy"}'
```

**설정:**
- 백엔드: `transformers`
- 정밀도: `float32` (원본 모델)
- 장점: 최고 정확도, 반복 문제 없음
- 단점: 가장 느림, 메모리 많이 필요
- **권장: 정확도가 중요한 경우**

**내부 파라미터 (최적화됨):**
```python
model.generate(
    input_features,
    num_beams=5,              # 빔 서치 (기본 1) → 5배 더 정확한 탐색
    early_stopping=True,      # 조기 종료로 안정성 확보
    temperature=0.0,          # Greedy 방식 (최고 확신 선택)
    repetition_penalty=1.2,   # 중복 단어 억제
    length_penalty=1.0,       # 길이 패널티 (기본값)
    no_repeat_ngram_size=2    # 2-gram 반복 방지
)
```

---

### 2️⃣ 균형 모드 (BALANCED)
**속도와 정확도의 균형**

```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "balanced"}'
```

**설정:**
- 백엔드: `faster-whisper`
- 정밀도: `float16` (반정밀도)
- 장점: 더 정확한 faster-whisper
- 단점: int8보다 느림, 메모리 더 필요
- **권장: 일반적인 사용**

---

### 3️⃣ 속도 우선 (SPEED)
**가장 빠른 처리**

```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "speed"}'
```

**설정:**
- 백엔드: `faster-whisper`
- 정밀도: `int8` (양자화)
- 장점: 매우 빠름, 메모리 적음
- 단점: 정확도 약간 낮음, **반복 문제 가능**
- **권장: 실시간 처리 필요 시**

---

### 4️⃣ 커스텀 설정 (CUSTOM)
**사용자가 backend/device/compute_type을 개별 지정**

```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "custom", "backend": "faster-whisper", "compute_type": "float32", "device": "cuda"}'
```

**설정:**
- 사용자가 각 옵션을 개별 지정
- 백엔드: `faster-whisper` | `transformers` | `openai-whisper`
- 정밀도: `int8` | `float16` | `float32` (faster-whisper만 적용)
- 디바이스: `cuda` | `cpu`
- **권장: 고급 사용자, 세밀한 조정 필요 시**

---

## 🚀 환경변수를 통한 초기화 (Docker 시작 시)

### 프리셋 지정 (권장)
```bash
docker run -e STT_PRESET=accuracy ...
```

**지원 값:**
- `accuracy` (기본): transformers + float32 (최고 정확도)
- `balanced`: faster-whisper + float16
- `speed`: faster-whisper + int8 (가장 빠름)
- `custom`: STT_DEVICE, STT_COMPUTE_TYPE, STT_BACKEND 환경변수 사용

### 디바이스 자동 감지 (기본값)
```bash
# 기본값: auto (실행 시점에 GPU 자동 감지)
docker run -e STT_PRESET=accuracy stt-engine:v1.9.7

# 운영환경 (GPU 있음)
docker run --gpus all -e STT_PRESET=accuracy stt-engine:v1.9.7
# → 자동으로 CUDA 감지하여 GPU 사용

# 빌드환경 (GPU 없음)
docker run -e STT_PRESET=accuracy stt-engine:v1.9.7
# → 자동으로 CPU 감지하여 CPU 사용

# 강제로 CPU 사용 (GPU가 있어도)
docker run --gpus all -e STT_DEVICE=cpu -e STT_PRESET=accuracy stt-engine:v1.9.7
```

**STT_DEVICE 값:**
- `auto` (기본): 실행 시점에 CUDA 자동 감지
  - GPU 있음 → cuda
  - GPU 없음 → cpu
- `cuda`: NVIDIA GPU 사용 (GPU 없으면 에러)
- `cpu`: CPU 사용 (권장: 디버깅, 낮은 사양 환경)

### 커스텀 모드로 세밀한 설정
```bash
docker run \
  -e STT_PRESET=custom \
  -e STT_BACKEND=faster-whisper \
  -e STT_COMPUTE_TYPE=float32 \
  -e STT_DEVICE=cpu \
  ...
```

**주의:**
- `STT_PRESET=custom`이 아니면 STT_DEVICE, STT_COMPUTE_TYPE은 무시됩니다.
- 프리셋이 모든 설정을 결정합니다: `accuracy` → transformers+float32, `speed` → faster-whisper+int8

---

## 🔧 커스텀 모드

각 파라미터를 직접 지정할 수 있습니다.

### 백엔드 선택
```bash
# transformers 백엔드로 변경
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"backend": "transformers"}'

# faster-whisper로 변경
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"backend": "faster-whisper"}'
```

### 정밀도 조정 (faster-whisper만)
```bash
# float32: 최대 정확도
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{
    "backend": "faster-whisper",
    "compute_type": "float32"
  }'

# float16: 균형
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{
    "backend": "faster-whisper",
    "compute_type": "float16"
  }'

# int8: 최고 속도 (양자화)
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{
    "backend": "faster-whisper",
    "compute_type": "int8"
  }'
```

### 디바이스 변경
```bash
# CUDA GPU 사용
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"device": "cuda"}'

# CPU 사용
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"device": "cpu"}'
```

### 종합 예시
```bash
# transformers + float32 + CUDA
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{
    "backend": "transformers",
    "device": "cuda",
    "compute_type": "float32"
  }'
```

---

## 📊 반응 형식

### 성공 응답
```json
{
  "status": "success",
  "message": "백엔드가 변경되었습니다",
  "previous_backend": "faster-whisper",
  "previous_settings": {
    "device": "cuda",
    "compute_type": "int8"
  },
  "current_backend": "transformers",
  "current_device": "cuda",
  "current_compute_type": "float32",
  "backend_info": {
    "current_backend": "transformers",
    "backend_type": "TransformersBackend",
    "device": "cuda",
    "compute_type": "float32",
    "loaded": true
  }
}
```

### 오류 응답
```json
{
  "status": "error",
  "message": "지원하지 않는 프리셋: invalid_preset"
}
```

---

## 🚀 Docker에서 초기 설정

### 속도 우선 (기본)
```bash
docker run -d \
  -e STT_DEVICE=cuda \
  -e STT_COMPUTE_TYPE=int8 \
  -p 8003:8000 \
  stt-engine:latest
```

### 정확도 우선 (권장)
현재 컨테이너 시작 후 다음 API 호출:
```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "accuracy"}'
```

또는 Docker 실행 후 직접 설정:
```bash
# 컨테이너 ID 조회
CONTAINER_ID=$(docker ps | grep stt-engine | awk '{print $1}')

# 정확도 모드로 변경
docker exec $CONTAINER_ID curl -X POST http://localhost:8000/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "accuracy"}'
```

---

## 📈 성능 비교 예시

같은 30초 오디오 파일 기준:

| 백엔드 | 처리 시간 | 정확도 | 메모리 |
|------|--------|------|------|
| faster-whisper (int8) | ~2초 ⚡ | 95% | 2GB |
| faster-whisper (float16) | ~4초 | 97% | 4GB |
| **transformers (float32)** | **~6초** | **99%** ⭐ | **6GB** |
| openai-whisper | ~8초 | 98% | 6GB |

---

## 🔍 현재 설정 확인

```bash
curl http://localhost:8003/backend/current
```

응답:
```json
{
  "current_backend": "transformers",
  "backend_type": "TransformersBackend",
  "device": "cuda",
  "compute_type": "float32",
  "model_path": "/app/models/openai_whisper-large-v3-turbo",
  "loaded": true,
  "available_backends": [
    "faster-whisper",
    "transformers",
    "openai-whisper"
  ]
}
```

---

## ⚠️ 알려진 문제 및 해결책

### 문제 1: faster-whisper에서 반복 단어
**증상:** "안녕하세요" → "안녕하세요 안녕하세요 안녕하세요..."

**원인:** CTranslate2 양자화(int8) 문제

**해결책:**
```bash
# 정확도 모드로 변경
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "accuracy"}'
```

또는 float16 사용:
```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "balanced"}'
```

---

### 문제 2: CUDA 메모리 부족
**증상:** `RuntimeError: CUDA out of memory`

**해결책:**
```bash
# CPU로 변경
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"device": "cpu"}'

# 또는 양자화 사용
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "speed"}'
```

---

### 문제 3: 느린 처리 속도
**증상:** 처리가 너무 오래 걸림

**해결책:**
```bash
# 속도 모드로 변경
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "speed"}'
```

---

## 📚 환경변수 설정 (Docker)

초기 시작 시에만 적용:

```bash
docker run -d \
  -e STT_DEVICE=cuda \           # cpu or cuda
  -e STT_COMPUTE_TYPE=int8 \     # int8, float16, float32
  stt-engine:latest
```

> **참고:** API로 변경한 설정은 컨테이너 재시작 시 초기화됩니다.
> 영구 변경하려면 Docker 환경변수를 조정하세요.

---

## 🎓 추천 설정

### 프로덕션 (일반적)
```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "balanced"}'
```

### 프로덕션 (정확도 중시)
```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "accuracy"}'
```

### 실시간 처리 (콜센터)
```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "speed"}'
```

---

## 📞 문제 해결

문제 발생 시 로그 확인:
```bash
docker logs -f stt-engine
```

백엔드 상태 확인:
```bash
curl http://localhost:8003/health | jq .
```

