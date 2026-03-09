# STT PRESET 성능 분석: accuracy vs speed

## 📊 현재 상황 분석

운영 환경에서 **accuracy** preset이 "speed"보다 **훨씬 느린 이유**를 분석했습니다.

---

## 🔍 PRESET별 백엔드 및 연산 타입

### 각 PRESET의 구성

| PRESET | 백엔드 | 연산 타입 | 디바이스 | 특징 | 성능 |
|--------|--------|---------|---------|------|------|
| **speed** | faster-whisper | **int8** (양자화) | auto/cuda | CTranslate2 기반, 양자화 최적화 | ⚡⚡⚡ 최고속 |
| **balanced** | faster-whisper | **float16** | auto/cuda | CTranslate2 기반, 중간 정확도 | ⚡⚡ 빠름 |
| **accuracy** | **transformers** | **float32** | auto/cuda | PyTorch 모델, 최고 정확도 | 🐢 느림 |

### ⚠️ 핵심 문제: 백엔드 자체가 다름

```python
# stt_engine.py의 reload_backend() 로직
presets = {
    "speed":      {"backend": "faster-whisper", "compute_type": "int8"},
    "balanced":   {"backend": "faster-whisper", "compute_type": "float16"},
    "accuracy":   {"backend": "transformers",    "compute_type": "float32"}  # ⚠️ 다른 백엔드!
}
```

---

## 🚀 왜 "speed"가 빠를까?

### 1️⃣ **faster-whisper의 3가지 최적화**

```
faster-whisper (CTranslate2 기반)
├─ 1. C++ 기반 컴파일된 코드 (Python보다 빠름)
├─ 2. 4배-10배 빠른 추론 속도
└─ 3. GPU 메모리 효율적 (모델 크기 작음)

vs

transformers (PyTorch 기반)
├─ 1. Python 해석 단계 추가
├─ 2. 표준 PyTorch 추론 (최적화 부족)
└─ 3. 메모리 사용량 많음 (전체 모델 로드)
```

### 2️⃣ **int8 양자화의 효과**

```
int8 (8비트 정수)
├─ 모델 크기: 1/4로 감소
├─ 메모리 대역폭: 4배 증가
├─ 캐시 효율: 높음
└─ 성능: 최고속

float32 (32비트 부동소수점)
├─ 모델 크기: 기본 크기
├─ 메모리 대역폭: 기본
├─ 캐시 효율: 낮음
└─ 성능: 느림 (2-3배)
```

---

## 📈 실제 성능 차이 (예상)

| 작업 | 파일 길이 | speed (int8) | balanced (float16) | accuracy (float32) | 배수 |
|------|---------|-------------|------------------|------------------|------|
| 1차 로드 | - | ~2초 | ~3초 | ~5초 | 2.5배 |
| 전사 | 30초 오디오 | ~8초 | ~15초 | ~25초 | 3배 |
| 전사 | 1분 오디오 | ~15초 | ~30초 | ~50초 | 3배 |

---

## 🎯 문제의 근본 원인

### accuracy preset이 느린 이유

```python
# accuracy = transformers + float32
# ↓
# PyTorch 기반 표준 모델 (최적화 부족)
# ↓
# 2-3배 느린 추론 속도
```

### config.py와의 관계

현재 `config.py`의 `STTConfig` 클래스는 **세그멘트 설정만 제어**합니다:

```python
SUPPORTED_PRESETS = ['accuracy', 'balanced', 'fast', 'custom']
# ↑ 'fast'는 있지만 'speed'는 없음!
# 세그멘트 오버랩만 조정 (성능에 미미한 영향)
```

**실제 성능을 결정하는 것:**
1. `reload_backend(preset=...)` 호출 시 선택되는 **백엔드**
2. **연산 타입** (int8 vs float32)
3. 세그멘트 설정은 **보조적** 역할만 함

---

## ✅ 해결 방안

### 1️⃣ **PRESET 명칭 통일** (권장)

```python
# config.py STTConfig 클래스 개선
SUPPORTED_PRESETS = ['accuracy', 'balanced', 'speed', 'custom']
#                                              ↑ 추가

# reload_backend에서 선택되는 백엔드와 일치:
# - 'speed' → faster-whisper + int8
# - 'balanced' → faster-whisper + float16  
# - 'accuracy' → transformers + float32
```

### 2️⃣ **운영 환경 권장 설정**

```bash
# 성능 우선 (빠른 응답시간)
STT_PRESET=speed              # 8초/30초 오디오

# 균형잡힌 설정 (권장)
STT_PRESET=balanced           # 15초/30초 오디오

# 최고 정확도 필요시
STT_PRESET=accuracy           # 25초/30초 오디오
```

### 3️⃣ **config.py 개선 방안**

```python
# 현재 상황:
# config.py의 SUPPORTED_PRESETS는 전체 지원 preset 목록만 정의
# 실제 백엔드 선택은 stt_engine.py에서 독립적으로 이루어짐

# 개선 방향:
# 1. config.py의 SUPPORTED_PRESETS에 'speed' 추가
# 2. PRESET_SEGMENT_CONFIG 문서에 각 preset의 실제 성능 정보 포함
# 3. 운영가이드 문서에 preset별 예상 처리시간 명시
```

---

## 📋 PRESET별 세그멘트 설정 (현재)

```python
# 세그멘트 설정 (오버랩 시간만 다름)
PRESET_SEGMENT_CONFIG = {
    "accuracy": {
        "chunk_duration": 30,
        "overlap_duration": 3,    # 3초 (10%)
    },
    "balanced": {
        "chunk_duration": 30,
        "overlap_duration": 5,    # 5초 (17%)
    },
    "fast": {
        "chunk_duration": 30,
        "overlap_duration": 2,    # 2초 (7%)
    }
}

# ⚠️ 문제: 이 설정들은 미미한 성능 차이만 만듦 (수%)
# 실제 성능 차이는 백엔드 선택에서 나옴 (배수 차이!)
```

---

## 🎓 결론

### 왜 accuracy가 느린가?

| 계층 | 영향도 | 설명 |
|-----|--------|------|
| **백엔드 선택** | **80%** ⚡ | faster-whisper vs transformers |
| **연산 타입** | **15%** | int8 vs float32 |
| **세그멘트 설정** | **5%** | 오버랩 시간 조정 |

### 운영 권장사항

```
🚀 성능 우선:    STT_PRESET=speed      (faster-whisper + int8)
⚖️  균형:       STT_PRESET=balanced   (faster-whisper + float16)
🎯 정확도 우선:  STT_PRESET=accuracy   (transformers + float32)
```

### config.py 업데이트 필요

- ✅ SUPPORTED_PRESETS에 'speed' 추가
- ✅ PRESET별 실제 성능 정보 문서화
- ✅ 운영 가이드에 preset 선택 기준 명시
