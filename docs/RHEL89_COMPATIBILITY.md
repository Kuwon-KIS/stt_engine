# RHEL 8.9 환경 호환성 확인 가이드

## 🔍 RHEL 8.9 서버에서 수집해야 할 정보

### 1. 기본 OS 정보
```bash
# OS 버전 확인
cat /etc/os-release
uname -a

# 예상 출력:
# NAME="Red Hat Enterprise Linux"
# VERSION="8.9"
```

### 2. glibc (C 라이브러리) 버전
```bash
# RHEL 8.9의 glibc 버전 확인 (중요!)
ldd --version
# 또는
rpm -qa | grep glibc

# 예상: glibc 2.28 이상 (RHEL 8.9 기본값)
```

### 3. OpenSSL 버전
```bash
openssl version
# 예상: OpenSSL 1.1.1 (RHEL 8.9)
```

### 4. libstdc++ 버전
```bash
strings /usr/lib64/libstdc++.so.6 | grep GLIBCXX | tail -1
# 예상: GLIBCXX_3.4.26 이상
```

### 5. NVIDIA 관련 정보
```bash
# CUDA Runtime 버전
nvcc --version
# 또는
nvidia-smi

# CUDA Toolkit 위치
which nvcc
ls -l /usr/local/cuda/

# cuDNN 확인
ldconfig -p | grep cudnn
```

### 6. 설치된 패키지
```bash
# 중요 패키지 확인
rpm -qa | grep -E "python|libsndfile|ffmpeg|openssl|gcc"

# Python 버전
python3 --version
python3.11 --version (있으면)

# 필수 라이브러리
ldconfig -p | grep -E "libsndfile|libffi|libssl"
```

### 7. 커널 버전
```bash
uname -r
# 예상: 4.18.x (RHEL 8.9 kernel)
```

---

## 📋 수집한 정보 저장 위치

이 정보들을 다음 파일에 저장하면 좋습니다:

```bash
# 서버에서:
bash /path/to/collect_rhel_info.sh > /tmp/rhel89_info.txt 2>&1

# Mac으로 다운로드:
scp user@server:/tmp/rhel89_info.txt ~/Downloads/
```

---

## 🎯 빌드 최적화 방법

수집한 정보를 바탕으로:

### 옵션 1: Ubuntu 기반 EC2 + RHEL 호환 설정
- EC2: Ubuntu 22.04 LTS (일반적)
- Base Image: python:3.11-slim (Debian 기반)
- ⚠️ 문제: glibc 버전 불일치 가능

### 옵션 2: RHEL 기반 EC2
- EC2: RHEL 8.9 AMI (정확한 호환성)
- Base Image: ubi8/python-311 (Red Hat Universal Base Image)
- ✅ 장점: 완벽한 호환성

### 옵션 3: 운영 서버에서 직접 빌드 (권장)
- 가장 정확한 호환성
- 네트워크 비용 절감
- ❌ 다운타임 필요

---

## 💡 권장사항

1. **glibc 버전이 중요합니다**
   - EC2 Ubuntu: glibc 2.35+
   - RHEL 8.9: glibc 2.28
   - → 호환성 문제 가능성

2. **최상의 방법**:
   ```bash
   # RHEL 8.9 서버에서 직접 빌드
   docker build ... (RHEL 8.9에서)
   ```

3. **EC2 사용 시**:
   ```bash
   # RHEL 8.9 AMI를 EC2에서 사용
   # Base Image: ubi8/python-311:latest
   ```

---

## 📝 정보 수집 스크립트

아래 명령어를 RHEL 8.9 서버에서 실행해주세요:

```bash
#!/bin/bash

echo "=== RHEL 8.9 환경 정보 수집 ==="
echo ""

echo "1. OS 정보:"
cat /etc/os-release

echo ""
echo "2. glibc 버전:"
ldd --version | head -1

echo ""
echo "3. OpenSSL:"
openssl version

echo ""
echo "4. CUDA/NVIDIA:"
nvidia-smi 2>/dev/null || echo "NVIDIA GPU 미감지"
nvcc --version 2>/dev/null || echo "CUDA Toolkit 설치 안됨"

echo ""
echo "5. Python:"
python3 --version
which python3.11

echo ""
echo "6. 필수 라이브러리:"
rpm -qa | grep -E "libsndfile|ffmpeg|openssl" || echo "패키지 미설치"

echo ""
echo "7. 커널:"
uname -r
```

---

## ✅ 현재 상황

- ✅ EC2 빌드 준비 완료 (Ubuntu 기반)
- ⚠️ RHEL 8.9 호환성 확인 필요
- 📌 다음 단계: RHEL 정보 수집 → Dockerfile 최적화
