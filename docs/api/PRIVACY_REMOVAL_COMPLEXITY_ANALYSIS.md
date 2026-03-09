# Privacy Removal 복잡성 분석 및 개선안

> **작성일**: 2026년 3월 9일  
> **대상**: 개발팀, 아키텍처  
> **목적**: Privacy Removal의 복잡한 설정 구조를 정리하고 개선방안 제시

---

## 📋 현재 구조의 복잡성

### 1️⃣ **다층 LLM 클라이언트 구조**

```
┌─ LLMClientFactory (팩토리)
│
├─ OpenAIClient        (OpenAI API용)
├─ AnthropicClient     (Claude용)
├─ GoogleGenerativeAIClient (Gemini용)
└─ QwenClient          (Qwen/vLLM용)  ⚠️ 복잡함
```

**문제점:**
- 4개의 클라이언트 클래스가 각각 다른 로직 구현
- 각 클라이언트가 독립적인 모델명 패턴, API 키, base_url 처리
- **vLLM (Qwen)의 경우 특히 복잡**

### 2️⃣ **QwenClient의 복잡성**

```python
class QwenClient:
    def __init__(self, model_name: str):
        # ⚠️ 복잡한 base_url 처리
        api_base = os.getenv("VLLM_QWEN_API_BASE", "http://localhost:8001/v1")
        
        # ⚠️ URL 검증 로직 (방어 코드)
        if api_base.endswith("/chat/completions"):
            # 제거
            api_base = api_base.replace("/chat/completions", "")
        
        if not api_base.endswith("/v1"):
            # /v1 추가
            api_base = api_base + "/v1"
        
        # OpenAI SDK로 초기화
        self.client = openai.OpenAI(api_key=api_key, base_url=api_base)
```

**문제점:**
- OpenAI SDK 호환 API 사용이라는 비즈니스 로직이 코드에 숨어있음
- base_url 정규화 로직이 필수이지만 반복 코드
- OpenAI API 키가 없어도 "dummy" 값으로 동작 (의도한 건지 불명확)
- 환경변수명 **VLLM_QWEN_API_BASE**는 임의적 (config에 미반영)

### 3️⃣ **설정값 흩어져 있음**

```
Privacy Removal에 필요한 설정값들:
├─ VLLM_MODEL_NAME                    (config.py에서 관리 ✅)
├─ VLLM_QWEN_API_BASE                 (privacy_remover.py에서 직접 os.getenv ❌)
├─ OPENAI_API_KEY                     (privacy_remover.py에서 직접 os.getenv ❌)
├─ privacy_remover_*.prompt (파일)    (PromptLoader에서 관리 ⚠️)
└─ prompt_type 매핑 (dict)            (SimplePromptProcessor에서 관리 ⚠️)
```

**문제점:**
- 일부는 config.py에서 관리, 일부는 privacy_remover.py에서 직접 관리
- 설정 우선순위가 일관성 없음
- FormData로 전달되는 값과 환경변수의 우선순위 명확하지 않음

### 4️⃣ **호출 흐름이 복잡함**

```
app.py /transcribe
  ↓
perform_privacy_removal() [transcribe_endpoint.py]
  ↓
get_privacy_remover_service() [싱글톤]
  ↓
PrivacyRemoverService.initialize()
  ├─ LLMClientFactory.create_client(model_name)
  │   └─ QwenClient (또는 다른 클라이언트)
  │       └─ OpenAI SDK init with base_url
  └─ SimplePromptProcessor init
      └─ PromptLoader init
          └─ 프롬프트 파일 경로 (다중 경로 지원)
  ↓
PrivacyRemoverService.process_text()
  ├─ 프롬프트 생성
  ├─ LLM 호출
  └─ 결과 파싱 (JSON)
```

**문제점:**
- 너무 많은 중간 단계
- 싱글톤 패턴 + 캐시 + 초기화 로직이 복잡
- 에러 발생 시 추적하기 어려움

### 5️⃣ **모델명 정규화 로직**

```python
# privacy_remover.py
self.model_name = os.getenv("VLLM_MODEL_NAME", VLLM_MODEL_NAME)  # 정규화 없음

# transcribe_endpoint.py
model_name = vllm_model_name  # FormData에서 받은 값 그대로 사용

# config.py (FormDataConfig)
def get_vllm_model_name(self, task):
    # ... 정규화 로직 (경로 제거)
    return self._normalize_model_name(...)
```

**문제점:**
- 모델명 정규화가 일관성 없음 (정규화하는 곳, 안 하는 곳 혼재)
- FormData에서 전달된 모델명과 환경변수 모델명의 처리 방식 다름
- `/model/qwen...` vs `qwen...` 형식이 혼용됨

---

## 🎯 개선안

### **Option A: 최소 리팩토링 (단기)**

#### 1. Config 계층 확장
```python
# api_server/config.py에 새로운 메서드 추가

class PrivacyRemovalConfig(FormDataConfig):
    """Privacy Removal 전용 설정"""
    
    def get_qwen_api_base(self) -> str:
        """
        Qwen vLLM API base_url 추출
        
        우선순위:
        1. FormData (privacy_qwen_api_base)
        2. VLLM_QWEN_API_BASE 환경변수
        3. 기본값 (http://localhost:8001/v1)
        """
        # FormData
        form_value = self.get_str('privacy_qwen_api_base')
        if form_value:
            return self._normalize_api_base(form_value)
        
        # 환경변수
        env_value = os.getenv('VLLM_QWEN_API_BASE', '').strip()
        if env_value:
            return self._normalize_api_base(env_value)
        
        # 기본값
        return "http://localhost:8001/v1"
    
    def get_privacy_model_name(self, default_fallback: Optional[str] = None) -> str:
        """
        Privacy Removal 모델명 추출 (get_vllm_model_name('privacy') 사용 가능)
        """
        return self.get_vllm_model_name('privacy', default_fallback)
    
    def get_privacy_prompt_type(self, default: str = "privacy_remover_default_v6") -> str:
        """
        Privacy Removal 프롬프트 타입 추출
        """
        return self.get_str('privacy_prompt_type') or os.getenv('PRIVACY_PROMPT_TYPE', default)
    
    @staticmethod
    def _normalize_api_base(api_base: str) -> str:
        """
        base_url 정규화:
        - /chat/completions 제거
        - /v1 추가 (없을 경우)
        """
        # 1. /chat/completions 제거
        if api_base.endswith("/chat/completions"):
            api_base = api_base.replace("/chat/completions", "")
        
        # 2. /v1 추가 (없을 경우)
        if not api_base.endswith("/v1"):
            if api_base.endswith("/"):
                api_base = api_base + "v1"
            else:
                api_base = api_base + "/v1"
        
        return api_base
```

#### 2. PrivacyRemoverService 단순화
```python
class PrivacyRemoverService:
    """개인정보 제거 서비스"""
    
    def __init__(self):
        self.model_name = None
        self.llm_client = None
        self.prompt_processor = None
    
    async def process(self, text: str, config: PrivacyRemovalConfig) -> Dict:
        """
        Privacy Removal 처리
        
        Args:
            text: 원본 텍스트
            config: PrivacyRemovalConfig 인스턴스 (FormData 파싱됨)
        """
        # 1. 설정 추출
        model_name = config.get_privacy_model_name()
        api_base = config.get_qwen_api_base()
        prompt_type = config.get_privacy_prompt_type()
        
        # 2. 클라이언트 초기화 (한 번만)
        if self.model_name != model_name:
            self.llm_client = LLMClientFactory.create_client_with_config(
                model_name=model_name,
                api_base=api_base  # ← 전달
            )
            self.model_name = model_name
        
        # 3. 처리 수행
        result = await self.llm_client.generate_response(
            prompt=self.prompt_processor.build_prompt(text, prompt_type),
            model_name=model_name,
            max_tokens=32768,
            temperature=0.3
        )
        
        return result
```

---

### **Option B: 전체 리팩토링 (중기, 권장)**

#### 1. LLMClientFactory 개선
```python
class LLMClientConfig:
    """LLM 클라이언트 공통 설정"""
    
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.api_base = kwargs.get('api_base')
        self.api_key = kwargs.get('api_key')
        self.max_tokens = kwargs.get('max_tokens', 32768)
        self.temperature = kwargs.get('temperature', 0.3)

class LLMClientFactory:
    """통일된 LLM 클라이언트 팩토리"""
    
    @staticmethod
    def create_client(config: LLMClientConfig):
        """
        설정 객체를 받아 클라이언트 생성
        """
        model_lower = config.model_name.lower()
        
        if 'qwen' in model_lower:
            return QwenClient(config)  # ← config 전달
        elif 'gpt' in model_lower:
            return OpenAIClient(config)
        # ...
```

#### 2. QwenClient 개선
```python
class QwenClient:
    """Qwen LLM 클라이언트 (OpenAI 호환)"""
    
    def __init__(self, config: LLMClientConfig):
        """
        Args:
            config: LLMClientConfig 인스턴스
                   - model_name: 모델명
                   - api_base: vLLM base_url (정규화됨)
                   - api_key: OpenAI API 키 (선택)
        """
        self.model_name = config.model_name
        self.api_base = config.api_base or "http://localhost:8001/v1"
        self.api_key = config.api_key or "dummy"
        
        # OpenAI SDK 초기화 (base_url이 이미 정규화됨)
        import openai
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
```

#### 3. FormData 파싱 단순화
```python
# transcribe_endpoint.py
async def perform_privacy_removal(form_data: FormData, config: FormDataConfig):
    # 1. 설정 추출
    privacy_config = PrivacyRemovalConfig(form_data)
    
    # 2. 서비스 호출 (간단함)
    service = get_privacy_remover_service()
    result = await service.process(text, privacy_config)
    
    return result
```

---

## 📊 복잡성 비교

### 현재 상태
```
설정 위치:     3곳 (config.py, privacy_remover.py, transcribe_endpoint.py)
클라이언트:    4종류 (OpenAI, Anthropic, Google, Qwen)
호출 깊이:     6단계
정규화 로직:   2곳 (QwenClient, FormDataConfig)
캐시 관리:     싱글톤 + dict 캐시 (혼용)
```

### Option A 후
```
설정 위치:     2곳 (config.py ✅, privacy_remover.py 간소화)
클라이언트:    4종류 (변화 없음)
호출 깊이:     5단계 (1단계 감소)
정규화 로직:   1곳 (config.py에 통합)
캐시 관리:     싱글톤만 (dict 제거)
```

### Option B 후
```
설정 위치:     1곳 (config.py만)
클라이언트:    4종류 (LLMClientConfig로 통합)
호출 깊이:     4단계 (2단계 감소)
정규화 로직:   1곳 (LLMClientConfig에서 수행)
캐시 관리:     싱글톤 + 타입 안전
```

---

## 🔧 즉시 적용 가능한 개선

### 1. PrivacyRemovalConfig 클래스 추가 (5분)
```python
# api_server/config.py 마지막에 추가

class PrivacyRemovalConfig(FormDataConfig):
    """Privacy Removal 전용 설정"""
    pass  # get_qwen_api_base(), get_privacy_model_name() 등 추가
```

### 2. transcribe_endpoint.py 간소화 (10분)
```python
# perform_privacy_removal() 함수 수정
config = PrivacyRemovalConfig(form_data)
service = get_privacy_remover_service()
result = await service.process(text, config)
```

### 3. 문서화 (15분)
- [x] Privacy Removal 설정 플로우 다이어그램
- [x] 각 클라이언트의 필수 설정값 명확화
- [x] base_url 정규화 규칙 명시

---

## 💡 권장사항

### **단기 (이번 주)**
✅ **Option A 적용**: PrivacyRemovalConfig 추가 + 설정 일관성 개선
- 소요시간: 1-2시간
- 리스크: 낮음
- 효과: 중간

### **중기 (다음달)**
🟡 **Option B 준비**: LLMClientConfig 설계 및 리팩토링 계획 수립
- 소요시간: 반나절 (회의 + 설계)
- 리스크: 중간 (광범위 변경)
- 효과: 높음

### **장기 (Q2)**
🔵 **Option B 실행**: 통합 LLM 클라이언트 구조 구현
- 소요시간: 2-3일
- 리스크: 중간 → 통합 테스트 필요
- 효과: 매우 높음 (코드 50% 감소, 유지보수성 크게 개선)

---

## ✅ 체크리스트

- [ ] PrivacyRemovalConfig 클래스 생성
- [ ] VLLM_QWEN_API_BASE를 config에 통합
- [ ] perform_privacy_removal() 간소화
- [ ] 테스트 케이스 추가
- [ ] 문서 업데이트
- [ ] LLMClientConfig 설계 문서 작성
- [ ] Option B 구현 일정 계획

