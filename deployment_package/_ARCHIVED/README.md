# STT Engine 오프라인 배포 패키지

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![CUDA 12.1/12.9](https://img.shields.io/badge/CUDA-12.1%2F12.9-green.svg)](https://developer.nvidia.com/cuda-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

외부 인터넷 통신이 불가능한 Linux 서버에 STT Engine을 배포하기 위한 완전한 패키지입니다.

## 🎯 특징

- ✅ **완전 오프라인 설치** - 인터넷 연결 불필요
- ✅ **자동 배포 스크립트** - 원클릭 설치
- ✅ **CUDA 12.1/12.9 최적화** - GPU 완벽 지원
- ✅ **Python 3.11 지원** - 최신 Python 버전
- ✅ **자동 검증** - 설치 후 자동 확인
- ✅ **상세한 가이드** - 단계별 설명

## 📦 패키지 구성

```
deployment_package/
├── wheels/                          # 모든 의존성 .whl 파일 (2-3GB)
│   ├── torch-2.1.2+cu121-*.whl
│   ├── torchaudio-2.1.2+cu121-*.whl
│   ├── transformers-4.37.2-*.whl
│   ├── librosa-0.10.0-*.whl
│   └── ... (50+ 패키지)
│
├── deploy.sh                        # 🚀 배포 스크립트 (인터넷 없음)
├── setup_offline.sh                 # 📦 수동 설치 스크립트
├── download_wheels.sh               # ⬇️  wheel 다운로드 (인터넷 있음)
│
├── requirements-cuda-12.9.txt       # 요구사항 명시
├── DEPLOYMENT_GUIDE.md              # 📖 상세 배포 가이드
└── README.md                        # 이 파일
```

## 🚀 빠른 시작

### 단계 1: 로컬 환경에서 wheel 다운로드 (인터넷 있는 곳)

```bash
cd deployment_package
chmod +x download_wheels.sh
./download_wheels.sh
```

**요구사항:**
- Python 3.11.x
- 인터넷 연결
- 5GB 이상 저장 공간

**시간:** 약 15-30분

### 단계 2: Linux 서버로 전송

```bash
# 로컬에서
scp -r deployment_package user@server:/home/user/

# 또는 USB/네트워크 드라이브로 전송
```

### 단계 3: Linux 서버에서 배포

```bash
cd deployment_package
chmod +x deploy.sh
./deploy.sh /opt/stt_engine_venv
```

**예상 시간:** 5-10분  
**요구사항:** Python 3.11.5, NVIDIA Driver

### 단계 4: 검증

```bash
source /opt/stt_engine_venv/bin/activate
python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

**성공 메시지:**
```
CUDA: True
```

## 📋 시스템 요구사항

### Linux 서버

| 항목 | 요구사항 | 확인 명령 |
|------|---------|----------|
| **OS** | Ubuntu 20.04+ 또는 동등 | `lsb_release -a` |
| **Python** | 3.11.5 (필수) | `python3 --version` |
| **NVIDIA Driver** | 575+ | `nvidia-smi` |
| **CUDA** | 12.1 또는 12.9 호환 | `nvidia-smi \| grep CUDA` |
| **GPU 메모리** | 6GB 이상 | `nvidia-smi` |
| **디스크 공간** | 10GB 이상 | `df -h` |
| **RAM** | 16GB 이상 (권장) | `free -h` |

### 로컬 환경 (wheel 다운로드)

| 항목 | 요구사항 |
|------|---------|
| **Python** | 3.11.x |
| **인터넷** | 필수 (15-30분) |
| **저장 공간** | 5GB 이상 |

## 📖 자세한 가이드

전체 배포 과정, 트러블슈팅, 최적화 방법은:

📄 **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** 참조

주요 섹션:
- [배포 준비](DEPLOYMENT_GUIDE.md#배포-준비)
- [서버 배포](DEPLOYMENT_GUIDE.md#서버-배포)
- [STT 엔진 설정](DEPLOYMENT_GUIDE.md#stt-엔진-설정)
- [실행](DEPLOYMENT_GUIDE.md#실행)
- [트러블슈팅](DEPLOYMENT_GUIDE.md#트러블슈팅)

## 🔧 포함된 패키지

### 핵심 라이브러리

| 패키지 | 버전 | 용도 |
|--------|------|------|
| **torch** | 2.1.2 | 딥러닝 프레임워크 (CUDA 12.1) |
| **torchaudio** | 2.1.2 | 음성 처리 (CUDA 12.1) |
| **transformers** | 4.37.2 | Hugging Face 모델 |
| **librosa** | 0.10.0 | 오디오 신호 처리 |
| **scipy** | 1.12.0 | 과학 계산 |
| **numpy** | 1.24.3 | 수치 연산 |

### 웹 프레임워크

| 패키지 | 버전 | 용도 |
|--------|------|------|
| **fastapi** | 0.109.0 | REST API 프레임워크 |
| **uvicorn** | 0.27.0 | ASGI 서버 |
| **pydantic** | 2.5.3 | 데이터 검증 |
| **requests** | 2.31.0 | HTTP 클라이언트 |

### 기타

| 패키지 | 버전 | 용도 |
|--------|------|------|
| **huggingface-hub** | 0.21.4 | 모델 다운로드 |
| **python-dotenv** | 1.0.0 | 환경 변수 |
| **pyyaml** | 6.0.1 | YAML 파싱 |

## 💻 사용 예제

### 1. 헬스 체크

```bash
curl http://localhost:8001/health
```

```json
{
  "status": "healthy",
  "device": "cuda",
  "models_loaded": true
}
```

### 2. 음성 변환 (STT)

```bash
curl -X POST \
  -F "file=@audio.wav" \
  http://localhost:8001/transcribe
```

```json
{
  "success": true,
  "text": "안녕하세요, 음성 인식 테스트입니다.",
  "language": "ko"
}
```

### 3. 음성 변환 + 텍스트 처리

```bash
curl -X POST \
  -F "file=@audio.wav" \
  -F "instruction=다음 텍스트를 요약해주세요:" \
  http://localhost:8001/transcribe-and-process
```

```json
{
  "success": true,
  "stt_result": {
    "text": "안녕하세요, 음성 인식 테스트입니다."
  },
  "vllm_result": {
    "processed_text": "음성 인식 테스트입니다."
  }
}
```

### 4. Python 클라이언트 사용

```python
from api_client import STTClient

client = STTClient("http://localhost:8001")

# 헬스 체크
client.health_check()

# STT 변환
result = client.transcribe("audio.wav")
print(result['text'])

# STT + vLLM 처리
result = client.transcribe_and_process(
    "audio.wav",
    instruction="이 내용을 요약해줄 수 있나요?"
)
```

## 🛠️ 트러블슈팅

### CUDA 문제

```bash
# CUDA 가용성 확인
python3 -c "import torch; print(torch.cuda.is_available())"

# GPU 정보 확인
nvidia-smi

# CUDA 버전 확인
cat /usr/local/cuda/version.txt
```

### 포트 충돌

```bash
# 사용 중인 포트 확인
lsof -i :8001
lsof -i :8000

# 포트 변경 실행
python3 api_server.py --port 8002
```

### 모델 문제

```bash
# 모델 디렉토리 확인
ls -la models/

# 모델 재다운로드 (인터넷 필요)
python3 download_model.py
```

더 많은 트러블슈팅은 **[DEPLOYMENT_GUIDE.md#트러블슈팅](DEPLOYMENT_GUIDE.md#트러블슈팅)** 참조

## 📊 설치 후 디렉토리 구조

```
/opt/
├── stt_engine/                      # 소스 코드
│   ├── api_server.py
│   ├── stt_engine.py
│   ├── models/
│   │   └── openai_whisper-large-v3-turbo/
│   └── ...
│
└── stt_engine_venv/                 # 가상환경
    ├── bin/
    │   ├── python3
    │   ├── pip
    │   └── activate
    ├── lib/
    │   └── python3.11/
    │       └── site-packages/       # 설치된 모든 패키지
    └── ...
```

## 🔐 보안 고려사항

1. **방화벽 설정**
   ```bash
   sudo ufw allow 8001/tcp  # STT Engine
   sudo ufw allow 8000/tcp  # vLLM (필요시)
   ```

2. **가상환경 분리**
   - 시스템 Python과 분리된 환경 사용
   - 권장: `/opt/` 또는 `/home/user/` 위치

3. **로그 모니터링**
   ```bash
   tail -f /var/log/stt-engine.log
   ```

## 📝 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

## 🤝 기여

버그 보고 및 개선 사항은 이슈로 등록해주세요.

## 📞 지원

문제 발생 시:

1. **DEPLOYMENT_GUIDE.md** 트러블슈팅 섹션 확인
2. 시스템 정보 수집:
   ```bash
   python3 --version
   nvidia-smi
   pip list
   ```
3. 에러 로그 확인 및 공유

---

**패키지 버전:** 1.0  
**Python:** 3.11  
**CUDA:** 12.1/12.9  
**생성 날짜:** 2026-01-30
