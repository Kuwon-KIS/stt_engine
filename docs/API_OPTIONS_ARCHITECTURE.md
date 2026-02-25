# API 구조 분석 및 옵션 처리 전략

## 1. 현재 API 현황

### transcribe vs transcribe_v2 차이

| 항목 | `/transcribe` (v2) | `/transcribe_legacy` |
|------|------------------|------------------|
| **상태** | 현재 권장 (신버전) | 호환성 유지용 |
| **엔드포인트** | POST /transcribe | POST /transcribe_legacy |
| **지원 기능** | Privacy, Classification, AI Agent | Privacy Removal만 지원 |
| **파라미터** | 풍부함 (15+개) | 기본적 (5-6개) |
| **주요 파라미터** | file_path, stt_text (NEW), skip_stt (NEW) | file_path만 |

**결론**: 
- `/transcribe` = 최신 다기능 API
- `/transcribe_legacy` = 이전 버전 (호환성 유지)
- **정리 필요**: transcribe_legacy 제거 또는 통합

---

## 2. 옵션 처리 아키텍처

### 현재 파라미터 구조

```python
@app.post("/transcribe")
async def transcribe_v2(
    # === 입력 선택 (A or B) ===
    file_path: str = Form(...),           # A. 오디오 파일
    stt_text: str = Form(None),           # B. 이미 변환된 텍스트 (NEW)
    
    # === STT 제어 ===
    language: str = Form("ko"),
    is_stream: str = Form("false"),
    
    # === 개인정보 처리 ===
    privacy_removal: str = Form("false"),
    privacy_prompt_type: str = Form("privacy_remover_default_v6"),
    
    # === 통화 분류 ===
    classification: str = Form("false"),
    classification_prompt_type: str = Form("classification_default_v1"),
    
    # === AI Agent (요소 탐지) ===
    ai_agent: str = Form("false"),
    ai_agent_type: str = Form("external"),  # "external" | "vllm" | "dummy"
    
    # === (추가) AI Agent 옵션 ===
    incomplete_elements_check: str = Form("false"),
    agent_url: str = Form(""),              # External agent URL
    agent_request_format: str = Form("text_only"),  # "text_only" | "prompt_based"
    
    # === 내보내기 ===
    export: Optional[str] = Query(None),   # "txt" | "json"
):
```

---

## 3. LLM 호출 옵션 처리 방식

### 문제점
현재 각 단계별로 **프롬프트 타입이 고정**되어 있음:
- Privacy Removal: `privacy_prompt_type`
- Classification: `classification_prompt_type`
- AI Agent: 별도 옵션 없음

### 해결책: 옵션 기반 플로우

#### 방식 1: 프롬프트 기반 (현재)
```
text + prompt_type 
    ↓
LLM에 프롬프트와 함께 전송
    ↓
응답 파싱 및 구조화
```

**장점**: 정확한 응답 형식 보장  
**단점**: 프롬프트 변경 시 API 수정 필요

#### 방식 2: 옵션 기반 (권장)
```
text + options {
    mode: "privacy_removal" | "classification" | "detection",
    prompt_type: "default_v6" | "strict" | "loose",
    llm_type: "openai" | "vllm" | "ollama",
    model_name: "gpt-4o" | "llama2" | ...
}
    ↓
LLM 클라이언트가 옵션에 맞는 프롬프트 로드
    ↓
동일한 인터페이스로 처리
```

**장점**: 유연한 설정 변경 가능  
**단점**: 옵션 조합 관리 필요

---

## 4. 개선 방안

### 단계 1: 옵션 통합 객체 정의

```python
from typing import Optional, Literal
from pydantic import BaseModel

class ProcessingOptions(BaseModel):
    """처리 옵션 통합 관리"""
    
    # Privacy Removal
    privacy_removal: bool = False
    privacy_prompt_type: str = "privacy_remover_default_v6"
    privacy_llm_type: Literal["openai", "vllm", "ollama"] = "openai"
    
    # Classification
    classification: bool = False
    classification_prompt_type: str = "classification_default_v1"
    classification_llm_type: Literal["openai", "vllm"] = "openai"
    
    # AI Agent
    ai_agent: bool = False
    ai_agent_type: Literal["external", "vllm", "dummy"] = "external"
    agent_url: str = ""
    agent_request_format: Literal["text_only", "prompt_based"] = "text_only"
    incomplete_elements_check: bool = False
    
    # LLM 모델 명시 (선택)
    vllm_model_name: Optional[str] = None  # "llama2", "qwen", ...
    ollama_model_name: Optional[str] = None  # "llama2", "mistral", ...
```

### 단계 2: 통합 엔드포인트

```python
@app.post("/transcribe")
async def transcribe(
    # 입력 선택
    file_path: Optional[str] = Form(None),
    stt_text: Optional[str] = Form(None),
    
    # 기본 설정
    language: str = Form("ko"),
    is_stream: str = Form("false"),
    
    # 처리 옵션 (FormData로 받기)
    privacy_removal: str = Form("false"),
    privacy_prompt_type: str = Form("privacy_remover_default_v6"),
    privacy_llm_type: str = Form("openai"),
    
    classification: str = Form("false"),
    classification_prompt_type: str = Form("classification_default_v1"),
    classification_llm_type: str = Form("openai"),
    
    ai_agent: str = Form("false"),
    ai_agent_type: str = Form("external"),
    agent_url: str = Form(""),
    agent_request_format: str = Form("text_only"),
    incomplete_elements_check: str = Form("false"),
    
    vllm_model_name: Optional[str] = Form(None),
    ollama_model_name: Optional[str] = Form(None),
    
    export: Optional[str] = Query(None),
):
    """
    통합 STT + 후처리 API
    
    입력 방식 선택:
    1. file_path: 오디오 파일 경로 → STT 수행 후 후처리
    2. stt_text: 이미 변환된 텍스트 → 후처리만 수행
    
    처리 옵션:
    - privacy_removal=true: 개인정보 제거
    - classification=true: 통화 분류  
    - ai_agent=true: 부당권유/불완전판매 탐지
    
    LLM 선택:
    - privacy_llm_type: "openai", "vllm", "ollama"
    - vllm_model_name: vLLM 사용시 모델명 (선택)
    - ollama_model_name: Ollama 사용시 모델명 (선택)
    """
    
    # 1. 옵션 객체 생성
    options = ProcessingOptions(
        privacy_removal=privacy_removal.lower() == 'true',
        privacy_prompt_type=privacy_prompt_type,
        privacy_llm_type=privacy_llm_type,
        
        classification=classification.lower() == 'true',
        classification_prompt_type=classification_prompt_type,
        classification_llm_type=classification_llm_type,
        
        ai_agent=ai_agent.lower() == 'true',
        ai_agent_type=ai_agent_type,
        agent_url=agent_url,
        agent_request_format=agent_request_format,
        incomplete_elements_check=incomplete_elements_check.lower() == 'true',
        
        vllm_model_name=vllm_model_name,
        ollama_model_name=ollama_model_name,
    )
    
    # 2. 입력 검증
    if file_path and stt_text:
        raise HTTPException(400, "file_path와 stt_text 중 하나만 제공하세요")
    if not file_path and not stt_text:
        raise HTTPException(400, "file_path 또는 stt_text 중 하나를 제공하세요")
    
    # 3. STT 단계
    if file_path:
        stt_result = await perform_stt(file_path, language, is_stream)
        text = stt_result.get('text', '')
    else:
        text = stt_text
        stt_result = {'text': text, 'language': language, 'skipped': True}
    
    # 4. 후처리 파이프라인
    result = await run_processing_pipeline(text, options)
    
    return result
```

### 단계 3: 처리 파이프라인 함수

```python
async def run_processing_pipeline(text: str, options: ProcessingOptions) -> dict:
    """통합 처리 파이프라인"""
    
    result = {
        "text": text,
        "processing_steps": {}
    }
    
    # Privacy Removal
    if options.privacy_removal:
        privacy_result = await perform_privacy_removal(
            text=text,
            prompt_type=options.privacy_prompt_type,
            llm_type=options.privacy_llm_type,
            model_name=options.vllm_model_name if options.privacy_llm_type == "vllm" else None
        )
        result["processing_steps"]["privacy_removal"] = privacy_result
        text = privacy_result.get("cleaned_text", text)
    
    # Classification
    if options.classification:
        classification_result = await perform_classification(
            text=text,
            prompt_type=options.classification_prompt_type,
            llm_type=options.classification_llm_type,
            model_name=options.vllm_model_name if options.classification_llm_type == "vllm" else None
        )
        result["processing_steps"]["classification"] = classification_result
    
    # AI Agent
    if options.ai_agent:
        agent_result = await perform_ai_agent(
            text=text,
            agent_type=options.ai_agent_type,
            agent_url=options.agent_url,
            request_format=options.agent_request_format,
            model_name=options.vllm_model_name if options.ai_agent_type == "vllm" else None
        )
        result["processing_steps"]["ai_agent"] = agent_result
    
    return result
```

---

## 5. 사용 예제

### 예제 1: 기존 방식 (음성파일)
```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/test.wav' \
  -F 'privacy_removal=true' \
  -F 'classification=true' \
  -F 'privacy_llm_type=openai'
```

### 예제 2: 새로운 방식 (텍스트 입력)
```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=김철수님(010-1234-5678) 저희 상품 가입하셔야 합니다' \
  -F 'privacy_removal=true' \
  -F 'privacy_llm_type=vllm' \
  -F 'vllm_model_name=llama2' \
  -F 'classification=true' \
  -F 'ai_agent=true' \
  -F 'ai_agent_type=vllm'
```

### 예제 3: Ollama 로컬 사용
```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=테스트 텍스트' \
  -F 'privacy_removal=true' \
  -F 'privacy_llm_type=ollama' \
  -F 'ollama_model_name=llama2' \
  -F 'classification=true' \
  -F 'classification_llm_type=ollama'
```

---

## 6. 코드 정리 계획

### 현재 상태
- `/transcribe` (v2): 최신, 다기능 ✅
- `/transcribe_legacy`: 호환성 유지용 (불필요)

### 정리 방안

**Option A: 완전 통합 (권장)**
```
1. /transcribe_legacy 제거
2. /transcribe에 모든 옵션 통합
3. 기존 코드는 호환성 유지 (new parameters optional)
```

**Option B: 점진적 마이그레이션**
```
1. /transcribe_legacy 유지 (경고 추가)
2. /transcribe에 모든 기능 통합
3. 문서에서 /transcribe_legacy 사용 권유 안 함
4. 향후 2-3 버전 후 제거
```

**권장**: Option A (완전 통합)

---

## 7. 구현 우선순위

### Phase 1: 기본 텍스트 입력 (1-2시간)
- [ ] `/transcribe` 파라미터 확장 (stt_text, skip_stt)
- [ ] STT 단계 조건부 처리
- [ ] 기존 기능 호환성 유지

### Phase 2: LLM 타입 선택 (2-3시간)
- [ ] `privacy_llm_type`, `classification_llm_type` 파라미터 추가
- [ ] LLM 클라이언트 선택 로직 구현
- [ ] vLLM/Ollama 클라이언트 확인

### Phase 3: 옵션 통합 (3-4시간)
- [ ] `ProcessingOptions` 클래스 정의
- [ ] `run_processing_pipeline()` 함수 리팩토링
- [ ] 각 LLM별 모델명 파라미터 추가

### Phase 4: 코드 정리 및 통합 (2시간)
- [ ] `/transcribe_legacy` 제거
- [ ] 문서 업데이트
- [ ] 테스트 케이스 작성

---

## 8. 응답 예제

### 텍스트 입력 + Privacy Removal + Classification + AI Agent
```json
{
  "success": true,
  "text": "김철수님(010-1234-5678) 저희 상품 가입하셔야 합니다",
  "processing_steps": {
    "stt": {
      "skipped": true,
      "reason": "Text input provided"
    },
    "privacy_removal": {
      "completed": true,
      "llm_type": "vllm",
      "model_name": "llama2",
      "cleaned_text": "고객님 저희 상품 가입하셔야 합니다",
      "privacy_entities": [
        {"type": "person_name", "value": "김철수"},
        {"type": "phone", "value": "010-1234-5678"}
      ]
    },
    "classification": {
      "completed": true,
      "code": "100-200",
      "category": "주의",
      "confidence": 0.87
    },
    "ai_agent": {
      "completed": true,
      "agent_type": "vllm",
      "improper_detection": {
        "detected": true,
        "confidence": 0.92,
        "reason": "강압적 판매 표현 사용"
      },
      "incomplete_detection": {
        "detected": false,
        "confidence": 0.15
      }
    }
  },
  "processing_time": 3.45
}
```

