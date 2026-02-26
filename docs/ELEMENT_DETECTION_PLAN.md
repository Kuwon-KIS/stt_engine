# Element Detection 구현 계획

## 개요
STT 결과에서 상담 요소를 자동 감지하는 기능 구현. 3가지 카테고리로 분류: 사전판매, 사후판매, 일반상담

---

## 완료 항목

### 1. Docker jq 설치 ✅
- `docker/Dockerfile.engine.rhel89` - jq 추가
- `docker/Dockerfile.engine.local` - jq 추가  
- `docker/Dockerfile` - jq 추가
- `web_ui/docker/Dockerfile.web_ui` - jq 추가
- `web_ui/docker/Dockerfile.web_ui.local` - jq 추가

### 2. 환경변수 시스템 확인 ✅
- **STT API**: `api_server/constants.py`에서 VLLM_BASE_URL 기본값 설정
  - 기본값: `http://localhost:8001/v1/chat/completions`
  - 오버라이드: 환경변수 `VLLM_BASE_URL` 사용 가능
  
- **Privacy Removal**: `api_server/services/privacy_remover.py`의 QwenClient
  - 우선순위: `QWEN_API_BASE` → `OPENAI_API_BASE` → `http://localhost:8001/v1` (기본값)

---

## 구현 필요 항목

### 1. 프롬프트 템플릿 생성
**파일**: `api_server/prompts/element_detection.md`

내용:
- 3가지 카테고리 분류 로직 (from scratch/element_detect/sample_question.md)
- 8가지 감지 규칙
- 요구사항: `{{User_Query}}` 플레이홀더 포함

```python
# 로드 방식
from api_server.prompts.element_detection_prompt import load_detection_prompt
prompt = load_detection_prompt("element_detection", user_query=text)
```

### 2. 프롬프트 로더 유틸 생성
**파일**: `api_server/prompts/element_detection_prompt.py`

필요 함수:
- `load_detection_prompt(prompt_name: str, **kwargs) -> str`
- `json_escape(text: str) -> str` - json.dumps() 사용
- `jq_escape(text: str) -> str` - 선택사항 (현재는 json_escape 권장)

### 3. STT API 업데이트
**파일**: `api_server/transcribe_endpoint.py`

변경 사항:
- `_call_local_llm()` 함수에서 element detection 프롬프트 로드
- LLM 응답에서 `category` 필드 파싱 추가
- 응답 형식:
  ```json
  {
    "category": "사전판매|사후판매|일반상담",
    "detected_yn": true/false,
    "detected_sentence": "감지된 문장들...",
    "reasons": ["이유1", "이유2"],
    "keywords": ["키워드1", "키워드2"]
  }
  ```

### 4. Web UI 분석 서비스 업데이트
**파일**: `web_ui/app/services/analysis_service.py`

변경 위치:
- Line 808, 826: 감지 결과 변환 로직
- 기존 형식 → 새 형식으로 변환

변환 예시:
```python
# Before (old)
detection_result = {
    "detected": bool,
    "score": float,
    "segments": []
}

# After (new)
detection_result = {
    "category": str,  # 사전판매/사후판매/일반상담
    "detected_yn": bool,
    "detected_sentences": [str],
    "detected_reasons": [str],
    "detected_keywords": [str]
}
```

### 5. 데이터베이스 스키마 주석 업데이트
**파일**: `web_ui/app/models/database.py`

변경 위치:
- Line 114-122: `improper_detection_results` JSON 필드 주석
- 기존 주석 제거, 새 스키마 구조 설명 추가

현재 필드는 이미 JSON 타입이므로 마이그레이션 불필요

---

## 기술 세부사항

### 환경변수 설정 방식

**Docker 실행 예시**:
```bash
# STT API vLLM 주소 변경
docker run -e VLLM_BASE_URL=http://custom-host:8001/v1/chat/completions [...]

# Privacy Removal vLLM 주소 변경  
docker run -e QWEN_API_BASE=http://custom-host:8001/v1 [...]

# 또는 OPENAI_API_BASE 사용
docker run -e OPENAI_API_BASE=http://custom-host:8001/v1 [...]
```

### JSON 처리
- Python 코드에서: `json.dumps()` 사용 (외부 도구 불필요)
- 환경변수: 직접 전달 (설정 파일 필요 없음)

---

## 다음 단계

1. [ ] `element_detection.md` 프롬프트 템플릿 생성
2. [ ] `element_detection_prompt.py` 로더 구현
3. [ ] `transcribe_endpoint.py` category 파싱 추가
4. [ ] `analysis_service.py` 결과 변환 로직 업데이트
5. [ ] `database.py` 스키마 주석 업데이트
6. [ ] 테스트: docker cp로 변경사항 적용 후 재시작
7. [ ] element detection 엔드포인트 테스트

---

## 참고 자료

- Sample Prompt: `scratch/element_detect/sample_question.md`
- Test Script: `scratch/element_detect/test_qwen.sh`
- Privacy Remover 구현: `api_server/services/privacy_remover.py` (Line 300-370)
- Current Config: `api_server/constants.py` (Line 210, 214)

---

## 상태
- **작성 일시**: 2026-02-26
- **담당자**: 요청 예정
- **우선순위**: 중간 (다른 에러 처리 후)
