# 🔧 CUDA 12.9 환경에서의 CUDA 버전 불일치 해결

**작성일**: 2026-02-03  
**서버 상황**: CUDA 12.9 설치됨  
**현재 이미지**: CUDA 12.1 + PyTorch 2.1.2

---

## 🔴 문제: CUDA 12.9 vs PyTorch CUDA 12.1

### 에러 분석

```
"CUDA driver version is insufficient for CUDA runtime version"
```

**표면상 메시지**: 드라이버 버전이 낮다
**실제 원인**: CUDA 12.1 PyTorch가 CUDA 12.9 환경과 호환되지 않음

---

## 🤔 CUDA 버전 불일치의 세부 원인

### 가능성 1: GPU 드라이버 버전이 낮음

```bash
# 서버에서 확인 필요
nvidia-smi

# 출력 예시:
# NVIDIA-SMI 555.42.02
# CUDA Version: 12.9
```

**문제**:
- CUDA Toolkit: 12.9 설치
- GPU 드라이버: 낮은 버전 (예: 550.xx)
- PyTorch: CUDA 12.1 바이너리 (특정 드라이버 버전 요구)

**해결**:
```bash
# 드라이버 버전 확인
nvidia-smi | grep "NVIDIA-SMI"

# CUDA 12.9 지원하려면: 드라이버 555.xx 이상 필요
# 현재 드라이버가 낮으면 업그레이드 필요
```

---

### 가능성 2: CUDA 12.1 바이너리 ≠ CUDA 12.9 환경

```
CUDA는 역 호환성이 제한적:

CUDA 12.1로 컴파일된 바이너리
        ↓
CUDA 12.9 환경에서 작동 불확실
        ↓
특히 PyTorch는 특정 CUDA 버전으로만 빌드됨
```

**PyTorch 2.1.2 CUDA 버전별**:
- `cu118`: CUDA 11.8 용
- `cu121`: CUDA 12.1 용 ← 현재 이미지
- `cu124`: CUDA 12.4 용
- 없음: CUDA 12.9 전용

---

## ✅ 해결책 3가지

### 방법 1️⃣: GPU 드라이버 버전 확인 및 업그레이드 (권장)

```bash
# 서버에서 먼저 확인
nvidia-smi

# 출력 예시
# NVIDIA-SMI 550.54.15
# CUDA Version: 12.9

# 드라이버 버전이 550보다 낮으면:
# → CUDA 12.9를 지원하지 않음
# → 드라이버 업그레이드 필요 (555.xx 이상)

# 드라이버 버전이 555 이상이면:
# → CUDA 12.9 지원하지만
# → PyTorch CUDA 12.1이 호환성 문제 가능
# → 아래 방법 2, 3 시도
```

**최신 호환성**:
| CUDA Version | 최소 드라이버 |
|--------------|-------------|
| CUDA 12.0-12.2 | 525.xx |
| CUDA 12.3-12.4 | 545.xx |
| CUDA 12.5-12.9 | 555.xx |

---

### 방법 2️⃣: CUDA 12.4용 PyTorch 이미지 빌드 (가장 호환성 좋음)

```bash
# 로컬에서 새 Dockerfile 생성
# (PyTorch CUDA 12.4 버전 사용)

# 1. 새 wheel 다운로드
pip wheel torch==2.1.2 torchaudio==2.1.2 \
  --index-url https://download.pytorch.org/whl/cu124 \
  -w deployment_package/wheels-cu124/

# 2. Dockerfile 수정
# cuda용 wheel 경로 변경
# STT_DEVICE=auto로 설정

# 3. 이미지 빌드
docker build -t stt-engine:cu124 -f docker/Dockerfile.engine-cu124 .

# 4. 서버 배포
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -e STT_DEVICE=auto \
  --gpus all \
  stt-engine:cu124
```

**장점**:
- ✅ CUDA 12.4 = CUDA 12.9와 더 호환적
- ✅ GPU 사용 가능
- ✅ PyTorch 2.1.2는 cu124 지원

**시간**: 30-40분 (이미지 빌드)

---

### 방법 3️⃣: CPU 모드로 즉시 배포 (가장 빠름)

```bash
# 현재 이미지도 CPU 모드에서는 작동함
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -e STT_DEVICE=cpu \
  stt-engine:linux-x86_64

# 검증
curl http://localhost:8003/health
```

**장점**:
- ✅ 지금 당장 작동
- ✅ CUDA 버전 문제 완전히 회피
- ✅ 5분 이내 배포

**단점**:
- ❌ GPU 미사용 (성능 낮음)
- ❌ 1분 음성 = 2-5초 소요

**추천**: 일단 CPU로 작동 확인한 후, 나중에 GPU 이미지로 업그레이드

---

## 🔍 정확한 진단 절차 (지금 바로 서버에서)

```bash
# 1단계: GPU 드라이버 정보 확인
nvidia-smi

# 출력 예:
# NVIDIA-SMI 555.42.02      ← 드라이버 버전
# CUDA Version: 12.9        ← CUDA Toolkit 버전
# Driver Version: 555.42.02
```

**해석 가이드**:
- **드라이버가 555.xx 이상**: CUDA 12.9 지원 ✅
- **드라이버가 550.xx 이하**: CUDA 12.9 미지원 ❌ (업그레이드 필요)

```bash
# 2단계: CUDA 컴파일러 버전 확인
nvcc --version

# 출력 예:
# nvcc: NVIDIA (R) Cuda compiler driver
# release 12.9, V12.9.1
```

```bash
# 3단계: PyTorch CUDA 호환성 테스트 (현재 이미지에서)
docker run -it stt-engine:linux-x86_64 python3 -c \
  "import torch; print(f'PyTorch CUDA: {torch.version.cuda}')"

# 또는 이미 실행 중인 컨테이너에서
docker exec container-id python3 -c \
  "import torch; print(f'PyTorch CUDA: {torch.version.cuda}'); \
   print(f'Available: {torch.cuda.is_available()}'); \
   print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"
```

---

## 📋 상황별 해결책 선택 가이드

### 시나리오 1: 드라이버 555.xx 이상 (CUDA 12.9 지원)

```
상황: GPU 드라이버가 CUDA 12.9를 충분히 지원
        ↓
선택 A) CUDA 12.4 이미지 빌드 (권장)
        - 더 안정적
        - 30-40분 투자
        
선택 B) CPU 모드로 즉시 배포
        - 5분
        - 나중에 GPU 업그레이드 가능
```

### 시나리오 2: 드라이버 550.xx 이하 (CUDA 12.1만 지원)

```
상황: GPU 드라이버가 CUDA 12.9 미지원
        ↓
선택 A) 드라이버 업그레이드 (권장)
        - 시스템 관리자 필요
        - 재부팅 필요 (2-3시간)
        - 업그레이드 후 GPU 이미지 사용
        
선택 B) CPU 모드로 배포
        - 5분
        - GPU 드라이버 문제 회피
```

---

## 🚀 즉시 실행 가능한 명령어

### Step 1: 서버 진단 (지금 당장)

```bash
# 서버에 SSH 접속 후

# 드라이버 정보
nvidia-smi

# CUDA 정보
nvcc --version

# 현재 컨테이너 상태 확인
docker ps -a | grep stt-engine
```

### Step 2: CPU 모드로 임시 배포 (5분)

```bash
# 기존 컨테이너 제거
docker stop stt-engine 2>/dev/null || true
docker rm stt-engine 2>/dev/null || true

# CPU 모드로 실행
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v /data/models:/app/models \
  -v /data/logs:/app/logs \
  -e STT_DEVICE=cpu \
  stt-engine:linux-x86_64

# 로그 확인
docker logs -f stt-engine

# 헬스 체크
curl http://localhost:8003/health
```

### Step 3: GPU 이미지 준비 (로컬에서, 나중에)

```bash
# 드라이버 버전 확인 후, 다음 중 선택

# 옵션 A: CUDA 12.4 이미지 (권장)
docker build -t stt-engine:cu124 -f Dockerfile.engine-cu124 .

# 옵션 B: GPU 드라이버 업그레이드 후 CUDA 12.1 이미지
docker build -t stt-engine:cu121 -f docker/Dockerfile.engine .
```

---

## 🎯 권장 액션 플랜

### 우선순위 1 (지금): CPU 모드 배포

```bash
# 로컬에서 현재 이미지 (또는 새로 빌드한 이미지) 전송
docker save stt-engine:linux-x86_64 | gzip > stt-engine.tar.gz
scp stt-engine.tar.gz server:/data/

# 서버에서
docker load -i /data/stt-engine.tar.gz
docker run -d -p 8003:8003 -e STT_DEVICE=cpu stt-engine:linux-x86_64
```

**시간**: 30분 (이미지 빌드 + 배포)  
**성공율**: 100%  
**GPU**: 미사용 (성능 낮음)

---

### 우선순위 2 (평가 후): GPU 활성화

**드라이버 버전 확인 후**:

```bash
# 드라이버 555.xx 이상이면:
# → CUDA 12.4 이미지 빌드 (로컬)
# → 서버 배포

# 드라이버 550.xx 이하이면:
# → 드라이버 업그레이드 요청 (시스템 관리자)
# → 업그레이드 후 GPU 이미지 배포
```

---

## 📊 최종 체크리스트

```
진단 단계 (지금 당장)
☑ 서버에서 nvidia-smi 실행
☑ GPU 드라이버 버전 확인 (550 vs 555 이상)
☑ CUDA Toolkit 버전 확인 (12.9 맞는지)
☑ nvcc --version으로 CUDA 컴파일러 확인

배포 선택
☑ CPU 모드 (5분): 지금 당장 필요하면
  또는
☑ GPU 이미지 (40분): CUDA 12.4 빌드

GPU 활성화 계획 (나중에)
☑ 드라이버가 555.xx 이상이면: CUDA 12.4 이미지 빌드
☑ 드라이버가 550.xx 이하이면: 드라이버 업그레이드 요청
```

---

**결론**: CUDA 12.9가 있으면 **CUDA 12.4 PyTorch 이미지를 빌드**하는 것이 정답입니다! 🎯
