#!/bin/bash

# 🔍 RHEL 8.9 환경 정보 수집 스크립트
# 사용: bash collect_rhel_info.sh > rhel89_info.txt

echo "════════════════════════════════════════════════════════════"
echo "🔍 RHEL 8.9 환경 정보 수집"
echo "════════════════════════════════════════════════════════════"
echo ""

echo "=== 1. OS 정보 ==="
echo "OS Version:"
cat /etc/os-release
echo ""

echo "=== 2. 커널 정보 ==="
echo "Kernel:"
uname -r
echo ""
uname -a
echo ""

echo "=== 3. glibc 버전 (중요!) ==="
echo "glibc version:"
ldd --version | head -1
echo ""
rpm -qa | grep glibc
echo ""

echo "=== 4. OpenSSL 버전 ==="
openssl version
echo ""

echo "=== 5. libstdc++ 버전 ==="
echo "Available GLIBCXX versions:"
strings /usr/lib64/libstdc++.so.6 | grep GLIBCXX | sort -V | tail -3
echo ""

echo "=== 6. GCC/G++ 버전 ==="
gcc --version | head -1
g++ --version | head -1
echo ""

echo "=== 7. Python 버전 ==="
echo "Python3:"
python3 --version 2>/dev/null || echo "python3 not found"
which python3
echo ""
echo "Python3.11:"
python3.11 --version 2>/dev/null || echo "python3.11 not found"
which python3.11
echo ""

echo "=== 8. NVIDIA / CUDA 정보 (GPU 있는 경우) ==="
echo "NVIDIA Driver:"
nvidia-smi 2>/dev/null | head -2 || echo "No NVIDIA GPU detected"
echo ""
echo "CUDA Toolkit:"
nvcc --version 2>/dev/null || echo "CUDA Toolkit not installed"
echo ""
echo "CUDA location:"
ls -ld /usr/local/cuda* 2>/dev/null || echo "No CUDA directory found"
echo ""

echo "=== 9. cuDNN (GPU 있는 경우) ==="
echo "cuDNN libraries:"
ldconfig -p | grep cudnn || echo "cuDNN not found"
echo ""
ls -la /usr/lib64/*cudnn* 2>/dev/null || echo "No cuDNN libraries in /usr/lib64"
echo ""

echo "=== 10. 시스템 라이브러리 ==="
echo "libsndfile:"
ldconfig -p | grep libsndfile || echo "libsndfile not found"
echo ""
echo "libffi:"
ldconfig -p | grep libffi | head -3
echo ""
echo "libssl:"
ldconfig -p | grep libssl | head -3
echo ""

echo "=== 11. 설치된 RPM 패키지 (관련) ==="
echo "Python packages:"
rpm -qa | grep -i python
echo ""
echo "Audio/Media packages:"
rpm -qa | grep -E "ffmpeg|sox|libsndfile" || echo "Audio packages not found"
echo ""
echo "Development packages:"
rpm -qa | grep -E "^gcc|^g\+\+|^make|^cmake" || echo "Some dev packages not found"
echo ""

echo "=== 12. yum 저장소 정보 ==="
echo "Enabled repositories:"
yum repolist enabled 2>/dev/null | tail -20
echo ""

echo "=== 13. Docker 정보 (있는 경우) ==="
echo "Docker version:"
docker --version 2>/dev/null || echo "Docker not installed"
echo ""
echo "Docker base images:"
docker images 2>/dev/null | head -5 || echo "Docker not available"
echo ""

echo "=== 14. 디스크 공간 ==="
df -h / /tmp 2>/dev/null
echo ""

echo "=== 15. 메모리 정보 ==="
free -h
echo ""

echo "════════════════════════════════════════════════════════════"
echo "✅ 정보 수집 완료"
echo "════════════════════════════════════════════════════════════"
