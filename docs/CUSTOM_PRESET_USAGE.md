# Custom Preset 사용 가이드

## 개요

`custom` preset을 사용하여 **hallucination 문제를 해결하기 위한 개별 설정 최적화**가 가능합니다.

---

## 🔧 Custom Preset의 핵심

### 문제점
- `preset="balanced"` + `faster-whisper`: 20분 이상 파일에서 반복 음절 (예 예 예) 발생
- `preset="accuracy"` + `transformers`: 메모리 사용량 많음

### 솔루션
`custom` preset으로 **세그먼트 설정 세밀 조정**:

```python
# preset이 custom으로 저장되고 유지됨
self.preset = "custom"

# 세그먼트 설정이 self.custom_segment_config에 저장됨
self.custom_segment_config = {
    "chunk_duration": 20,      # 청크 크기 (기본: 30초)
    "overlap_duration": 2      # 오버랩 크기 (기본: 3초)
}

# 다음 transcribe 호출 시 이 설정 자동 사용
```

---

## 📡 API 호출 방식

### 1️⃣ Custom Preset 초기 설정
```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{
    "preset": "custom",
    "backend": "transformers",
    "compute_type": "float32",
    "chunk_duration": 20,
    "overlap_duration": 2
  }' | jq .
```

**응답:**
```json
{
  "status": "success",
  "current_backend": "transformers",
  "preset": "custom",
  "device": "cuda",
  "compute_type": "float32",
  "custom_config": {
    "chunk_duration": 20,
    "overlap_duration": 2
  },
  "message": "..."
}
```

### 2️⃣ Custom 설정 업데이트 (현재 preset 유지)
```bash
# chunk_duration만 변경 (preset은 "custom" 유지)
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{
    "chunk_duration": 15,
    "overlap_duration": 2
  }' | jq .
```

**핵심:** preset 파라미터를 생략하면 현재 `self.preset`이 유지됩니다 ✅

### 3️⃣ 다른 프리셋으로 전환
```bash
# balanced로 전환 (세그먼트 설정 초기화)
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"preset": "balanced"}' | jq .
```

### 4️⃣ 다시 custom으로 돌아오기
```bash
# 이전 custom_segment_config 값이 그대로 유지됨
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{
    "preset": "custom",
    "backend": "transformers"
  }' | jq .
```

---

## 🎯 추천 설정 조합

### Hallucination 최소화 (⭐ 권장)
```json
{
  "preset": "custom",
  "backend": "transformers",
  "compute_type": "float32",
  "chunk_duration": 15,
  "overlap_duration": 2
}
```
- **특징**: 더 작은 청크로 hallucination 누적 방지
- **속도**: ~25초/30초
- **메모리**: ~3GB

### 속도 최적화
```json
{
  "preset": "custom",
  "backend": "faster-whisper",
  "compute_type": "float16",
  "chunk_duration": 30,
  "overlap_duration": 2
}
```
- **특징**: 빠른 처리, 적당한 정확도
- **속도**: ~15초/30초
- **메모리**: ~2GB

### 메모리 최적화
```json
{
  "preset": "custom",
  "backend": "transformers",
  "compute_type": "float32",
  "chunk_duration": 10,
  "overlap_duration": 1
}
```
- **특징**: 매우 작은 청크, 최소 메모리
- **속도**: ~35초/30초
- **메모리**: ~1.5GB

---

## 🔄 동작 흐름

### 첫 번째 호출
```bash
curl -X POST http://localhost:8003/backend/reload \
  -d '{
    "preset": "custom",
    "backend": "transformers",
    "chunk_duration": 20,
    "overlap_duration": 2
  }'
```

**내부 동작:**
```python
# 1. chunk_duration, overlap_duration 저장
self.custom_segment_config["chunk_duration"] = 20
self.custom_segment_config["overlap_duration"] = 2

# 2. preset 저장
self.preset = "custom"

# 3. backend 로드
# (transformers 로드)
```

### 두 번째 호출 (설정 업데이트)
```bash
curl -X POST http://localhost:8003/backend/reload \
  -d '{
    "chunk_duration": 15
  }'
```

**내부 동작:**
```python
# 1. 새로운 chunk_duration만 업데이트
self.custom_segment_config["chunk_duration"] = 15
# overlap_duration은 그대로 2 유지

# 2. preset은 업데이트되지 않음 (여전히 "custom")
self.preset  # 여전히 "custom"

# 3. 다음 transcribe에서 사용
# chunk_duration=15, overlap_duration=2 적용
```

---

## 📊 테스트 시나리오

### 시나리오 1: 20분 파일 hallucination 테스트

**Step 1: Custom preset 설정**
```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{
    "preset": "custom",
    "backend": "transformers",
    "compute_type": "float32",
    "chunk_duration": 15,
    "overlap_duration": 2
  }' | jq '.preset, .custom_config'
```

**Step 2: 파일 변환**
```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/20min_test.wav' \
  | jq '.text' | tail -c 200  # 마지막 200자 확인
```

**예상 결과:**
- ✅ 반복 음절 없음
- ✅ 마지막 부분도 정상 문장

---

## 🔍 상태 확인

### 현재 preset 및 설정 확인
```bash
curl http://localhost:8003/backend/current | jq .
```

**응답 예시:**
```json
{
  "current_backend": "transformers",
  "preset": "custom",
  "custom_config": {
    "chunk_duration": 15,
    "overlap_duration": 2
  },
  "device": "cuda",
  "compute_type": "float32"
}
```

---

## ⚙️ 파일 기반 설정

Docker 환경에서 환경변수로 기본 설정:

```bash
docker run -d \
  -e STT_PRESET=custom \
  -e STT_CHUNK_DURATION=15 \
  -e STT_OVERLAP_DURATION=2 \
  stt-engine:latest
```

> 현재 환경변수 지원은 미포함 (API 호출로 동적 설정)

---

## 💡 팁

1. **Hallucination 발생 시**: `chunk_duration`을 더 줄여보세요 (15 → 10)
2. **속도 개선 필요 시**: `chunk_duration`을 늘려보세요 (15 → 20)
3. **메모리 부족 시**: `chunk_duration`을 줄여보세요 (30 → 15)
4. **Preset 초기화**: `preset="accuracy"` 또는 `"balanced"` 또는 `"speed"`로 전환

---

## 🚀 추천 워크플로우

```bash
# 1️⃣ 현재 상태 확인
curl http://localhost:8003/backend/current | jq .

# 2️⃣ Custom preset 설정
curl -X POST http://localhost:8003/backend/reload \
  -d '{"preset": "custom", "backend": "transformers", "chunk_duration": 15, "overlap_duration": 2}'

# 3️⃣ 테스트 파일 변환
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test_20min.wav'

# 4️⃣ 결과 확인 후 필요시 설정 조정
curl -X POST http://localhost:8003/backend/reload \
  -d '{"chunk_duration": 12}'

# 5️⃣ 다시 테스트
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test_20min.wav'
```
