# 통합 vLLM API Base 설계

> **목적**: `get_vllm_qwen_api_base()`를 더 범용적인 `get_vllm_api_base(backend)`로 통합  
> **장점**: 백엔드별 특화 로직을 체계적으로 관리

---

## 🎯 문제점: 현재 방식의 한계

### 현재 설계
```python
# LLMConfig에 추가 예정
def get_vllm_endpoint(task: str) -> str:              # 일반 vLLM
def get_vllm_qwen_api_base() -> str:                 # Qwen 특화
def get_ollama_endpoint() -> str:                    # (미래) Ollama 추가
def get_llama_cpp_endpoint() -> str:                 # (미래) LLaMA.cpp 추가
```

**문제**:
- 메서드가 계속 증가 (백엔드마다 별도 메서드)
- 각 백엔드의 URL 정규화 로직이 중복
- 백엔드 추가 시마다 새 메서드 필요

---

## ✨ 개선된 설계: 백엔드 파라미터화

### 제안된 구조

```python
class LLMConfig(FormDataConfig):
    """LLM 설정 (통합 vLLM API base 구조)"""
    
    # 지원되는 vLLM 백엔드
    SUPPORTED_VLLM_BACKENDS = [
        'default',    # 기본 vLLM (포트 8000)
        'qwen',       # Qwen 전용 (포트 8001, OpenAI 호환)
        'ollama',     # Ollama (포트 11434)
        'llama_cpp',  # LLaMA.cpp (포트 8080)
    ]
    
    # 백엔드별 기본값
    VLLM_BACKEND_DEFAULTS = {
        'default':    'http://localhost:8000/v1',
        'qwen':       'http://localhost:8001/v1',
        'ollama':     'http://localhost:11434/api',
        'llama_cpp':  'http://localhost:8080/v1',
    }
    
    def get_vllm_api_base(self, 
                         backend: str = 'default',
                         task: str = '',
                         default: Optional[str] = None) -> str:
        """
        vLLM API base_url 추출 (모든 백엔드 지원)
        
        우선순위:
        1. FormData 파라미터
        2. 작업별 환경변수
        3. 공용 환경변수
        4. 백엔드 기본값
        
        Args:
            backend: 백엔드 타입 ('default', 'qwen', 'ollama', 'llama_cpp')
            task: 작업명 (privacy, detection 등) - 선택사항
            default: 명시적 기본값 (생략 시 백엔드 기본값 사용)
        
        Returns:
            정규화된 API base_url
        
        Example:
            # Qwen 특화 설정
            qwen_base = config.get_vllm_api_base(backend='qwen', task='privacy')
            
            # 일반 vLLM (task 미지정 시 VLLM_ENDPOINT 환경변수 사용)
            vllm_base = config.get_vllm_api_base(backend='default')
            
            # Ollama
            ollama_base = config.get_vllm_api_base(backend='ollama')
        """
        # 1. 백엔드 검증
        backend = backend.lower()
        if backend not in self.SUPPORTED_VLLM_BACKENDS:
            logger.warning(f"[LLMConfig] Unsupported backend: {backend}. Using 'default'")
            backend = 'default'
        
        # 2. FormData에서 확인 (작업명 포함)
        if task:
            form_key = f"{task}_vllm_{backend}_api_base"
            form_value = self.get_str(form_key)
            if form_value:
                return self._normalize_api_base_by_backend(form_value, backend)
        
        # 3. 작업별 환경변수에서 확인 (작업명 포함)
        if task:
            env_key = f"{task.upper()}_VLLM_{backend.upper()}_API_BASE"
            env_value = os.getenv(env_key, '').strip()
            if env_value:
                return self._normalize_api_base_by_backend(env_value, backend)
        
        # 4. 공용 환경변수에서 확인 (백엔드별 고정 환경변수)
        backend_env_key = f"VLLM_{backend.upper()}_API_BASE"
        backend_env_value = os.getenv(backend_env_key, '').strip()
        if backend_env_value:
            return self._normalize_api_base_by_backend(backend_env_value, backend)
        
        # 5. 작업이 지정되지 않았을 때의 폴백: 공용 VLLM_ENDPOINT
        if backend == 'default':
            common_env = os.getenv('VLLM_ENDPOINT', '').strip()
            if common_env:
                return self._normalize_api_base_by_backend(common_env, backend)
        
        # 6. 명시적 기본값 또는 백엔드 기본값
        final_default = default or self.VLLM_BACKEND_DEFAULTS.get(backend, '')
        return self._normalize_api_base_by_backend(final_default, backend)
    
    def get_vllm_api_key(self, backend: str = 'default', task: str = '') -> str:
        """
        vLLM API 키 추출 (백엔드별 특화)
        
        Args:
            backend: 백엔드 타입 ('default', 'qwen', 'ollama', 'llama_cpp')
            task: 작업명 (privacy, detection 등)
        
        Returns:
            API 키 (없으면 빈 문자열 또는 기본값)
        
        Note:
            - qwen: OPENAI_API_KEY (openai.OpenAI SDK 사용)
            - ollama: 키 불필요 (로컬 서비스)
            - llama_cpp: 키 불필요 (로컬 서비스)
        """
        backend = backend.lower()
        
        # Qwen은 OpenAI 키 사용
        if backend == 'qwen':
            return os.getenv('OPENAI_API_KEY', 'dummy')
        
        # Ollama, LLaMA.cpp는 키 불필요
        if backend in ['ollama', 'llama_cpp']:
            return ''
        
        # 기본 vLLM
        if backend == 'default':
            return os.getenv('VLLM_API_KEY', '')
        
        return ''
    
    @staticmethod
    def _normalize_api_base_by_backend(api_base: str, backend: str) -> str:
        """
        백엔드별 API base_url 정규화
        
        각 백엔드의 특수 요구사항 처리:
        - qwen: OpenAI 호환 → /v1 필수, /chat/completions 제거
        - ollama: 다른 형식 → /api로 끝남
        - llama_cpp: OpenAI 호환 → /v1 필수
        - default: 표준 vLLM → /v1 필수
        
        Args:
            api_base: 원본 URL
            backend: 백엔드 타입
        
        Returns:
            정규화된 URL
        """
        if not api_base:
            return api_base
        
        api_base = api_base.strip()
        
        # 1. Qwen (OpenAI 호환)
        if backend == 'qwen':
            # /chat/completions 제거
            if api_base.endswith("/chat/completions"):
                api_base = api_base.replace("/chat/completions", "")
            
            # /v1 추가 (없을 경우)
            if not api_base.endswith("/v1"):
                api_base = api_base + ("/v1" if api_base.endswith("/") else "/v1")
            
            return api_base
        
        # 2. Ollama (특수 경로)
        if backend == 'ollama':
            # /api로 끝나야 함
            if api_base.endswith("/v1"):
                api_base = api_base.replace("/v1", "/api")
            elif not api_base.endswith("/api"):
                api_base = api_base + ("/api" if api_base.endswith("/") else "/api")
            
            return api_base
        
        # 3. LLaMA.cpp, default (OpenAI 호환)
        if backend in ['llama_cpp', 'default']:
            # /v1로 끝나야 함
            if api_base.endswith("/chat/completions"):
                api_base = api_base.replace("/chat/completions", "")
            
            if not api_base.endswith("/v1"):
                api_base = api_base + ("/v1" if api_base.endswith("/") else "/v1")
            
            return api_base
        
        return api_base
    
    def get_vllm_model_name_for_backend(self, 
                                       backend: str = 'default',
                                       task: str = '') -> str:
        """
        백엔드별 모델명 추출 (백엔드 특화 정규화)
        
        Args:
            backend: 백엔드 타입 ('default', 'qwen', 'ollama', 'llama_cpp')
            task: 작업명 (privacy, detection 등)
        
        Returns:
            정규화된 모델명
        
        Note:
            - Ollama: 모델명 정규화 다를 수 있음 (namespace 처리)
            - Qwen: 표준 정규화 (경로 제거)
        """
        # 기본적으로 get_vllm_model_name 사용
        model_name = self.get_vllm_model_name(task)
        
        # 백엔드별 특화 정규화 (필요시)
        if backend == 'ollama':
            # Ollama는 namespace 형식 (예: library/llama2)
            # 특수 처리 필요 시 추가
            pass
        
        return model_name
```

---

## 📊 환경변수 우선순위 (통합 구조)

### Privacy + Qwen 예시

```
get_vllm_api_base(backend='qwen', task='privacy')

우선순위:
1. FormData[privacy_vllm_qwen_api_base]
   └─ /v1 정규화 (Qwen 특화)

2. env[PRIVACY_VLLM_QWEN_API_BASE]
   └─ /v1 정규화 (Qwen 특화)

3. env[VLLM_QWEN_API_BASE]
   └─ /v1 정규화 (Qwen 특화)

4. env[VLLM_ENDPOINT]  ← 작업 미지정 시에만
   └─ /v1 정규화 (기본값)

5. 백엔드 기본값: http://localhost:8001/v1
   └─ 이미 정규화됨
```

### Detection + Ollama 예시

```
get_vllm_api_base(backend='ollama', task='detection')

우선순위:
1. FormData[detection_vllm_ollama_api_base]
   └─ /api 정규화 (Ollama 특화)

2. env[DETECTION_VLLM_OLLAMA_API_BASE]
   └─ /api 정규화 (Ollama 특화)

3. env[VLLM_OLLAMA_API_BASE]
   └─ /api 정규화 (Ollama 특화)

4. 백엔드 기본값: http://localhost:11434/api
   └─ 이미 정규화됨
```

---

## 🔄 기존 코드와의 호환성

### 기존 메서드 (유지)
```python
# 기존 코드는 그대로 동작
def get_vllm_endpoint(self, task: str, default: str = "http://localhost:8000/v1") -> str:
    """기존 메서드 - 내부적으로 새 메서드 활용"""
    return self.get_vllm_api_base(backend='default', task=task, default=default)
```

### 기존 FormDataConfig 메서드 (유지)
```python
def get_vllm_model_name(self, task: str, default_fallback: Optional[str] = None) -> str:
    """기존 메서드 - 변경 없음"""
    # 기존 로직 그대로
```

### 새로운 Qwen 전용 wrapper (선택)
```python
def get_vllm_qwen_api_base(self, task: str = 'privacy') -> str:
    """편의 메서드 (Qwen만 사용 시)"""
    return self.get_vllm_api_base(backend='qwen', task=task)
```

---

## 💡 사용 예시

### Privacy Removal (Qwen)
```python
# 기존 방식
config = LLMConfig(form_data)
model_name = config.get_vllm_model_name('privacy')
endpoint = config.get_vllm_endpoint('privacy')

# 새로운 방식 (더 명확)
config = LLMConfig(form_data)
model_name = config.get_vllm_model_name('privacy')
api_base = config.get_vllm_api_base(backend='qwen', task='privacy')
api_key = config.get_vllm_api_key(backend='qwen')
```

### Element Detection (Ollama)
```python
config = ElementDetectionConfig(form_data)

# 미래에 Ollama 지원 추가 시
api_base = config.get_vllm_api_base(backend='ollama', task='detection')
model_name = config.get_vllm_model_name_for_backend(backend='ollama', task='detection')
```

### 기본 vLLM
```python
config = LLMConfig(form_data)

# 기존 방식 (호환성 유지)
api_base = config.get_vllm_endpoint('classification')

# 새로운 방식 (명확함)
api_base = config.get_vllm_api_base(backend='default', task='classification')
```

---

## 🎁 이 설계의 장점

### 1. 확장성
```
새로운 백엔드 추가 시:
1. SUPPORTED_VLLM_BACKENDS에 추가
2. VLLM_BACKEND_DEFAULTS에 기본값 추가
3. _normalize_api_base_by_backend() 로직 추가
→ 새 메서드 불필요!
```

### 2. 일관성
```
모든 백엔드가 동일한 인터페이스:
- get_vllm_api_base()
- get_vllm_api_key()
- get_vllm_model_name_for_backend()
```

### 3. 명확성
```
호출 시 백엔드와 작업이 명시적:
config.get_vllm_api_base(backend='qwen', task='privacy')
                         └─────────────────────────┘
                         의도가 분명함
```

### 4. 테스트 용이성
```python
# 백엔드별 독립적인 테스트 가능
def test_qwen_api_base_normalization():
    config = LLMConfig(...)
    result = config.get_vllm_api_base(backend='qwen')
    assert result.endswith('/v1')

def test_ollama_api_base_normalization():
    config = LLMConfig(...)
    result = config.get_vllm_api_base(backend='ollama')
    assert result.endswith('/api')
```

### 5. 중복 제거
```
현재:
- _normalize_api_base() (Qwen용)
- (미래) _normalize_ollama_base()
- (미래) _normalize_llama_cpp_base()

통합 후:
- _normalize_api_base_by_backend(api_base, backend)
  └─ 모든 백엔드 처리
```

---

## 📋 구현 체크리스트

- [ ] LLMConfig에 통합 메서드 추가:
  - `get_vllm_api_base(backend, task, default)`
  - `get_vllm_api_key(backend, task)`
  - `get_vllm_model_name_for_backend(backend, task)`
  - `_normalize_api_base_by_backend(api_base, backend)` (정적)

- [ ] 기존 메서드 호환성 유지:
  - `get_vllm_endpoint()` → `get_vllm_api_base()` 내부 호출로 변경
  
- [ ] 편의 메서드 추가 (선택):
  - `get_vllm_qwen_api_base(task='privacy')`
  - `get_vllm_ollama_api_base(task='')`
  
- [ ] 환경변수 문서 업데이트:
  - VLLM_QWEN_API_BASE (포트 8001)
  - VLLM_OLLAMA_API_BASE (포트 11434)
  - VLLM_LLAMA_CPP_API_BASE (포트 8080)
  
- [ ] 테스트 케이스 추가:
  - 각 백엔드별 정규화 테스트
  - 우선순위 체인 테스트
  - API 키 추출 테스트

- [ ] Privacy Removal 리팩토링:
  - QwenClient 초기화: `config.get_vllm_api_base(backend='qwen')`
  - API 키: `config.get_vllm_api_key(backend='qwen')`

