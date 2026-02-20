# 로컬 Docker 개발 환경 및 Dummy Fallback 리팩토링 계획

**작성일**: 2026년 2월 20일
**상태**: 계획 수립

---

## 1. 목표

### 1.1 주요 목표
1. **로컬 개발 환경 구축**: Mac에서 Docker로 각 컴포넌트(stt-api, web-ui)를 독립적으로 테스트
2. **Dummy Fallback 강화**: STT와 vLLM 호출 실패 시 자동으로 Dummy 응답 반환 + 상세 로깅
3. **개발 효율성 개선**: EC2 빌드 없이 로컬에서 전체 시스템 테스트 가능

### 1.2 현재 상태
```
개발 흐름 (현재):
  Local (코딩) → EC2 (빌드) → Linux OnPrem (운영)
  - EC2 빌드에 시간 소요 (20-30분)
  - 로컬 테스트 불가
  
개선 후 (목표):
  Local (코딩 + 테스트) → EC2 (빌드) → Linux OnPrem (운영)
  - 로컬에서 빠른 반복 테스트
  - Docker Compose로 통합 테스트
  - EC2는 최종 확정 이미지만 빌드
```

---

## 2. 아키텍처 설계

### 2.1 로컬 개발 환경 구성

```
Local Mac (Docker Desktop)
│
├─ stt-api (stt-engine 이미지)
│  ├─ Port: 8003
│  ├─ 이미지 베이스: docker/Dockerfile.engine.rhel89 최소화
│  ├─ 모델: /app/models (호스트 바인드)
│  └─ 특징: 로컬 개발용 (RHEL 기반에서 Linux 기반으로 변환)
│
├─ web-ui (stt-web-ui 이미지)
│  ├─ Port: 8100
│  ├─ 이미지 베이스: web_ui/docker/Dockerfile.web_ui
│  ├─ API: STT_API_URL=http://stt-api:8003
│  └─ 데이터: /app/data, /app/logs (호스트 바인드)
│
└─ vllm (선택, optional)
   ├─ Port: 8001
   └─ 모델: /app/models (호스트 바인드)
```

### 2.2 모델 준비 방식

```
EC2 방식 (현재):
  scripts/ec2_prepare_model.sh
  ├─ HF 다운로드
  ├─ ctranslate2 변환
  └─ 압축 (optional)

로컬 방식 (신규):
  scripts/prepare_model_local.sh
  ├─ HF 다운로드 (캐시 활용)
  ├─ ctranslate2 변환
  ├─ 압축 스킵
  └─ 모델 검증
```

### 2.3 Fallback 메커니즘

```
STT 호출 흐름:
  1. 모델 로드 시도
     └─ Fail → Dummy STT (로깅: "[STT-DUMMY] Model load failed")
  
  2. Audio 파일 검증
     └─ Fail → Dummy STT (로깅: "[STT-DUMMY] Invalid audio file")
  
  3. Transcription 처리
     └─ Fail → Dummy STT (로깅: "[STT-DUMMY] Transcription failed: {reason}")

vLLM 호출 흐름:
  1. 설정 검증 (AGENT_URL, request_format)
     └─ Fail → Dummy Agent (로깅: "[AGENT-DUMMY] Configuration invalid")
  
  2. 연결 시도
     └─ Fail → Dummy Agent (로깅: "[AGENT-DUMMY] Connection failed: {reason}")
  
  3. 요청 처리
     └─ Fail → Dummy Agent (로깅: "[AGENT-DUMMY] Request failed: {reason}")

응답 구조:
  {
    "success": true,
    "text": "STT 결과 or Dummy 응답",
    "backend": "faster-whisper|transformers|whisper|dummy",
    "is_dummy": true,  # ← 추가
    "error_reason": null,  # ← Fallback 원인 기록
    ...
  }
```

---

## 3. 구현 계획

### Phase 1: 로컬 Docker 이미지 및 Compose 구성

#### 3.1.1 docker/Dockerfile.stt-api (신규)
**목적**: 로컬 개발용 stt-api 이미지
**베이스**: 경량 Linux (not RHEL) - 로컬 빠른 빌드
**특징**:
- 기본 Python 3.11 이미지
- 필수 시스템 패키지만 설치
- 모델은 호스트 바인드 마운트
- CUDA 없음 (로컬 테스트용)

```dockerfile
FROM python:3.11-slim

# 필수 패키지만 설치
RUN apt-get update && apt-get install -y \
    ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드
COPY stt_*.py ./
COPY api_server/ ./api_server/
COPY scripts/ ./scripts/

# 모델은 호스트에서 바인드
WORKDIR /app
EXPOSE 8003

CMD ["python", "-m", "api_server.app"]
```

#### 3.1.2 docker/docker-compose.dev.yml (신규)
**목적**: 로컬 개발용 전체 스택 설정

```yaml
version: '3.8'

services:
  stt-api:
    build:
      context: .
      dockerfile: docker/Dockerfile.stt-api
    container_name: stt-api
    ports:
      - "8003:8003"
    environment:
      - STT_DEVICE=cpu  # 로컬 테스트
      - STT_COMPUTE_TYPE=default
      - LOG_LEVEL=DEBUG
    volumes:
      - ./models:/app/models:ro
      - ./audio/samples:/app/audio/samples:ro
    networks:
      - stt-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  web-ui:
    build:
      context: .
      dockerfile: web_ui/docker/Dockerfile.web_ui
    container_name: stt-web-ui
    ports:
      - "8100:8100"
    environment:
      - STT_API_URL=http://stt-api:8003
      - LOG_LEVEL=DEBUG
    volumes:
      - ./web_ui/data:/app/data
      - ./web_ui/logs:/app/logs
    depends_on:
      stt-api:
        condition: service_healthy
    networks:
      - stt-network

  # 선택: vLLM 서비스 (테스트용)
  # vllm:
  #   image: vllm/vllm-openai:latest
  #   container_name: vllm
  #   ports:
  #     - "8001:8000"
  #   environment:
  #     - MODEL_NAME=meta-llama/Llama-2-7b-chat-hf
  #   volumes:
  #     - ./models:/app/models:ro
  #   networks:
  #     - stt-network

networks:
  stt-network:
    driver: bridge
```

#### 3.1.3 scripts/prepare_model_local.sh (신규)
**목적**: 로컬 개발 환경용 모델 준비

### Phase 2: STT 호출 Fallback 강화

#### 3.2.1 stt_engine.py 수정
**변경사항**:
- `STTEngine.__init__()`: 모델 로드 실패 시 fallback 설정
- `STTEngine.transcribe()`: 예외 처리 강화 + Dummy 응답
- 로깅: `[STT]`, `[STT-DUMMY]` 프리픽스 추가

**코드 구조**:
```python
class STTEngine:
    def __init__(self, model_name, device="cpu", compute_type="default"):
        self.is_dummy = False
        self.error_reason = None
        
        try:
            # 실제 모델 로드
            self._load_model(model_name, device, compute_type)
        except Exception as e:
            self.is_dummy = True
            self.error_reason = str(e)
            logger.warning(f"[STT-DUMMY] Model initialization failed: {e}")
    
    def transcribe(self, audio_path, language=None, **kwargs):
        if self.is_dummy:
            logger.warning(f"[STT-DUMMY] Using dummy transcription")
            return self._dummy_response(audio_path)
        
        try:
            # 실제 transcription
            return self._transcribe_real(audio_path, language, **kwargs)
        except Exception as e:
            logger.error(f"[STT-DUMMY] Transcription failed: {e}")
            return self._dummy_response(audio_path, error_reason=str(e))
    
    def _dummy_response(self, audio_path, error_reason=None):
        return {
            "success": True,
            "text": f"[Dummy] Transcription of {Path(audio_path).name}",
            "backend": "dummy",
            "is_dummy": True,
            "error_reason": error_reason or self.error_reason,
            ...
        }
```

#### 3.2.2 TranscribeResponse 모델 수정
**추가 필드**:
```python
class TranscribeResponse(BaseModel):
    # 기존 필드들...
    
    # Fallback 관련 필드
    is_dummy: bool = False  # Dummy 응답 여부
    error_reason: Optional[str] = None  # 실패 원인
    component_status: Dict[str, bool] = {}  # 각 컴포넌트 상태
    
    # 예: {"stt": True, "classification": True, "vllm": False}
```

#### 3.2.3 Logging 통합
**로깅 포맷**:
```
[STT] Model loaded: faster-whisper
[STT] Transcription: 5.23s
[STT-DUMMY] Model load failed: CUDA not available
[STT-DUMMY] Using dummy transcription
[AGENT] Processing with vLLM
[AGENT-DUMMY] Connection failed: Connection refused
[AGENT-DUMMY] Using dummy response
```

### Phase 3: vLLM (Agent) 호출 Fallback 강화

#### 3.3.1 api_server/services/agent_backend.py 수정
**변경사항**:
- `AgentBackend.call()`: 연결 실패 시 자동 Dummy 응답
- 설정 검증: URL, request_format 유효성
- 상세 로깅: 각 단계별 성공/실패

**코드 구조**:
```python
class AgentBackend:
    async def call(self, request_text, url, request_format, timeout=30):
        try:
            # 1. 설정 검증
            self._validate_config(url, request_format)
            logger.info(f"[AGENT] Calling {self._detect_agent_type(url)}")
            
            # 2. 실제 호출
            result = await self._call_internal(request_text, url, request_format, timeout)
            logger.info(f"[AGENT] Success")
            return result
            
        except Exception as e:
            logger.warning(f"[AGENT-DUMMY] Failed: {e}")
            return self._dummy_response(request_text, error_reason=str(e))
    
    def _validate_config(self, url, request_format):
        if not url or not isinstance(url, str):
            raise ValueError("Invalid URL")
        if request_format not in ["text_only", "prompt_based"]:
            raise ValueError("Invalid request_format")
    
    def _dummy_response(self, request_text, error_reason=None):
        return {
            "success": True,
            "response": f"[Dummy] Processed: {request_text[:50]}...",
            "is_dummy": True,
            "error_reason": error_reason,
            "agent_type": "dummy"
        }
```

### Phase 4: API 엔드포인트 응답 통합

#### 3.4.1 api_server/app.py transcribe_v2() 수정
**변경사항**:
- component_status 수집 (STT, Classification, vLLM)
- Fallback 로깅 통합
- 응답에 is_dummy, error_reason 포함

**응답 구조**:
```json
{
  "success": true,
  "text": "STT 결과",
  "backend": "faster-whisper",
  "is_dummy": false,
  "error_reason": null,
  "component_status": {
    "stt": true,
    "classification": true,
    "vllm": false
  },
  "processing_time_seconds": 5.23,
  ...
}
```

---

## 4. 구현 순서

### Phase 1: 로컬 Docker 준비 (우선)
1. [ ] docker/Dockerfile.stt-api 생성
2. [ ] docker/docker-compose.dev.yml 생성
3. [ ] scripts/prepare_model_local.sh 생성
4. [ ] README 또는 quick_start 문서 업데이트

### Phase 2: STT Fallback 강화
1. [ ] stt_engine.py 모델 로드 부분 강화
2. [ ] stt_engine.py transcribe() fallback 추가
3. [ ] TranscribeResponse 모델 필드 추가
4. [ ] 로깅 포맷 통합

### Phase 3: Agent Fallback 강화
1. [ ] agent_backend.py 설정 검증 강화
2. [ ] agent_backend.py 에러 처리 강화
3. [ ] incomplete_sales_validator.py 통합

### Phase 4: API 통합 및 테스트
1. [ ] transcribe_v2() 응답 구조 업데이트
2. [ ] 로컬 테스트 (docker-compose)
3. [ ] E2E 테스트 케이스

---

## 5. 사용 흐름

### 5.1 로컬 개발 시작

```bash
# 1. 모델 준비 (처음 한 번만)
bash scripts/prepare_model_local.sh

# 2. Docker 이미지 빌드 및 실행
docker-compose -f docker/docker-compose.dev.yml up -d

# 3. 헬스 체크
curl http://localhost:8003/health
curl http://localhost:8100/health

# 4. STT 테스트
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test_ko_1min.wav'

# 5. Web UI 접속
open http://localhost:8100
```

### 5.2 로깅 확인

```bash
# 실시간 로그 확인
docker logs -f stt-api
docker logs -f stt-web-ui

# Fallback 로그 검색
docker logs stt-api | grep -E "\[STT-DUMMY\]|\[AGENT-DUMMY\]"
```

### 5.3 종료

```bash
docker-compose -f docker/docker-compose.dev.yml down
```

---

## 6. 고려사항

### 6.1 Mac Docker Desktop 리소스
```
권장 설정:
- CPU: 4+ cores
- Memory: 8GB+
- Disk: 20GB+
```

### 6.2 모델 캐싱
```
로컬 모델 경로:
  ~/.cache/huggingface/  (HF 캐시)
  ./models/              (프로젝트 모델)
  
Docker에서는 ./models 바인드마운트
```

### 6.3 Fallback vs 실제 기능
```
로컬 테스트 시:
- STT (faster-whisper): CPU에서 작동 가능
- Classification: vLLM 없으면 Dummy (로깅)
- Web UI: 정상 작동
```

### 6.4 EC2 빌드와 호환성
```
로컬 (docker-compose.dev.yml):
  - Linux 기반 이미지
  - CPU 모드
  - 빠른 테스트용

EC2 (docker/Dockerfile.engine.rhel89):
  - RHEL 8.9 기반
  - CUDA 12.9 + cuDNN
  - 프로덕션용

코드는 동일하게 유지
```

---

## 7. 검증 항목

### 7.1 기능 검증
- [ ] 로컬에서 docker-compose 정상 실행
- [ ] stt-api 엔드포인트 응답 확인
- [ ] web-ui 접속 및 파일 업로드
- [ ] Fallback 로깅 확인
- [ ] 응답에 is_dummy, error_reason 포함

### 7.2 통합 검증
- [ ] STT 호출 + 응답 (정상, fallback)
- [ ] Classification 호출 + 응답
- [ ] vLLM 호출 + 응답 (정상, fallback)
- [ ] 완전한 end-to-end 흐름

### 7.3 로깅 검증
- [ ] [STT] 로그 출력
- [ ] [STT-DUMMY] 로그 출력
- [ ] [AGENT] 로그 출력
- [ ] [AGENT-DUMMY] 로그 출력

---

## 8. 예상 효과

### 개발 효율성
- 로컬 테스트: ~2분 (vs EC2 빌드 20-30분)
- 빠른 피드백 루프
- Docker Desktop으로 독립적 테스트

### 안정성
- Fallback 자동화로 부분 장애 대응
- 상세 로깅으로 문제 추적 용이
- is_dummy 플래그로 실제/Dummy 구분 가능

### 운영
- 로컬 테스트 후 EC2 빌드 → 프로덕션 배포
- 명확한 컴포넌트별 상태 파악
- 구성 검증 강화

---

## 9. 진행 상황 추적

```
Phase 1 (로컬 Docker):    [ ] 계획 [ ] 구현 [ ] 테스트 [ ] 완료
Phase 2 (STT Fallback):   [ ] 계획 [✓] 구현 [ ] 테스트 [ ] 완료
Phase 3 (Agent Fallback): [ ] 계획 [✓] 구현 [ ] 테스트 [ ] 완료
Phase 4 (API 통합):       [ ] 계획 [ ] 구현 [ ] 테스트 [ ] 완료
```

---

## 부록: 참고 자료

### A. 기존 EC2 준비 스크립트
- `scripts/ec2_prepare_model.sh`: EC2에서 사용 중

### B. 기존 Dockerfile들
- `docker/Dockerfile.engine.rhel89`: 운영 서버용
- `web_ui/docker/Dockerfile.web_ui`: Web UI용

### C. 최근 리팩토링
- `api_server/services/agent_backend.py`: Agent 호출 추상화
- `api_server/services/incomplete_sales_validator.py`: 불완전판매요소 검증

