# Docker Run with Logging & Rotation

Docker Compose 대신 `docker run` 명령어로 배포할 때 로그 rotation 설정 방법

---

## 📋 로깅 설정 요약

### 애플리케이션 파일 로깅 (RotatingFileHandler)
- **api_server/app.py**: `logs/api_server.log` (10MB × 5 files)
- **stt_engine.py**: `logs/stt_engine.log` (10MB × 5 files)
- **web_ui/main.py**: `logs/web_ui.log` + `logs/performance.log` (10MB × 5 files each)

### Docker 로깅 드라이버 (stdout/stderr rotation)
- `json-file` 드라이버 사용
- 최대 파일 크기: **100MB**
- 보관 파일 개수: **5개**
- 저장 위치: `/var/lib/docker/containers/<container-id>/<container-id>-json.log*`

---

## � Docker Daemon 기본 로깅 설정 (한 번만)

`--log-opt max-size`, `--log-opt max-file`을 매번 지정하지 않도록 Docker daemon 전역 기본값 설정

### Linux / Docker 서버 환경

`/etc/docker/daemon.json` 파일 수정:

```bash
sudo nano /etc/docker/daemon.json
```

다음 내용 추가/수정:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "5"
  }
}
```

저장 후 Docker 데몬 재시작:

```bash
sudo systemctl restart docker
```

### Mac / Docker Desktop

**GUI 방법:**
1. Docker Desktop 메뉴 → **Settings** 
2. **Docker Engine** 탭
3. JSON 설정에 다음 추가:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "5"
  }
}
```

4. **Apply & Restart**

**CLI 방법:**

```bash
# Docker Desktop 설정 파일 직접 수정 (Mac)
nano ~/.docker/daemon.json
```

위의 JSON 설정 추가

### 설정 확인

```bash
docker info | grep -A 10 "Logging Driver"
```

출력 예:
```
 Logging Driver: json-file
 Cgroup Driver: cgroupfs
 Cgroup Version: 1
 Plugins:
  Log: awslogs local json-file splunk awsfirelens gcplogs awsfirelensexec syslog sumologic
```

---

## �🚀 네트워크 생성 (선택사항)

두 컨테이너가 통신할 경우만 필요:

```bash
docker network create stt-network
```

---

## 🐳 STT Engine API 컨테이너 실행

### 빌드 (처음 한 번)

```bash
cd /path/to/stt_engine
docker build -t stt-engine:latest -f docker/Dockerfile .
```

### 실행

**기본값 설정이 완료된 경우 (위 설정 완료 시):**

```bash
docker run -d \
  --name stt-api \
  --network stt-network \
  -p 8003:8003 \
  -e PYTHONUNBUFFERED=1 \
  -e HF_HOME=/app/models \
  -e STT_DEVICE=auto \
  -e LOG_LEVEL=INFO \
  -e MAX_CONCURRENT_SLOTS=6 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/logs:/app/logs \
  --health-cmd='curl -f http://localhost:8003/health' \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=60s \
  stt-engine:latest
```

**기본값 설정을 안 한 경우 (매번 지정):**

```bash
docker run -d \
  --name stt-api \
  --network stt-network \
  -p 8003:8003 \
  -e PYTHONUNBUFFERED=1 \
  -e HF_HOME=/app/models \
  -e STT_DEVICE=auto \
  -e LOG_LEVEL=INFO \
  -e MAX_CONCURRENT_SLOTS=6 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/logs:/app/logs \
  --log-driver json-file \
  --log-opt max-size=100m \
  --log-opt max-file=5 \
  --health-cmd='curl -f http://localhost:8003/health' \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=60s \
  stt-engine:latest
```

**로그 확인:**

```bash
# 실시간 로그 (stdout/stderr)
docker logs -f stt-api

# 파일 로그 (호스트 volume)
tail -f logs/api_server.log
tail -f logs/stt_engine.log
```

---

## 🌐 Web UI 컨테이너 실행

### 빌드 (처음 한 번)

```bash
cd /path/to/stt_engine
docker build -t stt-web-ui:latest -f web_ui/docker/Dockerfile.web_ui .
```

### 실행

**기본값 설정이 완료된 경우 (위 설정 완료 시):**

```bash
docker run -d \
  --name stt-web-ui \
  --network stt-network \
  -p 8100:8100 \
  -e PYTHONUNBUFFERED=1 \
  -e WEB_HOST=0.0.0.0 \
  -e WEB_PORT=8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -e LOG_LEVEL=INFO \
  -v $(pwd)/web_ui/data:/app/data \
  -v $(pwd)/web_ui/logs:/app/logs \
  --health-cmd='curl -f http://localhost:8100/health' \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=30s \
  stt-web-ui:latest
```

**기본값 설정을 안 한 경우 (매번 지정):**

```bash
docker run -d \
  --name stt-web-ui \
  --network stt-network \
  -p 8100:8100 \
  -e PYTHONUNBUFFERED=1 \
  -e WEB_HOST=0.0.0.0 \
  -e WEB_PORT=8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -e LOG_LEVEL=INFO \
  -v $(pwd)/web_ui/data:/app/data \
  -v $(pwd)/web_ui/logs:/app/logs \
  --log-driver json-file \
  --log-opt max-size=100m \
  --log-opt max-file=5 \
  --health-cmd='curl -f http://localhost:8100/health' \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=30s \
  stt-web-ui:latest
```

**로그 확인:**

```bash
# 실시간 로그 (stdout/stderr)
docker logs -f stt-web-ui

# 파일 로그 (호스트 volume)
tail -f web_ui/logs/web_ui.log
tail -f web_ui/logs/performance.log
```

---

## 🔄 로그 Rotation 동작

### 파일 로깅 (RotatingFileHandler)

```
logs/
├── api_server.log          # 현재 로그 (< 10MB)
├── api_server.log.1        # 자동 rotation (10MB 초과 시)
├── api_server.log.2
├── api_server.log.3
├── api_server.log.4
├── api_server.log.5        # 최대 5개 보관
│
├── stt_engine.log
├── stt_engine.log.1-5
│
├── web_ui.log
├── web_ui.log.1-5
│
└── performance.log
    └── performance.log.1-5
```

**자동 정리:**
- 파일 크기 10MB 초과 → 자동 `*.log.1`, `*.log.2` ... 로 rotate
- `*.log.5` 파일 초과 시 삭제

### Docker 로깅 드라이버 (json-file)

```
/var/lib/docker/containers/<container-id>/
├── <container-id>-json.log           # 현재 로그
├── <container-id>-json.log.1         # Rotate
├── <container-id>-json.log.2
├── <container-id>-json.log.3
├── <container-id>-json.log.4
└── <container-id>-json.log.5         # 최대 5개
```

**자동 정리:**
- 파일 크기 100MB 초과 → 자동 rotation
- 최대 5개 파일만 유지

---

## 📊 로그 위치 정리

| 로그 | 위치 | 크기 | 개수 | 확인 방법 |
|------|------|------|------|----------|
| API stdout/stderr | Docker daemon | 100MB | 5 | `docker logs stt-api` |
| API 파일 로그 | `logs/api_server.log*` | 10MB | 5 | `tail -f logs/api_server.log` |
| STT stdout/stderr | Docker daemon | 100MB | 5 | `docker logs stt-api` (포함) |
| STT 파일 로그 | `logs/stt_engine.log*` | 10MB | 5 | `tail -f logs/stt_engine.log` |
| Web UI stdout/stderr | Docker daemon | 100MB | 5 | `docker logs stt-web-ui` |
| Web UI 파일 로그 | `web_ui/logs/web_ui.log*` | 10MB | 5 | `tail -f web_ui/logs/web_ui.log` |
| Performance 로그 | `web_ui/logs/performance.log*` | 10MB | 5 | `tail -f web_ui/logs/performance.log` |

---

## 🛑 컨테이너 종료 & 정리

```bash
# 컨테이너 중지
docker stop stt-api stt-web-ui

# 컨테이너 삭제
docker rm stt-api stt-web-ui

# 네트워크 삭제 (선택사항)
docker network rm stt-network

# 이미지 삭제 (선택사항)
docker rmi stt-engine:latest stt-web-ui:latest
```

---

## 💡 팁

### 1. Mac에서 host 포트 접근
```bash
# web_ui → API 통신 시 (docker-to-host)
# 사용: http://host.docker.internal:8003
# docker network 내에서는: http://stt-api:8003
```

### 2. 로그 파일 크기 모니터링
```bash
du -sh logs/
du -sh web_ui/logs/
```

### 3. Docker 로그 저장소 크기
```bash
# 모든 컨테이너 로그 용량
docker ps -a --format '{{.ID}}' | xargs -I {} du -sh /var/lib/docker/containers/{}/
```

### 4. 환경변수 변경 시 다시 빌드 필요 없음
```bash
# 컨테이너만 다시 시작 (로그 레벨 변경 예)
docker run ... -e LOG_LEVEL=DEBUG ...
```

---

## 🔍 문제 해결

### 로그가 저장되지 않음
```bash
# 1. 호스트 logs 디렉토리 권한 확인
ls -la logs/

# 2. 컨테이너 내부 logs 디렉토리 생성 여부
docker exec stt-api ls -la /app/logs/

# 3. 파일 시스템 용량 확인
df -h logs/
```

### 컨테이너가 떨어짐
```bash
# 헬스 체크 상태 확인
docker inspect --format='{{.State.Health.Status}}' stt-api

# 자세한 로그 확인
docker logs stt-api | tail -50
```

### Docker 로그 드라이버 설정 확인
```bash
docker inspect stt-api | grep -A 5 '"LogConfig"'
```
