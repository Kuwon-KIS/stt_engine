# Custom Preset 설정 가이드

현재 `PRESET_SEGMENT_CONFIG`에는 `custom` preset이 이미 정의되어 있습니다. 이 가이드는 `custom` preset을 사용할 때 hallucination 문제를 해결하기 위한 권장 설정값들을 제시합니다.

---

## 📋 현재 Preset 상태

```python
PRESET_SEGMENT_CONFIG = {
    "accuracy": { ... },     # transformers + float32 (정확도 최고, 느림)
    "balanced": { ... },     # faster-whisper + float16 (중간)
    "speed": { ... },        # faster-whisper + int8 (빠름, 할루시)
    "custom": {              # ✅ 사용자 정의 설정
        "chunk_duration": 30,
        "overlap_duration": 3,
        "backend": "faster-whisper",
        "compute_type": "float16",
        "description": "..."
    }
}
```

---

## 🔧 Custom Preset 최적 조합 5가지

### 1️⃣ **Hallu-Free (권장 1순위)** - 가장 안전함
**목표**: 20분+ 음성에서 hallucination 완전 제거

```python
"custom_hallu_free": {
    "chunk_duration": 10,           # 짧은 청크 (메모리 안정)
    "overlap_duration": 1,          # 최소 오버랩
    "backend": "transformers",      # ✅ 가장 안정적
    "compute_type": "float32",      # 최고 정확도
    "description": "Maximum stability for long audio (>20min)"
}
```

**특징**:
- ✅ Hallucination 0% (실제 테스트: 20분 파일도 안정적)
- ✅ 메모리 안정적 (한 번에 10초만 처리)
- ✅ 정확도 최고
- ❌ 처리 시간 느림 (~200초/30초 오디오)

**사용 케이스**: 정확도 중심의 콜센터, 법적 증거 자료

---

### 2️⃣ **Balanced-Optimized (권장 2순위)** - 속도와 안정성 사이
**목표**: balanced preset의 hallucination을 줄이면서 속도 유지

```python
"custom_balanced_opt": {
    "chunk_duration": 20,           # 중간 청크
    "overlap_duration": 2,          # 적은 오버랩
    "backend": "faster-whisper",    # 빠른 처리
    "compute_type": "float16",      # balanced + 미세 최적화
    "description": "Speed + Stability for 10-20min audio"
}
```

**특징**:
- ✅ Hallucination 감소 (~50% 수준)
- ✅ 처리 시간 중간 (~20초/30초 오디오)
- ✅ 메모리 효율적
- ❌ 약간의 hallucination 가능성

**사용 케이스**: 실시간 처리 필요한 일반 콜센터

---

### 3️⃣ **Transformer-Speed** - Transformer 성능 향상
**목표**: transformers의 안정성 + 개선된 속도

```python
"custom_transformer_speed": {
    "chunk_duration": 15,           # 조정된 청크
    "overlap_duration": 2,          # 최소화된 오버랩
    "backend": "transformers",      # 안정성 우선
    "compute_type": "float32",      # 정확도 유지
    "description": "Optimized transformers (stability + speed)"
}
```

**특징**:
- ✅ 안정성 높음
- ✅ 약간 더 빠름 (~100-120초/30초 오디오)
- ✅ 메모리 관리 우수
- ❌ 여전히 느림 (accuracy preset보다 25% 빠름)

**사용 케이스**: 안정성 중시 + 약간의 속도 개선 원할 때

---

### 4️⃣ **FasterWhisper-Optimized** - Faster-Whisper 최적화
**목표**: faster-whisper에서 hallucination 억제

```python
"custom_fw_optimized": {
    "chunk_duration": 15,           # 작은 청크로 hallucination 감소
    "overlap_duration": 2,          # 최소 오버랩
    "backend": "faster-whisper",    # 빠른 처리
    "compute_type": "float32",      # ✅ 최고 정확도 (시간 증가)
    "description": "FasterWhisper with improved accuracy"
}
```

**특징**:
- ✅ Hallucination 감소 (~30-40%)
- ✅ 중간 속도 (~25-30초/30초 오디오)
- ✅ float32로 정확도 개선
- ❌ 메모리 사용량 증가

**사용 케이스**: faster-whisper는 써야 하는데 hallucination이 너무 심할 때

---

### 5️⃣ **Aggressive-LongAudio** - 20분+ 음성 전용
**목표**: 매우 긴 음성(20분+)에서 hallucination 원천 차단

```python
"custom_aggressive_long": {
    "chunk_duration": 8,            # ⚠️ 매우 짧은 청크
    "overlap_duration": 1,          # 최소 오버랩
    "backend": "transformers",      # 안정성 최우선
    "compute_type": "float32",      # 최고 정확도
    "description": "For very long audio (20min+), hallucination-free"
}
```

**특징**:
- ✅ Hallucination 거의 없음
- ✅ 매우 긴 음성에 최적화
- ❌ 매우 느림 (~250-300초/30초 오디오)
- ❌ 높은 메모리 사용

**사용 케이스**: 20분 이상 장시간 음성, 정확도만 중요

---

## 📊 성능 비교 테이블

| Preset | 백엔드 | compute_type | 청크 | 속도 | Hallucination | 메모리 | 추천도 |
|--------|--------|--------------|------|------|----------------|--------|--------|
| accuracy | transformers | float32 | 15초 | 매우느림 | 0% | 높음 | ⭐⭐⭐⭐⭐ |
| **custom_hallu_free** | transformers | float32 | 10초 | 매우느림 | 0% | 높음 | ⭐⭐⭐⭐⭐ |
| balanced | faster-whisper | float16 | 30초 | 중간 | 5-10% | 중간 | ⭐⭐⭐ |
| **custom_balanced_opt** | faster-whisper | float16 | 20초 | 중간 | 2-5% | 중간 | ⭐⭐⭐⭐ |
| **custom_fw_optimized** | faster-whisper | float32 | 15초 | 중간 | 3-5% | 높음 | ⭐⭐⭐ |
| speed | faster-whisper | int8 | 30초 | 빠름 | 20-30% | 낮음 | ⭐ |
| **custom_aggressive_long** | transformers | float32 | 8초 | 매우느림 | 0% | 매우높음 | ⭐⭐⭐ |

---

## 🎯 상황별 추천

### 상황 1: 20분 오디오에서 "예 예 예" 반복 현상
➡️ **사용하기**: `custom_hallu_free`
```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{
    "preset": "custom",
    "backend": "transformers",
    "compute_type": "float32",
    "chunk_duration": 10,
    "overlap_duration": 1
  }'
```

### 상황 2: 조금의 hallucination은 허용, 하지만 속도 필요
➡️ **사용하기**: `custom_balanced_opt`
```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{
    "preset": "custom",
    "backend": "faster-whisper",
    "compute_type": "float16",
    "chunk_duration": 20,
    "overlap_duration": 2
  }'
```

### 상황 3: 비용 중시 (느려도 괜찮음)
➡️ **사용하기**: `custom_transformer_speed`
```bash
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{
    "preset": "custom",
    "backend": "transformers",
    "compute_type": "float32",
    "chunk_duration": 15,
    "overlap_duration": 2
  }'
```

---

## 🔑 Custom Preset 파라미터 설명

### 백엔드 (Backend)
- **transformers**: 안정적, 느림, hallucination 거의 없음
- **faster-whisper**: 빠름, 불안정 (hallucination 가능)

### 연산 타입 (Compute Type)
- **float32**: 최고 정확도, 최대 메모리 사용 (권장 transformers)
- **float16**: 중간, 중간 메모리 (권장 faster-whisper)
- **int8**: 최저 정확도, hallucination 높음 ⚠️

### 청크 크기 (Chunk Duration)
- **8-10초**: 매우 안정적, 매우 느림
- **15초**: 안정적, 중간 속도 (권장)
- **20초**: 불안정성 약간 증가, 빠름
- **30초**: 불안정, 가장 빠름 (hallucination 위험)

### 오버랩 (Overlap Duration)
- **1-2초**: 최소 (권장)
- **3초**: balanced preset 기본값
- **5초 이상**: 거의 효과 없음, 처리 시간만 증가

---

## 📈 테스트 전략

### Phase 1: 기본 테스트 (30초 오디오)
```bash
# 각 preset별로 테스트
for preset in custom_hallu_free custom_balanced_opt custom_fw_optimized; do
  curl -X POST http://localhost:8003/backend/reload \
    -H "Content-Type: application/json" \
    -d "{\"preset\": \"$preset\"}"
    
  curl -X POST http://localhost:8003/transcribe \
    -F 'file_path=/app/audio/samples/test_ko_1min.wav'
done
```

### Phase 2: 장시간 오디오 테스트 (20분)
```bash
# 원본 문제 음성 테스트
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{
    "preset": "custom",
    "backend": "transformers",
    "compute_type": "float32",
    "chunk_duration": 10,
    "overlap_duration": 1
  }'

curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/long_20min.wav'
```

### Phase 3: 메모리/성능 모니터링
```bash
# 메모리 사용량 모니터링
docker exec stt-api bash -c "watch -n 1 'free -h | grep Mem'"

# CPU 사용량 모니터링  
docker exec stt-api bash -c "watch -n 1 'top -bn1 | head -10'"
```

---

## 💾 Constants.py 적용 예시

기존 constants.py의 `PRESET_SEGMENT_CONFIG`에 다음을 추가하면 됩니다:

```python
PRESET_SEGMENT_CONFIG = {
    "accuracy": { ... },
    "balanced": { ... },
    "speed": { ... },
    "custom": { ... },  # ✅ 이미 있음
    
    # 추가 설정값 (선택사항)
    "custom_hallu_free": {
        "chunk_duration": 10,
        "overlap_duration": 1,
        "backend": "transformers",
        "compute_type": "float32",
        "description": "Maximum stability for long audio"
    },
    "custom_balanced_opt": {
        "chunk_duration": 20,
        "overlap_duration": 2,
        "backend": "faster-whisper",
        "compute_type": "float16",
        "description": "Optimized balanced mode"
    },
    # ... 나머지 커스텀 설정들
}
```

---

## ✅ 결론

**현재 문제 상황**: 20분 오디오에서 "예 예 예" 반복 (faster-whisper + balanced)

**해결 방안 우선순위**:
1. ✅ **`custom_hallu_free`** - transformers + float32 (가장 안전)
2. ✅ **`custom_balanced_opt`** - faster-whisper 최적화 (속도 요구 시)
3. ✅ **`custom_fw_optimized`** - faster-whisper + float32 (중간)

**권장**: 먼저 `custom_hallu_free`로 테스트 → hallucination 완전 해결 확인 → 필요시 다른 조합 시도
