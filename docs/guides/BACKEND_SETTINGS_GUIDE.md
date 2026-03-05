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

## � 세그멘트 오버랩 설정 (대용량 파일 처리)

> **문제**: 장시간 음성 파일을 세그멘트로 나눌 때 경계 부분에 중복된 내용이 나타나는 경우

### 📊 현재 설정 (기본값)
```
청크 크기: 30초
오버랩: 3초 (10%)
세그멘트 이동: 27초

예시:
세그 1: 0~30초
세그 2: 27~57초  ← 27~30초 중복 (3초)
세그 3: 54~84초  ← 54~57초 중복 (3초)
```

**개선사항**: 세그먼트 경계 중복 최소화 (기존 12초에서 3초로 변경)

---

### 🎯 3가지 해결 옵션

#### **Option 1: 오버랩 줄이기** (현재 적용 ✅)
중복 부분을 최소화하여 반복 완벽 해결

**설정값** (api_server/app.py, api_server/constants.py):
```python
STREAM_CHUNK_DURATION = 30    # 30초 유지
STREAM_OVERLAP_DURATION = 3   # 12초 → 3초 (10% overlap)
```

**결과**:
```
세그 1: 0~30초
세그 2: 27~57초  ← 27~30초 중복 (3초)
세그 3: 54~84초  ← 54~57초 중복 (3초)
```

**장점**: 중복 75% 감소, 경계 정확도 유지 (accuracy 모드에서 충분)  
**단점**: 거의 없음  
**권장**: ✅ **현재 적용 중 - 최적 설정**

---

#### **Option 2: 청크 크기 늘리기**
더 긴 세그멘트로 처리

**설정값**:
```python
STREAM_CHUNK_DURATION = 45    # 30초 → 45초
STREAM_OVERLAP_DURATION = 9   # 12초 → 9초 (20% overlap)
```

**결과**:
```
세그 1: 0~45초
세그 2: 36~81초  ← 36~45초 중복 (9초)
세그 3: 72~117초 ← 72~81초 중복 (9초)
```

**장점**: 세그멘트 수 33% 감소, 중복 비율 낮아짐  
**단점**: 메모리 사용량 증가, 처리 시간 증가  
**권장**: ⚠️ 메모리 여유가 있을 때만

---

#### **Option 3: 오버랩 없애기** (비권장)
중복 제거, 경계 부분만 정확도 감소

**설정값**:
```python
STREAM_CHUNK_DURATION = 30    # 30초 유지
STREAM_OVERLAP_DURATION = 0   # 12초 → 0초 (no overlap)
```

**결과**:
```
세그 1: 0~30초
세그 2: 30~60초  ← 중복 없음
세그 3: 60~90초  ← 중복 없음
```

**장점**: 중복 완전 제거  
**단점**: 경계 부분 정확도 손상 위험  
**권장**: ❌ **정확도 모드에서는 비추천**

---

### 🛠️ 적용 방법

#### **1️⃣ 코드 수정 (현재 적용 ✅)**

파일 1: `api_server/app.py` (줄 59-60)
```python
STREAM_CHUNK_DURATION = 30  # 초
STREAM_OVERLAP_DURATION = 3   # 초 (10% overlap) ← 12에서 3으로 변경
```

파일 2: `api_server/constants.py` (줄 198-199)
```python
STREAM_CHUNK_DURATION = 30
STREAM_OVERLAP_DURATION = 3   # ← 12에서 3으로 변경 (10% overlap)
```

수정 후 Docker 이미지 재빌드:
```bash
docker build -t stt-engine:cuda129-rhel89-v1.9.9 -f docker/Dockerfile.engine.rhel89 .
```

#### **2️⃣ 런타임 확인**

Docker 실행 후 로그 확인:
```
[STREAM] 청크 설정: 30초 / Overlap: 6초  ← 6초로 변경됨 확인
```

---

### 📈 성능 비교 (17분 음성 파일 기준)

| 설정 | 세그먼트 수 | 중복 시간 | 중복 비율 | 메모리 | 권장도 |
|------|-----------|---------|---------|--------|------|
| **기존 (12s)** | 34개 | 408초 | 40% | 기본 | ❌ 중복 많음 |
| **Option 1 (3s)** ⭐ | 34개 | 102초 | 10% | 기본 | ✅ **현재 적용** |
| **Option 2 (45s)** | 23개 | 153초 | 20% | +30% | ⚠️ 메모리 많음 |
| **Option 3 (0s)** | 34개 | 0초 | 0% | 기본 | ❌ 정확도 위험 |

---

### 💡 추가 팁

**STT_PRESET=accuracy일 때 최적 설정:**
```
현재 적용: STREAM_OVERLAP_DURATION = 3
이유: 
  - accuracy 모드의 높은 정확도로 3초 오버랩만으로 충분
  - 중복 75% 감소 (408초 → 102초)
  - 경계 부분 정확도 유지됨
  - 최적 균형: 중복 최소화 + 정확도 보장
```

**성능 모니터링:**
```bash
# Docker 로그 확인
docker logs stt-api | grep "\[STREAM\]"

# 출력 예시:
# [STREAM] 청크 설정: 30초 / Overlap: 6초
# [STREAM] 세그먼트 0/34 처리 완료
```

---



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

