# STT Engine 오프라인 배포 가이드

## 📋 목차
1. [배포 준비 (인터넷 있는 환경)](#배포-준비)
2. [서버 배포 (인터넷 없는 환경)](#서버-배포)
3. [검증](#검증)
4. [트러블슈팅](#트러블슈팅)

---

## 배포 준비

### 1단계: 로컬 환경에서 wheel 다운로드

**요구사항:**
- Python 3.11.x
- 인터넷 연결
- 약 5GB 이상의 저장 공간

**실행:**
```bash
cd deployment_package
chmod +x download_wheels.sh
./download_wheels.sh
```

**예상 다운로드 시간:** 15-30분 (인터넷 속도에 따라)

**생성되는 파일:**
- `wheels/` - 모든 .whl 파일 (약 2-3GB)

### 2단계: 배포 패키지 준비

```bash
# deployment_package 전체를 복사
cp -r deployment_package /path/to/transfer/location
```

**패키지 구조:**
```
deployment_package/
├── wheels/                          # 모든 .whl 파일
├── deploy.sh                        # 배포 스크립트
├── setup_offline.sh                 # 오프라인 설치 스크립트
├── requirements-cuda-12.9.txt       # 요구사항 파일
├── DEPLOYMENT_GUIDE.md              # 이 파일
└── README.md                        # 설명서
```

### 3단계: Linux 서버로 전송

USB, 네트워크 드라이브 등으로 `deployment_package`를 서버로 전송합니다.

---

## 서버 배포

### 서버 요구사항

**필수:**
- Python 3.11.5
- NVIDIA Driver 575.57.08 이상
- CUDA 12.1/12.9 호환

**확인 명령:**
```bash
python3 --version
nvidia-smi
nvidia-smi --query-gpu=name --format=csv,noheader
```

**예상 출력:**
```
Python 3.11.5
# NVIDIA-SMI output...
Tesla V100  # 또는 다른 GPU
```

### 배포 스크립트 실행

#### 옵션 A: 자동 배포 (권장)

```bash
cd deployment_package
chmod +x deploy.sh
./deploy.sh /opt/stt_engine_venv
```

**또는 기본 경로 사용:**
```bash
./deploy.sh
# 가상환경이 ~/.venv/stt_engine에 생성됨
```

#### 옵션 B: 수동 설치

```bash
# 1. 가상환경 생성
python3 -m venv /opt/stt_engine_venv

# 2. 가상환경 활성화
source /opt/stt_engine_venv/bin/activate

# 3. pip 업그레이드
pip install --upgrade pip setuptools wheel

# 4. 오프라인에서 모든 패키지 설치
pip install --no-index --find-links=deployment_package/wheels \
    deployment_package/wheels/*.whl
```

### 검증

```bash
source /opt/stt_engine_venv/bin/activate

python3 -c "
import torch
import transformers
import fastapi
print('✅ PyTorch:', torch.__version__)
print('✅ Transformers:', transformers.__version__)
print('✅ FastAPI:', fastapi.__version__)
print('✅ CUDA Available:', torch.cuda.is_available())
print('✅ GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')
"
```

**예상 출력:**
```
✅ PyTorch: 2.1.2
✅ Transformers: 4.37.2
✅ FastAPI: 0.109.0
✅ CUDA Available: True
✅ GPU: Tesla V100
```

---

## STT 엔진 설정

### 1단계: 소스코드 복사

```bash
# deployment_package 외부의 소스파일들을 복사
cp -r stt_engine /opt/
```

**필요한 파일:**
- `api_server.py`
- `stt_engine.py`
- `vllm_client.py`
- `model_manager.py`
- 기타 .py 파일들

### 2단계: 모델 준비

#### 경우 A: 인터넷 접속 가능 (권장)

```bash
cd /opt/stt_engine
source /opt/stt_engine_venv/bin/activate

python3 download_model.py
```

**다운로드 시간:** 약 20-30분
**필요 공간:** 약 5GB

#### 경우 B: 사전 다운로드된 모델 사용

로컬에서 모델을 다운로드한 후 `models/` 디렉토리를 전송:

```bash
# 로컬에서
python3 download_model.py

# 전송
scp -r models/ user@server:/opt/stt_engine/
```

### 3단계: 환경 설정

```bash
cd /opt/stt_engine

# .env 파일 생성 (필요시)
cat > .env << EOF
VLLM_API_URL=http://localhost:8000
VLLM_MODEL_NAME=meta-llama/Llama-2-7b-hf
EOF
```

---

## 실행

### 터미널 1: STT 엔진 시작

```bash
cd /opt/stt_engine
source /opt/stt_engine_venv/bin/activate

python3 api_server.py
```

**예상 출력:**
```
🔗 vLLM 서버 연결 설정
   API URL: http://localhost:8000
   모델: meta-llama/Llama-2-7b-hf
✅ 모델 로드 완료
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### 터미널 2: vLLM 서버 시작

```bash
# Docker 사용 (권장)
docker run --gpus all \
  -p 8000:8000 \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf \
  --dtype float16

# 또는 venv 설치 후
source /opt/vllm_venv/bin/activate
python3 -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-hf \
  --dtype float16
```

### 터미널 3: 테스트

```bash
source /opt/stt_engine_venv/bin/activate

# 헬스 체크
python3 api_client.py --health

# STT 변환
python3 api_client.py --transcribe audio.wav

# STT + vLLM 처리
python3 api_client.py --process audio.wav --instruction "요약해주세요"
```

---

## 검증

### 헬스 체크 API

```bash
curl http://localhost:8001/health
```

**예상 응답:**
```json
{
  "status": "healthy",
  "device": "cuda",
  "models_loaded": true
}
```

### STT API 테스트

```bash
curl -X POST \
  -F "file=@audio.wav" \
  http://localhost:8001/transcribe
```

---

## 시스템 서비스화 (선택)

### systemd 서비스 생성

```bash
sudo cat > /etc/systemd/system/stt-engine.service << EOF
[Unit]
Description=STT Engine Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/stt_engine
ExecStart=/opt/stt_engine_venv/bin/python3 api_server.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable stt-engine
sudo systemctl start stt-engine
sudo systemctl status stt-engine
```

### 서비스 관리

```bash
# 상태 확인
sudo systemctl status stt-engine

# 로그 확인
sudo journalctl -u stt-engine -f

# 시작/중지
sudo systemctl start stt-engine
sudo systemctl stop stt-engine
sudo systemctl restart stt-engine
```

---

## 트러블슈팅

### 문제 1: CUDA 관련 오류

**증상:**
```
RuntimeError: CUDA out of memory
```

**해결:**
```bash
# GPU 메모리 확인
nvidia-smi

# 모델 크기 확인
ls -lh models/

# 필요시 smaller 모델 사용
# vllm_client.py에서 모델명 변경
```

### 문제 2: 포트 이미 사용 중

**증상:**
```
Address already in use: ('0.0.0.0', 8001)
```

**해결:**
```bash
# 사용 중인 프로세스 확인
lsof -i :8001

# 포트 변경
python3 api_server.py --port 8002
```

### 문제 3: 모델 로드 실패

**증상:**
```
FileNotFoundError: models/openai_whisper-large-v3-turbo not found
```

**해결:**
```bash
# 모델 디렉토리 확인
ls -la models/

# 필요시 모델 재다운로드
python3 download_model.py
```

### 문제 4: vLLM 연결 실패

**증상:**
```
❌ vLLM 서버 연결 불가
```

**해결:**
```bash
# vLLM 서버 실행 확인
curl http://localhost:8000/health

# vLLM 시작 (별도 터미널)
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf
```

### 문제 5: 패키지 설치 실패

**증상:**
```
ERROR: Could not find a version that satisfies the requirement
```

**해결:**
```bash
# 수동으로 wheel 파일 지정 설치
cd deployment_package/wheels
pip install *.whl --no-index

# 또는 특정 패키지만
pip install --no-index --find-links=. torch-2.1.2+cu121-cp311-cp311-linux_x86_64.whl
```

---

## 성능 최적화

### GPU 메모리 최대화

```python
# api_server.py 수정
import torch
torch.cuda.empty_cache()
```

### vLLM 최적화

```bash
docker run --gpus all \
  -p 8000:8000 \
  --ipc=host \
  -e VLLM_ATTENTION_BACKEND=xformers \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf \
  --dtype float16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.9
```

---

## 문의 및 피드백

배포 중 문제가 발생하면 다음 정보를 준비하세요:

1. **시스템 정보:**
   ```bash
   uname -a
   python3 --version
   nvidia-smi
   ```

2. **에러 로그:**
   ```bash
   # STT Engine 로그
   tail -100 stt_engine.log
   ```

3. **pip 정보:**
   ```bash
   pip list
   ```

---

**배포 가이드 버전:** 1.0  
**마지막 업데이트:** 2026-01-30  
**작성자:** STT Engine Team
