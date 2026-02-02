# 📦 STT Engine 오프라인 배포 체크리스트

**배포 대상:** RHEL 8.9, Python 3.11.5, CUDA 12.9 (외부 인터넷 없음)  
**배포 방법:** macOS에서 준비 → Linux 서버로 transfer → 온라인 PyTorch 설치

---

## ✅ macOS 준비 단계

### 파일 확인
- [x] `stt_engine_deployment_final.tar.gz` (2.8GB) - 권장
  - 44개 일반 패키지 wheels 포함
  - 모든 자동화 스크립트 포함
  - PyTorch 온라인 설치 스크립트 포함

- [x] `stt_engine_deployment_slim_v2.tar.gz` (137MB) - 경량
  - wheels만 포함 (이 경우 PyTorch는 Linux에서 설치)

### 가이드 문서 확인
- [x] `OFFLINE_DEPLOYMENT_GUIDE.md` - 전체 배포 절차
- [x] `LINUX_PYTORCH_INSTALL.sh` - 자동 설치 스크립트
- [x] `LINUX_PYTORCH_INSTALL_GUIDE.md` - 단계별 명령어

### PyTorch wheel 상태
- [x] macOS에서 다운로드 시도 완료
- [ ] **결과:** PyTorch CDN 완전 차단 → Linux 서버 온라인 설치로 변경
- [x] 대체 방법: Linux 서버에서 자동으로 설치하도록 스크립트 구성

---

## 📥 Linux 서버 배포 단계

### Step 1: 파일 전송
```bash
# macOS에서:
scp stt_engine_deployment_final.tar.gz user@your-server:/tmp/

# 확인
ssh user@your-server "ls -lh /tmp/stt_engine_deployment_final.tar.gz"
```

- [ ] 파일 전송 완료
- [ ] 파일 크기 확인 (2.8GB)
- [ ] 체크섬 검증 (옵션)

### Step 2: 추출
```bash
ssh user@your-server
cd /tmp
tar -xzf stt_engine_deployment_final.tar.gz
cd stt_engine
```

- [ ] tar 추출 성공
- [ ] 디렉토리 구조 확인
  ```bash
  ls -la
  # 포함되어야 할 파일:
  # - LINUX_PYTORCH_INSTALL.sh
  # - deployment_package/
  # - venv/
  # - api_server.py
  # - download_model.py
  ```

### Step 3: 자동 PyTorch 설치
```bash
bash LINUX_PYTORCH_INSTALL.sh
```

**스크립트 체크:**
- [ ] 시스템 정보 표시 (Python, CUDA, 디스크)
- [ ] 가상환경 활성화
- [ ] pip 업그레이드
- [ ] 44개 wheels 설치 (오프라인)
- [ ] PyTorch 온라인 다운로드 (자동)
- [ ] PyTorch 설치 완료
- [ ] 설치 검증 (torch import, GPU 확인)

**예상 소요 시간:** 20-30분

### Step 4: 설치 검증
```bash
# 자동 검증 (스크립트에서)
# 또는 수동:
python3 -c "import torch; print(f'✅ PyTorch {torch.__version__}')"
python3 -c "import torch; print(f'✅ GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"
```

- [ ] torch import 성공
- [ ] torchaudio import 성공
- [ ] CUDA available = True
- [ ] GPU 정보 출력

---

## 🔄 모델 설치 (온라인 필요)

**전제:** Linux 서버에 **인터넷 연결** 필요

```bash
python3 download_model.py
```

- [ ] 모델 다운로드 시작 (약 15-30분)
- [ ] `~/.cache/huggingface/hub/models--openai--whisper-large-v3-turbo/` 생성 확인
- [ ] 모델 파일 크기 확인 (약 5GB)

---

## 🚀 API 서버 실행

```bash
python3 api_server.py
```

**확인 사항:**
- [ ] 출력: `Uvicorn running on http://0.0.0.0:8001`
- [ ] 포트 8001 열려있음

### 헬스 체크
```bash
curl http://localhost:8001/health
# 응답: {"status":"ok","version":"1.0.0"}
```

- [ ] 헬스 체크 응답 200
- [ ] API 정상 작동

---

## 🔍 최종 검증

### 전체 기능 테스트
```bash
# 패키지 모두 import
python3 << 'EOF'
import torch
import torchaudio
import transformers
import librosa
import fastapi
print("✅ 모든 패키지 로드 성공")
EOF
```

- [ ] 모든 패키지 import 성공

### GPU 확인
```bash
python3 -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA Available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
"
```

- [ ] CUDA available = True
- [ ] GPU 메모리 표시
- [ ] GPU 이름 출력

### 모델 확인
```bash
ls -lah ~/.cache/huggingface/hub/models--openai--whisper-large-v3-turbo/
```

- [ ] 모델 디렉토리 존재
- [ ] safetensors 파일 존재 (약 1.4GB)

### API 테스트
```bash
# 헬스 체크
curl http://localhost:8001/health | jq .

# 또는 간단히
curl http://localhost:8001/health
```

- [ ] 응답 성공 (200)
- [ ] JSON 응답 유효

---

## 🆘 문제 해결

### 문제: "torch not found"
```bash
# 확인
source venv/bin/activate
which python
python -c "import torch"
```
- [ ] 가상환경 활성화 확인

### 문제: CUDA not available
```bash
# 확인
nvidia-smi
python -c "import torch; print(torch.version.cuda)"
```
- [ ] nvidia-smi 작동
- [ ] CUDA 버전 일치 (12.9)

### 문제: 디스크 부족
```bash
df -h /
du -sh ~/.cache/
```
- [ ] 최소 5GB 여유 공간 확인

### 문제: PyTorch 설치 실패
```bash
# 수동 설치 재시도
pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cu124 -v
```
- [ ] 네트워크 연결 확인
- [ ] 재시도

---

## 📊 배포 완료 기준

모든 항목이 체크되면 배포 완료:

| 항목 | 확인 |
|------|------|
| tar 파일 전송 | ✅ |
| tar 추출 | ✅ |
| 자동 스크립트 실행 | ✅ |
| PyTorch 설치 | ✅ |
| 모델 다운로드 | ✅ |
| API 서버 실행 | ✅ |
| 헬스 체크 성공 | ✅ |
| GPU 확인 | ✅ |
| **배포 완료** | **✅** |

---

## 📋 문제 보고 템플릿

설치 실패 시:

```bash
# 1. 시스템 정보 수집
uname -a > system_info.txt
python3 --version >> system_info.txt
nvidia-smi >> system_info.txt

# 2. 설치 로그 수집
bash LINUX_PYTORCH_INSTALL.sh 2>&1 | tee install.log

# 3. 파이썬 정보
python3 -c "import torch, sys; print(f'Python: {sys.version}'); print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.version.cuda}')" > torch_info.txt

# 4. 파일들 수집
# system_info.txt
# install.log
# torch_info.txt
```

---

## 💾 백업 및 복구

### 설치 후 백업
```bash
# 설치 성공 후 snapshot 생성
tar -czf stt_engine_deployed_backup.tar.gz stt_engine/
```

### 재배포 (복구)
```bash
# 백업에서 복원
tar -xzf stt_engine_deployed_backup.tar.gz
cd stt_engine
python3 api_server.py
```

---

## ⏱️ 예상 총 소요 시간

| 단계 | 시간 | 누적 |
|------|------|------|
| 파일 전송 | 5-30분* | 5-30분 |
| tar 추출 | 1-2분 | 6-32분 |
| PyTorch 설치 | 15-25분 | 21-57분 |
| 모델 다운로드 | 20-40분** | 41-97분 |
| 합계 | **40-100분** | |

\* 네트워크 속도에 따라 다름  
\** 모델은 별도 진행 가능

---

**상태:** ✅ 배포 준비 완료  
**최종 업데이트:** 2026-02-02  
**담당:** AI Deployment Team
