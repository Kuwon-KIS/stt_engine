# 로컬 개발 가이드: STT Engine + Dummy Fallback

## 개요

로컬 Mac/Linux에서 STT 시스템을 Docker로 실행하는 방법을 설명합니다.

**구조:**
- **EC2 빌드 환경**: 운영용 이미지 생성 (`Dockerfile.engine.rhel89`)
- **로컬 개발**: 로컬용 경량 이미지 사용 (`Dockerfile.engine.local`)
- **실행 방식**: EC2와 로컬 모두 `docker run` 명령 사용

---

## 1. 로컬 이미지 빌드

### 1.1 Dockerfile.engine.local 빌드

CPU-only 경량 이미지 (로컬 Mac/Linux 용):

```bash
# 이미지 빌드
docker build \
  -t stt-engine:local \
  -f docker/Dockerfile.engine.local \
  .
```

**시간**: 3-5분 (로컬 Mac에서)

**이미지 크기**: ~600MB (운영용 1.5GB vs)

### 1.2 네트워크 생성

```bash
docker network create stt-network
```

---

## 2. STT API 서버 실행

### 기본 실행 (모델 필수)

```bash
docker run -d \
  --name stt-api \
  --network stt-network \
  -p 8003:8003 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/logs:/app/logs \
  stt-engine:local
```

**포트**: 8003

**환경 변수** (기본값):
- `STT_DEVICE=cpu`
- `HF_HOME=/app/models`
- `LOG_LEVEL=DEBUG`

### 모델 없이 실행 (Dummy Fallback)

모델이 없어도 Dummy fallback으로 작동:

```bash
docker run -d \
  --name stt-api \
  --network stt-network \
  -p 8003:8003 \
  -v $(pwd)/logs:/app/logs \
  stt-engine:local
```

**결과**: 
- STT 실패 → Dummy 응답 (로깅)
- 모델 준비 후 재시작하면 자동으로 정상 작동

### 로그 확인

```bash
docker logs -f stt-api

# STT Dummy fallback 로그 확인
docker logs stt-api | grep "\[STT\]"
```

---

## 3. Web UI 실행 (선택사항)

```bash
docker run -d \
  --name stt-web-ui \
  --network stt-network \
  -p 8100:8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -v $(pwd)/web_ui/data:/app/data \
  -v $(pwd)/web_ui/logs:/app/logs \
  stt-web-ui:local
```

**포트**: 8100

**접속**: http://localhost:8100

---

## 4. 테스트

### 4.1 API 헬스 체크

```bash
curl http://localhost:8003/health
```

**응답**:
```json
{"status": "healthy"}
```

### 4.2 STT 테스트 (파일 경로 방식)

```bash
curl -X POST http://localhost:8003/transcribe \
  -F "file_path=/app/audio/test.wav" \
  -F "language=ko"
```

### 4.3 STT 테스트 (파일 업로드 방식)

```bash
curl -X POST http://localhost:8003/transcribe \
  -F "file=@/path/to/audio.wav" \
  -F "language=ko"
```

### 4.4 Dummy Fallback 테스트

모델 없이 실행했을 경우:

```bash
# 요청
curl -X POST http://localhost:8003/transcribe \
  -F "file_path=/app/audio/test.wav"

# 응답 (Dummy)
{
  "success": false,
  "text": "",
  "backend": "dummy",
  "is_dummy": true,
  "dummy_reason": "파일을 찾을 수 없습니다: /app/models/...",
  "error": "..."
}
```

---

## 5. 모델 준비 (로컬)

### HuggingFace에서 모델 다운로드

```bash
python download_model_hf.py
```

**시간**: 10-20분

**위치**: `./models/` 디렉토리

### 또는 EC2에서 다운로드

```bash
# EC2에서 모델 다운로드
bash scripts/ec2_prepare_model.sh

# 로컬로 복사 (SCP 사용)
scp -i ~/aws-key.pem \
  ec2-user@ec2-host:~/stt_engine/build/output/models.tar.gz \
  ./build/output/

# 해제
tar -xzf build/output/models.tar.gz -C .
```

---

## 6. 문제 해결

### 6.1 API 서버가 시작되지 않음

```bash
# 로그 확인
docker logs stt-api

# 컨테이너 상태 확인
docker ps | grep stt-api

# 컨테이너 재시작
docker restart stt-api
```

### 6.2 모델 로드 실패

```
[STT] 모델 로드 실패: FileNotFoundError
[STT] Dummy 응답으로 fallback
```

**해결**:
1. 모델이 `./models/` 디렉토리에 있는지 확인
2. 모델 다운로드: `python download_model_hf.py`
3. 컨테이너 재시작: `docker restart stt-api`

### 6.3 포트 이미 사용 중

```bash
# 기존 컨테이너 중지
docker stop stt-api

# 기존 컨테이너 제거
docker rm stt-api

# 다시 실행
docker run -d ... (위의 run 명령어 참고)
```

### 6.4 디스크 공간 부족

```bash
# 불필요한 이미지/컨테이너 정리
docker system prune -a

# 캐시 정리
rm -rf ~/.cache/huggingface/
```

---

## 7. docker-compose 사용 (선택사항)

`docker-compose.local.yml` 사용:

```bash
# 서비스 시작
docker-compose -f docker/docker-compose.local.yml up -d

# 로그 확인
docker-compose -f docker/docker-compose.local.yml logs -f api-server

# 서비스 중지
docker-compose -f docker/docker-compose.local.yml down

# 전체 정리 (데이터 포함)
docker-compose -f docker/docker-compose.local.yml down -v
```

**주의**: 로컬에서는 `docker run` 방식을 권장합니다.

---

## 8. Dummy Fallback 메커니즘

### 8.1 STT Dummy Fallback

**언제**: 모델 로드 또는 변환 실패

**로그**:
```
[STT] 모델 로드 실패: FileNotFoundError
[STT] Dummy 응답으로 fallback
```

**응답**:
```json
{
  "success": false,
  "text": "",
  "backend": "dummy",
  "is_dummy": true,
  "dummy_reason": "..."
}
```

### 8.2 Agent (vLLM) Dummy Fallback

**언제**: vLLM 서버 미실행 또는 연결 실패

**로그**:
```
[AgentBackend] 연결 실패: HTTPConnectionPool
[AgentBackend] Dummy 응답으로 fallback
```

**응답**:
```json
{
  "success": false,
  "response": "[Dummy Agent] 분석을 수행할 수 없습니다.",
  "agent_type": "dummy",
  "is_dummy": true
}
```

---

## 9. 로깅 확인

### 9.1 STT 로그

```bash
docker logs stt-api | grep "\[STT\]"
```

### 9.2 Agent 로그

```bash
docker logs stt-api | grep "\[AgentBackend\]"
```

### 9.3 전체 DEBUG 로그

```bash
docker logs -f stt-api --since 10m
```

---

## 10. EC2 빌드 환경과의 차이

### EC2 (운영/빌드)
- **Dockerfile**: `Dockerfile.engine.rhel89`
- **Base Image**: RHEL 8.9 (ubi8/python-311)
- **Device**: CUDA 12.9 지원
- **실행**: `docker run -e STT_DEVICE=cuda ...`

### 로컬 (개발)
- **Dockerfile**: `Dockerfile.engine.local`
- **Base Image**: python:3.11-slim
- **Device**: CPU-only
- **실행**: `docker run -e STT_DEVICE=cpu ...`

**주의**: 로컬에서는 GPU를 사용할 수 없습니다.

---

## 11. 빠른 시작 스크립트

`scripts/run-local-dev.sh`:

```bash
#!/bin/bash

set -e

echo "=== STT Local Development Setup ==="

# 1. 이미지 빌드
echo "1. Building Docker image..."
docker build \
  -t stt-engine:local \
  -f docker/Dockerfile.engine.local \
  .

# 2. 네트워크 생성
echo "2. Creating network..."
docker network create stt-network 2>/dev/null || true

# 3. API 서버 실행
echo "3. Running API server..."
docker run -d \
  --name stt-api \
  --network stt-network \
  -p 8003:8003 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/logs:/app/logs \
  stt-engine:local

# 4. 헬스 체크
echo "4. Waiting for API server..."
for i in {1..30}; do
  if curl -f http://localhost:8003/health 2>/dev/null; then
    echo "✅ API server is healthy"
    break
  fi
  echo "  Waiting... ($i/30)"
  sleep 2
done

echo ""
echo "=== Setup Complete ==="
echo "API Server: http://localhost:8003"
echo "Health Check: curl http://localhost:8003/health"
echo "Logs: docker logs -f stt-api"
```

---

## 참고 자료

- [Dockerfile.engine.local](../docker/Dockerfile.engine.local)
- [docker-compose.local.yml](../docker/docker-compose.local.yml)
- [Dummy Fallback 구현](../docs/LOCAL_DEVELOPMENT_WITH_DOCKER_AND_DUMMY_FALLBACK.md)
