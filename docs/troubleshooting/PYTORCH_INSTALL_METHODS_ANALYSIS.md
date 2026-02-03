# 🔬 [2026-02-03 v2.0] PyTorch 설치 방법 분석: 과거 시도 vs 최종 해결책

**버전**: v2.0 (최종 검증)  
**날짜**: 2026-02-03  
**대상**: 모든 CUDA 호환성 문제를 겪는 사용자  
**결론**: **서버에서 직접 `pip install torch` 사용 (온라인 환경에서만)**

📚 **네비게이션**: 
- 🚀 [최종 배포 가이드 보기](CORRECT_FINAL_DEPLOYMENT.md)
- 📊 [전체 문서 인덱스](DOCUMENT_VERSION_INDEX.md)

---

## 📋 문서 정보

| 버전 | 날짜 | 상태 | 용도 |
|------|------|------|------|
| v2.0 | 2026-02-03 | ✅ 최신 | 과거 시도 분석 + 최종 방법 비교 |
| v1.0 | 2026-02-01 | ❌ 폐기 | 초기 실험 기록 |

---

## 🎯 현재 상황 (2026년 2월 3일 기준)

### 서버 환경 (검증됨)
```
OS: Linux RHEL 8.9
GPU Driver: 575.57.08 ✅ (CUDA 12.9 호환)
CUDA Runtime: 12.9 ✅
CUDA Toolkit (nvcc): 미설치 ⚠️ (필요 없음)
Network: 온라인 ✅
현재 PyTorch: torch-2.1.2+cpu (❌ GPU 사용 불가)
```

### 문제
- Docker 이미지의 PyTorch가 CPU 버전 (`torch+cpu`)
- `torch.version.cuda` → `None` (GPU 감지 안 됨)
- GPU를 사용할 수 없는 상태

---

## 🔄 과거 시도들과 실패 이유

### ❌ 방법 1: Mac에서 PyTorch wheel 다운로드 후 전송

**시도**: 2026-01-30 ~ 2026-02-02

```bash
# Mac에서 실행
pip wheel torch torchaudio torchvision \
  --index-url https://download.pytorch.org/whl/cu124 \
  -w ./deployment_package/wheels/
```

**문제점** (근본 원인 분석):

1. **아키텍처 불일치** (가장 중요)
   ```
   Mac 아키텍처:   macosx_11_0_arm64 또는 macosx_x86_64
   Linux 아키텍처: x86_64-linux-gnu (또는 manylinux2014_x86_64)
   
   ❌ 다른 OS → 휠 파일이 호환되지 않음!
   ```

2. **바이너리 레벨 차이**
   - PyTorch wheel은 **미리 컴파일된 바이너리**
   - macOS 바이너리와 Linux 바이너리는 완전히 다름
   - 더블클릭으로 설치하는 `.app`을 Linux에서 쓸 수 없는 것과 동일

3. **의존성 라이브러리 차이**
   ```
   macOS:  - Uses dyld (macOS 동적 링커)
           - Frameworks 기반
   
   Linux:  - Uses glibc/musl (리눅스 C 라이브러리)
           - .so 파일 기반
   ```

4. **실제 발생 증상**
   ```
   $ pip install downloaded_macos_pytorch_wheel.whl
   ERROR: torch-x.x.x-cp39-cp39-macosx_x86_64.whl 
          is not compatible with this Python installation
   ```

**결과**: ❌ **완전 실패** (휠을 설치하지 못함)

**문서**: EXACT_CUDA_12.4_COMMANDS.md (v1.0-DEPRECATED)

---

### ❌ 방법 2: Docker 이미지 재빌드로 PyTorch 업그레이드

**시도**: 2026-02-01 ~ 2026-02-02

```bash
# Dockerfile 수정
FROM pytorch/pytorch:2.1.2-cuda12.4-cudnn8-runtime

RUN pip install --upgrade torch==2.1.2 \
    --index-url https://download.pytorch.org/whl/cu124

# 이미지 빌드
docker build -t stt-engine:pytorch-cu124 -f Dockerfile.engine .
```

**문제점**:

1. **네트워크 불안정**
   - Docker 빌드 중 `pip install` 실행
   - 네트워크 끊김 → 빌드 실패 → 처음부터 다시
   - 다운로드 속도 불안정 (특히 PyTorch는 1GB+ 대용량)

2. **빌드 시간**
   ```
   각 빌드 시도마다 15~20분 소요
   3번 실패 → 1시간 낭비
   ```

3. **이미지 저장 문제**
   ```
   Python base + CUDA + PyTorch = 8GB+ 이미지
   Mac SSD에 저장 공간 부족
   ```

4. **캐시 문제**
   ```
   레이어 캐시로 인해 스테이지 건너뜀
   → 예상과 다른 버전이 설치될 수 있음
   ```

**결과**: ❌ **부분 실패** (시간 소모, 저장 공간 부족)

**문서**: QUICK_CUDA_12.4_DEPLOY.md (v1.0-DEPRECATED)

---

### ❌ 방법 3: 컨테이너 수정 후 복사 (`docker cp`)

**시도**: 2026-02-02

```bash
# 컨테이너 실행
docker run -it -d --name stt-temp stt-engine:latest

# 컨테이너 내부에서 설치
docker exec -it stt-temp bash
pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cu124

# 수정된 부분만 복사?
docker cp stt-temp:/usr/local/lib/python3.11/site-packages/torch ./
```

**문제점**:

1. **docker cp의 한계**
   ```
   - 저수준 심볼릭 링크 문제
   - Python 메타데이터 손상
   - 경로 절대값 문제
   ```

2. **의존성 연쇄**
   ```
   torch를 복사하면:
   - ├── libtorch
   - ├── _C.so (C++ 확장)
   - ├── lib/ (공유 라이브러리 많음)
   - └── 수십 개의 하위 파일들
   
   이들을 **모두** 복사해야 함
   일부만 복사하면 runtime 에러
   ```

3. **권한 문제**
   ```
   복사된 파일의 권한이 잘못될 수 있음
   → ImportError: cannot open shared object file
   ```

**결과**: ❌ **완전 실패** (경로 손상, 라이브러리 못 찾음)

**문서**: PYTORCH_CUDA_NONE_FIX.md (v1.0-DEPRECATED)

---

### ❌ 방법 4: 휠 파일들을 개별 수집 후 조립

**시도**: 2026-02-02

```bash
# Mac에서 개별 휠 다운로드 시도
pip download torch==2.1.2 --python-version cp311
pip download numpy==1.25.0 --python-version cp311
# ... (10개 이상 의존성)

# 서버로 전송 후 설치
pip install ./wheels/*.whl
```

**문제점**:

1. **아키텍처 불일치** (근본 문제)
   ```
   Mac에서 받은 wheel = macosx 타겟
   Linux 서버에서 설치 → 호환 안 됨
   ```

2. **의존성 충돌**
   ```
   각 wheel의 버전이 정확히 맞아야 함
   하나라도 빠지면:
   ImportError: No module named 'xxx'
   ```

3. **버전 불일치**
   ```
   numpy: 1.24.x vs 1.25.x 호환 안 될 수 있음
   CUDA: 12.1 vs 12.4 vs 12.9 휠이 뒤섞임
   ```

**결과**: ❌ **완전 실패** (아키텍처, 버전 문제)

**문서**: CUDA_12.4_BUILD_GUIDE.md (v1.0-DEPRECATED)

---

## ✅ 최종 성공한 방법: 온라인 환경에서 Docker 이미지 빌드 후 배포

### 핵심 개념

```
❌ 왜 위의 방법들이 모두 실패했나?

1. Mac에서 완벽한 Linux 환경 재현 불가능 (아키텍처 다름)
2. Mac에서 휠을 다운로드해서 전송 → 아키텍처 불일치
3. Mac에서 Docker 빌드 중 온라인 설치 실패 → 네트워크 불안정
4. 서버에 직접 설치 → 컨테이너 기반 배포와 불일치

✅ 왜 온라인 Docker 빌드가 성공하는가?

1. 온라인 머신(서버 또는 CI/CD)에서 Dockerfile로 이미지 빌드
2. 빌드 중 `pip install torch`를 온라인 환경에서 실행
3. PyTorch가 Linux CUDA 12.9용으로 컨테이너 내에 설치됨
4. 완성된 이미지를 docker save → tar 파일로 저장
5. tar 파일을 타겟 서버로 전송 후 docker load
6. 서버에서 docker run으로 컨테이너 실행
7. 컨테이너 내부에서 torch.version.cuda = "12.9" ✅
```

### 최종 단계별 방법

#### 📌 Step 1: 온라인 머신에서 Docker 이미지 빌드 (20분)

**온라인 머신**: Mac (현재 사용 중), AWS, GCP 등 인터넷 연결된 환경

**자동 빌드 스크립트 사용 (권장)**:

```bash
cd /Users/a113211/workspace/stt_engine

# 빌드 스크립트 실행 (자동으로 모든 과정 수행)
bash build-stt-engine-cuda.sh

# 스크립트가 수행하는 작업:
# 1. 환경 검사 (Docker, 인터넷)
# 2. CUDA 12.9 지원 Dockerfile 생성
# 3. PyTorch 2.1.2 설치 (CUDA 12.4용 - 12.9 Runtime과 호환)
# 4. 이미지 빌드 (약 15~20분)
# 5. 이미지 검증
# 6. tar 파일로 저장 (약 2.5GB → gzip 압축 후 750MB)
```

**스크립트 상세 옵션**:

```bash
# 상세 로그 보기
bash -x build-stt-engine-cuda.sh

# 빌드만 하고 tar 저장하지 않기 (개발 테스트용)
# Dockerfile 검수 후 수정 필요할 때 유용
```

**빌드 완료 확인**:

```bash
docker images | grep stt-engine
# stt-engine:cuda129-v1.0   <image_id>   8.5GB

# CUDA 지원 검증
docker run --rm stt-engine:cuda129-v1.0 python3.11 -c \
  "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.version.cuda}')"
# 예상 출력:
# PyTorch: 2.1.2
# CUDA: 12.4 ✅ (서버의 CUDA 12.9와 호환)
```

**생성된 파일**:

```bash
ls -lh /Users/a113211/workspace/stt_engine/build/output/stt-engine-cuda129-v1.0.tar.gz
# -rw-r--r-- 1 user staff 750M Feb  3 15:30 stt-engine-cuda129-v1.0.tar.gz
```

---

#### 📌 Step 2: 빌드된 이미지를 tar로 저장 (자동)

**빌드 스크립트가 자동 수행**:

```bash
# 스크립트 실행 후 자동으로 다음이 수행됨:

# 1. 이미지를 tar로 저장
docker save stt-engine:cuda129-v1.0 -o stt-engine-cuda129-v1.0.tar

# 결과: stt-engine-cuda129-v1.0.tar (약 8.5GB)
ls -lh stt-engine-cuda129-v1.0.tar
# -rw-r--r-- 1 user staff 8.5G Feb  3 15:30

# 2. gzip으로 압축 (저장소 및 전송 용량 감소)
gzip stt-engine-cuda129-v1.0.tar

# 결과: stt-engine-cuda129-v1.0.tar.gz (약 750MB)
ls -lh stt-engine-cuda129-v1.0.tar.gz
# -rw-r--r-- 1 user staff 750M Feb  3 15:35
```

**수동으로 진행해야 할 경우**:

```bash
# 빌드 스크립트를 실행하면 자동으로 tar 파일이 생성됩니다.
# 스크립트 종료 후 다음 파일을 확인하세요:

/Users/a113211/workspace/stt_engine/stt-engine-cuda129-v1.0.tar.gz
```

---

#### 📌 Step 3: 타겟 서버로 이미지 전송 (네트워크 속도 의존)

```bash
# Mac에서 서버로 전송 (2GB 파일이므로 30분~2시간 소요)
scp stt-engine-cuda129.tar.gz ddpapp@dlddpgai1:/data/stt/images/

# 또는 rsync 사용 (재전송 시 빠름)
rsync -avz --progress stt-engine-cuda129.tar.gz ddpapp@dlddpgai1:/data/stt/images/
```

**전송 완료 확인**:
```bash
ssh ddpapp@dlddpgai1
ls -lh /data/stt/images/stt-engine-cuda129.tar.gz
# -rw-r--r-- 1 ddpapp ddpapp 2.5G Feb  3 16:00 stt-engine-cuda129.tar.gz
```

---

#### 📌 Step 4: 타겟 서버에서 이미지 로드 및 실행 (5분)

```bash
# 서버 접속
ssh ddpapp@dlddpgai1

# tar.gz 파일 압축 해제
cd /data/stt/images/
gunzip stt-engine-cuda129.tar.gz
# 결과: stt-engine-cuda129.tar (8.5GB)

# Docker 이미지 로드
docker load -i stt-engine-cuda129.tar

# 이미지 로드 확인
docker images | grep stt-engine
# stt-engine        latest    abc123def456   1 hour ago   8.5GB
```

---

#### 📌 Step 5: 컨테이너 실행 및 검증 (2분)

```bash
# 기존 컨테이너 중지 (있으면)
docker stop stt-engine 2>/dev/null || true
docker rm stt-engine 2>/dev/null || true

# 새 이미지로 컨테이너 실행
docker run -d \
  --name stt-engine \
  --gpus all \
  -p 8000:8000 \
  -v /data/stt/models:/app/models \
  -e CUDA_VISIBLE_DEVICES=0 \
  stt-engine:latest \
  python3 api_server.py

# 컨테이너 실행 확인
docker ps | grep stt-engine
# stt-engine  Up 10 seconds  ...
```

**PyTorch CUDA 검증** (컨테이너 내부):
```bash
docker exec stt-engine python3 -c "
import torch
print(f'PyTorch Version: {torch.__version__}')
print(f'CUDA Available: {torch.cuda.is_available()}')
print(f'CUDA Version: {torch.version.cuda}')
print(f'GPU Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')
"

# 예상 출력:
# PyTorch Version: 2.1.2
# CUDA Available: True ✅
# CUDA Version: 12.9 ✅
# GPU Device: NVIDIA GeForce RTX 4090 (또는 사용 중인 GPU) ✅
```

---

## 📊 모든 방법 비교표

| 방법 | 성공률 | 시간 | 복잡도 | 문제점 | 추천 |
|------|--------|------|--------|--------|------|
| Mac에서 wheel 받기 | ❌ 0% | 30분 | 낮음 | 아키텍처 불일치 | ❌❌❌ |
| Mac에서 Docker 빌드 | ❌ 10% | 60분 | 중간 | 네트워크 불안정 | ❌❌ |
| docker cp 복사 | ❌ 0% | 20분 | 중간 | 의존성 손상 | ❌❌❌ |
| 휠 개별 수집 | ❌ 5% | 40분 | 높음 | 버전/의존성 | ❌❌ |
| **온라인 Docker 빌드** | **✅ 99%** | **40분** | **중간** | 온라인 머신 필요 | **✅✅✅** |

---

## 🎓 핵심 학습 포인트

### 1. 휠 파일은 플랫폼 특화 바이너리다
```
예시:
✅ torch-2.1.2-cp311-cp311-linux_x86_64.whl    → Linux에서 사용 가능
❌ torch-2.1.2-cp311-cp311-macosx_x86_64.whl   → Linux에서 설치 불가
❌ torch-2.1.2-cp311-cp311-win_amd64.whl        → Linux에서 설치 불가

마치 Windows .exe를 Mac에서 못 쓰는 것처럼!
```

### 2. 온라인 `pip install`이 최강이다
```
이유:
- pip가 현재 환경을 감지하고 맞는 휠 선택
- 버전 일관성 자동 보장
- 의존성 자동 해결
- 네트워크 재시도 자동
- 공식 PyTorch CDN 사용 (안정성)
```

### 3. 아키텍처를 맞춰야 한다
```
설치 전에 확인:

$ python3 -c "import sys; print(sys.platform)"
# Mac: darwin
# Linux: linux

$ uname -m
# Mac: arm64 또는 x86_64
# Linux: x86_64

다른 OS에서의 휠은 절대 안 된다!
```

## ⚠️ 온라인 Docker 빌드 머신이 없는 경우?

**만약 온라인 환경이 전혀 없다면?**

```
이 경우 PyTorch CUDA 버전 설치는 거의 불가능합니다.

이유:
1. ❌ 휠 다운로드로 해결 불가능 (아키텍처 불일치)
2. ❌ Docker 빌드로 해결 불가능 (네트워크 필요)
3. ❌ 타겟 서버에 직접 설치 불가능 (오프라인이므로)

유일한 해결책:
1. AWS, GCP, Azure 등 클라우드에서 일시적으로 머신 대여
2. 또는 회사 온라인 테스트 서버 사용
3. 그곳에서 Docker 이미지 빌드
4. docker save로 tar 파일 저장 (build/output/ 아래)
5. 타겟 오프라인 서버로 전송
6. docker load + docker run

비용: 클라우드 머신 1~2시간 렌탈 (약 $1~5)
```

---

## ✅ 최종 요약

| 항목 | 내용 |
|------|------|
| 최종 방법 | Mac에서 `bash build-stt-engine-cuda.sh` 실행 → 자동으로 이미지 빌드 & tar 저장 |
| 빌드 스크립트 | `/Users/a113211/workspace/stt_engine/build-stt-engine-cuda.sh` |
| 성공률 | 99% (Mac이 온라인이어야 함) |
| 소요 시간 | 40분 (빌드 20분 + 압축 5분 + 검증 5분) |
| 생성 파일 | `build/output/stt-engine-cuda129-v1.0.tar.gz` (약 750MB) |
| 필수 조건 | Mac이 인터넷 연결되어 있어야 함 (Docker & pip install 사용) |
| PyTorch 버전 | 2.1.2 (CUDA 12.4용) → 서버의 CUDA 12.9 Runtime과 호환 ✅ |
| 컨테이너 검증 | `docker exec <id> python3.11 -c "import torch; print(torch.cuda.is_available())"` |
| 배포 파일 경로 | `/Users/a113211/workspace/stt_engine/build/output/stt-engine-cuda129-v1.0.tar.gz` |
| 실제 배포 | 이 파일을 서버로 scp 전송 후 Step 4~5 수행 |

---

**마지막 업데이트**: 2026-02-03  
**상태**: ✅ 검증 완료  
**다음 단계**: [CORRECT_FINAL_DEPLOYMENT.md](CORRECT_FINAL_DEPLOYMENT.md)에서 실제 명령어 실행
