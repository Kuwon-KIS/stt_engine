# STT Engine 오프라인 배포 - 빠른 시작 가이드

## 📋 전체 프로세스

```
단계 1 (로컬 - 인터넷 있음)              단계 2 (Linux 서버 - 인터넷 없음)
┌─────────────────────────────┐         ┌──────────────────────────┐
│ Wheel 다운로드 (15-30분)     │         │ 배포 (5-10분)            │
│ • download_wheels_macos.sh   │ ──────► │ • deploy.sh              │
│ • wheels/ 생성 (2-3GB)       │ (USB)   │ • venv 생성 및 설정      │
└─────────────────────────────┘         └──────────────────────────┘
                                         ↓
                                        단계 3
                                        ┌──────────────────────────┐
                                        │ 실행 (지속적)            │
                                        │ • api_server.py          │
                                        │ • vLLM (Docker)          │
                                        └──────────────────────────┘
```

---

## 🖥️ 시스템 요구사항

### 로컬 머신 (wheel 다운로드)

```bash
# macOS 또는 Linux
• Python 3.11.x
• 인터넷 연결 (필수)
• 5GB 이상 여유 공간
```

### Linux 서버 (배포 대상)

```bash
# 확인 명령
python3 --version                    # → Python 3.11.5
nvidia-smi                          # → Driver 575.57.08+
nvidia-smi | grep CUDA              # → CUDA 12.1 또는 12.9
```

---

## 🚀 빠른 시작 (3단계)

### 📍 단계 1: 로컬에서 Wheel 다운로드

```bash
# 1. 이 디렉토리로 이동
cd deployment_package

# 2. 스크립트 권한 설정
chmod +x download_wheels_macos.sh

# 3. 실행 (15-30분 소요)
./download_wheels_macos.sh

# 결과: wheels/ 디렉토리에 .whl 파일 생성 (2-3GB)
```

**확인:**
```bash
ls -lh wheels/ | head -20        # .whl 파일들이 보여야 함
du -sh wheels/                   # 약 2-3GB
```

### 📍 단계 2: Linux 서버로 전송

```bash
# 방법 A: scp 사용
scp -r deployment_package user@server:/home/user/

# 방법 B: USB/네트워크 드라이브
cp -r deployment_package /media/usb/
```

### 📍 단계 3: Linux 서버에서 배포

```bash
# 1. 서버로 접속
ssh user@server

# 2. deployment_package로 이동
cd /home/user/deployment_package

# 3. 배포 스크립트 실행
chmod +x deploy.sh
./deploy.sh /opt/stt_engine_venv

# 또는 기본 경로 사용
./deploy.sh
# → ~/.venv/stt_engine에 설치됨
```

**예상 출력:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 배포 완료!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

가상환경 경로: /opt/stt_engine_venv

다음 단계:
  1. STT 엔진 소스코드를 /opt/stt_engine으로 복사
  2. 모델 다운로드 (인터넷 필요시)
  3. 실행: python3 api_server.py
```

---

## 🔧 설치 후 세팅

### 1. 소스코드 복사

```bash
# 로컬에서 (deployment_package 외부)
scp -r stt_engine user@server:/opt/

# 또는 직접 (서버에서)
git clone <repo> /opt/stt_engine
cd /opt/stt_engine
```

### 2. 모델 다운로드

**경우 A: 서버가 인터넷 접속 가능**

```bash
cd /opt/stt_engine
source /opt/stt_engine_venv/bin/activate

python3 download_model.py
# → 약 20-30분, 5GB 다운로드
```

**경우 B: 로컬에서 미리 다운로드**

```bash
# 로컬에서 (인터넷 있음)
python3 download_model.py

# 서버로 복사
scp -r models/ user@server:/opt/stt_engine/
```

### 3. 환경 설정 (선택)

```bash
cd /opt/stt_engine

# .env 파일 생성
cat > .env << EOF
VLLM_API_URL=http://localhost:8000
VLLM_MODEL_NAME=meta-llama/Llama-2-7b-hf
EOF
```

---

## ▶️ 실행

### 옵션 A: 통합 스크립트 (권장)

```bash
# 터미널 1
cd /opt/stt_engine
source /opt/stt_engine_venv/bin/activate
python3 api_server.py

# 터미널 2 (vLLM - Docker 필요)
docker run --gpus all -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf \
  --dtype float16
```

### 옵션 B: 커스텀 포트

```bash
# STT Engine - 포트 8002로 실행
python3 api_server.py --port 8002

# vLLM - 포트 8001로 실행
docker run --gpus all -p 8001:8000 \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf \
  --dtype float16
```

---

## ✅ 검증

### 1. 패키지 설치 확인

```bash
source /opt/stt_engine_venv/bin/activate

python3 -c "
import torch
import transformers
print('✅ PyTorch:', torch.__version__)
print('✅ Transformers:', transformers.__version__)
print('✅ CUDA Available:', torch.cuda.is_available())
print('✅ GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')
"
```

**성공 메시지:**
```
✅ PyTorch: 2.1.2
✅ Transformers: 4.37.2
✅ CUDA Available: True
✅ GPU: Tesla V100
```

### 2. API 헬스 체크

```bash
# STT Engine
curl http://localhost:8001/health

# vLLM
curl http://localhost:8000/health
```

### 3. 음성 변환 테스트

```bash
# 클라이언트로 테스트
source /opt/stt_engine_venv/bin/activate
cd /opt/stt_engine

python3 api_client.py --health

python3 api_client.py --transcribe test_audio.wav

python3 api_client.py --process test_audio.wav --instruction "요약해주세요"
```

---

## 📦 파일 구조

```
deployment_package/
├── wheels/                              # 모든 .whl 파일 (2-3GB)
│   ├── torch-2.1.2+cu121-*.whl
│   ├── transformers-4.37.2-*.whl
│   └── ... (50+ 파일)
│
├── 🚀 deploy.sh                         # 메인 배포 스크립트 (Linux)
├── 📥 download_wheels_macos.sh          # Wheel 다운로드 (macOS/Linux)
├── 📦 setup_offline.sh                  # 수동 설치 스크립트
├── ▶️  run_all.sh                        # 서비스 실행 스크립트
│
├── requirements.txt                     # 의존성 목록
├── requirements-cuda-12.9.txt           # CUDA 버전 명시
│
├── README.md                            # 상세 설명서
├── DEPLOYMENT_GUIDE.md                  # 전체 배포 가이드
└── QUICKSTART.md                        # 이 파일
```

---

## 🆘 문제 해결

### CUDA 관련

```bash
# CUDA 가용성 확인
python3 -c "import torch; print(torch.cuda.is_available())"

# 설치된 CUDA 버전
cat /usr/local/cuda/version.txt

# GPU 정보
nvidia-smi
```

### 포트 충돌

```bash
# 사용 중인 포트 확인
lsof -i :8001
lsof -i :8000

# 해결: 다른 포트 사용
python3 api_server.py --port 8002
```

### 패키지 누락

```bash
# 설치된 패키지 확인
pip list

# 특정 패키지 수동 설치
pip install --no-index --find-links=deployment_package/wheels <package>
```

더 많은 문제 해결: **[DEPLOYMENT_GUIDE.md#트러블슈팅](DEPLOYMENT_GUIDE.md#트러블슈팅)**

---

## 📊 예상 시간

| 단계 | 시간 | 비고 |
|------|------|------|
| Wheel 다운로드 | 15-30분 | 인터넷 속도에 따라 |
| 서버 배포 | 5-10분 | 오프라인 설치 |
| 모델 다운로드 | 20-30분 | 인터넷 필요, 선택사항 |
| 총 시간 | 40-70분 | - |

---

## 💡 팁

### 백그라운드 실행

```bash
# nohup 사용
nohup python3 api_server.py > stt.log 2>&1 &

# screen 사용
screen -S stt python3 api_server.py

# systemd 서비스 (자동 시작)
# 내용은 DEPLOYMENT_GUIDE.md 참조
```

### 로그 확인

```bash
# 실시간 로그
tail -f stt.log

# 에러만 필터링
grep ERROR stt.log

# 특정 시간대
grep "2026-01-30" stt.log
```

### 성능 모니터링

```bash
# GPU 모니터링
watch -n 1 nvidia-smi

# 메모리 사용
free -h

# 디스크 사용
df -h

# 프로세스 모니터링
top -p $(pgrep -f api_server.py)
```

---

## 📞 문의

문제 발생 시 준비할 정보:

```bash
# 시스템 정보
python3 --version
nvidia-smi
nvidia-driver-query

# 파이썬 환경
pip list | grep -E "torch|transformers|fastapi"

# 에러 로그
python3 api_server.py 2>&1 | tail -50
```

---

**최종 수정:** 2026-01-30  
**버전:** 1.0  
**상태:** ✅ 완성
