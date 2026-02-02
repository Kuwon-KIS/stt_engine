# Linux 서버에서 PyTorch 설치 - 단계별 명령어

## 🚀 빠른 시작 (한 줄 명령)

```bash
cd /path/to/stt_engine && \
source venv/bin/activate && \
pip install --upgrade pip && \
pip install torch torchaudio torchvision && \
python3 -c "import torch; print(f'✅ PyTorch {torch.__version__}')"
```

---

## 📋 단계별 명령어

### Step 1: 프로젝트 디렉토리로 이동

```bash
cd /path/to/stt_engine
```

### Step 2: 가상환경 활성화

```bash
source venv/bin/activate
```

**확인:**
```bash
which python
# 출력: /path/to/stt_engine/venv/bin/python
```

### Step 3: pip 업그레이드

```bash
pip install --upgrade pip setuptools wheel
```

### Step 4: 기존 wheels 설치 (PyTorch 제외)

```bash
# 모든 wheel 설치 (PyTorch는 별도로 처리)
ls deployment_package/wheels/*.whl 2>/dev/null || echo "wheel 없음"

# 설치
find deployment_package/wheels -name "*.whl" ! -name "torch*" ! -name "torchaudio*" -type f \
  | xargs pip install -q
```

### Step 5: PyTorch 설치

#### 옵션 A: 최신 버전 (권장) ⭐

```bash
pip install torch torchaudio torchvision
```

**장점:**
- 자동으로 CUDA 12.9와 최적화된 버전 선택
- 가장 새로운 기능
- 가장 간단

**시간:** 5-10분

---

#### 옵션 B: CUDA 12.4 명시

```bash
pip install torch torchaudio torchvision \
    --index-url https://download.pytorch.org/whl/cu124
```

**특징:**
- CUDA 12.9와 완벽 호환
- 좀 더 안정적인 버전

**시간:** 5-10분

---

#### 옵션 C: CUDA 12.1 명시 (보수적)

```bash
pip install torch torchaudio torchvision \
    --index-url https://download.pytorch.org/whl/cu121
```

**특징:**
- 가장 낮은 CUDA 요구사항
- 모든 환경에서 작동

**시간:** 5-10분

---

### Step 6: 설치 검증

```bash
python3 << 'EOF'
import torch
import torchaudio

print(f"✅ PyTorch: {torch.__version__}")
print(f"✅ torchaudio: {torchaudio.__version__}")
print(f"✅ CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"✅ CUDA Version: {torch.version.cuda}")
    print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
    print(f"✅ GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
EOF
```

**예상 출력:**
```
✅ PyTorch: 2.4.0+cu124
✅ torchaudio: 2.4.0+cu124
✅ CUDA Available: True
✅ CUDA Version: 12.4
✅ GPU: NVIDIA A100 (또는 당신의 GPU)
✅ GPU Memory: 40.0 GB (또는 당신의 GPU 메모리)
```

---

## 🔧 자동 스크립트 실행

이 스크립트를 사용하면 위 모든 단계를 자동으로 실행합니다:

```bash
cd /path/to/stt_engine
bash LINUX_PYTORCH_INSTALL.sh
```

**스크립트가 하는 일:**
1. 시스템 정보 확인 (Python, CUDA, 디스크)
2. 가상환경 활성화
3. pip 업그레이드
4. 기존 wheels 설치
5. PyTorch 설치
6. 설치 검증
7. 다음 단계 안내

---

## ⏱️ 예상 소요 시간

| 단계 | 시간 |
|------|------|
| pip 업그레이드 | 1-2분 |
| wheels 설치 (44개) | 2-3분 |
| PyTorch 다운로드 | 3-5분 |
| PyTorch 설치 | 2-3분 |
| **총합** | **8-15분** |

---

## 📊 디스크 용량 확인

설치 전 필요 디스크 용량 확인:

```bash
# 현재 디스크 용량 확인
df -h /

# 필요 용량:
# - PyTorch: ~2.5GB
# - torchaudio: ~500MB
# - 기타 wheels: ~300MB
# 최소: 4GB 권장
```

---

## 🆘 문제 해결

### 문제 1: "No module named torch" 에러

**원인:** 가상환경이 활성화되지 않음

**해결:**
```bash
source venv/bin/activate
python3 -c "import torch"  # 다시 확인
```

---

### 문제 2: "CUDA not available" 경고

**원인:** NVIDIA 드라이버 또는 CUDA 불일치

**확인:**
```bash
nvidia-smi
python3 -c "import torch; print(torch.version.cuda)"
```

**해결:** CPU 모드로도 작동하므로 무시하고 진행 가능

---

### 문제 3: "Connection timeout" (다운로드 실패)

**원인:** 네트워크 불안정

**해결:**
```bash
# 재시도 (pip는 자동으로 3회 재시도)
pip install torch torchaudio torchvision --retries 5

# 또는 다른 인덱스 사용
pip install torch torchaudio torchvision \
    --index-url https://download.pytorch.org/whl/cu124 \
    --retries 5
```

---

### 문제 4: "Disk space" 에러

**원인:** 디스크 부족

**확인:**
```bash
df -h /
du -sh venv/
```

**해결:**
```bash
# 불필요한 파일 삭제
rm -rf ~/.cache/pip/*
# 다시 설치
pip install torch torchaudio torchvision
```

---

## ✅ 다음 단계

PyTorch 설치 후:

```bash
# 1. 자동 설정 (권장)
bash deployment_package/post_deploy_setup.sh

# 또는 수동으로:

# 2. 모델 다운로드 (약 15-30분)
python3 download_model.py

# 3. API 서버 실행
python3 api_server.py

# 4. 헬스 체크
curl http://localhost:8001/health
```

---

## 💡 팁

**1. 백그라운드에서 설치 (연결이 끊겨도 계속 실행)**
```bash
nohup bash LINUX_PYTORCH_INSTALL.sh > pytorch_install.log 2>&1 &
tail -f pytorch_install.log  # 진행 상황 확인
```

**2. 설치 로그 저장**
```bash
bash LINUX_PYTORCH_INSTALL.sh | tee pytorch_install_$(date +%Y%m%d_%H%M%S).log
```

**3. 여러 버전 테스트**
```bash
# 현재 버전 확인
pip show torch

# 다른 버전으로 재설치
pip install torch==2.0.1 --index-url https://download.pytorch.org/whl/cu124
```

---

## 📞 문제 발생 시

로그와 함께 보고해주세요:

```bash
# 1. 설치 명령 다시 실행 (로그 저장)
bash LINUX_PYTORCH_INSTALL.sh 2>&1 | tee error.log

# 2. 시스템 정보 저장
python3 -c "import torch; print(torch.__version__, torch.cuda.is_available())" > gpu_info.txt
nvidia-smi >> gpu_info.txt

# 3. 에러 파일 첨부 (error.log, gpu_info.txt)
```
