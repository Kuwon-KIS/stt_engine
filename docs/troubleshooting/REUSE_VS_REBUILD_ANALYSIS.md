# 🔍 기존 이미지 재활용 vs 새 빌드 - 상세 분석

**작성일**: 2026-02-03  
**목적**: 기존 이미지 재활용 가능성 철저히 검토

---

## 1️⃣ Exited 상태에서 docker cp 가능한가?

### 짧은 답: **YES, 가능합니다!** ✅

```bash
# Exited 상태의 컨테이너도 docker cp 가능
docker cp /local/file.py container-name:/app/file.py

# 확인: 컨테이너가 Exited 상태여도 작동
$ docker ps -a | grep stt-engine
container-id ... stt-engine ... Exited (1)  # ← 이 상태에서도 가능
$ docker cp api_server.py container-id:/app/
# 성공 ✅
```

**핵심**: 
- Docker 컨테이너 파일시스템은 Exited 상태에서도 유지됨
- docker exec (명령 실행)은 불가능하지만
- docker cp (파일 복사)는 가능함

---

## 2️⃣ 기존 이미지를 docker cp로 재활용하는 전략

### 문제점 분석

**기존 이미지에 없는 것들**:
1. ❌ python-multipart wheel (라이브러리)
2. ❌ os import (코드)
3. ❌ STT_DEVICE 환경변수 (설정)

### 전략: **부분 해결만 가능**

```
Step 1: docker cp로 api_server.py 복사
Step 2: Exited 상태에서 컨테이너 재시작 시도
Step 3: 에러 발생
  └─> api_server.py는 로드되지만
  └─> fastapi import 시 python-multipart 필요로 함
  └─> 여전히 실패 ❌
```

---

## 3️⃣ 왜 docker cp만으로는 안 되는가?

### 문제 구조도

```
기존 이미지 (python-multipart 없음)
        ↓
docker run → 컨테이너 시작
        ↓
api_server.py 실행 시도
        ↓
import fastapi  ← 성공
        ↓
from fastapi import File, UploadFile  ← 실패!
        │
        └─→ RuntimeError: "Form data requires python-multipart"
            (내부적으로 fastapi가 python-multipart 필요로 함)
        ↓
컨테이너 Exited (1) ← 여기서 멈춤
```

### docker cp로 api_server.py를 복사해도

```bash
$ docker cp api_server.py container-id:/app/

# 하지만 컨테이너 재시작 시도하면
$ docker start container-id

# 로그 보기
$ docker logs container-id

# 여전히 같은 에러!
# RuntimeError: "Form data requires python-multipart"
```

**이유**: 
- api_server.py 내용이 아니라
- FastAPI 라이브러리 자체가 python-multipart 필요로 함
- 코드만 바꿔서는 해결 불가능

---

## 4️⃣ 그럼 python-multipart를 docker cp로 설치 가능한가?

### 이론상 가능하지만, 실제로는...

```bash
# 1. python-multipart wheel 파일을 서버로 전송
scp python_multipart-0.0.22-py3-none-any.whl server:/data/

# 2. Exited 상태의 컨테이너에 복사
docker cp /data/python_multipart-0.0.22-py3-none-any.whl \
  container-id:/tmp/

# 3. pip install 하려면?
docker exec container-id pip install /tmp/python_multipart-0.0.22-py3-none-any.whl
# ❌ 실패! (Exited 상태에서 docker exec 불가능)

# 4. 컨테이너 시작 후에 하려면?
docker start container-id
# ❌ 실패! (python-multipart 없어서 시작 실패)
```

### 결론: **순환 논리 (Catch-22)**

```
python-multipart 설치 필요 → python-multipart 없어서 시작 실패
                      ↓
                컨테이너 Exited
                      ↓
           docker exec 불가능
                      ↓
          pip install 할 수 없음
```

---

## 5️⃣ GPU 강제 사용은 가능한가?

### 현재 상황

```bash
# 서버에서 본 CUDA 에러
"CUDA driver version is insufficient for CUDA runtime version"

# 이미지: CUDA 12.1 PyTorch 2.1.2
# 서버: CUDA 드라이버 버전 낮음
```

### GPU 강제 사용 방법들

#### 옵션 1: 기존 방식 (device="cuda")
```python
device="cuda"  # ← 강제
```
**결과**: ❌ 같은 CUDA 버전 에러 발생
- 해결 안 됨

#### 옵션 2: CUDA 버전 맞추기
```
현재: CUDA 12.1 (너무 높음)
        ↓
낮은 버전 사용: CUDA 11.8 또는 CPU 전용 PyTorch
        ↓
새 이미지 빌드 필요 (PyTorch 버전 바꿈)
```
**결과**: ⏳ 가능하지만 새 이미지 필요

#### 옵션 3: GPU 드라이버 업그레이드
```
서버 시스템 레벨 작업
        ↓
nvidia-driver 설치/업그레이드
        ↓
CUDA 12.1과 호환되는 버전
        ↓
기존 이미지 사용 가능
```
**결과**: ✅ 가능하지만 시스템 관리자 권한 필요

---

## 📊 선택지별 비용/효과 분석

| 방식 | 시간 | 복잡도 | 성공율 | 비고 |
|------|------|--------|--------|------|
| **docker cp만 사용** | 5분 | 낮음 | ❌ 10% | python-multipart 없어서 실패 |
| **whl 반입 + docker cp** | 15분 | 중간 | ❌ 20% | 순환 논리로 설치 불가 |
| **새 이미지 빌드 (CPU)** | 30-40분 | 중간 | ✅ 95% | 안정적, 모든 문제 해결 |
| **GPU 드라이버 업그레이드** | 2-3시간 | 높음 | ✅ 90% | 시스템 관리자 작업 필요 |
| **CUDA 11.8 이미지 빌드** | 30-40분 | 중간 | ✅ 85% | 추가 테스트 필요 |

---

## 🎯 현실적 해결책

### Case 1: 가장 빠른 방법 (지금 당장 작동 필요)

**→ 새 CPU 이미지 빌드 (30-40분)**

```bash
# 로컬에서
docker build -t stt-engine:linux-x86_64 -f docker/Dockerfile.engine .
docker save stt-engine:linux-x86_64 | gzip > stt-engine-linux-x86_64.tar.gz

# 서버에서
docker load -i stt-engine-linux-x86_64.tar.gz
docker run -d -p 8003:8003 -e STT_DEVICE=cpu stt-engine:linux-x86_64
```

**장점**:
- ✅ 모든 문제 한 번에 해결
- ✅ 가장 안정적
- ✅ 테스트 가능

**단점**:
- ⏳ 빌드 시간 필요

---

### Case 2: GPU가 필수인 경우

#### 옵션 A: GPU 드라이버 업그레이드 (권장)

```bash
# 서버 시스템 관리자에게 요청
# nvidia-driver 업그레이드 후

# 기존 이미지 사용 가능 (device="cuda")
# 또는 새 이미지로 device=auto 설정
```

**필요한 것**:
1. 서버 관리자 권한 (드라이버 설치)
2. 서버 재부팅 가능성

#### 옵션 B: CUDA 11.8 전용 이미지 빌드

```bash
# 로컬에서 새 Dockerfile 생성
# PyTorch CUDA 11.8 버전으로 변경
# → 더 낮은 GPU 드라이버와 호환

docker build -t stt-engine:cuda-11.8 -f Dockerfile.engine-cu118 .
```

**필요한 것**:
1. 새 Dockerfile 작성
2. PyTorch CUDA 11.8 wheel 다운로드
3. wheels 재구성

---

## 🚨 기존 이미지 재활용 불가능한 이유 (최종 정리)

### 문제 1: python-multipart 라이브러리 (코드 해결 불가)

```
라이브러리 = Python 패키지 = 이미지에 포함되어야 함
코드 수정 ≠ 라이브러리 설치

api_server.py 아무리 고쳐도
이미지에 python-multipart 없으면 import 실패
```

### 문제 2: Exited 상태에서 pip install 불가능 (순환 논리)

```
pip install 하려면 → 컨테이너 실행 필요
컨테이너 실행하려면 → python-multipart 필요 (import time)
                     ↑
                 순환!
```

### 문제 3: CUDA 버전 불일치 (코드로 해결 불가)

```
device="cuda" 강제 사용하면
→ 같은 CUDA 버전 에러 반복

이미지의 CUDA 버전과 서버의 GPU 드라이버 버전 차이
→ 이미지 다시 빌드하거나 드라이버 업그레이드 필요
```

---

## ✅ 최종 권장사항

### 지금 상황에서 가장 실용적인 선택

**→ 새 CPU 이미지 빌드 (30-40분 투자)**

이유:
1. ✅ 가장 확실한 해결책
2. ✅ 모든 문제 한 번에 해결
3. ✅ 추후 GPU 사용 가능하게 설정
4. ✅ 테스트 가능한 환경

```bash
# Step 1: 로컬 빌드 (30분)
docker build -t stt-engine:linux-x86_64 -f docker/Dockerfile.engine .

# Step 2: 이미지 저장 (5분)
docker save stt-engine:linux-x86_64 | gzip > stt-engine.tar.gz

# Step 3: 서버 배포 (5분)
scp stt-engine.tar.gz server:/data/
ssh server "docker load -i /data/stt-engine.tar.gz && \
  docker run -d -p 8003:8003 -e STT_DEVICE=cpu stt-engine:linux-x86_64"
```

**총 소요 시간**: ~40분  
**성공율**: 95%+  
**추후 GPU 사용 시**: `docker run -e STT_DEVICE=cuda` 명령어 한 줄로 변경 가능

---

## 📝 만약 기존 이미지를 꼭 써야 한다면?

### 유일한 방법: 이미지 내부에서 wheel 설치

```bash
# 이미지 자체에서 wheel을 직접 설치
# (오프라인 모드는 불가능)

# 1. 컨테이너 실행 (Start failed일 수 있음)
docker run -it stt-engine:linux-x86_64 /bin/bash

# 2. pip install (네트워크 있을 경우)
pip install python-multipart

# 3. 새 이미지로 커밋
docker commit container-id stt-engine:patched

# 4. 저장
docker save stt-engine:patched | gzip > stt-engine-patched.tar.gz
```

**문제점**:
- ❌ Exited 상태에서 docker run 불가능
- ❌ /bin/bash로 시작되지 않음 (API 서버 시작 설정)
- ❌ 네트워크 필요 (오프라인 배포 원칙 위배)

---

**결론**: 🟢 새 이미지 빌드가 가장 현실적입니다 ✅
