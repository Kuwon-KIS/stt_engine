# STT 이후 단계 텍스트 기반 테스트 전략

## 문제 정의

- **현황**: STT 기능은 확인됨 ✅
- **필요**: Privacy Removal, Classification, AI Agent 단계를 텍스트로 직접 테스트
- **제약**: 기존 transcribe API와 통합 관리 필요

---

## 방안: `/transcribe` API 파라미터 확장

### 핵심 아이디어
**audio 파일을 건너뛰고 텍스트로 바로 시작하는 옵션** 추가

```python
POST /transcribe
├── 기존 방식: file_path (audio file) 기반
└── 새로운 방식: stt_text (이미 transcribe된 텍스트) 제공
```

---

## 구현 방안

### 1. **API 파라미터 확장** (Best Practice)

현재 `/transcribe` 엔드포인트에 다음 파라미터 추가:

```python
@app.post("/transcribe")
async def transcribe_v2(
    # 기존 파라미터
    file_path: str = Form(None),  # 선택사항으로 변경
    
    # 새로운 파라미터
    stt_text: str = Form(None),   # 텍스트 직접 입력 (파일 대신)
    skip_stt: str = Form("false"), # STT 스킵 플래그
    
    # 나머지는 동일
    language: str = Form("ko"),
    privacy_removal: str = Form("false"),
    classification: str = Form("false"),
    ...
):
```

### 2. **로직 흐름**

```
1. 파라미터 검증
   ├─ file_path와 stt_text 중 하나만 제공 필수
   ├─ 둘 다 제공: 에러 반환
   └─ 둘 다 없음: 에러 반환

2. STT 단계
   ├─ file_path 제공 → 기존 대로 처리 (STT 수행)
   └─ stt_text 제공 → STT 스킵, 제공된 텍스트 사용

3. 이후 단계 (동일)
   ├─ Privacy Removal
   ├─ Classification
   └─ AI Agent
```

### 3. **사용 예제**

#### 기존 방식 (audio 파일)
```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/test.wav' \
  -F 'privacy_removal=true' \
  -F 'classification=true'
```

#### 새로운 방식 (텍스트 직접 입력)
```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=고객님, 저희 상품 정말 좋습니다. 지금 가입하면 할인이 있습니다.' \
  -F 'skip_stt=true' \
  -F 'privacy_removal=true' \
  -F 'classification=true' \
  -F 'ai_agent=true'
```

---

## 구현 체크리스트

### Step 1: API 파라미터 확장
- [ ] `api_server/app.py`의 `transcribe_v2()` 함수 수정
  - `file_path` → 선택사항으로 변경 (기본값: None)
  - `stt_text` 파라미터 추가
  - `skip_stt` 파라미터 추가
  - 파라미터 검증 로직 추가

### Step 2: 로직 흐름 수정
- [ ] `api_server/transcribe_endpoint.py` 함수 수정
  - `validate_and_prepare_file()` → 선택사항으로 변경
  - STT 단계 조건 처리 (file_path or stt_text)
  - 응답에 `skip_stt` 플래그 반영

### Step 3: 테스트 케이스 작성
- [ ] 각 단계별 테스트 스크립트 작성
  - `privacy_removal` 테스트
  - `classification` 테스트
  - `ai_agent` 테스트
  - 전체 파이프라인 테스트

---

## 응답 예제

### 성공 응답 (텍스트 입력 기반)
```json
{
  "success": true,
  "text": "고객님, 저희 상품 정말 좋습니다. 지금 가입하면 할인이 있습니다.",
  "processing_steps": {
    "stt": {
      "completed": true,
      "skipped": true,
      "reason": "Text input provided"
    },
    "privacy_removal": {
      "completed": true,
      "text": "고객님, 저희 상품 정말 좋습니다. 지금 [할인] 있습니다."
    },
    "classification": {
      "completed": true,
      "code": "100-100",
      "category": "정상",
      "confidence": 0.95
    },
    "ai_agent": {
      "completed": true,
      "improper_detection": {...},
      "incomplete_detection": {...}
    }
  },
  "processing_time": 2.34
}
```

---

## 장점

| 항목 | 장점 |
|------|------|
| **통합 관리** | 기존 `/transcribe` 하나로 모든 시나리오 처리 |
| **간단성** | 새 엔드포인트 추가 불필요 |
| **호환성** | 기존 코드 호환성 유지 |
| **테스트 효율** | 다양한 테스트 케이스 쉽게 생성 |
| **프로덕션 준비** | 추후 음성→텍스트→후처리 전체 플로우 제어 가능 |

---

## 단계별 파라미터 조합 테스트

### Phase 1: Privacy Removal 검증
```bash
# 입력 텍스트 (개인정보 포함)
stt_text="김철수 고객님(010-1234-5678), 서울시 강남구 거주"

# 파라미터
privacy_removal=true
classification=false
ai_agent=false

# 결과: 개인정보 제거된 텍스트 확인
```

### Phase 2: Classification 검증
```bash
# 입력 텍스트
stt_text="저희 상품은 부당한 방법으로 판매되고 있습니다"

# 파라미터
privacy_removal=true
classification=true
ai_agent=false

# 결과: 분류 코드 및 신뢰도 확인
```

### Phase 3: AI Agent 검증
```bash
# 입력 텍스트
stt_text="제품 가격을 말씀하지 않고 판매를 강요했습니다"

# 파라미터
privacy_removal=true
classification=true
ai_agent=true
ai_agent_type=external

# 결과: 불완전판매요소 탐지 결과 확인
```

---

## vLLM/Ollama 로컬 연결 테스트

텍스트 기반 테스트가 준비된 후:

```bash
# 1. Ollama 로컬 실행
ollama run llama2

# 2. vLLM 클라이언트 추가
# api_server/services/privacy_remover.py에 OllamaClient 구현

# 3. 텍스트 기반 테스트로 검증
curl -X POST http://localhost:8003/transcribe \
  -F 'stt_text=...' \
  -F 'privacy_removal=true'
```

---

## 다음 단계

1. **즉시**: API 파라미터 확장 구현
2. **단계적**: 각 처리 단계별 테스트 스크립트 작성
3. **최종**: vLLM/Ollama 클라이언트 추가 (선택)

