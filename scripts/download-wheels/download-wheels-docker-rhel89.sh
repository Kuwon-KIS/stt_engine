#!/bin/bash

###############################################################################
# PyTorch + 모든 의존성 wheels 다운로드 (Docker 기반, RHEL 8.9 호환)
# - CUDA 12.1/12.9 호환 PyTorch 2.2.0
# - Python 3.11, manylinux_2_17_x86_64
# - 900MB 청크로 분할 압축
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEELS_DIR="$SCRIPT_DIR/wheels"
DOCKER_IMAGE_NAME="stt-wheels-downloader:latest"
CHUNK_SIZE_MB=900

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐳 Docker 기반 PyTorch + 모든 의존성 wheels 다운로드"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "배포 대상: RHEL 8.9 (CUDA 12.9)"
echo "PyTorch: 2.2.0 (CUDA 12.1, CUDA 12.9 호환)"
echo "플랫폼: manylinux_2_17_x86_64, Python 3.11"
echo ""

# 1. Docker 이미지 빌드
echo "🐳 Step 1/3: Docker 이미지 빌드 중..."
cd "$SCRIPT_DIR/.."

docker build \
    -f deployment_package/Dockerfile.wheels-download \
    -t "$DOCKER_IMAGE_NAME" \
    deployment_package/ 2>&1 | grep -E "(Successfully|ERROR|Step)" | head -50

if [ $? -ne 0 ]; then
    echo "❌ Docker 빌드 실패"
    exit 1
fi

echo "✅ Docker 이미지 빌드 완료"
echo ""

# 2. Docker 컨테이너 실행으로 wheels 추출
echo "⬇️  Step 2/3: Docker 컨테이너에서 wheels 다운로드 중..."
docker run --rm \
    -v "$WHEELS_DIR:/wheels" \
    "$DOCKER_IMAGE_NAME" \
    bash -c "ls -1 /wheels/*.whl | wc -l && du -sh /wheels" 2>&1

echo "✅ wheels 다운로드 완료"
echo ""

# 3. 분할 압축
echo "📦 Step 3/3: 분할 압축 처리..."
cd "$WHEELS_DIR"

# 기존 압축 파일 제거
rm -f wheels-*.tar.gz

# 모든 wheel을 tarball로 생성
tar -czf wheels-all.tar.gz *.whl

# 파일 크기 확인
if [[ "$OSTYPE" == "darwin"* ]]; then
    TOTAL_SIZE_BYTES=$(stat -f%z wheels-all.tar.gz)
else
    TOTAL_SIZE_BYTES=$(stat -c%s wheels-all.tar.gz)
fi

TOTAL_SIZE_MB=$((TOTAL_SIZE_BYTES / 1024 / 1024))

if [ "$TOTAL_SIZE_MB" -gt "$CHUNK_SIZE_MB" ]; then
    echo "  ⚠️  총 크기 ${TOTAL_SIZE_MB}MB > ${CHUNK_SIZE_MB}MB, 분할 압축 진행..."
    
    # split으로 분할
    split -b ${CHUNK_SIZE_MB}m wheels-all.tar.gz "wheels-part-"
    rm -f wheels-all.tar.gz
    
    # 재명명
    i=1
    for file in $(ls -1 wheels-part-* 2>/dev/null | sort); do
        mv "$file" "wheels-part$(printf %02d $i).tar.gz"
        ((i++))
    done
    
    echo "  ✅ 분할 완료:"
    ls -lh wheels-part*.tar.gz | awk '{printf "     • %s (%s)\n", $9, $5}'
else
    echo "  ✅ 단일 파일 (${TOTAL_SIZE_MB}MB):"
    ls -lh wheels-all.tar.gz | awk '{printf "     • %s (%s)\n", $9, $5}'
fi

cd "$SCRIPT_DIR"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📂 생성된 파일:"
ls -1 "$WHEELS_DIR"/*.tar.gz 2>/dev/null | while read file; do
    size=$(ls -lh "$file" | awk '{print $5}')
    name=$(basename "$file")
    printf "  • %s (%s)\n" "$name" "$size"
done
echo ""
echo "📊 원본 wheel 파일:"
WHEEL_COUNT=$(ls -1 "$WHEELS_DIR"/*.whl 2>/dev/null | wc -l)
printf "  • %d개 파일 (deployment_package/wheels/)\n" "$WHEEL_COUNT"
echo ""
echo "🚀 다음 단계: RHEL 8.9 서버로 전송"
echo "   scp -r deployment_package/ user@rhel-server:/opt/stt/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
