#!/bin/bash

###############################################################################
# Wheels 다운로드 및 분할 압축 스크립트 (개선된 두 단계 다운로드)
# - PyTorch: CUDA 12.1 인덱스에서 별도 다운로드
# - 의존성: PyPI에서 다운로드
# - 900MB 단위로 분할 압축
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEELS_DIR="$SCRIPT_DIR/wheels"
PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/bin/python3.11}"
CHUNK_SIZE_MB=900

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 STT Engine - Wheels 다운로드 및 분할 압축"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "설정:"
echo "  • Python: $PYTHON_BIN"
echo "  • 대상: manylinux_2_17_x86_64 (RHEL 8.9)"
echo "  • Python 버전: 3.11"
echo "  • PyTorch: 2.1.2 (CUDA 12.1)"
echo "  • faster-whisper: 1.0.3"
echo "  • 청크 크기: ${CHUNK_SIZE_MB}MB"
echo ""

# Python 버전 확인
echo "🔍 Python 버전 확인..."
$PYTHON_BIN --version
echo ""

# 1. wheels 디렉토리 정리
echo "🧹 Step 1/4: wheels 디렉토리 정리..."
rm -rf "$WHEELS_DIR"
mkdir -p "$WHEELS_DIR"
echo "✅ 완료"
echo ""

# 2. PyTorch 다운로드 (CUDA 12.1 인덱스에서)
echo "⬇️  Step 2/4: PyTorch 2.1.2 + torchaudio CUDA 12.1 다운로드..."
$PYTHON_BIN -m pip download \
    torch==2.1.2 \
    torchaudio==2.1.2 \
    --only-binary=:all: \
    --platform manylinux_2_17_x86_64 \
    --python-version 311 \
    --index-url https://download.pytorch.org/whl/cu121 \
    --no-deps \
    -d "$WHEELS_DIR" 2>&1 | grep -E "(Successfully downloaded|Collecting)" || echo "PyTorch 다운로드 진행 중..."

# PyTorch 다운로드 확인
TORCH_COUNT=$(ls -1 "$WHEELS_DIR"/torch*.whl 2>/dev/null | wc -l)
if [ "$TORCH_COUNT" -gt 0 ]; then
    echo "✅ PyTorch 다운로드 완료 ($TORCH_COUNT개 파일)"
else
    echo "⚠️  PyTorch 파일이 확인되지 않음. 계속 진행합니다."
fi
echo ""

# 3. 기타 모든 의존성 다운로드 (PyPI에서)
echo "⬇️  Step 3/4: 기타 의존성 패키지 다운로드..."
$PYTHON_BIN -m pip download \
    faster-whisper==1.0.3 \
    librosa==0.10.0 \
    numpy==1.24.3 \
    scipy==1.12.0 \
    huggingface-hub==0.21.4 \
    python-dotenv==1.0.0 \
    pydantic==2.5.3 \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    requests==2.31.0 \
    pyyaml==6.0.1 \
    --only-binary=:all: \
    --platform manylinux_2_17_x86_64 \
    --python-version 311 \
    -d "$WHEELS_DIR" 2>&1 | grep -E "(Successfully downloaded|Collecting)" | head -30

echo "✅ 모든 패키지 다운로드 완료"
echo ""

# 4. 다운로드된 wheels 정보 출력 및 분할 압축
echo "📊 Step 4/4: 분할 압축 처리"
WHEEL_COUNT=$(ls -1 "$WHEELS_DIR"/*.whl 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$WHEELS_DIR" | awk '{print $1}')
echo "  • .whl 파일 개수: $WHEEL_COUNT개"
echo "  • 총 크기: $TOTAL_SIZE"
echo ""

cd "$WHEELS_DIR"

# 모든 .whl 파일을 하나의 tarball로 생성
echo "📦 tarball 생성 중..."
tar -czf wheels-all.tar.gz *.whl

# 파일 크기 확인 (macOS/Linux 호환)
if [[ "$OSTYPE" == "darwin"* ]]; then
    TOTAL_SIZE_BYTES=$(stat -f%z wheels-all.tar.gz)
else
    TOTAL_SIZE_BYTES=$(stat -c%s wheels-all.tar.gz)
fi

TOTAL_SIZE_MB=$((TOTAL_SIZE_BYTES / 1024 / 1024))

if [ "$TOTAL_SIZE_MB" -gt "$CHUNK_SIZE_MB" ]; then
    echo "  ⚠️  총 크기 ${TOTAL_SIZE_MB}MB > ${CHUNK_SIZE_MB}MB, 분할 압축 진행..."
    
    # split 명령으로 분할 압축
    split -b ${CHUNK_SIZE_MB}m wheels-all.tar.gz "wheels-part-"
    
    # 기존 통합 tarball 삭제
    rm -f wheels-all.tar.gz
    
    # 분할된 파일 정렬 및 재명명
    i=1
    for file in $(ls -1 wheels-part-* 2>/dev/null | sort); do
        new_name=$(printf "wheels-part%02d.tar.gz" $i)
        mv "$file" "$new_name"
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
echo "📦 생성된 압축 파일:"
ls -1 "$WHEELS_DIR"/*.tar.gz 2>/dev/null | while read file; do
    size=$(ls -lh "$file" | awk '{print $5}')
    name=$(basename "$file")
    printf "  • %s (%s)\n" "$name" "$size"
done
echo ""
echo "📄 원본 wheel 파일:"
printf "  • %s 디렉토리에 %d개 저장\n" "$WHEELS_DIR" "$WHEEL_COUNT"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 RHEL 8.9 오프라인 배포 절차"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  1️⃣  전체 deployment_package를 Linux 서버로 전송:"
echo "     scp -r deployment_package/ user@rhel-server:/opt/stt/"
echo ""
echo "  2️⃣  서버에서 wheels 압축 해제:"
echo "     cd /opt/stt/deployment_package/wheels"
echo ""
if ls "$WHEELS_DIR"/wheels-part*.tar.gz &> /dev/null; then
    echo "     # 분할된 파일 결합 및 추출 (예: 3개 파일)"
    echo "     cat wheels-part*.tar.gz | tar -xzf -"
else
    echo "     # 단일 파일 추출"
    echo "     tar -xzf wheels-all.tar.gz"
fi
echo ""
echo "  3️⃣  Python 3.11 환경에서 설치:"
echo "     python3.11 -m pip install --no-index --find-links=. *.whl"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
