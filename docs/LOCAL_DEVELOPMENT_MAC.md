# STT Engine - Mac 로컬 개발 가이드

**최종 업데이트**: 2026년 2월 20일

## 📋 개요

Mac 환경에서 STT Engine을 로컬로 개발하기 위한 완벽한 가이드입니다.

- **STT Engine**: 음성인식 모델 (Whisper)
- **Web UI**: 사용자 인터페이스
- **환경**: macOS (Apple Silicon/Intel), CPU 기반

---

## 🎯 빠른 시작 (5분)

### 1단계: 이미지 빌드

```bash
# STT Engine 빌드 (10~20분)
bash scripts/build-local-engine-image.sh

# Web UI 빌드 (3~5분)
bash scripts/build-local-web-ui-image.sh
```

### 2단계: 네트워크 생성

```bash
docker network create stt-network
```

### 3단계: 컨테이너 실행

```bash
# 터미널 1: STT Engine 실행
docker run -d --name stt-engine-local -p 8003:8003 \
  -e STT_DEVICE=cpu \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/audio/samples:/app/audio/samples \
  stt-engine:local

# 터미널 2: Web UI 실행
docker run -d --name stt-web-ui-local -p 8100:8100 \
  -e STT_API_URL=http://host.docker.internal:8003 \
  -v $(pwd)/web_ui/data:/app/data \
  -v $(pwd)/web_ui/logs:/app/logs \
  stt-web-ui:local
```

### 4단계: 접속

- **Web UI**: http://localhost:8100
- **STT API**: http://localhost:8003

---

## 🛠️ 상세 설정

### 사전 요구사항

- **macOS**: 10.15 이상
- **Docker Desktop**: 최신 버전 (M1/M2 지원)
- **저장공간**: 20GB 이상
- **메모리**: 8GB 이상 권장

### Docker Desktop 설정 확인

```bash
# Docker 버전 확인
docker --version

# Apple Silicon 지원 확인
docker run --platform linux/amd64 alpine uname -m
# 출력: x86_64
```

---

## 📦 빌드 스크립트 상세

### STT Engine 빌드

```bash
# 기본값 (latest 태그)
bash scripts/build-local-engine-image.sh

# 특정 버전으로 빌드
bash scripts/build-local-engine-image.sh v1.0

# 수동 빌드 (고급)
docker build --platform linux/amd64 \
  -t stt-engine:local-v1.0 \
  -f docker/Dockerfile.engine.local .
```

**생성 결과:**
- 이미지명: `stt-engine:local` 또는 `stt-engine:local-v1.0`
- 크기: ~600MB
- 시간: 10~20분

### Web UI 빌드

```bash
# 기본값
bash scripts/build-local-web-ui-image.sh

# 특정 버전
bash scripts/build-local-web-ui-image.sh v1.0

# 수동 빌드
docker build --platform linux/amd64 \
  -t stt-web-ui:local \
  -f web_ui/docker/Dockerfile.web_ui.local .
```

**생성 결과:**
- 이미지명: `stt-web-ui:local`
- 크기: ~200MB
- 시간: 3~5분

---

## 🚀 컨테이너 실행 상세

### STT Engine 실행

```bash
docker run -d \
  --name stt-engine-local \
  -p 8003:8003 \
  -e STT_DEVICE=cpu \
  -e STT_BACKEND=faster-whisper \
  -e LOG_LEVEL=INFO \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/audio/samples:/app/audio/samples \
  -v $(pwd)/logs:/app/logs \
  stt-engine:local
```

**환경 변수:**
- `STT_DEVICE=cpu`: 고정 (로컬용)
- `STT_BACKEND`: `faster-whisper` | `transformers` | `openai-whisper`
- `LOG_LEVEL`: `DEBUG` | `INFO` | `WARNING`

**헬스 체크:**
```bash
curl http://localhost:8003/health | jq
```

### Web UI 실행

```bash
docker run -d \
  --name stt-web-ui-local \
  -p 8100:8100 \
  -e STT_API_URL=http://host.docker.internal:8003 \
  -e LOG_LEVEL=INFO \
  -v $(pwd)/web_ui/data:/app/data \
  -v $(pwd)/web_ui/logs:/app/logs \
  stt-web-ui:local
```

**환경 변수:**
- `STT_API_URL`: Mac에서 `http://host.docker.internal:8003` 필수
- `LOG_LEVEL`: `DEBUG` | `INFO` | `WARNING`

**헬스 체크:**
```bash
curl http://localhost:8100/health | jq
```

---

## 📡 API 테스트

### 1. STT 음성인식 테스트

```bash
# 파일 업로드로 테스트
curl -X POST http://localhost:8003/transcribe \
  -F "file=@audio/samples/short_0.5s.wav" | jq

# 파일 경로로 테스트 (컨테이너 경로)
curl -X POST http://localhost:8003/transcribe \
  -F "file_path=/app/audio/samples/short_0.5s.wav" | jq

# 응답 예시
{
  "success": true,
  "text": "안녕하세요.",
  "language": "ko",
  "backend": "faster-whisper",
  "duration": 0.5,
  "processing_time_seconds": 2.3,
  "is_dummy": false
}
```

### 2. 모델 전환 테스트

```bash
# 현재 백엔드 확인
curl http://localhost:8003/backend/current | jq

# 백엔드 전환
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"backend": "transformers"}' | jq
```

### 3. Dummy Fallback 테스트

```bash
# 모델 디렉토리 제거 (강제 폴백 테스트)
docker exec stt-engine-local rm -rf /app/models/*

# API 호출 (Dummy 응답 반환)
curl -X POST http://localhost:8003/transcribe \
  -F "file=@audio/samples/short_0.5s.wav" | jq

# 응답 예시
{
  "success": false,
  "text": "",
  "is_dummy": true,
  "dummy_reason": "파일을 찾을 수 없음",
  "error": "[Errno 2] No such file or directory",
  "error_type": "FileNotFoundError"
}
```

---

## 📊 로그 확인

### 실시간 로그

```bash
# STT Engine 로그
docker logs -f stt-engine-local

# Web UI 로그
docker logs -f stt-web-ui-local

# 마지막 100줄
docker logs --tail=100 stt-engine-local
```

### 로그 레벨 변경

```bash
# 디버그 모드로 재실행
docker stop stt-engine-local
docker run -d \
  --name stt-engine-local \
  -p 8003:8003 \
  -e STT_DEVICE=cpu \
  -e LOG_LEVEL=DEBUG \
  -v $(pwd)/models:/app/models \
  stt-engine:local
```

---

## 🔧 문제 해결

### 이슈 1: 포트 충돌

```bash
# 포트 사용 확인
lsof -i :8003
lsof -i :8100

# 포트 해제
sudo kill -9 <PID>

# 또는 다른 포트로 실행
docker run -d --name stt-engine-local -p 8004:8003 \
  -e STT_DEVICE=cpu \
  -v $(pwd)/models:/app/models \
  stt-engine:local
```

### 이슈 2: 메모리 부족

```bash
# Docker 메모리 할당 증가 (Settings → Resources)
# 또는 모델을 작은 버전으로 변경

docker run -d --name stt-engine-local -p 8003:8003 \
  -e STT_DEVICE=cpu \
  -e STT_MODEL=tiny \
  -v $(pwd)/models:/app/models \
  stt-engine:local
```

### 이슈 3: Mac에서 호스트 포트 접근 불가

```bash
# host.docker.internal 사용 확인
docker exec stt-web-ui-local curl -v http://host.docker.internal:8003/health

# 해결: Docker Desktop 설정
# Settings → Resources → Network → Docker subnet 확인
```

### 이슈 4: 모델 다운로드 실패

```bash
# 호스트에서 모델 미리 다운로드
python download_model_hf.py

# 또는 EC2에서 다운로드 후 복사
scp -i aws-key.pem ec2-user@host:~/stt_engine/build/output/models.tar.gz .
tar -xzf models.tar.gz -C models/
```

---

## 🧹 정리 및 제거

### 컨테이너 정지

```bash
# 개별 정지
docker stop stt-engine-local stt-web-ui-local

# 모든 stt 컨테이너 정지
docker stop $(docker ps -q -f "label=app=stt" 2>/dev/null) 2>/dev/null || true
```

### 컨테이너 삭제

```bash
# 개별 삭제
docker rm stt-engine-local stt-web-ui-local

# 이미지 삭제
docker rmi stt-engine:local stt-web-ui:local

# 전체 정리 (주의!)
docker system prune -a --volumes
```

---

## 📚 고급 사용법

### docker-compose 사용

```bash
# 실행 (참고용)
docker-compose -f docker/docker-compose.local.yml up -d

# 로그 확인
docker-compose -f docker/docker-compose.local.yml logs -f

# 종료
docker-compose -f docker/docker-compose.local.yml down
```

### 환경 변수 커스터마이징

```bash
# .env 파일 생성
cat > .env.local << EOF
STT_DEVICE=cpu
STT_BACKEND=faster-whisper
LOG_LEVEL=DEBUG
STT_API_URL=http://host.docker.internal:8003
EOF

# 사용
docker run -d --name stt-engine-local -p 8003:8003 \
  --env-file .env.local \
  -v $(pwd)/models:/app/models \
  stt-engine:local
```

### 성능 측정

```bash
# API 응답 시간 측정
time curl -X POST http://localhost:8003/transcribe \
  -F "file=@audio/samples/test.wav" > /dev/null

# 메모리 사용량 확인
docker stats stt-engine-local --no-stream

# CPU 사용률 확인
docker top stt-engine-local
```

---

## 🔄 EC2와의 차이점

| 항목 | Mac 로컬 | EC2 (RHEL 8.9) |
|------|---------|--------------|
| **이미지** | `Dockerfile.engine.local` | `Dockerfile.engine.rhel89` |
| **CPU** | CPU-only | CUDA 12.9 |
| **빌드 시간** | 10~20분 | 20~40분 |
| **이미지 크기** | ~600MB | ~1.5GB |
| **호스트 접근** | `host.docker.internal` | docker network bridge |
| **스크립트** | `build-local-*.sh` | `build-ec2-*.sh` |

---

## 💡 팁과 트릭

### 1. 반복적인 빌드 가속화

```bash
# Docker 빌드 캐시 활용
docker build --platform linux/amd64 \
  --cache-from stt-engine:local \
  -t stt-engine:local \
  -f docker/Dockerfile.engine.local .
```

### 2. 모델 캐시 재사용

```bash
# 호스트 models 디렉토리 사용
mkdir -p models
docker run -d --name stt-engine-local -p 8003:8003 \
  -v $(pwd)/models:/app/models \
  stt-engine:local
```

### 3. 빠른 개발 루프

```bash
# 컨테이너 중지 및 재실행 (코드 수정 후)
docker stop stt-engine-local
docker start stt-engine-local  # 또는 run으로 다시 시작
```

---

## 📞 지원

문제 발생 시:

1. **로그 확인**: `docker logs stt-engine-local`
2. **헬스 체크**: `curl http://localhost:8003/health`
3. **Docker 재시작**: `docker restart stt-engine-local`
4. **전체 재구성**: `docker system prune -a` 후 재빌드

---

## ✅ 체크리스트

- [ ] Docker Desktop 설치 (M1/M2 지원)
- [ ] `docker --version` 확인
- [ ] `build-local-engine-image.sh` 실행
- [ ] `build-local-web-ui-image.sh` 실행
- [ ] `docker network create stt-network` 실행
- [ ] STT Engine 컨테이너 시작
- [ ] Web UI 컨테이너 시작
- [ ] `http://localhost:8100` 접속 확인
- [ ] API 테스트 (curl 예제)
- [ ] 로그 확인 및 Dummy Fallback 테스트

---

**Last Updated**: 2026년 2월 20일  
**Author**: STT Engine Team  
**Platform**: macOS (Apple Silicon/Intel) + Linux
