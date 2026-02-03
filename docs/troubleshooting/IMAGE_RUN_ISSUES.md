# 🚨 Docker 이미지 실행 오류 진단 및 해결

**목적**: `docker run` 실패 또는 컨테이너 즉시 종료 문제 해결  
**난이도**: 중급

---

## 📊 오류 진단 절차

### Step 1: 오류 메시지 수집

```bash
# 1-1. 컨테이너 ID 확인
docker ps -a | grep stt-engine

# 1-2. 상세 오류 메시지 확인
docker logs <CONTAINER_ID>

# 1-3. 오류가 많으면 전체 출력
docker logs <CONTAINER_ID> > error.log
cat error.log
```

### Step 2: 오류 유형 식별

아래에서 해당하는 오류를 찾아 해결책을 따르세요.

---

## 🔍 일반적인 오류와 해결책

### ❌ 오류 1: "No such file or directory"

**증상:**
```
FileNotFoundError: No such file or directory: '/app/models/...'
```

**원인:**
- 모델 파일이 마운트되지 않음
- 경로가 잘못됨

**해결책:**

```bash
# 1. 모델 파일 존재 확인
ls -lh /path/to/local/models/

# 2. 마운트 경로 확인
docker inspect <CONTAINER_ID> | grep -A 5 "Mounts"

# 3. 올바른 경로로 재실행
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v /home/user/models/openai_whisper-large-v3-turbo:/app/models/openai_whisper-large-v3-turbo \
  stt-engine:linux-x86_64
```

---

### ❌ 오류 2: "Address already in use"

**증상:**
```
Error response from daemon: Ports are not available: exposing port TCP 0.0.0.0:8003 -> 0.0.0.0:0: listen tcp 0.0.0.0:8003: bind: address already in use
```

**원인:**
- 포트 8003이 이미 사용 중

**해결책:**

```bash
# 1. 포트 점유 확로 확인
lsof -i :8003
# 또는
netstat -tulpn | grep 8003

# 2. 기존 컨테이너 확인 및 중지
docker ps | grep stt-engine
docker stop <OLD_CONTAINER_ID>
docker rm <OLD_CONTAINER_ID>

# 3. 다른 포트 사용 (임시)
docker run -d \
  --name stt-engine \
  -p 8004:8003 \
  stt-engine:linux-x86_64

# 4. 프로세스 강제 종료 (최후의 수단)
kill -9 $(lsof -t -i :8003)
```

---

### ❌ 오류 3: "Out of memory"

**증상:**
```
Killed
# 또는
MemoryError
```

**원인:**
- 컨테이너 메모리 제한이 너무 작음
- 모델이 너무 큼

**해결책:**

```bash
# 1. 시스템 메모리 확인
free -h

# 2. 메모리 한계 증설
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -m 8gb \
  --memory-swap 8gb \
  -v /path/to/models:/app/models \
  stt-engine:linux-x86_64

# 3. 또는 docker-compose.yml에서
services:
  stt-engine:
    mem_limit: 8g
    memswap_limit: 8g
```

**메모리 요구사항:**
| 모델 | 최소 메모리 | 권장 메모리 |
|------|-----------|-----------|
| large-v3 | 4GB | 8GB |
| medium | 2GB | 4GB |
| base | 1GB | 2GB |

---

### ❌ 오류 4: "ModuleNotFoundError"

**증상:**
```
ModuleNotFoundError: No module named 'faster_whisper'
```

**원인:**
- Python 패키지 설치 실패
- Wheel 파일 설치 안 됨

**해결책:**

```bash
# 1. 컨테이너 진입
docker exec -it <CONTAINER_ID> /bin/bash

# 2. 패키지 설치 상태 확인
pip list | grep faster-whisper

# 3. 누락된 패키지 설치
pip install faster-whisper

# 또는 wheel 파일에서 설치
pip install --no-index --find-links=/wheels/ faster-whisper

# 4. 컨테이너 재시작
docker restart <CONTAINER_ID>
```

---

### ❌ 오류 5: "Model not found"

**증상:**
```
RuntimeError: Model not found at /app/models/...
```

**원인:**
- 모델 폴더 이름 불일치
- 경로 오류

**해결책:**

```bash
# 1. 컨테이너 내 모델 구조 확인
docker exec <CONTAINER_ID> ls -lh /app/models/

# 2. 예상되는 구조:
# /app/models/
# └── openai_whisper-large-v3-turbo/
#     ├── config.json
#     ├── model.bin
#     └── ...

# 3. 구조가 다르면 압축 해제
docker exec <CONTAINER_ID> tar -xzf /app/models/whisper-model.tar.gz -C /app/models/

# 4. 확인
docker exec <CONTAINER_ID> ls -lh /app/models/openai_whisper-large-v3-turbo/
```

---

### ❌ 오류 6: "CUDA/GPU not found"

**증상:**
```
WARNING: CUDA not found, falling back to CPU
# 또는
torch.cuda.is_available() = False
```

**원인:**
- NVIDIA Docker 미설치
- GPU 드라이버 문제
- Docker에 GPU 접근 권한 없음

**해결책:**

```bash
# 1. NVIDIA Docker 설치 확인
nvidia-docker --version

# 설치 안 되어 있으면
apt-get install nvidia-docker2

# 2. Docker 데몬 재시작
sudo systemctl restart docker

# 3. GPU 사용하여 실행
docker run -d \
  --gpus all \
  --name stt-engine \
  -p 8003:8003 \
  -v /path/to/models:/app/models \
  stt-engine:linux-x86_64

# 4. GPU 인식 확인
docker exec <CONTAINER_ID> nvidia-smi
```

---

### ❌ 오류 7: "Uvicorn bind failed"

**증상:**
```
ERROR: [Errno 99] Cannot assign requested address
```

**원인:**
- 포트 바인딩 설정 오류
- 네트워크 인터페이스 문제

**해결책:**

```bash
# 1. 호스트 모드 확인
docker inspect <CONTAINER_ID> | grep "NetworkMode"

# 2. 명시적으로 바인드 설정
docker run -d \
  --name stt-engine \
  -p 0.0.0.0:8003:8003 \
  stt-engine:linux-x86_64

# 3. localhost만 바인드 (로컬 접근만)
docker run -d \
  --name stt-engine \
  -p 127.0.0.1:8003:8003 \
  stt-engine:linux-x86_64
```

---

## 🔧 컨테이너 상태 확인

### 기본 진단

```bash
# 1. 컨테이너 상태
docker ps -a | grep stt-engine

# 2. 상세 정보
docker inspect <CONTAINER_ID> | jq '.State'

# 예상 출력:
# {
#   "Status": "running",
#   "Running": true,
#   "Paused": false,
#   "Restarting": false,
#   "OOMKilled": false,
#   "Dead": false,
#   "Pid": 12345,
#   "ExitCode": 0,
#   "Error": ""
# }
```

### 상세 진단

```bash
# 1. 마운트 확인
docker inspect <CONTAINER_ID> | jq '.Mounts'

# 2. 포트 확인
docker inspect <CONTAINER_ID> | jq '.HostConfig.PortBindings'

# 3. 환경 변수 확인
docker inspect <CONTAINER_ID> | jq '.Config.Env'

# 4. 메모리 설정 확인
docker inspect <CONTAINER_ID> | jq '.HostConfig | {Memory, MemorySwap, MemoryReservation}'
```

---

## 📝 로그 분석 팁

### 로그 필터링

```bash
# 특정 단어 포함 로그만 보기
docker logs <CONTAINER_ID> 2>&1 | grep -i "error"

# 마지막 N줄만 보기
docker logs --tail 50 <CONTAINER_ID>

# 타임스탬프 포함
docker logs --timestamps <CONTAINER_ID>

# 실시간 로그
docker logs -f <CONTAINER_ID>

# 특정 시간 이후
docker logs --since 30m <CONTAINER_ID>
```

### 로그 저장

```bash
# 전체 로그 저장
docker logs <CONTAINER_ID> > container.log 2>&1

# 분석용 정렬
docker logs <CONTAINER_ID> 2>&1 | grep -E "ERROR|WARNING|FAIL" | tee errors.log
```

---

## 🚀 복구 절차

### 완전 초기화

```bash
# 1. 컨테이너 중지 및 제거
docker stop <CONTAINER_ID>
docker rm <CONTAINER_ID>

# 2. 이미지 다시 로드 (필요시)
docker load -i stt-engine-linux-x86_64.tar

# 3. 새로 실행
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v /path/to/models:/app/models \
  stt-engine:linux-x86_64

# 4. 로그 확인
docker logs stt-engine
```

### 부분 복구

```bash
# 1. 컨테이너만 재시작
docker restart <CONTAINER_ID>

# 2. 특정 파일만 업데이트
docker cp stt_engine.py <CONTAINER_ID>:/app/
docker restart <CONTAINER_ID>
```

---

## 📊 진단 체크리스트

오류 발생 시 다음을 확인하세요:

```
□ docker ps -a 에서 컨테이너 상태 확인
□ docker logs 로 오류 메시지 수집
□ 오류 유형 식별
□ 해당 섹션의 해결책 적용
□ docker restart 실행
□ curl http://localhost:8003/health 로 확인
□ 문제 해결되지 않으면 다음 섹션 시도
```

---

## 📞 추가 도움말

- [CONTAINER_FILE_UPDATES.md](./CONTAINER_FILE_UPDATES.md) - 파일 업데이트 방법
- [SERVER_DEPLOYMENT_GUIDE.md](../SERVER_DEPLOYMENT_GUIDE.md) - 배포 가이드
- Docker 공식 문서: https://docs.docker.com/

---

**상태**: 🟢 대부분의 오류 해결 가능 ✅
