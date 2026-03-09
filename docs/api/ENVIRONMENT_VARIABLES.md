# STT API 서버 환경변수 설정 가이드

> **작성일**: 2026년 3월 9일  
> **대상**: DevOps, 배포 담당자, 개발자

---

## 📋 개요

STT API Docker 컨테이너(stt-api)의 환경변수들을 실제 코드 동작 방식에 따라 정리합니다.

**핵심**: 환경변수들은 독립적이 아니라 **계층적 우선순위**와 **조건부 디펜던시**를 가집니다.

---

## 🎯 STT 설정 (가장 중요)

### **STT_PRESET** ⭐ (Primary 설정)

**설명**: STT 처리의 전체 전략을 결정하는 가장 중요한 환경변수

**기본값**: `"accuracy"`

**허용값**:
- `"accuracy"` - 정확도 우선 (기본값)
- `"balanced"` - 균형 모드
- `"fast"` - 속도 우선
- `"custom"` - 커스텀 모드 (추가 설정 필요)

**동작 방식**:
```
STT_PRESET 선택
  ↓
해당 PRESET_SEGMENT_CONFIG 적용
  ├─ accuracy: chunk=30초, overlap=3초, float32
  ├─ balanced: chunk=30초, overlap=5초, float32
  └─ fast: chunk=30초, overlap=2초, float16

STT_PRESET="custom"인 경우만
  ↓
추가 환경변수 활성화 (STT_DEVICE, STT_COMPUTE_TYPE, STT_BACKEND)
```

**예시**:
```bash
# 기본 사용 (accuracy 프리셋 적용)
docker run stt-api:latest

# 빠른 처리 필요 시
docker run -e STT_PRESET=balanced stt-api:latest

# 커스텀 설정
docker run -e STT_PRESET=custom -e STT_DEVICE=cuda -e STT_BACKEND=faster-whisper stt-api:latest
```

---

### **STT_DEVICE** (조건부 사용)

**설명**: 모델 실행 디바이스 선택

**기본값**: `"auto"`

**허용값**: `"auto"`, `"cuda"`, `"cpu"`

**활성화 조건**:
- ✅ STT_PRESET을 설정하지 않은 경우 (기본값 "accuracy" 사용)
- ✅ STT_PRESET="custom"인 경우 **필수**
- ❌ STT_PRESET="accuracy"/"balanced"/"fast"인 경우 무시됨

**우선순위** (STT_PRESET=custom일 때만):
```
1. STT_DEVICE 환경변수 (명시적으로 설정한 값)
2. 초기 로드 시 device 값 (기본값 "auto")
```

**자세한 동작**:
- `"auto"`: 런타임에 CUDA 가용성 확인 (GPU 있으면 cuda, 없으면 cpu)
- `"cuda"`: NVIDIA GPU 강제 사용
- `"cpu"`: CPU만 사용

**예시**:
```bash
# auto: 자동 감지 (권장)
docker run -e STT_PRESET=custom -e STT_DEVICE=auto stt-api:latest

# CUDA 강제 사용
docker run -e STT_PRESET=custom -e STT_DEVICE=cuda stt-api:latest

# CPU만 사용
docker run -e STT_PRESET=custom -e STT_DEVICE=cpu stt-api:latest
```

---

### **STT_COMPUTE_TYPE** (조건부 사용)

**설명**: 모델 연산 시 사용할 데이터 정밀도

**기본값**: `None` (device/PRESET에 따라 자동 결정)

**허용값**: `"float16"`, `"float32"`, `"bfloat16"` 등

**활성화 조건**:
- ✅ STT_PRESET="custom"인 경우 **필수**
- ❌ 미리정의된 프리셋(accuracy/balanced/fast) 선택 시 무시됨

**우선순위** (STT_PRESET=custom일 때만):
```
1. STT_COMPUTE_TYPE 환경변수 (명시적으로 설정한 값)
2. STT_DEVICE 기반 자동 결정:
   ├─ device="cuda" → "float16" (빠르고 메모리 효율)
   └─ device="cpu" → "float32" (정확도 우선)
```

**예시**:
```bash
# Custom 모드: 수동 지정
docker run \
  -e STT_PRESET=custom \
  -e STT_DEVICE=cuda \
  -e STT_COMPUTE_TYPE=float16 \
  stt-api:latest

# Custom 모드: 자동 선택 (권장)
docker run \
  -e STT_PRESET=custom \
  -e STT_DEVICE=cuda \
  stt-api:latest  # STT_COMPUTE_TYPE 자동 선택: float16
```

---

### **STT_BACKEND** (조건부 사용)

**설명**: 사용할 Whisper 백엔드 지정

**기본값**: `None` (자동 선택)

**허용값**:
- `"faster-whisper"` - CTranslate2 기반 (권장, 가장 빠름)
- `"transformers"` - HuggingFace Transformers (안정적)
- `"openai-whisper"` - OpenAI 공식 모델 (느림)

**활성화 조건**:
- ✅ STT_PRESET="custom"인 경우만 의미있음 **필수**
- ❌ 미리정의된 프리셋 선택 시 자동으로 선택되어 무시됨

**우선순위** (STT_PRESET=custom일 때만):
```
1. STT_BACKEND 환경변수 (명시적으로 설정)
2. 자동 선택 (faster-whisper → transformers → openai-whisper 순서)
```

**코드 동작**:
```python
if initial_preset == "custom":
    custom_backend = os.getenv("STT_BACKEND")  # ← 이 값
    stt.reload_backend(
        preset="custom",
        backend=custom_backend,  # 명시적 지정
        device=custom_device,
        compute_type=custom_compute_type
    )
else:
    # accuracy/balanced/fast: backend 자동 선택
    stt.reload_backend(preset=initial_preset)
```

**예시**:
```bash
# Custom 모드: 특정 백엔드 강제
docker run \
  -e STT_PRESET=custom \
  -e STT_BACKEND=transformers \
  stt-api:latest

# 기본 프리셋 (accuracy): 백엔드 자동 선택
docker run -e STT_PRESET=accuracy stt-api:latest
```

---

## 🔐 Privacy Removal 설정

### **PRIVACY_VLLM_MODEL_NAME**

**설명**: Privacy Removal(개인정보 제거)에 사용할 vLLM 모델

**우선순위**:
```
1. 요청 파라미터 (privacy_vllm_model_name)
2. PRIVACY_VLLM_MODEL_NAME 환경변수
3. VLLM_MODEL_NAME 환경변수
4. constants.py의 VLLM_MODEL_NAME 기본값
```

**기본값**: `constants.VLLM_MODEL_NAME` (예: "qwen30_thinking_2507")

**코드 동작**:
```python
privacy_vllm_model_name = _normalize_model_name(
    form_data.get('privacy_vllm_model_name')  # 1순위
    or os.getenv('PRIVACY_VLLM_MODEL_NAME', ...)  # 2순위
    or os.getenv('VLLM_MODEL_NAME', VLLM_MODEL_NAME)  # 3, 4순위
)
```

**예시**:
```bash
# 특정 모델 지정
docker run -e PRIVACY_VLLM_MODEL_NAME=qwen30_thinking_2507 stt-api:latest

# 공통 모델 사용 (모든 LLM 작업)
docker run -e VLLM_MODEL_NAME=qwen30_thinking_2507 stt-api:latest
```

---

## 🏷️ Classification 설정

### **CLASSIFICATION_VLLM_MODEL_NAME**

**설명**: 통화 분류(Classification)에 사용할 vLLM 모델

**우선순위** (Privacy와 동일):
```
1. 요청 파라미터 (classification_vllm_model_name)
2. CLASSIFICATION_VLLM_MODEL_NAME 환경변수
3. VLLM_MODEL_NAME 환경변수
4. 기본값
```

**예시**:
```bash
docker run -e CLASSIFICATION_VLLM_MODEL_NAME=qwen30_thinking_2507 stt-api:latest
```

---

## 🔍 Element Detection 설정

### **ELEMENT_DETECTION_API_TYPE** (조건부 디펜던시)

**설명**: Element Detection(법규 위반 탐지) 실행 방식

**기본값**: `"fallback"`

**허용값**:
- `"fallback"` - ai_agent 시도 → 실패 시 vllm으로 자동 전환
- `"ai_agent"` - 외부 KIS AI Agent API만 사용
- `"vllm"` - 로컬 vLLM만 사용
- `"external"` - 레거시 (ai_agent 동의어)
- `"local"` - 레거시 (vllm 동의어)

**조건부 디펜던시**:
```
ELEMENT_DETECTION_API_TYPE="ai_agent" 또는 "fallback" 모드
  ↓
EXTERNAL_API_URL 필수
또는
AGENT_URL 필수

ELEMENT_DETECTION_API_TYPE="vllm"
  ↓
DETECTION_VLLM_MODEL_NAME 사용
+ VLLM_BASE_URL 연결
```

**코드 동작**:
```python
# 설정 읽기
detection_api_type_input = form_data.get('detection_api_type') \
    or os.getenv('ELEMENT_DETECTION_API_TYPE', 'fallback')

# 레거시 변환
detection_api_type_map = {'external': 'ai_agent', 'local': 'vllm'}
detection_api_type = detection_api_type_map.get(detection_api_type_input, detection_api_type_input)
```

**예시**:
```bash
# Fallback 모드 (권장) - 외부 API 설정 필수
docker run \
  -e ELEMENT_DETECTION_API_TYPE=fallback \
  -e EXTERNAL_API_URL=https://api.kis.com/v1/detect \
  stt-api:latest

# vLLM만 사용
docker run \
  -e ELEMENT_DETECTION_API_TYPE=vllm \
  -e DETECTION_VLLM_MODEL_NAME=qwen30_thinking_2507 \
  -e VLLM_BASE_URL=http://vllm-server:8001/v1 \
  stt-api:latest

# AI Agent만 사용
docker run \
  -e ELEMENT_DETECTION_API_TYPE=ai_agent \
  -e EXTERNAL_API_URL=https://api.kis.com/v1/detect \
  stt-api:latest
```

---

### **EXTERNAL_API_URL & AGENT_URL** (중복 방지)

**설명**: Element Detection의 외부 AI Agent API 주소

**우선순위**:
```
1. 요청 파라미터 (agent_url)
2. EXTERNAL_API_URL 환경변수 ← 권장
3. AGENT_URL 환경변수 ← 레거시
```

**활성화 조건**:
- ✅ `ELEMENT_DETECTION_API_TYPE="ai_agent"` 또는 `"fallback"`일 때만 사용
- ❌ `ELEMENT_DETECTION_API_TYPE="vllm"`일 때 무시됨

**코드 동작**:
```python
# 순서: 요청 > EXTERNAL_API_URL > AGENT_URL > 빈 문자열
agent_url = form_data.get('agent_url', '') \
    or os.getenv('EXTERNAL_API_URL', \
    or os.getenv('AGENT_URL', ''))
```

**마이그레이션 전략**:
- **현재**: `EXTERNAL_API_URL` 사용 권장
- **레거시**: `AGENT_URL` 지원 (하위호환성)
- **향후**: `AGENT_URL` 제거 예정

**예시**:
```bash
# 새 방식 (권장) ✅
docker run -e EXTERNAL_API_URL=https://api.kis.com/v1/detect stt-api:latest

# 레거시 방식 (호환성 유지)
docker run -e AGENT_URL=https://api.kis.com/v1/detect stt-api:latest
```

---

### **DETECTION_VLLM_MODEL_NAME**

**설명**: Element Detection에 사용할 vLLM 모델

**우선순위**:
```
1. 요청 파라미터 (detection_vllm_model_name)
2. DETECTION_VLLM_MODEL_NAME 환경변수
3. VLLM_MODEL_NAME 환경변수
4. 기본값
```

**활성화 조건**:
- ✅ `ELEMENT_DETECTION_API_TYPE="vllm"` 또는 `"fallback"`일 때 사용
- ❌ `ELEMENT_DETECTION_API_TYPE="ai_agent"`일 때 무시됨

**예시**:
```bash
docker run \
  -e ELEMENT_DETECTION_API_TYPE=vllm \
  -e DETECTION_VLLM_MODEL_NAME=qwen30_thinking_2507 \
  stt-api:latest
```

---

## 🔗 vLLM 공통 설정

### **VLLM_MODEL_NAME** (모든 LLM 작업의 기본값)

**설명**: Privacy, Classification, Element Detection이 모두 사용할 공통 LLM 모델

**우선순위**:
```
각 작업별 모델 환경변수가 없을 때만 사용

예:
- PRIVACY_VLLM_MODEL_NAME이 없으면 VLLM_MODEL_NAME 사용
- CLASSIFICATION_VLLM_MODEL_NAME이 없으면 VLLM_MODEL_NAME 사용
- DETECTION_VLLM_MODEL_NAME이 없으면 VLLM_MODEL_NAME 사용
```

**기본값**: `constants.VLLM_MODEL_NAME`

**사용 사례**:
```bash
# 모든 LLM 작업에 같은 모델 사용
docker run -e VLLM_MODEL_NAME=qwen30_thinking_2507 stt-api:latest
```

---

### **VLLM_BASE_URL** (vLLM 서버 연결)

**설명**: 로컬 vLLM 서버의 연결 주소

**기본값**: `"http://localhost:8001/v1"` 또는 `"http://localhost:8001"`

**형식**: `http://[hostname]:[port]/v1` 또는 `http://[hostname]:[port]`

**활성화 조건**:
- ✅ vLLM을 사용하는 모든 LLM 작업 (Privacy, Classification, Element Detection)
- ✅ Docker Compose에서 vLLM 서버가 별도 컨테이너일 때

**코드 동작**:
```python
# Element Detection에서 사용
vllm_base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8001")

# Privacy Removal, Classification에서도 동일하게 사용
```

**예시**:
```bash
# 로컬 vLLM 서버 (같은 마신)
docker run stt-api:latest  # 기본값 사용

# 별도 vLLM 서버 (다른 호스트)
docker run -e VLLM_BASE_URL=http://vllm-server:8001/v1 stt-api:latest

# Docker Compose 사용
docker run -e VLLM_BASE_URL=http://vllm-service:8001/v1 stt-api:latest
```

---

## 🚀 실전 설정 예제

### 예제 1: 로컬 개발 (기본)
```bash
docker run \
  -e STT_PRESET=balanced \
  -e VLLM_BASE_URL=http://localhost:8001/v1 \
  -e VLLM_MODEL_NAME=qwen30_thinking_2507 \
  -e EXTERNAL_API_URL=https://api.kis.com/v1/detect \
  -p 8003:8003 \
  stt-api:latest
```

### 예제 2: Production (고성능)
```bash
docker run \
  -e STT_PRESET=accuracy \
  -e STT_DEVICE=cuda \
  -e VLLM_BASE_URL=http://vllm-server:8001/v1 \
  -e VLLM_MODEL_NAME=qwen30_thinking_2507 \
  -e ELEMENT_DETECTION_API_TYPE=fallback \
  -e EXTERNAL_API_URL=https://api.kis.com/v1/detect \
  -p 8003:8003 \
  stt-api:latest
```

### 예제 3: Element Detection vLLM만 사용
```bash
docker run \
  -e ELEMENT_DETECTION_API_TYPE=vllm \
  -e DETECTION_VLLM_MODEL_NAME=qwen30_thinking_2507 \
  -e VLLM_BASE_URL=http://vllm-server:8001/v1 \
  -p 8003:8003 \
  stt-api:latest
```

### 예제 4: 커스텀 STT 백엔드
```bash
docker run \
  -e STT_PRESET=custom \
  -e STT_DEVICE=cpu \
  -e STT_COMPUTE_TYPE=float32 \
  -e STT_BACKEND=transformers \
  -p 8003:8003 \
  stt-api:latest
```

---

## 📊 환경변수 체크리스트

**필수 확인 사항**:
```
☐ STT_PRESET 확인 (기본값: accuracy)
  ├─ custom이면 STT_DEVICE, STT_COMPUTE_TYPE, STT_BACKEND 설정 필수
  └─ accuracy/balanced/fast면 위 3개는 무시됨

☐ LLM 모델 설정
  ├─ 작업별: PRIVACY_VLLM_MODEL_NAME, CLASSIFICATION_VLLM_MODEL_NAME, DETECTION_VLLM_MODEL_NAME
  └─ 또는 공통: VLLM_MODEL_NAME

☐ vLLM 서버 연결
  └─ VLLM_BASE_URL (기본값: http://localhost:8001/v1)

☐ Element Detection API
  ├─ ELEMENT_DETECTION_API_TYPE=ai_agent/fallback → EXTERNAL_API_URL 필수
  └─ ELEMENT_DETECTION_API_TYPE=vllm → DETECTION_VLLM_MODEL_NAME + VLLM_BASE_URL 필수

☐ 레거시 호환성
  ├─ AGENT_URL 대신 EXTERNAL_API_URL 사용
  ├─ detection_api_type의 "external"/"local" 대신 "ai_agent"/"vllm" 사용
```

---

## 💡 주의사항

1. **STT_PRESET이 primary 설정**: 모든 STT 동작을 이것이 결정합니다
2. **ELEMENT_DETECTION_API_TYPE에 따라 필수 환경변수가 달라짐**: 확인 필수
3. **EXTERNAL_API_URL과 AGENT_URL은 중복**: EXTERNAL_API_URL 사용 권장
4. **.env 파일**: 프로젝트 루트의 `.env` 파일에서 자동 로드됨

