# Qwen vLLM 통합 분석

> **목적**: Qwen vLLM 호출에 필요한 정보들을 명확하게 정리  
> **현재 상황**: 환경변수와 설정이 흩어져 있어서 관리가 복잡함

---

## 📋 Qwen vLLM 호출에 필요한 정보들

### 1️⃣ **API 기본 정보**

```
필요한 정보:
├─ api_base: vLLM base URL (예: http://localhost:8001/v1)
├─ api_key: OpenAI API 키 (Qwen은 OpenAI 호환이라 OPENAI_API_KEY 사용)
└─ model_name: 모델명 (예: qwen30_thinking_2507)
```

### 2️⃣ **현재 정보 출처 분산**

```
api_base:
  현재: os.getenv("VLLM_QWEN_API_BASE", "http://localhost:8001/v1")
  위치: privacy_remover.py QwenClient.__init__
  
api_key:
  현재: os.getenv("OPENAI_API_KEY") or "dummy"
  위치: privacy_remover.py QwenClient.__init__
  
model_name:
  현재: os.getenv("VLLM_MODEL_NAME", VLLM_MODEL_NAME)
  위치: privacy_remover.py PrivacyRemoverService.__init__
  
prompt_type:
  현재: 직접 전달 (transcribe_endpoint.py에서)
  위치: transcribe_endpoint.py perform_privacy_removal()
```

### 3️⃣ **정보 간의 연결 관계**

```
model_name이 "qwen" 포함
  ↓
QwenClient 생성 필요
  ↓
api_base와 api_key 필요
  ├─ api_base는 qwen 특화 (포트 8001)
  └─ api_key는 OPENAI_API_KEY

prompt_type과 model_name은 독립적
  ├─ prompt_type: 어떤 프롬프트 템플릿을 쓸지
  └─ model_name: 어떤 모델로 처리할지
```

---

## 🎯 개선 방향

### 현재 문제점

```
❌ 정보들이 여러 곳에 흩어져 있음
   - QwenClient.__init__에서 os.getenv 직접 호출
   - PrivacyRemoverService.__init__에서 VLLM_MODEL_NAME 읽기
   - perform_privacy_removal에서 prompt_type 처리

❌ config 계층이 Qwen에 특화되지 않음
   - LLMConfig는 일반적인 설정만 함
   - Qwen 특화 정보를 명확하게 정리하지 않음

❌ FormData와 환경변수의 우선순위가 불명확
   - Qwen 호출 시 어떤 우선순위를 써야 하는지 불명확
```

### 해결 방향

```
✅ Qwen 호출에 필요한 정보들을 한 곳에 모으기
   - QwenVLLMConfig 또는 PrivacyRemovalQwenConfig 클래스 신설
   - 필요 정보: api_base, api_key, model_name, prompt_type

✅ 명확한 우선순위 체인 정의
   - 각 정보별로 FormData > 환경변수 > 기본값 정의

✅ 정보들 간의 관계 명시
   - model_name = "qwen..." → api_base와 api_key 자동 연결
```

---

## 📊 상세 정보 매핑

### api_base (Qwen 전용 base_url)

```
현재 값:
  위치: privacy_remover.py line 311
  코드: os.getenv("VLLM_QWEN_API_BASE", "http://localhost:8001/v1")

필요 정보:
  - 기본값: http://localhost:8001/v1 (포트 8001, /v1 포함)
  - 환경변수: VLLM_QWEN_API_BASE
  - FormData: (현재 없음 - 추가할 것인가?)

특수 처리:
  - URL 정규화 필요 (/chat/completions 제거, /v1 추가)
  - OpenAI SDK 호환 형식으로 변환

의문점:
  Q1: FormData에서 privacy_removal_qwen_api_base 같은 파라미터 받을 것인가?
  Q2: 아니면 환경변수만 유지할 것인가?
```

### api_key (OpenAI API 키)

```
현재 값:
  위치: privacy_remover.py line 308
  코드: os.getenv("OPENAI_API_KEY") or "dummy"

필요 정보:
  - 기본값: "dummy" (로컬 테스트 시)
  - 환경변수: OPENAI_API_KEY
  - FormData: (현재 없음 - 필요한가?)

특징:
  - Qwen은 OpenAI 호환 API라 OPENAI_API_KEY 사용
  - 실제 키 없으면 "dummy" 사용 가능 (로컬 vLLM)

의문점:
  Q3: FormData에서 api_key 받을 필요가 있는가?
  Q4: 보안상 문제는 없는가?
```

### model_name (vLLM 모델명)

```
현재 값:
  위치: privacy_remover.py PrivacyRemoverService.__init__ line 548
  코드: os.getenv("VLLM_MODEL_NAME", VLLM_MODEL_NAME)

필요 정보:
  - 기본값: constants.VLLM_MODEL_NAME
  - 환경변수: VLLM_MODEL_NAME
  - FormData: vllm_model_name (이미 있음)

정규화:
  - "/model/qwen..." → "qwen..." 처리
  - FormDataConfig._normalize_model_name() 사용

우선순위:
  1. FormData[vllm_model_name]
  2. env[VLLM_MODEL_NAME]
  3. constants.VLLM_MODEL_NAME

연결:
  - model_name이 "qwen"을 포함 → Qwen 호출 필요
  - 이 경우 api_base는 VLLM_QWEN_API_BASE 사용
```

### prompt_type (프롬프트 템플릿 타입)

```
현재 값:
  위치: transcribe_endpoint.py perform_privacy_removal() 파라미터
  기본값: "privacy_remover_default_v6"

필요 정보:
  - 기본값: "privacy_remover_default_v6"
  - 환경변수: PRIVACY_REMOVAL_PROMPT_TYPE (새로 추가할 것인가?)
  - FormData: privacy_prompt_type (이미 있음, app.py에서 처리)

정규화:
  - "privacy_remover_default" → "privacy_remover_default_v6"
  - "privacy_remover_loosed" → "privacy_remover_loosed_contact_v6"

우선순위:
  1. FormData[privacy_prompt_type] (app.py에서 받음)
  2. 기본값 "privacy_remover_default_v6"

참고:
  - model_name과 무관 (어떤 모델을 쓰든 상관없음)
```

---

## 🔄 현재 호출 흐름

```
app.py @router.post("/transcribe")
  ↓
  FormData 파라미터 추출:
  - privacy_removal: bool
  - privacy_prompt_type: str
  - privacy_vllm_model_name: str (없으면 기본값 사용)
  
  ↓
  perform_privacy_removal() 호출
  - text: STT 결과
  - prompt_type: privacy_prompt_type
  - vllm_model_name: privacy_vllm_model_name
  
  ↓
  PrivacyRemoverService.initialize(model_name)
  - model_name: FormData에서 받은 것 또는 환경변수
  
  ↓
  LLMClientFactory.create_client(model_name)
  - model_name에 "qwen" 포함 → QwenClient 생성
  
  ↓
  QwenClient.__init__(model_name)
  - os.getenv("OPENAI_API_KEY") → api_key
  - os.getenv("VLLM_QWEN_API_BASE") → api_base
  - URL 정규화
  - openai.OpenAI(api_key, base_url) 초기화
```

---

## ❓ 주요 의문점

### Q1: FormData에서 Qwen 설정값을 받을 것인가?

**옵션 A**: 환경변수만 (현재)
```
장점:
  - 간단함
  - 로컬 개발 시 .env 파일로 관리 가능
  
단점:
  - 런타임에 다른 vLLM 서버로 전환 불가능
  - 테스트할 때 환경변수 변경 필요
```

**옵션 B**: FormData도 지원
```
장점:
  - 런타임에 유연하게 변경 가능
  - 같은 요청으로 다른 vLLM 서버 사용 가능
  
단점:
  - 코드 복잡도 증가
  - 필요한가?
```

### Q2: model_name이 "qwen"일 때 자동으로 api_base를 VLLM_QWEN_API_BASE로 할 것인가?

**현재 상황**:
```
VLLM_ENDPOINT (포트 8000, 일반 vLLM)
VLLM_QWEN_API_BASE (포트 8001, Qwen 특화)

model_name에 따라 자동으로 선택하는 게 맞나?
```

### Q3: LLMConfig를 유지할 것인가, 아니면 Qwen 전용 Config를 만들 것인가?

**현재 코드**:
```
LLMConfig (일반 LLM 설정)
  ├─ get_vllm_qwen_api_base()
  ├─ get_vllm_qwen_api_key()
  └─ get_vllm_qwen_prompt_type()
```

**문제**:
- 이름이 일관성 없음 (get_vllm_*인데 Qwen 전용)
- Qwen이 주력이지만 이름이 일반적임

**개선안**:
```
PrivacyRemovalQwenConfig (Qwen 전용)
  ├─ get_api_base()
  ├─ get_api_key()
  ├─ get_model_name()
  └─ get_prompt_type()
```

---

## ✅ 필요한 결정사항

1. **FormData에서 vLLM 설정 받을 것인가?**
   - `privacy_removal_qwen_api_base`
   - `privacy_removal_openai_api_key`

2. **model_name으로 api_base 자동 선택할 것인가?**
   - "qwen..." → VLLM_QWEN_API_BASE
   - 다른 모델 → VLLM_ENDPOINT

3. **Config 클래스 이름과 구조?**
   - LLMConfig 유지 vs 새로운 PrivacyRemovalQwenConfig
   - 메서드 네이밍 규칙

4. **우선순위 체인?**
   - FormData > 환경변수 > 기본값
   - 각 정보별 명시

