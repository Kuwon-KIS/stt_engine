#!/bin/bash

################################################################################
#
# 🚀 STT Engine Docker 이미지 빌드 스크립트 (AWS EC2 RHEL 8.9)
#
# 목적: Docker 이미지 빌드만 수행 (모델 다운로드 제외)
# 사용: bash scripts/build-ec2-engine-image.sh [버전]
# 예시: 
#   bash scripts/build-ec2-engine-image.sh          # v1.4 (기본값)
#   bash scripts/build-ec2-engine-image.sh v1.5     # v1.5로 빌드
#   bash scripts/build-ec2-engine-image.sh v2.0     # v2.0으로 빌드
#
# 결과: stt-engine:cuda129-rhel89-[버전] (7.3GB)
# 소요시간: 20~40분 (Docker 빌드만)
#
# 주의사항:
#   1. RHEL 8.9 EC2 인스턴스에서만 실행
#   2. Docker 사전 설치 필수
#   3. 100GB 이상 스토리지 필요
#   4. 인터넷 연결 필수
#
################################################################################

set -e

# ============================================================================
# 설정
# ============================================================================

# 스크립트 경로 (scripts/ 디렉토리)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 프로젝트 루트 (scripts/의 부모 디렉토리)
WORKSPACE="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="${WORKSPACE}/docker"
OUTPUT_DIR="${WORKSPACE}/build/output"
BUILD_LOG="/tmp/build-image-$(date +%Y%m%d-%H%M%S).log"

# 버전 정보 (동적 할당)
DEFAULT_VERSION="v1.4"
VERSION="${1:-$DEFAULT_VERSION}"
IMAGE_NAME="stt-engine"
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

log_warn() {
    echo "⚠️  $1"
    echo "[WARN] $1" >> "$BUILD_LOG"
}

log_error() {
    echo "❌ $1"
    echo "[ERROR] $1" >> "$BUILD_LOG"
    exit 1
}

log_info() {
    echo "ℹ️  $1"
    echo "[INFO] $1" >> "$BUILD_LOG"
}

print_elapsed() {
    local end_time=$(date +%s)
    local elapsed=$((end_time - START_TIME))
    local hours=$((elapsed / 3600))
    local minutes=$(((elapsed % 3600) / 60))
    local seconds=$((elapsed % 60))
    printf "⏱️  경과시간: %02dh %02dm %02ds\n" $hours $minutes $seconds
}

# ============================================================================
# 환경 확인
# ============================================================================

check_prerequisites() {
    log_step 0 "사전 확인"
    
    # Docker 확인
    if ! command -v docker &> /dev/null; then
        log_error "Docker가 설치되어 있지 않습니다"
    fi
    log_success "Docker 확인: $(docker --version)"
    
    # git 확인
    if ! command -v git &> /dev/null; then
        log_error "git이 설치되어 있지 않습니다"
    fi
    log_success "git 확인: $(git --version)"
    
    # 디스크 공간 확인 (100GB)
    available=$(df "$WORKSPACE" | tail -1 | awk '{print $4}')
    if [ "$available" -lt 102400000 ]; then
        log_warn "디스크 공간 부족 (필요: 100GB, 현재: $(($available / 1024 / 1024))GB)"
    else
        log_success "디스크 공간 확인: $(($available / 1024 / 1024))GB"
    fi
    
    # 인터넷 연결 확인
    if ! ping -c 1 8.8.8.8 &> /dev/null 2>&1; then
        log_error "인터넷 연결이 없습니다. 온라인 빌드 필수"
    fi
    log_success "인터넷 연결 확인: OK"
}

# ============================================================================
# 기존 이미지 확인
# ============================================================================

check_existing_image() {
    log_step "Pre" "기존 이미지 확인"
    
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$IMAGE_TAG$"; then
        log_warn "기존 이미지가 있습니다: $IMAGE_TAG"
        log_info "옵션:"
        log_info "  1. 기존 이미지 사용 (엔터 누르기)"
        log_info "  2. 새로 빌드 (rebuild 입력)"
        
        read -p "선택 (기본: 사용): " choice
        
        if [ "$choice" != "rebuild" ]; then
            log_success "기존 이미지 사용"
            echo "SKIP_BUILD=1"
            return 0
        fi
        
        log_info "기존 이미지 제거 중..."
        docker rmi "$IMAGE_TAG" || true
    fi
    
    echo "SKIP_BUILD=0"
}

# ============================================================================
# Step 1: Docker 이미지 빌드 (20~40분)
# ============================================================================

build_docker_image() {
    log_step 1 "Docker 이미지 빌드 (20~40분)"
    
    if [ ! -f "$DOCKER_DIR/Dockerfile.engine.rhel89" ]; then
        log_error "Dockerfile.engine.rhel89를 찾을 수 없습니다"
    fi
    
    log_info "빌드 시작: $IMAGE_TAG"
    
    # Docker 빌드 실행
    cd "$WORKSPACE"
    docker build \
        --platform linux/amd64 \
        -t "$IMAGE_TAG" \
        -f "$DOCKER_DIR/Dockerfile.engine.rhel89" \
        --progress=plain \
        . 2>&1 | tee -a "$BUILD_LOG"
    
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        log_error "Docker 빌드 실패"
    fi
    
    # 이미지 확인
    if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$IMAGE_TAG$"; then
        log_error "Docker 이미지 빌드 완료되지 않음"
    fi
    
    local image_size=$(docker images "$IMAGE_TAG" --format "{{.Size}}")
    log_success "Docker 이미지 빌드 완료 (크기: $image_size)"
    print_elapsed
}

# ============================================================================
# 이미지 저장
# ============================================================================

save_image() {
    log_step 2 "Docker 이미지 저장 (2~5분)"
    
    mkdir -p "$OUTPUT_DIR"
    
    # pigz 확인 (병렬 압축으로 훨씬 빠름)
    if command -v pigz &> /dev/null; then
        log_info "pigz로 병렬 압축 중 (cores: $(nproc), 압축률: 빠름) ..."
        docker save "$IMAGE_TAG" | pigz -1 -p $(nproc) > "$OUTPUT_DIR/stt-engine-${IMAGE_VERSION}.tar.gz"
    else
        log_info "gzip으로 압축 중 (pigz 미설치, 압축률: 낮음) ..."
        log_info "더 빠른 압축을 원하면: yum install -y pigz"
        docker save "$IMAGE_TAG" | gzip -1 > "$OUTPUT_DIR/stt-engine-${IMAGE_VERSION}.tar.gz"
    fi
    
    local image_tar_size=$(du -sh "$OUTPUT_DIR/stt-engine-${IMAGE_VERSION}.tar.gz" | awk '{print $1}')
    log_success "Docker 이미지 저장 완료 (크기: $image_tar_size)"
    
    # 빌드 정보 저장
    cat > "$OUTPUT_DIR/BUILD_IMAGE_INFO.txt" << EOF
# STT Engine Docker Image Build Information
# Generated: $(date)

## Image Information
- Name: $IMAGE_TAG
- Size: $image_tar_size
- Archive: stt-engine-${IMAGE_VERSION}.tar.gz

## Build Details
- Dockerfile: docker/Dockerfile.engine.rhel89
- Base Image: registry.access.redhat.com/ubi8/python-311:latest
- Platform: linux/amd64
- CUDA: 12.9
- PyTorch: 2.6.0

## Files
- stt-engine-${IMAGE_VERSION}.tar.gz (Docker image archive)
- BUILD_IMAGE_INFO.txt (This file)

## Next Steps
1. Verify image locally:
   docker run --rm $IMAGE_TAG python3.11 -c "import torch; print(torch.__version__)"

2. Transfer to production server:
   scp stt-engine-${IMAGE_VERSION}.tar.gz production-server:/tmp/

3. Load on production server:
   docker load < stt-engine-${IMAGE_VERSION}.tar.gz

## Timeline
- Build Start: $(date -r "$BUILD_LOG" 2>/dev/null || echo "N/A")
- Build End: $(date)

EOF
    
    log_success "빌드 정보 저장됨"
    
    log_info "생성된 파일:"
    ls -lh "$OUTPUT_DIR/" | tail -5
    
    print_elapsed
}

# ============================================================================
# 최종 요약
# ============================================================================

print_summary() {
    log_step "Final" "빌드 완료"
    
    echo ""
    echo "✅ Docker 이미지 빌드 완료!"
    echo ""
    echo "📊 빌드 결과:"
    
    # Docker 이미지 확인
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$IMAGE_TAG$"; then
        local image_size=$(docker images "$IMAGE_TAG" --format "{{.Size}}")
        echo "   이미지: $IMAGE_TAG"
        echo "   크기: $image_size"
    fi
    
    echo ""
    echo "📝 로그 파일: $BUILD_LOG"
    echo ""
    
    echo "🎯 다음 단계:"
    echo "   1. 모델 준비 (아직 실행하지 않았다면):"
    echo "      bash scripts/ec2_prepare_model.sh"
    echo ""
    echo "   2. 이미지 기본 검증 (모델 없이):"
    echo "      docker run --rm $IMAGE_TAG python3.11 -c \"import torch; print('✓ PyTorch OK')\""
    echo ""
    echo "   3. 이미지 태그 변경 (선택사항):"
    echo "      docker tag $IMAGE_TAG stt-engine:latest"
    echo ""
    echo "   4. 이미지 저장 (선택사항):"
    echo "      docker save $IMAGE_TAG | gzip > stt-engine-${IMAGE_VERSION}.tar.gz"
    echo ""
    
    print_elapsed
}

# ============================================================================
# 에러 처리
# ============================================================================

trap 'log_error "빌드 중 오류 발생. 로그를 확인하세요: $BUILD_LOG"' ERR

# ============================================================================
# 메인 실행
# ============================================================================

main() {
    log_header "🚀 STT Engine Docker 이미지 빌드 (RHEL 8.9)"
    
    log_info "작업공간: $WORKSPACE"
    log_info "출력 디렉토리: $OUTPUT_DIR"
    log_info "로그 파일: $BUILD_LOG"
    
    # 사전 확인
    check_prerequisites
    
    # 기존 이미지 확인
    skip_build=$(check_existing_image)
    
    if [ "$skip_build" = "SKIP_BUILD=1" ]; then
        log_info "이미지 빌드 건너뜀"
        print_summary
        return 0
    fi
    
    # Docker 빌드
    build_docker_image
    
    # 이미지 저장
    save_image
    
    # 최종 요약
    print_summary
}

# 스크립트 실행
main "$@"
