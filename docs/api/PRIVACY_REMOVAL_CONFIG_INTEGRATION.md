# PrivacyRemovalConfig 통합 분석

> **목적**: Option A 적용 시 기존 Config 클래스와의 겹침 여부 확인  
> **분석 대상**: FormDataConfig, STTConfig, LLMConfig, ElementDetectionConfig

---

## 📊 기존 Config 클래스 구조

### 상속 계층도
```
FormDataConfig (기본 클래스)
├─ STTConfig (STT 엔진 설정)
├─ LLMConfig (LLM 일반 설정)
└─ ElementDetectionConfig (요소 탐지 설정)
```

### 각 클래스의 역할

| 클래스 | 역할 | 주요 메서드 | 대상 서비스 |
|--------|------|-----------|-----------|
| **FormDataConfig** | 기본 타입 변환 및 우선순위 체인 | `get_str()`, `get_bool()`, `get_int()` | 모든 서비스 |
| **STTConfig** | STT 엔진 전용 설정 | `get_preset()`, `get_device()`, `get_backend()` | `stt_engine.py` |
| **LLMConfig** | LLM 프레임워크 설정 (vLLM, Ollama) | `get_llm_type()`, `get_vllm_endpoint()` | Privacy Removal (부분), 다른 LLM 서비스 |
| **ElementDetectionConfig** | 요소 탐지 전용 설정 | `get_detection_api_type()`, `get_agent_url_for_detection()` | Element Detection Service |

---

## ✅ PrivacyRemovalConfig는 새로운 클래스가 필요한가?

### 분석: 기존 LLMConfig로 충분한가?

**현재 LLMConfig가 제공하는 것:**
```python
class LLMConfig(FormDataConfig):
    def get_llm_type(self, task: str) -> str           # ✅ 있음
    def get_vllm_endpoint(self, task: str) -> str      # ✅ 있음
    # 그 외 get_vllm_model_name()은 FormDataConfig에서 상속
```

**Privacy Removal이 필요한 것:**
```python
# 필요 1: vLLM Qwen API base_url 추출
config.get_vllm_qwen_api_base()  # ❌ 없음

# 필요 2: Privacy 전용 모델명
config.get_vllm_model_name('privacy')  # ✅ 이미 있음 (FormDataConfig에서)

# 필요 3: Privacy 전용 endpoint
config.get_vllm_endpoint('privacy')  # ✅ 이미 있음 (LLMConfig에서)

# 필요 4: Prompt type 추출
config.get_privacy_prompt_type()  # ❌ 없음
```

---

## 🎯 겹치는 부분 분석

### 1️⃣ **vLLM 엔드포인트 설정 (겹침)**

```python
# 기존: LLMConfig.get_vllm_endpoint('privacy')
endpoint = config.get_vllm_endpoint('privacy', default="http://localhost:8000/v1")
# → 우선순위: FormData[privacy_vllm_endpoint] 
#             > env[PRIVACY_VLLM_ENDPOINT] 
#             > env[VLLM_ENDPOINT] 
#             > 기본값

# 필요: 동일 기능
privacy_config.get_vllm_endpoint_for_privacy()
# 또는 단순하게
privacy_config.get_vllm_endpoint('privacy')  # 기존 것 사용 가능
```

**결론**: **겹침** ✅  
**해결**: PrivacyRemovalConfig는 LLMConfig 상속 후, `get_vllm_endpoint('privacy')`로 재사용

---

### 2️⃣ **vLLM 모델명 설정 (겹침)**

```python
# 기존: FormDataConfig.get_vllm_model_name('privacy')
model_name = config.get_vllm_model_name('privacy')
# → 우선순위: FormData[privacy_vllm_model_name] 
#             > env[PRIVACY_VLLM_MODEL_NAME] 
#             > env[VLLM_MODEL_NAME] 
#             > constants.VLLM_MODEL_NAME

# 필요: 동일 기능
privacy_config.get_vllm_model_name_for_privacy()
# 또는 단순하게
privacy_config.get_vllm_model_name('privacy')  # 기존 것 사용 가능
```

**결론**: **겹침** ✅  
**해결**: FormDataConfig의 메서드 재사용, wrapper 메서드 선택사항

---

### 3️⃣ **vLLM Qwen API base_url 설정 (새로운 필요)**

```python
# 현재 코드 (privacy_remover.py:307)
api_base = os.getenv("VLLM_QWEN_API_BASE", "http://localhost:8001/v1")

# 필요한 것 (새로운 메서드)
api_base = privacy_config.get_vllm_qwen_api_base()

# 혼동: VLLM_ENDPOINT vs VLLM_QWEN_API_BASE
# - VLLM_ENDPOINT: 일반 vLLM 서버 (모든 모델용)
# - VLLM_QWEN_API_BASE: Qwen 전용 vLLM API (OpenAI 호환)
```

**혼동점**:
- `VLLM_ENDPOINT` (포트 8000) vs `VLLM_QWEN_API_BASE` (포트 8001)
- 두 개의 다른 vLLM 서버를 동시에 운영할 수 있음

**결론**: **겹치지 않음** ✅ 새 메서드 필요

---

### 4️⃣ **Prompt Type 설정 (부분 겹침)**

```python
# 기존 ElementDetectionConfig: 요소 탐지 prompt_type만 있음
# get_detection_types()  # ← 탐지 타입 리스트 (다른 개념)

# 필요: Privacy Removal prompt_type
privacy_config.get_privacy_prompt_type()

# 혼동: "prompt_type"이라는 개념이 없음
# - privacy_removal_*.prompt 파일명이 prompt 타입을 결정
# - SimplePromptProcessor에서 파일 경로 매핑
```

**결론**: **겹치지 않음** ✅ 새 메서드 필요  
**참고**: ElementDetectionConfig의 `get_detection_types()`와는 다른 개념

---

## 📋 권장 통합 방안

### **방안 1: LLMConfig 확장 (권장)**

PrivacyRemovalConfig를 새로 만들지 말고, **LLMConfig에 메서드 추가**

```python
class LLMConfig(FormDataConfig):
    """기존 LLMConfig"""
    # 기존 메서드들...
    
    # ✨ 추가할 메서드 (Privacy Removal 전용)
    
    def get_vllm_qwen_api_base(self, default: str = "http://localhost:8001/v1") -> str:
        """
        Qwen vLLM API base_url (Privacy Removal 전용)
        
        다른 vLLM 엔드포인트와 구분되는 별도의 설정
        """
        form_value = self.get_str('privacy_qwen_api_base')
        if form_value:
            return self._normalize_api_base(form_value)
        
        env_value = os.getenv('VLLM_QWEN_API_BASE', '').strip()
        if env_value:
            return self._normalize_api_base(env_value)
        
        return default
    
    def get_privacy_prompt_type(self, default: str = "privacy_remover_default_v6") -> str:
        """
        Privacy Removal 프롬프트 타입
        """
        return self.get_str('privacy_prompt_type') or os.getenv('PRIVACY_PROMPT_TYPE', default)
    
    @staticmethod
    def _normalize_api_base(api_base: str) -> str:
        """base_url 정규화 (QwenClient 로직 통합)"""
        if api_base.endswith("/chat/completions"):
            api_base = api_base.replace("/chat/completions", "")
        
        if not api_base.endswith("/v1"):
            api_base = api_base + "/v1" if api_base.endswith("/") else api_base + "/v1"
        
        return api_base
```

**장점:**
- ✅ 계층 구조 명확함 (LLMConfig는 모든 LLM 관련 설정)
- ✅ 새 클래스 불필요 (중복 상속 제거)
- ✅ 메서드 재사용 (get_vllm_endpoint('privacy') 그대로 사용)
- ✅ 관리 포인트 단일화

**단점:**
- ⚠️ LLMConfig의 책임 범위가 약간 넓어짐

---

### **방안 2: PrivacyRemovalConfig 신설 (LLMConfig 상속)**

만약 Privacy Removal이 매우 복잡해지면...

```python
class PrivacyRemovalConfig(LLMConfig):
    """Privacy Removal 전용 설정 (LLMConfig 상속)"""
    
    def get_privacy_model_name(self) -> str:
        """단순 wrapper"""
        return self.get_vllm_model_name('privacy')
    
    def get_privacy_endpoint(self) -> str:
        """단순 wrapper"""
        return self.get_vllm_endpoint('privacy')
    
    def get_privacy_qwen_api_base(self) -> str:
        """새로운 메서드"""
        return self.get_vllm_qwen_api_base()
    
    def get_privacy_prompt_type(self) -> str:
        """새로운 메서드"""
        return super().get_privacy_prompt_type()
```

**장점:**
- ✅ Privacy Removal 전용 네이밍
- ✅ 메서드명이 명확함 (get_privacy_model_name vs get_vllm_model_name('privacy'))

**단점:**
- ⚠️ 클래스만 많아지고 실질적 로직은 동일
- ⚠️ wrapper 메서드 남용

---

## 🔍 코드 수준의 겹침 세부 분석

### FormDataConfig 메서드 (이미 있는 것)

```python
get_str(key, default)           # ✅ Privacy Removal도 사용 가능
get_bool(key, default)          # ✅ Privacy Removal도 사용 가능
get_int(key, default)           # ✅ Privacy Removal도 사용 가능
get_vllm_model_name(task, ...)  # ✅ task='privacy' 사용 가능
get_agent_url()                 # ❌ Privacy Removal에는 불필요 (Element Detection 용)
_normalize_model_name(...)      # ⚠️ 프라이빗, 모델명용만
```

### LLMConfig 메서드 (이미 있는 것)

```python
get_llm_type(task, ...)         # ✅ task='privacy' 사용 가능
get_vllm_endpoint(task, ...)    # ✅ task='privacy' 사용 가능
```

### ElementDetectionConfig 메서드 (이미 있는 것)

```python
get_detection_api_type()        # ❌ Privacy Removal에는 불필요 (Element Detection 용)
get_agent_url_for_detection()   # ❌ Privacy Removal에는 불필요
get_vllm_model_name_for_detection()  # ❌ 다른 용도
get_vllm_endpoint_for_detection()    # ❌ 다른 용도
validate_for_ai_agent_mode()    # ❌ Privacy Removal에는 불필요
validate_for_vllm_mode()        # ⚠️ 로직은 재사용 가능, 하지만 메서드명이 다름
```

---

## 💡 최종 권장안

### ✅ **방안 1 사용** (LLMConfig 확장)

```python
# ✨ 수정: api_server/config.py의 LLMConfig에 추가

class LLMConfig(FormDataConfig):
    """기존 코드는 그대로 두고, 다음 메서드만 추가"""
    
    def get_vllm_qwen_api_base(self, default: str = "http://localhost:8001/v1") -> str:
        """Qwen vLLM base_url (VLLM_QWEN_API_BASE 환경변수)"""
        form_value = self.get_str('privacy_qwen_api_base')
        if form_value:
            return self._normalize_api_base(form_value)
        
        env_value = os.getenv('VLLM_QWEN_API_BASE', '').strip()
        if env_value:
            return self._normalize_api_base(env_value)
        
        return default
    
    def get_privacy_prompt_type(self, default: str = "privacy_remover_default_v6") -> str:
        """Privacy Removal 프롬프트 타입"""
        return self.get_str('privacy_prompt_type') or os.getenv('PRIVACY_PROMPT_TYPE', default)
    
    @staticmethod
    def _normalize_api_base(api_base: str) -> str:
        """OpenAI SDK 호환을 위한 base_url 정규화"""
        if api_base.endswith("/chat/completions"):
            api_base = api_base.replace("/chat/completions", "")
        if not api_base.endswith("/v1"):
            api_base = api_base + ("/v1" if api_base.endswith("/") else "/v1")
        return api_base
```

### 사용 방법

```python
# transcribe_endpoint.py에서
config = LLMConfig(form_data)  # 기존 형태

# 기존 메서드 (겹치지 않음)
model_name = config.get_vllm_model_name('privacy')  # ✅ FormDataConfig
endpoint = config.get_vllm_endpoint('privacy')      # ✅ LLMConfig

# 새로운 메서드 (추가됨)
qwen_api_base = config.get_vllm_qwen_api_base()     # ✨ 새로운 메서드
prompt_type = config.get_privacy_prompt_type()      # ✨ 새로운 메서드
```

### 변경 없이 재사용되는 것

```python
# privacy_remover.py QwenClient에서
# 기존:
api_key = os.getenv("OPENAI_API_KEY", "dummy")
api_base = os.getenv("VLLM_QWEN_API_BASE", "http://localhost:8001/v1")

# 리팩토링 후:
api_key = config.get_str('privacy_openai_api_key') or os.getenv("OPENAI_API_KEY", "dummy")
api_base = config.get_vllm_qwen_api_base()  # ← LLMConfig 메서드
```

---

## ❌ 겹치는 것을 피해야 할 이유

1. **STTConfig처럼 분리한 이유**:
   - STT와 LLM은 설정 구조가 완전히 다름
   - STT는 프리셋(speed/accuracy) 중심, LLM은 모델명 중심

2. **ElementDetectionConfig를 분리한 이유**:
   - 탐지는 ai_agent vs vllm 모드에 따라 필수 파라미터가 다름
   - Mode-specific validation 필요

3. **Privacy Removal의 경우**:
   - LLM 기반 서비스 (ElementDetection과 구조 유사)
   - 하지만 특수한 점: 다양한 LLM 클라이언트 (OpenAI, Anthropic, Google, Qwen)
   - **그래서 ElementDetectionConfig처럼 분리할 여지가 있으나, 현재로선 LLMConfig 확장이 충분함**

---

## ✅ 체크리스트 (방안 1 적용 시)

- [ ] LLMConfig에 `get_vllm_qwen_api_base()` 메서드 추가
- [ ] LLMConfig에 `get_privacy_prompt_type()` 메서드 추가
- [ ] LLMConfig에 `_normalize_api_base()` 헬퍼 추가
- [ ] privacy_remover.py QwenClient를 config 사용으로 변경
- [ ] transcribe_endpoint.py 업데이트 (config 전달)
- [ ] 테스트 케이스 추가 (VLLM_QWEN_API_BASE 우선순위)
- [ ] 문서 업데이트 (ENVIRONMENT_VARIABLES.md)

