# 🚀 STT Engine 오프라인 배포 최종 가이드

**상황:** RHEL 8.9 Linux 서버는 외부 인터넷 없음 → macOS에서 패키지 준비 → 서버로 transfer → 설치

---

## 📦 준비된 배포 파일

### 옵션 1: 권장 (2.8GB - 완전 패키지)
```bash
stt_engine_deployment_final.tar.gz
```
- ✅ 44개 일반 패키지 wheels 포함
- ✅ 모든 설정 스크립트
- ✅ 자동 PyTorch 온라인 설치 스크립트
- ✅ 모든 문서 포함

### 옵션 2: 경량 (137MB - wheels만)
```bash
stt_engine_deployment_slim_v2.tar.gz
```
- 44개 wheels만 포함 (venv 제외)
- PyTorch는 Linux 서버에서 온라인 설치

---

## 🎯 Linux 서버 배포 절차

### Step 1: 파일 전송 (macOS → Linux 서버)

```bash
# macOS 터미널에서:
scp stt_engine_deployment_final.tar.gz user@your-server:/tmp/

# 또는 경량 버전:
scp stt_engine_deployment_slim_v2.tar.gz user@your-server:/tmp/
```

### Step 2: 서버에서 추출 및 설정

```bash
# Linux 서버에서 로그인:
ssh user@your-server

# 추출
cd /tmp
tar -xzf stt_engine_deployment_final.tar.gz
cd stt_engine

# 또는
tar -xzf stt_engine_deployment_slim_v2.tar.gz
cd stt_engine
```

### Step 3: PyTorch 자동 설치

#### 옵션 A: 자동 스크립트 (권장)
```bash
bash LINUX_PYTORCH_INSTALL.sh
```

**스크립트가 하는 일:**
- 시스템 정보 확인 (Python, CUDA, GPU)
- 가상환경 활성화
- pip 업그레이드
- 44개 wheels 설치
- **PyTorch 온라인 다운로드 및 설치** (약 10-20분)
- 설치 검증 (GPU 확인)
- 다음 단계 안내

**예상 소요 시간:** 15-30분

#### 옵션 B: 한 줄 명령
```bash
source venv/bin/activate && \
pip install --upgrade pip && \
pip install deployment_package/wheels/*.whl && \
pip install torch torchaudio torchvision
```

#### 옵션 C: 단계별 수동 설치
```bash
# 1. 가상환경 활성화
source venv/bin/activate

# 2. pip 업그레이드
pip install --upgrade pip setuptools wheel

# 3. 기존 wheels 설치
find deployment_package/wheels -name "*.whl" ! -name "torch*" ! -name "torchaudio*" -type f \
  | xargs pip install -q

# 4. PyTorch 설치 (자동 선택)
pip install torch torchaudio torchvision

# 또는 CUDA 12.4 명시:
pip install torch torchaudio torchvision \
    --index-url https://download.pytorch.org/whl/cu124
```

### Step 4: 설치 검증

```bash
python3 << 'EOF'
import torch
import torchaudio

print(f"✅ PyTorch: {torch.__version__}")
print(f"✅ torchaudio: {torchaudio.__version__}")
print(f"✅ CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
    print(f"✅ GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
EOF
```

**예상 출력:**
```
✅ PyTorch: 2.4.0+cu124 (또는 최신 버전)
✅ torchaudio: 2.4.0+cu124
✅ CUDA Available: True
✅ GPU: NVIDIA A100 (또는 당신의 GPU)
✅ GPU Memory: 40.0 GB
```

### Step 5: 모델 다운로드

```bash
# venv 활성화 상태에서:
python3 download_model.py
```

**예상 소요 시간:** 15-30분 (네트워크 속도에 따라)

**다운로드될 모델:**
- OpenAI Whisper Large v3 (~5GB)
- HuggingFace에서 자동 다운로드

### Step 6: API 서버 실행

```bash
python3 api_server.py
```

**출력:**
```
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Step 7: 헬스 체크

```bash
# 다른 터미널에서:
curl http://localhost:8001/health

# 응답:
# {"status":"ok","version":"1.0.0"}
```

---

## 🔧 트러블슈팅

### 문제 1: "torch not found"
**원인:** 가상환경 미활성화

**해결:**
```bash
source venv/bin/activate
python3 -c "import torch; print(torch.__version__)"
```

### 문제 2: "CUDA not available" (경고)
**원인:** NVIDIA 드라이버/CUDA 불일치

**해결:** CPU 모드로도 작동 (느림), 또는:
```bash
# NVIDIA driver 확인
nvidia-smi

# CUDA 버전 확인
nvcc --version
```

### 문제 3: "Connection refused" (모델 다운로드 실패)
**원인:** 인터넷 연결 필요

**해결:**
- Linux 서버에 인터넷 연결 필요 (모델 다운로드)
- 또는 미리 다운로드한 모델 파일 transfer

### 문제 4: 디스크 부족
**확인:**
```bash
df -h /
du -sh ~/.cache/pip/  # pip 캐시
du -sh ~/.cache/huggingface/  # HF 캐시
```

**해결:**
```bash
# pip 캐시 정리
rm -rf ~/.cache/pip/*

# 필요시 모델만 다운로드 (전체 설치 스킵)
python3 download_model.py
```

---

## 📊 설치 예상 시간 분석

| 단계 | 시간 | 비고 |
|------|------|------|
| tar 추출 | 1-2분 | 디스크 속도 의존 |
| pip 업그레이드 | 1-2분 | 빠름 |
| 44개 wheels 설치 | 2-3분 | 오프라인 |
| PyTorch 다운로드 | 5-10분 | 네트워크 의존 |
| PyTorch 설치 | 3-5분 | 디스크 속도 의존 |
| 모델 다운로드 | 15-30분 | 네트워크 의존 |
| **총합** | **30-60분** | |

---

## 🎯 체크리스트

배포 전:
- [ ] macOS에서 `stt_engine_deployment_final.tar.gz` 생성 확인
- [ ] 파일 크기 확인 (~2.8GB)
- [ ] tar 구조 검증: `tar -tzf file.tar.gz | head -20`

서버에서:
- [ ] tar 파일 전송 완료
- [ ] 추출 완료
- [ ] `LINUX_PYTORCH_INSTALL.sh` 존재 확인
- [ ] `deployment_package/wheels/` 디렉토리 확인

설치 후:
- [ ] Python import torch 성공
- [ ] nvidia-smi 실행 성공
- [ ] 모델 다운로드 완료
- [ ] API 서버 실행 성공
- [ ] 헬스 체크 200 응답

---

## 💡 추가 팁

### 1. 백그라운드 설치 (SSH 연결 끊겨도 계속)
```bash
nohup bash LINUX_PYTORCH_INSTALL.sh > install.log 2>&1 &

# 진행 상황 확인
tail -f install.log
```

### 2. 설치 로그 저장
```bash
bash LINUX_PYTORCH_INSTALL.sh 2>&1 | tee install_$(date +%Y%m%d_%H%M%S).log
```

### 3. 여러 버전 동시 테스트
```bash
# PyTorch 버전 확인
pip show torch | grep Version

# 다른 CUDA 버전으로 재설치
pip install torch==2.2.0 --index-url https://download.pytorch.org/whl/cu121
```

### 4. 모델 캐시 위치 변경
```bash
# HuggingFace 캐시 위치 변경 (큰 디스크로)
export HF_HOME=/large/disk/path
python3 download_model.py
```

---

## 📞 문제 발생 시 수집 정보

설치 실패 시 이 정보들을 수집해주세요:

```bash
# 시스템 정보
uname -a
python3 --version
nvidia-smi
nvcc --version

# PyTorch 설치 상태
pip show torch
python3 -c "import torch; print(torch.version.cuda, torch.cuda.is_available())"

# 에러 로그
cat install.log | tail -50
```

---

## ✅ 최종 확인

배포 완료 기준:

```bash
# 1. 패키지 확인
python3 -c "import torch, torchaudio, transformers, librosa; print('✅ All packages OK')"

# 2. GPU 확인
python3 -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}' if torch.cuda.is_available() else 'CPU mode')"

# 3. 모델 확인
ls -lah ~/.cache/huggingface/hub/ | grep whisper

# 4. API 확인
curl -s http://localhost:8001/health | python3 -m json.tool
```

모두 성공하면 **배포 완료! 🎉**

---

**Last Updated:** 2026-02-02
**Deployment Method:** Offline (44 wheels) + Online PyTorch
**Target Server:** RHEL 8.9, Python 3.11.5, CUDA 12.9
