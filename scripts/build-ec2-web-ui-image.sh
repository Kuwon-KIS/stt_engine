#!/bin/bash

################################################################################
#
# 🚀 STT Web UI Docker 이미지 빌드 스크립트 (AWS EC2 RHEL 8.9)
#
# 목적: STT Web UI Docker 이미지 빌드
# 사용: bash scripts/build-ec2-web-ui-image.sh [버전]
# 예시: 
#   bash scripts/build-ec2-web-ui-image.sh          # latest (기본값)
#   bash scripts/build-ec2-web-ui-image.sh v1.0     # v1.0으로 빌드
#
# 결과: stt-web-ui:cuda129-rhel89-[버전]
# 소요시간: 5~10분
#
# 주의사항:
#   1. RHEL 8.9 EC2 인스턴스에서만 실행
#   2. Docker 사전 설치 필수
#   3. 30GB 이상 스토리지 필요
#   4. STT Engine 이미지가 먼저 빌드되어 있어야 함 (선택)
#
################################################################################

set -e

# ============================================================================
# 설정
# ============================================================================

# 스크립트 경로
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(dirname "$SCRIPT_DIR")"
WEB_UI_DIR="${WORKSPACE}/web_ui"
OUTPUT_DIR="${WORKSPACE}/build/output"
BUILD_LOG="/tmp/build-web-ui-$(date +%Y%m%d-%H%M%S).log"

# 버전 정보
DEFAULT_VERSION="latest"
VERSION="${1:-$DEFAULT_VERSION}"
IMAGE_NAME="stt-web-ui"
IMAGE_VERSION="cuda129-rhel89-${VERSION}"
IMAGE_TAG="${IMAGE_NAME}:${IMAGE_VERSION}"

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

log_header "STT Web UI Docker 이미지 빌드"

# Step 1: 전제 조건 확인
log_step "1" "전제 조건 확인"

if ! command -v docker &> /dev/null; then
    log_error "Docker가 설치되지 않았습니다"
fi
log_success "Docker 설치 확인: $(docker --version)"

if [ ! -d "$WEB_UI_DIR" ]; then
    log_error "Web UI 디렉토리를 찾을 수 없습니다: $WEB_UI_DIR"
fi
log_success "Web UI 디렉토리 확인: $WEB_UI_DIR"

# Step 2: 빌드 전 정리 (선택)
log_step "2" "이전 이미지 확인"

if docker images | grep -q "^stt-web-ui"; then
    log_success "기존 이미지를 찾았습니다"
    echo ""
    echo "📋 선택 옵션:"
    echo "   [1] 기존 이미지 사용 (기본값 - n 입력)"
    echo "   [2] 새로 빌드 (y 입력)"
    echo ""
    read -p "⚙️  기존 이미지를 삭제하고 새로 빌드하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker rmi stt-web-ui:* || true
        log_success "기존 이미지 삭제 완료"
    else
        log_success "기존 이미지 사용"
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
echo "  Dockerfile: $WEB_UI_DIR/docker/Dockerfile.web_ui"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if docker build \
    -f "${WEB_UI_DIR}/docker/Dockerfile.web_ui" \
    -t "$IMAGE_TAG" \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    "$WORKSPACE" 2>&1 | tee -a "$BUILD_LOG"; then
    
    log_success "Docker 이미지 빌드 성공"
    
    # 이미지 정보 출력
    echo ""
    docker images | grep "$IMAGE_NAME" | head -5
    
else
    log_error "Docker 이미지 빌드 실패"
fi

# Step 5: Docker 이미지 tar.gz으로 저장
log_step "5" "Docker 이미지 저장 (tar.gz 압축)"

mkdir -p "$OUTPUT_DIR"

# pigz 사용 가능 여부 확인 (병렬 압축으로 훨씬 빠름)
if command -v pigz &> /dev/null; then
    log_success "pigz로 병렬 압축 중 (cores: $(nproc))..."
    docker save "$IMAGE_TAG" | pigz -6 -p $(nproc) > "${OUTPUT_DIR}/stt-web-ui-${IMAGE_VERSION}.tar.gz"
else
    log_success "gzip으로 압축 중 (pigz 미설치)..."
    docker save "$IMAGE_TAG" | gzip -6 > "${OUTPUT_DIR}/stt-web-ui-${IMAGE_VERSION}.tar.gz"
fi

IMAGE_TAR_SIZE=$(du -sh "${OUTPUT_DIR}/stt-web-ui-${IMAGE_VERSION}.tar.gz" | awk '{print $1}')
log_success "Docker 이미지 저장 완료 (크기: $IMAGE_TAR_SIZE)"

# Step 6: 빌드 결과 저장
log_step "6" "빌드 정보 저장"

BUILD_INFO_FILE="${OUTPUT_DIR}/web_ui_build_info_${IMAGE_VERSION}.txt"
{
    echo "========================================="
    echo "STT Web UI Docker 빌드 정보"
    echo "========================================="
    echo "빌드 일시: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "버전: $VERSION"
    echo "이미지명: $IMAGE_TAG"
    echo "이미지 파일: stt-web-ui-${IMAGE_VERSION}.tar.gz"
    echo "파일 크기: $IMAGE_TAR_SIZE"
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
echo "  소요시간: $(elapsed_time)"
echo "  빌드로그: $BUILD_LOG"
echo ""

echo "🚀 실행 명령어"
echo "───────────────────────────────────────"
echo ""
echo "  1️⃣  Docker 네트워크 생성 (처음 한 번만):"
echo "     docker network create stt-network"
echo ""
echo "  2️⃣  STT API 실행 (별도 터미널):"
echo "     docker run -d --name stt-api --network stt-network -p 8003:8003 \\"
echo "       -e STT_DEVICE=cuda -e STT_COMPUTE_TYPE=int8 \\"
echo "       -v \$(pwd)/models:/app/models \\"
echo "       stt-engine:cuda129-rhel89-[버전]"
echo ""
echo "  3️⃣  Web UI 실행 (별도 터미널):"
echo "     docker run -d --name stt-web-ui --network stt-network -p 8100:8100 \\"
echo "       -e STT_API_URL=http://stt-api:8003 \\"
echo "       -v \$(pwd)/web_ui/data:/app/data \\"
echo "       -v \$(pwd)/web_ui/logs:/app/logs \\"
echo "       $IMAGE_TAG"
echo ""
echo "  4️⃣  접속 주소:"
echo "     🌐 Web UI: http://localhost:8100"
echo "     📡 STT API: http://localhost:8003"
echo ""

echo "✅ 모든 단계가 완료되었습니다!"
echo ""
echo "📂 생성된 파일 (최신 5개):"
echo "────────────────────────────────────────────────────────────"
ls -lht "${OUTPUT_DIR}"/* 2>/dev/null | head -5 | awk '{print $9, "(" $5 ")"}' || echo "   생성된 파일 없음"
echo ""
echo "📝 자세한 로그: $BUILD_LOG"
