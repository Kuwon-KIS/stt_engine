# Docker 빌드 및 배포 가이드 (Phase 3 업데이트)

**작성일**: 2026년 2월 25일  
**버전**: Phase 3 (OpenAI 제거, vLLM/Ollama 전환)

---

## 변경 사항 요약

### 의존성 변경

**제거된 패키지**:
- `openai>=1.0.0` - OpenAI API 클라이언트
- `anthropic>=0.18.0` - Anthropic Claude API
- `google-generativeai>=0.3.0` - Google Generative AI

**유지된 패키지**:
- `httpx>=0.24.0` - HTTP 클라이언트 (vLLM, Ollama 통신용)

### requirements.txt 업데이트

#### 이전 (Phase 2)
```
openai>=1.0.0
anthropic>=0.18.0
google-generativeai>=0.3.0
pandas>=2.0.0
openpyxl>=3.1.0
xlrd>=2.0.0
```

#### 현재 (Phase 3)
```
# Data processing
pandas>=2.0.0
openpyxl>=3.1.0
xlrd>=2.0.0

# HTTP client for LLM API calls
httpx>=0.24.0
```

### 배포 패키지 요구사항 동기화

**파일**:
- `/Users/a113211/workspace/stt_engine/requirements.txt`
- `/Users/a113211/workspace/stt_engine/deployment_package/requirements.txt`

**상태**: ✅ 동기화됨 (OpenAI 및 외부 LLM API 제거)

---

## Docker 빌드 명령어

### 기본 빌드

```bash
# 로컬 개발 환경
cd /Users/a113211/workspace/stt_engine
docker build -t stt-engine:latest -f docker/Dockerfile .

# RHEL 8.9 환경
docker build -t stt-engine:rhel89 -f docker/Dockerfile.engine.rhel89 .
```

### 이미지 확인

```bash
# 빌드된 이미지 확인
docker images | grep stt-engine

# 이미지 상세 정보
docker inspect stt-engine:latest

# 이미지 크기 확인
docker images --format "table {{.Repository}}\t{{.Size}}" | grep stt-engine
```

### 빌드 옵션

```bash
# 캐시 무시 (완전 재빌드)
docker build --no-cache -t stt-engine:latest -f docker/Dockerfile .

# 빌드 로그 출력
docker build -t stt-engine:latest -f docker/Dockerfile . --progress=plain

# 빌드 타임 측정
time docker build -t stt-engine:latest -f docker/Dockerfile .
```

---

## Docker Compose 배포

### 전체 스택 시작

```bash
cd /Users/a113211/workspace/stt_engine

# 서비스 시작
docker-compose up -d

# 또는 빌드와 함께 시작
docker-compose up -d --build

# 로그 확인
docker-compose logs -f stt-engine-api
docker-compose logs -f stt-web-ui

# 서비스 상태 확인
docker-compose ps
```

### 개별 서비스 시작

```bash
# STT API만 시작
docker-compose up -d stt-engine-api

# Web UI만 시작
docker-compose up -d stt-web-ui

# 특정 서비스 재시작
docker-compose restart stt-engine-api
```

### 서비스 중지 및 제거

```bash
# 서비스 중지
docker-compose stop

# 서비스 제거 (컨테이너만)
docker-compose down

# 모든 리소스 제거 (볼륨 포함)
docker-compose down -v

# 컨테이너 로그 삭제
docker-compose logs --tail=0 -f
```

---

## LLM 서버 실행 옵션

### 옵션 1: 호스트에서 LLM 서버 실행 (권장)

```bash
# 터미널 1: vLLM 실행
python -m vllm.entrypoints.openai.api_server \
  --model mistral-7b-instruct-v0.2 \
  --host 0.0.0.0 \
  --port 8000

# 터미널 2: Docker 컨테이너로 STT API 실행
docker-compose up -d stt-engine-api

# 환경변수 설정 (.env 파일)
VLLM_API_URL=http://host.docker.internal:8000  # Mac/Windows
VLLM_API_URL=http://172.17.0.1:8000           # Linux
```

### 옵션 2: Docker 네트워크로 LLM 서버 함께 실행

```bash
# docker-compose.yml에 vLLM 서비스 추가
cat >> docker/docker-compose-with-llm.yml << 'EOF'
  vllm-server:
    image: vllm/vllm-openai:latest
    container_name: vllm-server
    ports:
      - "8000:8000"
    volumes:
      - ../models:/root/.cache/huggingface
    environment:
      - MODEL_NAME=mistral-7b-instruct-v0.2
    command: >
      python -m vllm.entrypoints.openai.api_server
      --model mistral-7b-instruct-v0.2
      --host 0.0.0.0
      --port 8000
    restart: unless-stopped

  ollama-server:
    image: ollama/ollama:latest
    container_name: ollama-server
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    restart: unless-stopped

volumes:
  ollama-data:
EOF
```

### 옵션 3: Kubernetes 배포 (선택사항)

```yaml
# kubernetes/stt-engine-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stt-engine-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: stt-engine-api
  template:
    metadata:
      labels:
        app: stt-engine-api
    spec:
      containers:
      - name: stt-engine-api
        image: stt-engine:latest
        ports:
        - containerPort: 8003
        env:
        - name: PYTHONUNBUFFERED
          value: "1"
        - name: VLLM_API_URL
          value: "http://vllm-service:8000"
        livenessProbe:
          httpGet:
            path: /health
            port: 8003
          initialDelaySeconds: 60
          periodSeconds: 30
```

---

## 성능 최적화

### 빌드 최적화

1. **멀티 스테이지 빌드**

```dockerfile
# Dockerfile.optimized
FROM python:3.11-slim as builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /usr/local /usr/local
COPY . .

CMD ["python3.11", "main.py"]
```

2. **레이어 캐싱 활용**

```bash
# 자주 변경되는 파일을 마지막에 복사
# 1. 기본 시스템 패키지 (거의 변경 없음)
# 2. Python 패키지 (가끔 변경)
# 3. 애플리케이션 코드 (자주 변경)
```

3. **이미지 크기 축소**

```bash
# 빌드된 이미지 최소화
docker build -t stt-engine:slim -f docker/Dockerfile .

# 불필요한 파일 제거
docker run --rm stt-engine:slim find /app -name "*.pyc" -delete
docker run --rm stt-engine:slim find /app -name "__pycache__" -type d -exec rm -rf {} +
```

### 런타임 최적화

1. **메모리 제한 설정**

```bash
# docker-compose.yml
services:
  stt-engine-api:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

2. **CPU 제한 설정**

```bash
deploy:
  resources:
    limits:
      cpus: '2.0'
    reservations:
      cpus: '1.0'
```

3. **헬스 체크 최적화**

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
  interval: 30s      # 체크 간격 (기본 30초)
  timeout: 5s        # 타임아웃 (기본 10초)
  retries: 3         # 재시도 횟수
  start_period: 60s  # 시작 대기 시간
```

---

## 문제 해결

### 빌드 실패

```bash
# 상세 로그 출력
docker build --progress=plain -t stt-engine:latest -f docker/Dockerfile .

# 빌드 캐시 초기화
docker build --no-cache -t stt-engine:latest -f docker/Dockerfile .

# 빌드 중간 상태 검사
docker build -t stt-engine:debug -f docker/Dockerfile . \
  --progress=plain 2>&1 | tail -50
```

### 컨테이너 실행 오류

```bash
# 컨테이너 로그 확인
docker logs -f stt-engine-api

# 컨테이너 내부 접근
docker exec -it stt-engine-api bash

# 의존성 확인
docker run --rm stt-engine:latest python -m pip list | grep -E "httpx|pydantic|fastapi"

# 포트 충돌 확인
lsof -i :8003
netstat -tlnp | grep 8003
```

### 메모리 부족

```bash
# 컨테이너 메모리 사용량 확인
docker stats stt-engine-api

# 시스템 메모리 확인
docker system df

# 불필요한 이미지/컨테이너 정리
docker system prune -a
docker image prune -a
docker container prune
```

---

## 배포 체크리스트

### 빌드 전
- [ ] `requirements.txt` 업데이트 확인 (OpenAI 제거됨)
- [ ] `deployment_package/requirements.txt` 동기화 확인
- [ ] 모든 소스 코드 커밋
- [ ] `.dockerignore` 파일 존재 확인

### 빌드
- [ ] 캐시 없이 빌드 실행: `--no-cache` 옵션
- [ ] 빌드 로그 검토 (경고/에러 없음)
- [ ] 최종 이미지 크기 확인

### 실행
- [ ] 이미지 실행 테스트: `docker run`
- [ ] 포트 바인딩 확인 (8003 for API, 8100 for Web UI)
- [ ] 헬스 체크 통과 확인
- [ ] API 엔드포인트 응답 확인 (curl)

### 통합
- [ ] Docker Compose 전체 스택 실행
- [ ] 서비스 간 통신 확인
- [ ] Web UI → API 연결 확인

### 배포
- [ ] 레지스트리에 이미지 푸시 (필요시)
- [ ] 프로덕션 환경 변수 설정
- [ ] 로그 수집 설정 (ELK, Splunk 등)
- [ ] 모니터링 설정 (Prometheus, Grafana 등)

---

## 환경별 배포

### 로컬 개발

```bash
# 호스트의 LLM 서버 사용
docker-compose up -d stt-engine-api

# STT API 접근
curl http://localhost:8003/health
```

### 스테이징

```bash
# 전체 스택 실행 (vLLM + Ollama 포함)
docker-compose -f docker/docker-compose-with-llm.yml up -d

# 네트워크 격리
docker network create stt-network
docker-compose --network stt-network up -d
```

### 프로덕션

```bash
# 1. 이미지 레지스트리에 푸시
docker tag stt-engine:latest registry.example.com/stt-engine:v1.0.0
docker push registry.example.com/stt-engine:v1.0.0

# 2. 프로덕션 Compose 파일 사용
docker-compose -f docker/docker-compose.prod.yml up -d

# 3. 모니터링 활성화
docker-compose exec stt-engine-api curl http://localhost:8003/metrics
```

---

## 추가 리소스

- **Docker 문서**: https://docs.docker.com/
- **Docker Compose**: https://docs.docker.com/compose/
- **Dockerfile 최적화**: https://docs.docker.com/develop/dev-best-practices/dockerfile_best-practices/

---

**작성자**: GitHub Copilot  
**마지막 수정**: 2026년 2월 25일  
**상태**: ✅ Phase 3 완료
