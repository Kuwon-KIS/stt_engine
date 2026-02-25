# 구현 로드맵 및 액션 플랜

## 현재 상황 요약

### 확인된 사실
1. **기존 API**: `/transcribe` (v2) + `/transcribe_legacy` 이중 구조
2. **옵션**: privacy_llm_type, classification_llm_type 없음 → LLM 선택 불가능
3. **텍스트 입력**: 아직 구현 안 됨
4. **vLLM/Ollama**: 클라이언트 미구현

---

## 권장 구현 순서

### ✅ Phase 1: 기본 텍스트 입력 지원 (필수)

**시간**: 1-2시간  
**목표**: `stt_text` 파라미터로 텍스트 직접 입력 가능

**수정 파일**:
- `api_server/app.py` - `transcribe_v2()` 함수
- `api_server/transcribe_endpoint.py` - `validate_and_prepare_file()` 함수

**체크리스트**:
```
[ ] file_path를 선택사항으로 변경 (기본값: None)
[ ] stt_text 파라미터 추가
[ ] 입력 검증 로직 추가 (둘 중 하나만)
[ ] STT 단계 조건부 처리 (file_path가 있을 때만)
[ ] 응답에 skip_stt 플래그 추가
[ ] 기존 호출 호환성 유지
```

**구현 예**:
```python
# Before
@app.post("/transcribe")
async def transcribe_v2(
    file_path: str = Form(...),  # 필수
    ...
):

# After
@app.post("/transcribe")
async def transcribe_v2(
    file_path: Optional[str] = Form(None),  # 선택
    stt_text: Optional[str] = Form(None),   # NEW
    ...
):
    # 입력 검증
    if not file_path and not stt_text:
        raise HTTPException(400, "file_path 또는 stt_text 제공 필수")
    if file_path and stt_text:
        raise HTTPException(400, "둘 중 하나만 제공하세요")
    
    # STT 단계 분기
    if file_path:
        stt_result = await perform_stt(...)  # 기존
    else:
        stt_result = {'text': stt_text, 'skipped': True}  # 새로운
```

### 🔄 Phase 2: LLM 타입 선택 옵션 추가 (선택)

**시간**: 2-3시간  
**목표**: privacy_llm_type, classification_llm_type 파라미터로 LLM 선택 가능

**수정 파일**:
- `api_server/app.py`
- `api_server/transcribe_endpoint.py`
- `api_server/services/privacy_remover.py`
- `api_server/services/classification_service.py`

**체크리스트**:
```
[ ] privacy_llm_type 파라미터 추가 ("openai" | "vllm" | "ollama")
[ ] classification_llm_type 파라미터 추가
[ ] vllm_model_name, ollama_model_name 파라미터 추가
[ ] perform_privacy_removal()에 llm_type 전달
[ ] perform_classification()에 llm_type 전달
[ ] 각 LLM 클라이언트에서 모델명 처리
```

**구현 예**:
```python
# perform_privacy_removal() 함수 시그니처 확장
async def perform_privacy_removal(
    text: str,
    prompt_type: str = "privacy_remover_default_v6",
    llm_type: str = "openai",  # NEW
    model_name: Optional[str] = None,  # NEW
) -> dict:
    """
    llm_type = "openai": OpenAI API (기존)
    llm_type = "vllm": vLLM 로컬 (NEW)
    llm_type = "ollama": Ollama 로컬 (NEW)
    """
    
    if llm_type == "openai":
        client = LLMClientFactory.create_client("gpt-4o")
    elif llm_type == "vllm":
        # vLLMClient 구현 필요
        client = VLLMClient(model_name or "default-vllm-model")
    elif llm_type == "ollama":
        # OllamaClient 구현 필요
        client = OllamaClient(
            model_name or "llama2",
            api_url=os.getenv("OLLAMA_API_URL", "http://localhost:11434")
        )
    else:
        raise ValueError(f"지원하지 않는 LLM 타입: {llm_type}")
    
    # 프롬프트 로드
    prompt = load_prompt(prompt_type)
    
    # LLM 호출 (동일한 인터페이스)
    response = await client.generate_response(
        prompt=f"{prompt}\n\n{text}",
        temperature=0.3,
        max_tokens=2048
    )
    
    return parse_response(response)
```

### 📋 Phase 3: vLLM/Ollama 클라이언트 구현 (필요시)

**시간**: 3-4시간  
**목표**: vLLM과 Ollama를 통해 로컬 LLM 호출 가능

**수정 파일**:
- `api_server/services/privacy_remover.py` - `VLLMClient` 클래스 추가
- `api_server/services/privacy_remover.py` - `OllamaClient` 클래스 추가

**구현 예**:
```python
class VLLMClient:
    """vLLM 로컬 서버 클라이언트"""
    
    def __init__(self, model_name: str, api_url: str = "http://localhost:8000"):
        self.model_name = model_name
        self.api_url = api_url
    
    async def generate_response(self, prompt: str, **kwargs):
        """
        vLLM API 호출
        POST http://localhost:8000/v1/completions
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/v1/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                result = await response.json()
                return result["choices"][0]["text"]


class OllamaClient:
    """Ollama 로컬 서버 클라이언트"""
    
    def __init__(self, model_name: str, api_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.api_url = api_url
    
    async def generate_response(self, prompt: str, **kwargs):
        """
        Ollama API 호출
        POST http://localhost:11434/api/generate
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": kwargs.get("temperature", 0.7),
            "stream": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                result = await response.json()
                return result["response"]
```

---

## 빠른 시작 (Phase 1만 진행)

### Step 1: 확인 작업 (5분)
```bash
# 현재 API 동작 확인
cd /Users/a113211/workspace/stt_engine

# STT API 실행
python api_server.py &

# 기존 방식 테스트
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/test.wav' \
  -F 'privacy_removal=false'
```

### Step 2: Phase 1 구현 (1-2시간)
1. `api_server/app.py`의 `transcribe_v2()` 함수 수정
2. `api_server/transcribe_endpoint.py` 함수 수정
3. 입력 검증 로직 추가
4. STT 단계 조건부 처리

### Step 3: 테스트 (30분)
```bash
# 텍스트 입력 방식 테스트 (NEW)
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=고객님, 저희 상품 정말 좋습니다' \
  -F 'privacy_removal=true'

# 기존 방식 호환성 테스트 (기존)
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/test.wav' \
  -F 'privacy_removal=true'
```

---

## 옵션 처리 설계 결정

### 질문: "프롬프트 기반 vs 텍스트 기반?"

**답변**: **프롬프트 기반 유지 (변경 없음)**

**이유**:
1. 현재 구조가 이미 프롬프트 기반 ✅
2. 텍스트만으로는 복잡한 지시사항 전달 불가
3. 프롬프트 타입으로 유연성 확보 가능

**옵션 처리 방식**:
```
입력: stt_text + privacy_prompt_type + privacy_llm_type

처리 로직:
1. prompt_type 선택 (privacy_remover_default_v6, loosed, strict 등)
2. LLM 타입 선택 (openai, vllm, ollama)
3. 프롬프트 로드 + 텍스트 결합
4. 해당 LLM 호출
5. 응답 파싱
```

**예**:
```bash
# privacy_prompt_type으로 프롬프트 선택
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=...' \
  -F 'privacy_removal=true' \
  -F 'privacy_prompt_type=privacy_remover_default_v6' \
  -F 'privacy_llm_type=vllm' \
  -F 'vllm_model_name=llama2'
  
# 처리 흐름:
# 1. privacy_remover_default_v6.prompt 파일 로드
# 2. 텍스트와 결합
# 3. vLLM (llama2) 호출
# 4. 응답 파싱
```

---

## 통합 vs 분리 결정

### 현재: `/transcribe` + `/transcribe_legacy`

| API | 상태 | 구현 범위 | 유지 여부 |
|-----|------|---------|---------|
| /transcribe | 현재 사용중 | 모든 기능 | **통합 대상** |
| /transcribe_legacy | 호환성 | 기본만 | **제거 대상** |

### 권장 방안: 통합

```
Before (현재):
/transcribe ──────► (v2, 모든 기능)
/transcribe_legacy → (기본만)

After (통합):
/transcribe ──────► (모든 기능 + 텍스트 입력)
```

**장점**:
- API 하나로 모든 시나리오 처리
- 옵션 관리 단순화
- 유지보수 용이

**작업**:
1. Phase 1-3 구현 완료
2. `/transcribe_legacy` 엔드포인트 제거 (또는 deprecated 처리)
3. 문서 업데이트

---

## 다음 진행 방식

**어떤 방식으로 진행하시겠어요?**

### Option A: Phase 1만 먼저 (권장)
- 텍스트 입력 기능 추가
- 기존 기능 호환성 유지
- 빠른 테스트 가능 (1-2시간)
- 나중에 Phase 2-3 진행 가능

### Option B: Phase 1-3 한번에
- 완전한 LLM 선택 기능 포함
- 시간 소요 (5-6시간)
- 즉시 vLLM/Ollama 테스트 가능

### Option C: Phase 1 + 2만
- 텍스트 입력 + LLM 선택
- 적절한 수준 (3-4시간)
- Phase 3는 나중에 필요할 때

