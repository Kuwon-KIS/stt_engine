#!/bin/bash

###############################################################################
# Docker를 사용한 Wheels 다운로드 및 분할 압축 스크립트
# - Linux manylinux_2_17_x86_64 환경에서 wheels 다운로드
# - PyTorch는 CUDA 12.1 인덱스 사용
# - 900MB 단위로 분할 압축
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEELS_DIR="$SCRIPT_DIR/wheels"
DOCKER_IMAGE_NAME="stt-wheels-downloader:latest"
CHUNK_SIZE_MB=900

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐳 Docker 기반 Wheels 다운로드 및 분할 압축"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. wheels 디렉토리 정리
echo "🧹 Step 1/5: wheels 디렉토리 정리..."
rm -rf "$WHEELS_DIR"
mkdir -p "$WHEELS_DIR"
echo "✅ 완료"
echo ""

# 2. Docker 이미지 빌드
echo "🐳 Step 2/5: Docker 이미지 빌드 중 (약 10-15분)..."
docker build \
    -f "$SCRIPT_DIR/Dockerfile.wheels-download" \
    -t "$DOCKER_IMAGE_NAME" \
    "$SCRIPT_DIR"
echo "✅ Docker 이미지 빌드 완료"
echo ""

# 3. Docker 컨테이너 실행하여 wheels 추출
echo "⬇️  Step 3/5: Docker 컨테이너에서 wheels 다운로드 중..."
docker run --rm \
    -v "$WHEELS_DIR:/wheels" \
    "$DOCKER_IMAGE_NAME" \
    bash -c "echo '✅ wheels 다운로드 완료' && ls -1 /wheels/*.whl | wc -l"
echo "✅ wheels 다운로드 완료"
echo ""

# 4. 다운로드된 wheels 정보 출력
echo "📊 Step 4/5: 다운로드된 wheels 정보"
echo "  • 파일 개수: $(ls -1 "$WHEELS_DIR"/*.whl 2>/dev/null | wc -l) 개"
echo "  • 총 크기: $(du -sh "$WHEELS_DIR" | awk '{print $1}')"
echo ""

# 5. 분할 압축 (900MB 청크)
echo "📦 Step 5/5: 분할 압축 중 (${CHUNK_SIZE_MB}MB 단위)..."
cd "$WHEELS_DIR"

# 모든 .whl 파일을 하나의 tarball로 생성
tar -czf wheels-all.tar.gz *.whl

TOTAL_SIZE=$(stat -f%z wheels-all.tar.gz 2>/dev/null || stat -c%s wheels-all.tar.gz 2>/dev/null)
TOTAL_SIZE_MB=$((TOTAL_SIZE / 1024 / 1024))

if [ "$TOTAL_SIZE_MB" -gt "$CHUNK_SIZE_MB" ]; then
    echo "  ⚠️  총 크기 ${TOTAL_SIZE_MB}MB는 ${CHUNK_SIZE_MB}MB 초과하므로 분할 압축 중..."
    
    # split 명령으로 분할 압축
    split -b ${CHUNK_SIZE_MB}M wheels-all.tar.gz "wheels-part-"
    
    # 기존 통합 tarball 삭제
    rm -f wheels-all.tar.gz
    
    # 분할된 파일 정렬 및 재명명
    ls -1 wheels-part-* | sort | awk '{
        i++
        new_name = sprintf("wheels-part%02d.tar.gz", i)
        system("mv " $0 " " new_name)
    }'
    
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
echo "📦 생성된 파일:"
ls -1 "$WHEELS_DIR"/*.tar.gz 2>/dev/null | while read file; do
    size=$(ls -lh "$file" | awk '{print $5}')
    name=$(basename "$file")
    printf "  • %s (%s)\n" "$name" "$size"
done
echo ""
echo "🚀 다음 단계:"
echo "  1. deployment_package 디렉토리 전체를 Linux 서버로 전송:"
echo "     scp -r deployment_package/ user@rhel-server:/tmp/"
echo ""
echo "  2. 서버에서 wheels 압축 해제:"
echo "     cd deployment_package/wheels"
echo "     cat wheels-part*.tar.gz | tar -xzf -   # 분할된 경우"
echo "     tar -xzf wheels-all.tar.gz              # 단일 파일인 경우"
echo ""
echo "  3. pip로 설치:"
echo "     pip install *.whl"
echo ""
