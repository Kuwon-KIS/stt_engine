#!/bin/bash

################################################################################
#
# 🚀 STT Engine Docker 이미지 빌드 스크립트 (Local Development - Mac/Linux)
#
# 목적: 로컬 개발용 CPU-only Docker 이미지 빌드
# 사용: bash scripts/build-local-engine-image.sh [버전]
# 예시: 
#   bash scripts/build-local-engine-image.sh          # latest (기본값)
#   bash scripts/build-local-engine-image.sh v1.0     # v1.0으로 빌드
#
# 결과: stt-engine:local-[버전]
# 소요시간: 10~20분 (CPU-only, 경량 빌드)
#
# 주의사항:
#   1. macOS (Apple Silicon/Intel) 또는 Linux에서 실행
#   2. Docker Desktop 설치 필수
#   3. 20GB 이상 스토리지 필요
#   4. 인터넷 연결 필수
#
################################################################################

set -e

# ============================================================================
# 설정
# ============================================================================

# 스크립트 경로
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="${WORKSPACE}/docker"
OUTPUT_DIR="${WORKSPACE}/build/output"
BUILD_LOG="/tmp/build-local-engine-$(date +%Y%m%d-%H%M%S).log"

# 버전 정보
DEFAULT_VERSION="latest"
VERSION="${1:-$DEFAULT_VERSION}"
IMAGE_NAME="stt-engine"
IMAGE_VERSION="local-${VERSION}"
IMAGE_TAG="${IMAGE_NAME}:${IMAGE_VERSION}"

# 플랫폼 감지
OS_TYPE="$(uname -s)"
if [ "$OS_TYPE" = "Darwin" ]; then
    PLATFORM="macOS"
    PLATFORM_FLAG="--platform linux/amd64"  # Mac의 Docker Desktop에서 amd64 빌드
elif [ "$OS_TYPE" = "Linux" ]; then
    PLATFORM="Linux"
    PLATFORM_FLAG=""
else
    PLATFORM="Unknown"
    PLATFORM_FLAG=""
fi

# 타이머
START_TIME=$(date +%s)

# ============================================================================
# 유틸리티 함수
# ============================================================================

log_header() {
    local msg="$1"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "  $msg"
    echo "════════════════════════════════════════════════════════════════"
    echo "$msg" >> "$BUILD_LOG"
}

log_step() {
    local step_num="$1"
    local step_name="$2"
    echo ""
    echo "📌 Step $step_num: $step_name"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step $step_num: $step_name" >> "$BUILD_LOG"
}

log_success() {
    echo "✅ $1"
    echo "[SUCCESS] $1" >> "$BUILD_LOG"
}

log_info() {
    echo "ℹ️  $1"
    echo "[INFO] $1" >> "$BUILD_LOG"
}

log_error() {
    echo "❌ 에러: $1"
    echo "[ERROR] $1" >> "$BUILD_LOG"
    exit 1
}

elapsed_time() {
    local end_time=$(date +%s)
    local elapsed=$((end_time - START_TIME))
    echo "$((elapsed / 60))분 $((elapsed % 60))초"
}

# ============================================================================
# 메인 로직
# ============================================================================

log_header "STT Engine Local Development Docker 이미지 빌드"

echo ""
echo "📊 빌드 환경"
echo "───────────────────────────────────────"
echo "  플랫폼: $PLATFORM"
echo "  버전: $VERSION"
echo "  이미지명: $IMAGE_TAG"
echo "  Dockerfile: docker/Dockerfile.engine.local"
echo ""

# Step 1: 전제 조건 확인
log_step "1" "전제 조건 확인"

if ! command -v docker &> /dev/null; then
    log_error "Docker가 설치되지 않았습니다"
fi
log_success "Docker 설치 확인: $(docker --version)"

if [ ! -f "${DOCKER_DIR}/Dockerfile.engine.local" ]; then
    log_error "Dockerfile.engine.local을 찾을 수 없습니다: ${DOCKER_DIR}/Dockerfile.engine.local"
fi
log_success "Dockerfile 확인: ${DOCKER_DIR}/Dockerfile.engine.local"

# Mac에서 Docker Desktop 버전 확인
if [ "$OS_TYPE" = "Darwin" ]; then
    if ! docker run --platform linux/amd64 alpine echo "✓" > /dev/null 2>&1; then
        log_info "주의: Docker Desktop이 linux/amd64 플랫폼을 지원하지 않을 수 있습니다"
        log_info "Settings → Features in development → Use containerd for pulling and storing images 확인"
    fi
fi

# Step 2: 기존 이미지 확인
log_step "2" "기존 이미지 확인"

if docker images | grep -q "^$IMAGE_NAME.*$IMAGE_VERSION"; then
    log_success "기존 이미지 발견: $IMAGE_TAG"
    read -p "⚙️  기존 이미지를 삭제하고 새로 빌드하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker rmi "$IMAGE_TAG" 2>/dev/null || true
        log_success "기존 이미지 삭제 완료"
    else
        log_success "기존 이미지 사용 (빌드 스킵)"
        echo ""
        docker images | grep "$IMAGE_TAG"
        exit 0
    fi
else
    log_success "기존 이미지 없음 (새로운 빌드)"
fi

# Step 3: 출력 디렉토리 생성
log_step "3" "출력 디렉토리 생성"

mkdir -p "$OUTPUT_DIR"
log_success "출력 디렉토리: $OUTPUT_DIR"

# Step 4: Docker 이미지 빌드
log_step "4" "Docker 이미지 빌드 시작"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  이미지: $IMAGE_TAG"
echo "  플랫폼: linux/amd64"
echo "  Dockerfile: docker/Dockerfile.engine.local"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if docker build \
    $PLATFORM_FLAG \
    -f "${DOCKER_DIR}/Dockerfile.engine.local" \
    -t "$IMAGE_TAG" \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    "$WORKSPACE" 2>&1 | tee -a "$BUILD_LOG"; then
    
    log_success "Docker 이미지 빌드 성공"
    
    # 이미지 정보 출력
    echo ""
    docker images | grep "$IMAGE_NAME" | grep "local"
    
else
    log_error "Docker 이미지 빌드 실패"
fi

# Step 5: 빌드 결과 저장
log_step "5" "빌드 정보 저장"

BUILD_INFO_FILE="${OUTPUT_DIR}/engine_local_build_info_${VERSION}.txt"
IMAGE_SIZE=$(docker images "$IMAGE_TAG" --format "{{.Size}}")
{
    echo "========================================="
    echo "STT Engine Local Docker 빌드 정보"
    echo "========================================="
    echo "빌드 일시: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "플랫폼: $PLATFORM"
    echo "버전: $VERSION"
    echo "이미지명: $IMAGE_TAG"
    echo "이미지 크기: $IMAGE_SIZE"
    echo "소요시간: $(elapsed_time)"
    echo ""
    echo "이미지 정보:"
    docker images | grep "$IMAGE_TAG"
    echo ""
    echo "빌드 로그: $BUILD_LOG"
} > "$BUILD_INFO_FILE"

log_success "빌드 정보 저장: $BUILD_INFO_FILE"

# Step 6: 완료 메시지
log_header "빌드 완료! 🎉"

echo ""
echo "📊 빌드 통계"
echo "───────────────────────────────────────"
echo "  이미지명: $IMAGE_TAG"
echo "  이미지 크기: $IMAGE_SIZE"
echo "  소요시간: $(elapsed_time)"
echo "  빌드로그: $BUILD_LOG"
echo ""

echo "🚀 실행 명령어 (Mac 환경)"
echo "───────────────────────────────────────"
echo ""
echo "  1️⃣  Docker 네트워크 생성 (처음 한 번만):"
echo "     docker network create stt-network"
echo ""
echo "  2️⃣  STT Engine 실행:"
echo "     docker run -d --name stt-engine-local -p 8003:8003 \\"
echo "       -e STT_DEVICE=cpu \\"
echo "       -v \$(pwd)/models:/app/models \\"
echo "       -v \$(pwd)/audio/samples:/app/audio/samples \\"
echo "       $IMAGE_TAG"
echo ""
echo "  3️⃣  Web UI 실행 (별도 터미널):"
echo "     docker run -d --name stt-web-ui-local -p 8100:8100 \\"
echo "       -e STT_API_URL=http://host.docker.internal:8003 \\"
echo "       -v \$(pwd)/web_ui/data:/app/data \\"
echo "       -v \$(pwd)/web_ui/logs:/app/logs \\"
echo "       stt-web-ui:local"
echo ""
echo "  4️⃣  로그 확인:"
echo "     docker logs -f stt-engine-local"
echo ""
echo "  5️⃣  접속 주소:"
echo "     🌐 Web UI: http://localhost:8100"
echo "     📡 STT API: http://localhost:8003"
echo ""
echo "  6️⃣  컨테이너 정리:"
echo "     docker stop stt-engine-local stt-web-ui-local"
echo "     docker rm stt-engine-local stt-web-ui-local"
echo ""

echo "✅ 모든 단계가 완료되었습니다!"
echo ""
echo "📝 자세한 로그: $BUILD_LOG"
echo ""
