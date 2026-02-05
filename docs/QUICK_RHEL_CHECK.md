# RHEL 8.9 환경 정보 수집 - 한 줄 명령어 모음

## 📋 필수 정보 수집 (가장 중요한 것들)

### 한 번에 모든 정보 수집
```bash
# Mac/로컬에서 실행:
ssh user@rhel_server 'bash' < /Users/a113211/workspace/stt_engine/scripts/collect_rhel_info.sh > ~/rhel89_info.txt

# 또는 RHEL 서버에서 직접 실행:
bash collect_rhel_info.sh > /tmp/rhel89_info.txt
```

---

## 🚀 빠른 확인 (필수 항목만)

```bash
# 1. OS 버전
cat /etc/os-release | grep VERSION

# 2. glibc 버전 (가장 중요!)
ldd --version | head -1

# 3. Python 3.11 설치 확인
python3.11 --version

# 4. CUDA/GPU 확인
nvidia-smi

# 5. cuDNN 확인
ldconfig -p | grep cudnn

# 6. 전체 한줄
echo "=== OS ===" && cat /etc/os-release | head -3 && echo "" && echo "=== glibc ===" && ldd --version | head -1 && echo "" && echo "=== Python3.11 ===" && python3.11 --version 2>&1 && echo "" && echo "=== GPU ===" && nvidia-smi --version 2>&1 && echo "" && echo "=== cuDNN ===" && ldconfig -p | grep cudnn || echo "No cuDNN"
```

---

## 📋 각 항목별 명령어

### A. 기본 OS 정보
```bash
# 1. OS 버전 및 릴리즈
cat /etc/os-release

# 2. 커널 버전
uname -r

# 3. 커널 상세 정보
uname -a
```

### B. glibc 버전 (매우 중요!)
```bash
# 1. glibc 버전 확인
ldd --version

# 2. 설치된 glibc 패키지
rpm -qa | grep glibc

# 3. glibc 파일 위치
ls -lah /lib64/libc.so.6
```

### C. OpenSSL 및 라이브러리
```bash
# 1. OpenSSL 버전
openssl version

# 2. libstdc++ 버전
strings /usr/lib64/libstdc++.so.6 | grep GLIBCXX | tail -5

# 3. libffi
ldconfig -p | grep libffi
```

### D. Python 버전 확인
```bash
# 1. Python 3 기본
python3 --version

# 2. Python 3.11 확인
python3.11 --version

# 3. Python 위치
which python3.11

# 4. 설치된 Python 패키지
rpm -qa | grep python
```

### E. NVIDIA/CUDA 정보
```bash
# 1. NVIDIA Driver
nvidia-smi

# 2. CUDA Toolkit 버전
nvcc --version

# 3. CUDA 설치 위치
ls -ld /usr/local/cuda*

# 4. CUDA 라이브러리
ldconfig -p | grep cuda

# 5. cuDNN 확인
ldconfig -p | grep cudnn
```

### F. 시스템 라이브러리
```bash
# 1. libsndfile
ldconfig -p | grep libsndfile

# 2. ffmpeg
which ffmpeg
ffmpeg -version | head -3

# 3. gcc/g++
gcc --version
g++ --version

# 4. make/cmake
make --version
cmake --version
```

### G. RPM 패키지 확인
```bash
# 1. 설치된 개발 패키지
rpm -qa | grep -E "^gcc|^g\+\+|^make|^python"

# 2. 멀티미디어 패키지
rpm -qa | grep -E "ffmpeg|sox|libsndfile|soundfile"

# 3. 전체 패키지 목록 (길어짐)
rpm -qa | sort
```

### H. yum 저장소
```bash
# 1. 활성화된 저장소
yum repolist enabled

# 2. 비활성화된 저장소 포함
yum repolist all
```

### I. 디스크 및 리소스
```bash
# 1. 디스크 사용량
df -h

# 2. 메모리
free -h

# 3. CPU 정보
nproc
lscpu
```

---

## 💾 결과 저장 및 전송

### RHEL 서버에서:
```bash
# 1. 정보 수집 및 저장
bash /path/to/collect_rhel_info.sh > /tmp/rhel89_info.txt

# 2. 파일 확인
cat /tmp/rhel89_info.txt

# 3. 파일 크기
ls -lh /tmp/rhel89_info.txt
```

### Mac에서 다운로드:
```bash
# SSH로 직접 실행 및 저장
ssh user@rhel_server 'bash /path/to/collect_rhel_info.sh' > ~/Downloads/rhel89_info.txt

# 또는 기존 파일 다운로드
scp user@rhel_server:/tmp/rhel89_info.txt ~/Downloads/
```

---

## 📊 결과 분석 팁

수집한 정보에서 확인할 사항:

```
✅ 확인 항목:
1. glibc >= 2.28 (RHEL 8.9 기본값)
2. Python 3.11 설치 여부
3. NVIDIA Driver 설치 여부
4. CUDA Toolkit 버전 (12.9 권장)
5. cuDNN 설치 여부
6. libsndfile, ffmpeg 설치 여부
7. 커널 버전 4.18.x (RHEL 8)
8. 디스크 여유 공간 50GB 이상
```

---

## 🎯 가장 중요한 3개 명령어

**필수 실행:**
```bash
# 1번째 - OS/glibc 확인
cat /etc/os-release && echo "---" && ldd --version | head -1

# 2번째 - Python 확인
python3.11 --version && which python3.11

# 3번째 - GPU 확인
nvidia-smi && echo "---" && ldconfig -p | grep cudnn | head -1
```
