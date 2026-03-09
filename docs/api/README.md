# STT API 문서

STT (Speech-to-Text) API 서버 관련 문서 및 가이드입니다.

## 📚 주요 문서

### 1. [환경변수 설정](./ENVIRONMENT_VARIABLES.md)
**가장 먼저 읽어야 할 문서**

STT API Docker 컨테이너(stt-api)가 실행될 때 설정되는 모든 환경변수를 정리합니다.
- STT 처리 관련 환경변수 (STT_DEVICE, STT_PRESET 등)
- Privacy Removal 관련 환경변수
- Element Detection 관련 환경변수
- vLLM 서버 연결 환경변수

**대상**: DevOps, 운영팀, 배포 담당자

### 2. [API 리팩토링 요약](./API_REFACTORING_SUMMARY.md)

API 구조 변경사항, 엔드포인트 정의, 요청/응답 형식을 정리합니다.
- `/transcribe` 엔드포인트 상세 명세
- Privacy Removal, Classification, Element Detection 통합
- 단계별 처리 흐름

**대상**: API 개발자, 인터그레이션 담당자

### 3. [API 테스트 가이드](./API_TESTING_GUIDE.md)

실제 API 테스트 방법 및 vLLM, Ollama 연동 가이드입니다.
- cURL, Python, JavaScript를 통한 테스트
- vLLM 서버 설정 및 연동
- 각 기능별 테스트 케이스

**대상**: QA 담당자, 개발자

### 4. [Element Detection 분석 흐름](./ELEMENT_DETECTION_ANALYSIS_FLOW.md)

Element Detection(법규 위반 탐지) 상세 분석 문서입니다.
- 탐지 카테고리 (불완전판매, 공격적 판매)
- 판매단계별 법규 요구사항
- LLM 프롬프트 및 응답 형식

**대상**: 금융규정 담당자, 분석팀

### 5. [Element Detection 코드 레퍼런스](./ELEMENT_DETECTION_CODE_REFERENCE.md)

Element Detection 구현 코드의 자세한 설명입니다.
- 주요 클래스 및 함수 설명
- 프롬프트 파일 위치 및 구성
- 응답 JSON 스키마

**대상**: 백엔드 개발자

### 6. [Element Detection 빠른 시작](./ELEMENT_DETECTION_QUICK_GUIDE.md)

Element Detection 기능을 빠르게 시작하는 가이드입니다.
- 기본 설정 및 활성화 방법
- 간단한 API 호출 예제
- 문제 해결 팁

**대상**: 개발자, 신규 사용자

### 7. [Privacy Removal 구현 검증](./PRIVACY_REMOVAL_IMPLEMENTATION_VALIDATION.md)

개인정보 제거 기능 구현 및 검증 문서입니다.
- 감지되는 개인정보 유형
- 프롬프트 기반 제거 방식
- 테스트 결과

**대상**: 보안팀, 개발자

---

## 🚀 빠른 시작

### 1단계: 환경변수 설정
```bash
# Docker 실행 시 필수 환경변수
export STT_DEVICE=cuda
export VLLM_BASE_URL=http://vllm-server:8001/v1
export VLLM_MODEL_NAME=qwen30_thinking_2507

# 상세 설정은 ENVIRONMENT_VARIABLES.md 참고
```

### 2단계: Docker 시작
```bash
docker run \
  -e STT_DEVICE=cuda \
  -e VLLM_BASE_URL=http://vllm-server:8001/v1 \
  -e VLLM_MODEL_NAME=qwen30_thinking_2507 \
  -p 8003:8003 \
  stt-api:latest
```

### 3단계: API 테스트
```bash
# STT 처리
curl -X POST http://localhost:8003/transcribe \
  -F "file_path=/app/audio.wav"

# Privacy Removal 포함
curl -X POST http://localhost:8003/transcribe \
  -F "file_path=/app/audio.wav" \
  -F "privacy_removal=true"

# Element Detection 포함
curl -X POST http://localhost:8003/transcribe \
  -F "file_path=/app/audio.wav" \
  -F "element_detection=true" \
  -F "detection_api_type=vllm"
```

**상세 테스트 가이드는 [API_TESTING_GUIDE.md](./API_TESTING_GUIDE.md) 참고**

---

## 📊 환경변수 요약

| 환경변수 | 용도 | 기본값 | 필수 |
|---------|------|-------|------|
| **STT_DEVICE** | 실행 디바이스 (cpu/cuda/auto) | auto | 아니오 |
| **STT_PRESET** | 성능 프리셋 (accuracy/balanced/speed/custom) | accuracy | 아니오 |
| **VLLM_BASE_URL** | vLLM 서버 주소 | http://localhost:8001/v1 | 아니오 |
| **VLLM_MODEL_NAME** | 기본 LLM 모델명 | 기본값 | 아니오 |
| **PRIVACY_VLLM_MODEL_NAME** | Privacy Removal 모델 | VLLM_MODEL_NAME | 아니오 |
| **ELEMENT_DETECTION_API_TYPE** | Element Detection 방식 (ai_agent/vllm/fallback) | fallback | 아니오 |
| **EXTERNAL_API_URL** | 외부 AI Agent API URL | 없음 | ai_agent 모드에서만 |

**전체 환경변수는 [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) 참고**

---

## 🔗 관련 문서

- [Docker 배포 가이드](../deployment/README.md)
- [아키텍처 설계](../architecture/)
- [트러블슈팅](../troubleshooting/)

---

## 📞 문의

API 관련 문제 발생 시:
1. [트러블슈팅](../troubleshooting/) 문서 확인
2. API 로그 분석
3. [테스트 가이드](./API_TESTING_GUIDE.md)로 단계별 테스트
