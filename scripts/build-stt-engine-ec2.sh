#!/bin/bash

# 🚀 STT Engine Docker Image Build Script for AWS EC2 (CUDA 12.9)
# 
# 목적: AWS EC2 (Linux x86_64) 온라인 환경에서 STT Engine Docker 이미지 빌드
# 사용: bash build-stt-engine-ec2.sh
# 결과: stt-engine-cuda129-v1.2.tar.gz (500MB ~ 1GB, 로컬로 다운로드 가능)

set -e

# ============================================================================
# 설정
# ============================================================================

WORKSPACE="${PWD}"
BUILD_DIR="${WORKSPACE}/docker"
OUTPUT_DIR="${WORKSPACE}/build/output"

# 버전 정보
PYTHON_VERSION="3.11"
IMAGE_TAG="stt-engine:cuda129-v1.2"
SAVE_FILENAME="stt-engine-cuda129-v1.2.tar.gz"

# ============================================================================
# 함수 정의
# ============================================================================

print_header() {
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "$1"
    echo "════════════════════════════════════════════════════════════"
}

print_step() {
    echo ""
    echo "📌 $1"
}

print_success() {
    echo "✅ $1"
}

print_error() {
    echo "❌ $1"
    exit 1
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker이 설치되어 있지 않습니다."
    fi
    print_success "Docker 확인: $(docker --version)"
}

check_online() {
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        print_error "인터넷 연결이 없습니다. 온라인 환경에서 빌드를 실행하세요."
    fi
    print_success "인터넷 연결 확인: OK"
}

check_disk_space() {
    available=$(df "$WORKSPACE" | tail -1 | awk '{print $4}')
    # 50GB (51200MB) 이상 필요
    if [ "$available" -lt 51200000 ]; then
        print_error "디스크 공간 부족 (필요: 50GB, 현재: $((available/1024/1024))GB)"
    fi
    print_success "디스크 공간 확인: OK ($((available/1024/1024))GB 사용 가능)"
}

# ============================================================================
# 메인 프로세스
# ============================================================================

print_header "🚀 STT Engine Docker Image Build for AWS EC2 (CUDA 12.9)"

echo ""
echo "⚙️  빌드 설정:"
echo "   Workspace: $WORKSPACE"
echo "   Output: $OUTPUT_DIR"
echo ""
echo "📦 버전:"
echo "   Python: $PYTHON_VERSION"
echo "   Image Tag: $IMAGE_TAG"
echo ""
echo "🎯 결과:"
echo "   Tar File: $SAVE_FILENAME"

# ============================================================================
# Step 1: 환경 검사
# ============================================================================

print_step "Step 1: 환경 검사"

check_docker
check_online
check_disk_space

# 필수 파일 확인
if [ ! -f "$WORKSPACE/api_server.py" ]; then
    print_error "api_server.py를 찾을 수 없습니다"
fi
if [ ! -f "$WORKSPACE/stt_engine.py" ]; then
    print_error "stt_engine.py를 찾을 수 없습니다"
fi
print_success "필수 파일 확인: OK"

# ============================================================================
# Step 2: Dockerfile 복사/생성 (Dockerfile.engine.cuda 기반)
# ============================================================================

print_step "Step 2: Dockerfile 준비"

DOCKERFILE_PATH="$BUILD_DIR/Dockerfile.engine.cuda"

if [ ! -f "$DOCKERFILE_PATH" ]; then
    print_error "Dockerfile.engine.cuda를 찾을 수 없습니다: $DOCKERFILE_PATH"
fi

print_success "Dockerfile 확인: $DOCKERFILE_PATH"

# ============================================================================
# Step 3: 기존 이미지 정리
# ============================================================================

print_step "Step 3: 기존 이미지 정리"

OLD_IMAGE=$(docker images | grep "stt-engine:cuda129" | wc -l)
if [ "$OLD_IMAGE" -gt 0 ]; then
    echo "기존 이미지 제거..."
    docker rmi -f stt-engine:cuda129-v1.2 2>/dev/null || true
    docker rmi -f stt-engine:cuda129-v1.1 2>/dev/null || true
    docker rmi -f stt-engine:cuda129-v1.0 2>/dev/null || true
fi
print_success "이미지 정리 완료"

# ============================================================================
# Step 4: 빌드 디렉토리 확인
# ============================================================================

print_step "Step 4: 빌드 디렉토리 확인"

mkdir -p "$OUTPUT_DIR"
print_success "빌드 디렉토리: $OUTPUT_DIR"

# ============================================================================
# Step 5: Docker 이미지 빌드
# ============================================================================

print_step "Step 5: Docker 이미지 빌드"
echo ""
echo "⏱️  예상 소요 시간: 15-30분 (네트워크 속도에 따라 변동)"
echo "🔄 진행 상황: 터미널에서 다음 메시지를 모니터링하세요"
echo ""

# 빌드 시작
docker build \
    --platform linux/amd64 \
    --tag "$IMAGE_TAG" \
    --file "$DOCKERFILE_PATH" \
    --progress=plain \
    "$WORKSPACE"

if [ $? -ne 0 ]; then
    print_error "Docker 빌드 실패"
fi

print_success "Docker 이미지 빌드 완료: $IMAGE_TAG"

# ============================================================================
# Step 6: 이미지 검증
# ============================================================================

print_step "Step 6: 이미지 검증"

# 이미지 크기 확인
IMAGE_SIZE=$(docker images "$IMAGE_TAG" --format "{{.Size}}")
echo "이미지 크기: $IMAGE_SIZE"

# PyTorch/CUDA 확인
echo ""
echo "⏳ PyTorch/CUDA 검증 중..."
docker run --rm "$IMAGE_TAG" python3.11 -c "
import sys
try:
    import torch
    print(f'✅ PyTorch 로드 성공: {torch.__version__}')
    print(f'✅ CUDA 가능: {torch.cuda.is_available()}')
except ImportError as e:
    print(f'❌ PyTorch 로드 실패: {e}')
    sys.exit(1)
" || print_error "PyTorch 검증 실패"

print_success "이미지 검증 완료"

# ============================================================================
# Step 7: 이미지 저장 (tar.gz)
# ============================================================================

print_step "Step 7: 이미지 tar.gz로 저장"
echo ""
echo "⏳ 압축 중... (3-5분 소요)"

SAVE_PATH="$OUTPUT_DIR/$SAVE_FILENAME"

docker save "$IMAGE_TAG" | gzip > "$SAVE_PATH"

if [ ! -f "$SAVE_PATH" ]; then
    print_error "이미지 저장 실패"
fi

SAVE_SIZE=$(ls -lh "$SAVE_PATH" | awk '{print $5}')
print_success "이미지 저장 완료: $SAVE_PATH ($SAVE_SIZE)"

# ============================================================================
# Step 8: MD5 체크섬 생성 (무결성 검증용)
# ============================================================================

print_step "Step 8: 무결성 검증 파일 생성"

MD5_FILE="$OUTPUT_DIR/$SAVE_FILENAME.md5"
md5sum "$SAVE_PATH" > "$MD5_FILE"
print_success "MD5 체크섬: $MD5_FILE"

echo ""
echo "검증 명령어 (다운로드 후):"
echo "  md5sum -c $SAVE_FILENAME.md5"

# ============================================================================
# Step 9: 최종 요약
# ============================================================================

print_header "✅ 빌드 완료!"

echo ""
echo "📦 생성된 파일:"
echo "   tar.gz: $SAVE_PATH ($SAVE_SIZE)"
echo "   md5sum: $MD5_FILE"
echo ""
echo "📥 다운로드 (로컬 Mac에서):"
echo "   scp -i your-key.pem ubuntu@\$EC2_IP:$SAVE_PATH ~/"
echo ""
echo "🔧 로드 (운영 서버에서):"
echo "   gunzip $SAVE_FILENAME"
echo "   docker load < ${SAVE_FILENAME%.gz}"
echo "   docker images | grep stt-engine"
echo ""
echo "✨ 빌드 완료!"
