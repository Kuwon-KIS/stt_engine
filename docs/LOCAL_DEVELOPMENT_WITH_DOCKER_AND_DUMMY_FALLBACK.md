# 로컬 Docker 기반 개발 및 Dummy Fallback 메커니즘

**목표**: 
1. 로컬 Mac에서 Docker를 이용해 각 컴포넌트 (STT, vLLM, API Server) 독립적으로 테스트
2. 모델 로드 실패, 서비스 호출 실패 시 자동으로 Dummy fallback (로깅 필수)
3. 부분 성공 시나리오 처리 (예: STT는 성공, vLLM은 실패)

---

## 1. 로컬 개발 환경 구성

### 1.1 디렉토리 구조

```
stt_engine/
├── docker/
│   ├── docker-compose.yml           # 기존 (운영 서버용)
│   └── docker-compose.local.yml     # 신규 (로컬 개발용)
│   └── Dockerfile.local-stt         # 신규 (로컬 STT 컨테이너)
│   └── Dockerfile.local-vllm        # 신규 (로컬 vLLM 컨테이너)
├── models/
│   └── (STT 모델 저장 위치)
├── logs/
│   └── (로그 파일)
└── ...
```

### 1.2 로컬 docker-compose.yml 구성

```yaml
version: '3.8'

services:
  # STT 모델 서빙 (로컬 전용 - API 없음)
  stt-model:
    build:
      context: ..
      dockerfile: docker/Dockerfile.local-stt
    image: stt-engine-local:latest
    container_name: stt-model
    
    volumes:
      - ../models:/app/models
      - ../logs:/app/logs
    
    environment:
      - PYTHONUNBUFFERED=1
      - HF_HOME=/app/models
      - STT_DEVICE=cpu
    
    # 헬스 체크만 (실제 서빙은 하지 않음 - 모델 로드 테스트용)
    healthcheck:
      test: ["CMD", "python", "-c", 
             "from pathlib import Path; exit(0 if Path('/app/models').exists() else 1)"]
      interval: 10s
      timeout: 5s
      retries: 3
    
    ports:
      - "8001:8001"  # (향후 FastAPI 추가 시)

  # vLLM 모델 서빙
  vllm:
    image: vllm/vllm-openai:latest
    container_name: vllm-local
    
    volumes:
      - ../models:/root/.cache/huggingface
    
    environment:
      - HF_HOME=/root/.cache/huggingface
      - VLLM_ATTENTION_BACKEND=xformers
    
    ports:
      - "8000:8000"
    
    command: >
      python -m vllm.entrypoints.openai.api_server
      --model meta-llama/Llama-2-7b-chat-hf
      --port 8000
      --host 0.0.0.0
    
    # 헬스 체크
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    
    # Mac에서 메모리 제한 (필요시)
    deploy:
      resources:
        limits:
          memory: 4G

  # API 서버
  api-server:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    image: stt-engine-api-local:latest
    container_name: api-server-local
    
    ports:
      - "8003:8003"
    
    volumes:
      - ../models:/app/models
      - ../audio:/app/audio
      - ../logs:/app/logs
    
    environment:
      - PYTHONUNBUFFERED=1
      - HF_HOME=/app/models
      - STT_DEVICE=cpu
      - VLLM_API_URL=http://vllm:8000/v1
      - LOG_LEVEL=DEBUG
    
    depends_on:
      vllm:
        condition: service_healthy
    
    # 헬스 체크
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    
    restart: unless-stopped

networks:
  default:
    name: stt-local-network
    driver: bridge
```

---

## 2. Dummy Fallback 메커니즘

### 2.1 STT 모듈 Fallback

**위치**: `stt_engine.py` - `transcribe()` 메서드

```python
def transcribe(self, audio_path: str, language: Optional[str] = None, ...) -> Dict:
    """
    음성 파일을 텍스트로 변환합니다.
    모든 백엔드 로드 또는 호출 실패 시 Dummy 응답 반환 (로깅 필수)
    """
    try:
        # 기존 로직
        ...
    except Exception as e:
        # 모든 실패 케이스를 여기서 처리
        logger.error(f"[STT] 모든 백엔드 실패: {type(e).__name__}: {str(e)}")
        logger.warning(f"[STT] Dummy 응답으로 fallback (로깅됨)")
        
        # Dummy 응답 반환
        return {
            "success": False,
            "text": "",
            "text_en": "",
            "duration": 0,
            "language": language or "ko",
            "error": str(e),
            "error_type": type(e).__name__,
            "backend": "dummy",
            "is_dummy": True,
            "dummy_reason": "모든 백엔드 실패로 인한 자동 fallback"
        }
```

**실패 시나리오**:
1. ❌ 모델 파일 없음
2. ❌ 메모리 부족
3. ❌ GPU 초기화 실패
4. ❌ 음성 로드 실패
5. ❌ 변환 프로세스 크래시

**로깅 포맷**:
```
[2026-02-20 10:15:30] ERROR - [STT] 모델 로드 실패: FileNotFoundError: /app/models/faster-whisper-large-v3-turbo not found
[2026-02-20 10:15:31] WARNING - [STT] Dummy 응답으로 fallback (로깅됨)
[2026-02-20 10:15:31] INFO - [STT] Dummy 응답: is_dummy=True, reason=모든 백엔드 실패로 인한 자동 fallback
```

### 2.2 vLLM 호출 Fallback

**위치**: `api_server/services/agent_backend.py` - `call()` 메서드

```python
async def call(self, request_text: str, url: str, ...) -> Dict[str, Any]:
    """
    Agent 호출. vLLM 또는 외부 Agent 실패 시 Dummy 응답 반환 (로깅 필수)
    """
    start_time = time.time()
    
    logger.info(f"[AgentBackend] 호출 시작 (url={url}, format={request_format})")
    
    try:
        # 기존 로직
        ...
    except asyncio.TimeoutError:
        logger.error(f"[AgentBackend] 타임아웃 발생 (timeout={timeout}s)")
        logger.warning(f"[AgentBackend] Dummy 응답으로 fallback (로깅됨)")
        return self._create_dummy_response(
            error=f"Agent 호출 타임아웃 ({timeout}s)",
            error_type="TimeoutError",
            request_text=request_text
        )
    except ConnectionError as e:
        logger.error(f"[AgentBackend] 연결 실패: {str(e)}")
        logger.warning(f"[AgentBackend] Dummy 응답으로 fallback (로깅됨)")
        return self._create_dummy_response(
            error=f"Agent 서버 연결 실패: {str(e)}",
            error_type="ConnectionError",
            request_text=request_text
        )
    except Exception as e:
        logger.error(f"[AgentBackend] 예기치 않은 오류: {type(e).__name__}: {str(e)}")
        logger.warning(f"[AgentBackend] Dummy 응답으로 fallback (로깅됨)")
        return self._create_dummy_response(
            error=str(e),
            error_type=type(e).__name__,
            request_text=request_text
        )

def _create_dummy_response(self, error: str, error_type: str, request_text: str) -> Dict[str, Any]:
    """Dummy Agent 응답 생성"""
    processing_time = time.time() - self.start_time
    
    return {
        'success': False,
        'response': '[DUMMY 응답] 분석을 수행할 수 없습니다.',
        'agent_type': 'dummy',
        'is_dummy': True,
        'dummy_reason': error,
        'error': error,
        'error_type': error_type,
        'processing_time_sec': processing_time
    }
```

**실패 시나리오**:
1. ❌ vLLM 서버 미실행
2. ❌ 포트 연결 불가
3. ❌ API 타임아웃
4. ❌ 모델 로드 미완료
5. ❌ GPU 메모리 부족

**로깅 포맷**:
```
[2026-02-20 10:16:00] INFO - [AgentBackend] 호출 시작 (url=http://vllm:8000/v1/chat/completions, format=prompt_based)
[2026-02-20 10:16:05] ERROR - [AgentBackend] 연결 실패: HTTPConnectionPool(host='vllm', port=8000): 최대 재시도 초과
[2026-02-20 10:16:05] WARNING - [AgentBackend] Dummy 응답으로 fallback (로깅됨)
[2026-02-20 10:16:05] INFO - [AgentBackend] Dummy 응답: is_dummy=True, reason=Agent 서버 연결 실패
```

### 2.3 API 엔드포인트 Fallback

**위치**: `api_server/app.py` - `transcribe_v2()` 엔드포인트

```python
async def transcribe_v2(...) -> TranscribeResponse:
    """
    개선된 음성인식 엔드포인트
    부분 성공 시나리오 처리:
    - STT 성공, vLLM 실패 → STT 결과만 반환
    - STT 실패 → Dummy STT 사용, vLLM 시도
    """
    
    try:
        # 1. STT 처리
        logger.info(f"[Transcribe] STT 처리 시작")
        try:
            text_result = stt.transcribe(file_path, language)
            if text_result.get('success') or text_result.get('text'):
                logger.info(f"[Transcribe] STT 성공")
                stt_success = True
            else:
                logger.warning(f"[Transcribe] STT 실패하였으나 Dummy 사용")
                stt_success = False
        except Exception as e:
            logger.error(f"[Transcribe] STT 크래시: {type(e).__name__}: {str(e)}")
            logger.warning(f"[Transcribe] Dummy STT 사용")
            text_result = get_dummy_transcription()
            stt_success = False
        
        # 2. vLLM 처리 (선택사항)
        incomplete_elements = None
        if incomplete_elements_check == "true":
            logger.info(f"[Transcribe] vLLM 불완전판매요소 검증 시작")
            try:
                validator = get_incomplete_elements_validator(agent_backend)
                incomplete_elements = await validator.validate(
                    call_transcript=text_result.get('text', ''),
                    agent_config={'url': agent_url, 'format': agent_request_format},
                    timeout=30
                )
                if incomplete_elements.get('success'):
                    logger.info(f"[Transcribe] vLLM 검증 성공")
                else:
                    logger.warning(f"[Transcribe] vLLM 검증 실패하였으나 부분 결과 사용")
            except Exception as e:
                logger.error(f"[Transcribe] vLLM 크래시: {type(e).__name__}: {str(e)}")
                logger.warning(f"[Transcribe] vLLM 검증 생략 (Dummy 사용 안함 - 선택사항)")
                incomplete_elements = None
        
        # 3. 최종 응답 생성
        return TranscribeResponse(
            success=stt_success,
            text=text_result.get('text', ''),
            incomplete_elements=incomplete_elements,
            is_partial_failure=incomplete_elements is None and incomplete_elements_check == "true"
        )
```

---

## 3. 로컬 테스트 실행 방법

### 3.1 Docker Compose 실행

```bash
# 로컬 개발용 docker-compose 실행
cd /Users/a113211/workspace/stt_engine/docker
docker-compose -f docker-compose.local.yml up -d

# 확인
docker-compose -f docker-compose.local.yml ps
docker-compose -f docker-compose.local.yml logs -f
```

### 3.2 헬스 체크

```bash
# vLLM 헬스 체크
curl http://localhost:8000/health

# API 서버 헬스 체크
curl http://localhost:8003/health
```

### 3.3 STT 테스트 (모델 로드 테스트)

```bash
# 로컬 컨테이너에서 STT 모델 로드 테스트
docker exec stt-model python -c "
from stt_engine import WhisperSTT
stt = WhisperSTT('/app/models/openai_whisper-large-v3-turbo')
print('✓ 모델 로드 성공')
"

# 실제 음성 파일로 테스트
docker exec stt-model python -c "
from stt_engine import WhisperSTT
stt = WhisperSTT('/app/models/openai_whisper-large-v3-turbo')
result = stt.transcribe('/app/audio/test.wav', language='ko')
print(result)
"
```

### 3.4 vLLM 테스트

```bash
# vLLM API 직접 호출
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "messages": [{"role": "user", "content": "안녕하세요"}],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

### 3.5 전체 Transcribe API 테스트

```bash
# 정상 동작
curl -X POST http://localhost:8003/transcribe \
  -F "file_path=/app/audio/test.wav" \
  -F "incomplete_elements_check=true" \
  -F "agent_url=http://vllm:8000/v1/chat/completions" \
  -F "agent_request_format=prompt_based"

# STT 실패 시나리오 (모델 없음)
docker-compose -f docker-compose.local.yml exec stt-model bash
rm -rf /app/models/*
exit

# 재실행 (STT 실패 → Dummy fallback)
curl -X POST http://localhost:8003/transcribe \
  -F "file_path=/app/audio/test.wav" \
  -F "incomplete_elements_check=true"

# vLLM 실패 시나리오 (vLLM 중단)
docker-compose -f docker-compose.local.yml stop vllm

# 재실행 (STT 성공, vLLM 실패 → 부분 성공)
curl -X POST http://localhost:8003/transcribe \
  -F "file_path=/app/audio/test.wav" \
  -F "incomplete_elements_check=true"
```

### 3.6 로그 확인

```bash
# STT 모듈 로그
docker logs stt-model | grep "\[STT\]"

# vLLM 로그
docker logs vllm-local | grep "error\|ERROR\|Traceback"

# API 서버 로그
docker logs api-server-local | grep "\[Transcribe\]\|\[AgentBackend\]\|\[STT\]"

# 전체 로그 (최근 50줄)
docker logs -f api-server-local | tail -50
```

### 3.7 컨테이너 중단 및 정리

```bash
# 모든 컨테이너 중단
docker-compose -f docker-compose.local.yml down

# 이미지 제거 (재빌드 필요 시)
docker-compose -f docker-compose.local.yml down -v --rmi all

# 로그 파일 확인
tail -100 /Users/a113211/workspace/stt_engine/logs/api-server.log
```

---

## 4. 로깅 포맷 및 구조

### 4.1 로깅 레벨 정의

```
[TIMESTAMP] LEVEL - [COMPONENT] 메시지
```

**LEVEL**:
- `INFO`: 정상 진행 (예: 모델 로드 시작/완료)
- `WARNING`: 부분 실패 (예: Dummy fallback 사용)
- `ERROR`: 명확한 실패 (예: 모델 로드 실패)
- `DEBUG`: 상세 정보 (예: 메모리 사용량, 처리 시간)

**COMPONENT**:
- `[STT]`: STT 모듈
- `[AgentBackend]`: Agent 호출 계층
- `[Transcribe]`: Transcribe 엔드포인트
- `[Validation]`: 불완전판매요소 검증
- `[HealthCheck]`: 헬스 체크

### 4.2 로깅 예시

```
[2026-02-20 10:15:30] INFO - [STT] 모델 로드 시작 (/app/models/openai_whisper-large-v3-turbo)
[2026-02-20 10:15:35] INFO - [STT] 모델 로드 완료 (faster-whisper, 5.2초)
[2026-02-20 10:15:36] INFO - [Transcribe] 음성 파일 로드 시작 (/app/audio/test.wav)
[2026-02-20 10:15:37] INFO - [STT] 음성 변환 시작 (language=ko)
[2026-02-20 10:15:45] INFO - [STT] 음성 변환 완료 (8.2초, text="안녕하세요")
[2026-02-20 10:15:46] INFO - [Transcribe] vLLM 검증 시작
[2026-02-20 10:15:47] INFO - [AgentBackend] 호출 시작 (url=http://vllm:8000/v1/chat/completions)
[2026-02-20 10:16:00] INFO - [AgentBackend] 응답 수신 완료 (13.2초)
[2026-02-20 10:16:01] INFO - [Transcribe] 최종 응답 생성 완료

---

[2026-02-20 10:20:15] ERROR - [STT] 모델 로드 실패: FileNotFoundError: /app/models not found
[2026-02-20 10:20:16] WARNING - [STT] Dummy 응답으로 fallback (로깅됨)
[2026-02-20 10:20:17] INFO - [STT] Dummy 응답: is_dummy=True, reason=모든 백엔드 실패

---

[2026-02-20 10:25:10] ERROR - [AgentBackend] 연결 실패: HTTPConnectionPool(host='vllm', port=8000)
[2026-02-20 10:25:11] WARNING - [AgentBackend] Dummy 응답으로 fallback (로깅됨)
[2026-02-20 10:25:12] INFO - [AgentBackend] Dummy 응답: is_dummy=True, reason=Agent 서버 연결 실패
```

---

## 5. 데이터 모델 업데이트

### 5.1 TranscribeResponse

```python
class TranscribeResponse(BaseModel):
    success: bool
    text: str
    duration: float = 0.0
    language: str = "ko"
    
    # STT 관련
    error: Optional[str] = None
    error_type: Optional[str] = None
    backend: Optional[str] = None  # faster-whisper, transformers, openai-whisper, dummy
    is_dummy: bool = False  # Dummy fallback 여부
    dummy_reason: Optional[str] = None  # Dummy 사용 이유
    
    # vLLM 관련
    incomplete_elements: Optional[Dict[str, Any]] = None
    agent_analysis: Optional[str] = None
    agent_type: Optional[str] = None  # external, vllm, dummy
    is_agent_dummy: bool = False  # Agent Dummy fallback 여부
    agent_dummy_reason: Optional[str] = None  # Agent Dummy 사용 이유
    
    # 부분 성공 표시
    is_partial_failure: bool = False  # STT는 성공, 다른 단계는 실패
    partial_failure_reason: Optional[str] = None
```

### 5.2 AgentBackendResponse

```python
{
    'success': bool,
    'response': str,
    'agent_type': str,  # external, vllm, dummy
    'is_dummy': bool,
    'dummy_reason': Optional[str],
    'error': Optional[str],
    'error_type': Optional[str],
    'processing_time_sec': float,
    'chat_thread_id': Optional[str]
}
```

---

## 6. 향후 개선 사항

### 6.1 Circuit Breaker 패턴
```python
# vLLM이 연속 5회 실패 시 자동으로 Dummy 사용 (복구 대기)
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.is_open = False
        self.recovery_timeout = recovery_timeout
    
    async def call(self, func, *args, **kwargs):
        if self.is_open:
            logger.warning("[CircuitBreaker] Circuit 열림 - Dummy 사용")
            return self.get_dummy_response()
        
        try:
            result = await func(*args, **kwargs)
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.is_open = True
                logger.error(f"[CircuitBreaker] Circuit 열림 (실패 {self.failure_count}회)")
            raise
```

### 6.2 메트릭스 수집
```python
# Dummy 사용 빈도, 실패율 등 모니터링
class FailureMetrics:
    stt_failure_count = 0
    agent_failure_count = 0
    stt_total_count = 0
    agent_total_count = 0
    
    @property
    def stt_failure_rate(self):
        return self.stt_failure_count / self.stt_total_count if self.stt_total_count > 0 else 0
```

### 6.3 자동 모델 다운로드
```python
# 모델 파일 없을 시 자동 다운로드
from huggingface_hub import hf_hub_download

def ensure_model_exists(model_name, cache_dir):
    if not Path(cache_dir).exists():
        logger.info(f"[STT] 모델 자동 다운로드 시작: {model_name}")
        hf_hub_download(repo_id=model_name, cache_dir=cache_dir)
        logger.info(f"[STT] 모델 다운로드 완료")
```

---

## 7. 체크리스트

### 코드 변경사항
- [ ] `stt_engine.py` - `transcribe()` Dummy fallback 추가
- [ ] `api_server/services/agent_backend.py` - 강화된 fallback 로직
- [ ] `api_server/app.py` - 부분 성공 시나리오 처리
- [ ] `api_server/models.py` - Response 모델 확장 (is_dummy, dummy_reason 등)

### Docker 파일
- [ ] `docker/docker-compose.local.yml` 생성
- [ ] `docker/Dockerfile.local-stt` 생성 (필요시)
- [ ] `docker/Dockerfile.local-vllm` 생성 (필요시)

### 테스트
- [ ] 로컬에서 docker-compose up 실행 확인
- [ ] STT 모델 로드 성공 확인
- [ ] vLLM 서버 실행 확인
- [ ] STT 정상 동작 테스트
- [ ] vLLM 정상 동작 테스트
- [ ] STT 실패 → Dummy fallback 로깅 확인
- [ ] vLLM 실패 → Dummy fallback 로깅 확인
- [ ] 부분 성공 시나리오 (STT 성공, vLLM 실패) 테스트

### 문서
- [ ] 로컬 개발 가이드 작성
- [ ] Fallback 메커니즘 설명 문서
- [ ] 로깅 가이드

---

## 부록 A: 주요 파일 변경 위치

### stt_engine.py
- `transcribe()` 메서드 (라인 ~1176)
  - try-except 확장
  - Dummy 응답 추가

### agent_backend.py
- `call()` 메서드 (라인 ~80)
  - try-except 확장
  - _create_dummy_response() 메서드 추가

### app.py
- `transcribe_v2()` 엔드포인트 (라인 ~284)
  - STT/vLLM 부분 실패 처리
  - partial_failure_reason 설정

### models.py
- TranscribeResponse (라인 ~)
  - is_dummy, dummy_reason 필드 추가
  - is_agent_dummy, agent_dummy_reason 필드 추가
  - is_partial_failure, partial_failure_reason 필드 추가

---

이제 구현을 시작하겠습니다!
