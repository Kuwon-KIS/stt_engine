# 🔍 근본 원인 분석 및 해결책

**작성일**: 2026-02-03  
**현황**: 세 가지 실제 문제 식별 및 해결 방안 제시

---

## ⚠️ 발견된 문제들

### 문제 1: python-multipart Wheel 파일 누락 ❌

**확인 결과**:
```bash
$ ls deployment_package/wheels/ | grep -i multipart
# 결과: 없음 ❌
```

**영향**:
- FastAPI의 File Upload 기능 사용 불가
- `/transcribe` 엔드포인트 로드 실패
- 오프라인 환경에서 pip 설치 불가능

**해결책**: 두 가지 옵션

---

## 🔧 해결 방법 1: python-multipart Wheel 추가

### 옵션 A: 새 Wheel 다운로드 후 추가

로컬 머신에서:
```bash
# 1. pip-wheel 설치 (아직 없으면)
pip install pip-wheel

# 2. python-multipart wheel 다운로드
pip wheel python-multipart -w deployment_package/wheels/

# 3. 다운로드 확인
ls -lh deployment_package/wheels/ | grep multipart

# 4. wheels.tar.gz 다시 생성
tar -czf build/output/wheels.tar.gz -C deployment_package wheels/
```

### 옵션 B: 기존 Wheel 파일 찾기

```bash
# 시스템에 이미 설치된 wheel 위치 찾기
find /path/to/pip/cache -name "*multipart*.whl" 2>/dev/null

# 또는 PyPI에서 직접 다운로드
wget https://files.pythonhosted.org/packages/.../python_multipart-0.0.6-py3-none-any.whl \
  -O deployment_package/wheels/

# 확인
ls -lh deployment_package/wheels/python_multipart*
```

### 옵션 C: Dockerfile에서 직접 설치

Dockerfile.engine 수정:
```dockerfile
# ... (기존 내용)

# Install packages from wheels (offline)
RUN python3.11 -m pip install --no-index --find-links=/wheels/ \
    torch torchaudio faster-whisper \
    librosa scipy numpy \
    fastapi uvicorn requests pydantic \
    huggingface-hub python-dotenv pyyaml \
    python-multipart  # ← 추가
```

---

## 🔧 문제 2: CUDA 드라이버 호환성

**현재 상황**:
- 이미지: CUDA 12.1 기반 PyTorch 2.1.2
- 서버: CUDA 드라이버 버전 낮음 (충돌)
- 오류: `CUDA driver version is insufficient for CUDA runtime version`

**왜 반영이 안 됐는가**:

api_server.py 라인 25:
```python
device="cuda",  # ← 하드코딩되어 있음
```

stt_engine.py 라인 237:
```python
device = "cuda"  # ← 기본값이 cuda
```

**문제**: CPU 옵션이 없이 항상 CUDA 사용 시도

### 해결책 1: CPU 모드로 빌드 (권장 - 서버 환경)

api_server.py 수정:
```python
# 라인 25 변경
device="cpu",  # CUDA 드라이버 불일치 문제 해결
```

또는 환경변수 사용:
```python
# 라인 25 변경
device=os.getenv("STT_DEVICE", "cpu"),  # 기본값: cpu
```

Dockerfile.engine 수정:
```dockerfile
ENV STT_DEVICE=cpu  # CUDA 드라이버 호환성 문제 있는 서버용
```

### 해결책 2: 여러 버전 이미지 빌드

**Dockerfile.engine-cpu** (새로 생성):
```dockerfile
FROM python:3.11-slim

# ... (동일한 내용)

# CPU 최적화
ENV STT_DEVICE=cpu
CMD ["python3.11", "api_server.py"]
```

빌드 명령:
```bash
docker build -t stt-engine:linux-x86_64-cpu -f docker/Dockerfile.engine-cpu .
```

---

## 🔧 문제 3: Exited 컨테이너에서 docker exec 불가

**현재 상황**:
```
[ddpapp@dlddpgai1 sw]$ docker ps
# stt-engine: Exited (1)
```

**이유**: 컨테이너가 시작 실패로 종료됨 (exec 불가능)

### 해결책: 새 이미지로 컨테이너 재실행

```bash
# 1. 기존 컨테이너 제거
docker stop 29534921b493
docker rm 29534921b493

# 2. 새 이미지 로드 (수정 후)
docker load -i stt-engine-linux-x86_64.tar

# 3. 새로 실행
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v /path/to/models:/app/models \
  stt-engine:linux-x86_64

# 4. 확인
docker ps | grep stt-engine
```

---

## 📋 완전한 해결 순서

### Step 1: 로컬에서 준비 (10분)

```bash
cd /Users/a113211/workspace/stt_engine

# 1-1. python-multipart wheel 추가
pip wheel python-multipart -w deployment_package/wheels/

# 1-2. wheels.tar.gz 갱신
tar -czf build/output/wheels.tar.gz -C deployment_package wheels/

# 1-3. api_server.py CPU 모드로 변경
sed -i '' 's/device="cuda"/device="cpu"/' api_server.py

# 또는 환경변수 방식 사용 (더 나음)
```

### Step 2: Dockerfile 수정

**docker/Dockerfile.engine** 수정:
```dockerfile
# 라인 19-22 변경:
RUN python3.11 -m pip install --no-index --find-links=/wheels/ \
    torch torchaudio faster-whisper \
    librosa scipy numpy \
    fastapi uvicorn requests pydantic \
    huggingface-hub python-dotenv pyyaml \
    python-multipart

# 라인 31 추가:
ENV STT_DEVICE=cpu  # 또는 cuda (CUDA 드라이버가 충분하면)
```

### Step 3: 새 이미지 빌드

```bash
bash scripts/build-engine-image.sh
# 또는
docker build -t stt-engine:linux-x86_64 -f docker/Dockerfile.engine .
```

### Step 4: 서버로 전송 및 배포

```bash
# 로컬에서
scp build/output/stt-engine-linux-x86_64.tar user@server:/path/to/

# 서버에서
docker load -i stt-engine-linux-x86_64.tar
docker stop stt-engine
docker rm stt-engine
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v /path/to/models:/app/models \
  stt-engine:linux-x86_64

# 확인
docker logs stt-engine
curl http://localhost:8003/health
```

---

## 📊 실제 코드 변경 사항

### api_server.py - 라인 20-28

**변경 전**:
```python
# 모델 초기화
# faster-whisper는 자동으로 CUDA 감지
try:
    model_path = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"
    stt = WhisperSTT(
        str(model_path),
        device="cuda",
        compute_type="float16"  # VRAM 효율적, 빠른 추론
    )
```

**변경 후 (옵션 1 - 고정)**:
```python
# 모델 초기화
# CPU/CUDA 자동 선택 또는 고정
try:
    model_path = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"
    stt = WhisperSTT(
        str(model_path),
        device=os.getenv("STT_DEVICE", "cpu"),  # 환경변수로 제어
        compute_type="float16"  # VRAM 효율적, 빠른 추론
    )
```

**import 추가**:
```python
import os  # 라인 8에 추가
```

### Dockerfile.engine - 라인 19-23

**변경 전**:
```dockerfile
RUN python3.11 -m pip install --no-index --find-links=/wheels/ \
    torch torchaudio faster-whisper \
    librosa scipy numpy \
    fastapi uvicorn requests pydantic \
    huggingface-hub python-dotenv pyyaml && \
```

**변경 후**:
```dockerfile
RUN python3.11 -m pip install --no-index --find-links=/wheels/ \
    torch torchaudio faster-whisper \
    librosa scipy numpy \
    fastapi uvicorn requests pydantic \
    huggingface-hub python-dotenv pyyaml \
    python-multipart && \
```

**라인 31에 추가**:
```dockerfile
ENV STT_DEVICE=cpu
```

---

## 🎯 최종 체크리스트

```
사전 작업
□ python-multipart wheel 추가 (deployment_package/wheels/)
□ wheels.tar.gz 갱신
□ api_server.py 수정 (device 설정)
□ Dockerfile.engine 수정 (python-multipart 추가, STT_DEVICE 설정)
□ 새 이미지 빌드 (scripts/build-engine-image.sh)

배포
□ 서버로 이미지 전송
□ 기존 컨테이너 중지/제거
□ 새 이미지 로드 (docker load)
□ 새 컨테이너 실행 (docker run)
□ 로그 확인 (docker logs)
□ 헬스 체크 성공 (curl /health)
□ 음성 파일 테스트
```

---

## 📝 정리

### 근본 원인 3가지:

1. **python-multipart 누락** 
   - ✅ Wheel 추가로 해결

2. **CUDA 드라이버 호환성**
   - ✅ 환경변수 방식으로 CPU/CUDA 선택 가능하게 변경

3. **Exited 컨테이너에서 exec 불가**
   - ✅ 새 이미지로 재시작하면 해결

**상태**: 🟢 명확한 해결 방안 제시 ✅
