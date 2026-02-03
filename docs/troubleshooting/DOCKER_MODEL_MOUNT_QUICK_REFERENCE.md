# 🐳 STT Engine Docker with Model Mount - Quick Reference

**날짜**: 2026-02-03  
**목적**: 모델을 마운트하고 Health Check를 수행하는 방법

---

## 🚀 가장 빠른 방법: 스크립트 실행

### 자동 실행 (권장)

```bash
bash /Users/a113211/workspace/stt_engine/docker-run-with-models.sh
```

**이 스크립트가 자동으로 수행하는 작업:**
1. ✅ 이전 컨테이너 정리
2. ✅ 모델 디렉토리 확인
3. ✅ Docker 이미지 확인
4. ✅ 모델 마운트 (-v 옵션)
5. ✅ 컨테이너 실행
6. ✅ Health Check 수행 (최대 30초 대기)
7. ✅ 모델 경로 확인
8. ✅ PyTorch 정보 출력

---

## 📋 수동 실행 (한 줄 명령어)

### Step 1: 이전 컨테이너 정리

```bash
docker stop stt-engine-test 2>/dev/null || true
docker rm stt-engine-test 2>/dev/null || true
```

### Step 2: 컨테이너 실행 (모델 마운트 포함)

```bash
docker run -d \
  --name stt-engine-test \
  -p 8003:8003 \
  -v /Users/a113211/workspace/stt_engine/models:/app/models \
  -e STT_DEVICE=cpu \
  -e HF_HOME=/app/models \
  stt-engine:cuda129-v1.0
```

**주요 옵션 설명:**
| 옵션 | 설명 |
|------|------|
| `-d` | 백그라운드 실행 |
| `--name stt-engine-test` | 컨테이너 이름 |
| `-p 8003:8003` | 포트 매핑 |
| `-v 로컬경로:컨테이너경로` | **모델 디렉토리 마운트** (핵심!) |
| `-e STT_DEVICE=cpu` | CPU 모드 사용 |
| `-e HF_HOME=/app/models` | Hugging Face 캐시 경로 |

### Step 3: Health Check

```bash
curl -X GET http://localhost:8003/health
```

**예상 응답:**
```json
{"status":"healthy"}
```

---

## 🔍 상태 확인 명령어

### 1. 컨테이너 실행 상태

```bash
docker ps | grep stt-engine
```

**예상 출력:**
```
CONTAINER ID   IMAGE                    STATUS        PORTS
abc12345...    stt-engine:cuda129...    Up 2 minutes  0.0.0.0:8003->8003/tcp
```

### 2. 실시간 로그 보기 (모델 로딩 확인)

```bash
docker logs -f stt-engine-test
```

**예상 로그:**
```
Loading model 'openai_whisper-large-v3-turbo'...
✅ Model loaded successfully (Device: cpu, compute: int8)
Uvicorn running on http://0.0.0.0:8003
```

### 3. 컨테이너 내부 모델 확인

```bash
docker exec stt-engine-test ls -lh /app/models/
```

**예상 출력:**
```
openai_whisper-large-v3-turbo/  [모델 디렉토리]
```

### 4. PyTorch 정보 확인

```bash
docker exec stt-engine-test python3 << 'EOF'
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA Available: {torch.cuda.is_available()}')
print(f'CUDA Version: {torch.version.cuda}')
print(f'Device: {"cuda" if torch.cuda.is_available() else "cpu"}')
EOF
```

**예상 출력:**
```
PyTorch: 2.6.0
CUDA Available: False
CUDA Version: None
Device: cpu
```

### 5. API Health Check 상세 정보

```bash
curl -v http://localhost:8003/health
```

---

## 🧪 STT 테스트

### 음성 파일 업로드 테스트

```bash
# 테스트 음성 파일 경로 (예시)
TEST_AUDIO="/path/to/test_audio.wav"

curl -X POST http://localhost:8003/transcribe \
  -F "file=@$TEST_AUDIO"
```

**예상 응답:**
```json
{
  "text": "인식된 음성 텍스트...",
  "duration_seconds": 5.2,
  "processing_time_seconds": 0.8,
  "model": "whisper-large-v3-turbo",
  "device": "cpu"
}
```

---

## 🔴 문제 해결

### 문제 1: "Health Check 실패 (타임아웃)"

**원인:** 모델 로딩 실패  
**확인 방법:**
```bash
docker logs stt-engine-test | tail -50
```

**해결책:**
```bash
# 1. 모델 경로 확인
docker exec stt-engine-test ls -lh /app/models/

# 2. 컨테이너 디버그 모드 실행
docker run -it --rm \
  -v /Users/a113211/workspace/stt_engine/models:/app/models \
  stt-engine:cuda129-v1.0 \
  python3 -c "from faster_whisper import WhisperModel; \
              model = WhisperModel('large-v3-turbo', device='cpu')"
```

### 문제 2: "포트 8003이 이미 사용 중"

```bash
# 다른 포트로 실행
docker run -d \
  --name stt-engine-test \
  -p 8004:8003 \  # 8004:8003으로 변경
  -v /Users/a113211/workspace/stt_engine/models:/app/models \
  -e STT_DEVICE=cpu \
  stt-engine:cuda129-v1.0

# 새 포트로 확인
curl http://localhost:8004/health
```

### 문제 3: "모델을 찾을 수 없음"

```bash
# 1. 로컬 모델 디렉토리 확인
ls -la /Users/a113211/workspace/stt_engine/models/

# 2. 모델 구조 확인 (openai_whisper-large-v3-turbo 있는지)
ls -la /Users/a113211/workspace/stt_engine/models/openai_whisper-large-v3-turbo/

# 3. 컨테이너 내 마운트 확인
docker inspect stt-engine-test | grep -A 5 "Mounts"
```

---

## 🧹 정리

### 컨테이너 중지

```bash
docker stop stt-engine-test
```

### 컨테이너 완전 제거

```bash
docker rm stt-engine-test
```

### 이미지 제거 (필요한 경우)

```bash
docker rmi stt-engine:cuda129-v1.0
```

---

## 📊 주요 파일 경로

| 항목 | 경로 |
|------|------|
| 실행 스크립트 | `/Users/a113211/workspace/stt_engine/docker-run-with-models.sh` |
| 로컬 모델 | `/Users/a113211/workspace/stt_engine/models/` |
| 컨테이너 모델 경로 | `/app/models/` |
| Docker 이미지 | `stt-engine:cuda129-v1.0` |

---

## 💡 팁

### 1. 빠른 테스트

```bash
# 스크립트로 모든 검사 자동화
bash docker-run-with-models.sh
```

### 2. 모델 업데이트

로컬 모델을 변경하면 컨테이너에 자동으로 반영됨 (마운트 덕분)

### 3. 여러 컨테이너 동시 실행

```bash
# 다른 포트와 이름으로 실행
docker run -d --name stt-engine-gpu -p 8004:8003 \
  -v /Users/a113211/workspace/stt_engine/models:/app/models \
  -e STT_DEVICE=cuda \
  stt-engine:cuda129-v1.0
```

---

**마지막 업데이트**: 2026-02-03  
**상태**: ✅ 사용 가능
