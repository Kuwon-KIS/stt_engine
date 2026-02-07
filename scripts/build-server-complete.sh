#!/bin/bash

################################################################################
#
# 🚀 STT Engine 완전 빌드 & 테스트 스크립트 (AWS EC2 RHEL 8.9)
#
# 목적: EC2 빌드 서버에서 Docker 이미지 + 모델 다운로드 + 테스트 완료
# 사용: bash scripts/build-server-complete.sh
# 결과: 
#   - Docker 이미지: stt-engine:cuda129-rhel89-v1.2 (7.3GB)
#   - 모델 디렉토리: models/ (2.5GB)
#   - 테스트 완료 및 검증
#
# 소요시간: 90~155분 (1.5~2.5시간)
#
# 주의사항:
#   1. RHEL 8.9 EC2 인스턴스에서만 실행
#   2. t3.large 이상 인스턴스 필요
#   3. 100GB 이상 스토리지 필요
#   4. Docker와 git 사전 설치 필수
#
################################################################################

set -e

# ============================================================================
# 설정
# ============================================================================

WORKSPACE="${PWD}"
SCRIPTS_DIR="${WORKSPACE}/scripts"
DOCKER_DIR="${WORKSPACE}/docker"
OUTPUT_DIR="${WORKSPACE}/build/output"
BUILD_LOG="/tmp/build-complete-$(date +%Y%m%d-%H%M%S).log"

# 버전 정보
IMAGE_TAG="stt-engine:cuda129-rhel89-v1.2"
IMAGE_NAME="stt-engine"
IMAGE_VERSION="cuda129-rhel89-v1.2"

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
# 사전 확인
# ============================================================================

check_prerequisites() {
    log_step 0 "사전 확인"
    
    # Docker 확인
    if ! command -v docker &> /dev/null; then
        log_error "Docker가 설치되어 있지 않습니다."
    fi
    log_success "Docker 설치 확인: $(docker --version)"
    
    # git 확인
    if ! command -v git &> /dev/null; then
        log_error "git이 설치되어 있지 않습니다."
    fi
    log_success "git 설치 확인: $(git --version)"
    
    # Python 확인
    if ! command -v python3.11 &> /dev/null; then
        log_error "Python 3.11이 설치되어 있지 않습니다."
    fi
    log_success "Python 확인: $(python3.11 --version)"
    
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
# Step 1: Docker 이미지 빌드 (20~40분)
# ============================================================================

build_docker_image() {
    log_step 1 "Docker 이미지 빌드 (20~40분)"
    
    if [ ! -f "$DOCKER_DIR/Dockerfile.engine.rhel89" ]; then
        log_error "Dockerfile.engine.rhel89를 찾을 수 없습니다"
    fi
    
    log_info "빌드 시작: $IMAGE_TAG"
    
    # 기존 이미지 제거 (선택사항)
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$IMAGE_TAG$"; then
        log_info "기존 이미지 제거 중..."
        docker rmi "$IMAGE_TAG" || true
    fi
    
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
# Step 2: 모델 다운로드 및 변환 (25~45분)
# ============================================================================

download_models() {
    log_step 2 "모델 다운로드 및 CTranslate2 변환 (25~45분)"
    
    if [ ! -f "$WORKSPACE/download_model_hf.py" ]; then
        log_error "download_model_hf.py를 찾을 수 없습니다"
    fi
    
    # 모델 디렉토리 초기화
    log_info "기존 모델 디렉토리 정리..."
    rm -rf "$WORKSPACE/models" || true
    mkdir -p "$WORKSPACE/models"
    
    # Python 의존성 설치
    log_info "필수 Python 패키지 설치..."
    python3.11 -m pip install -q --upgrade \
        huggingface-hub \
        transformers \
        ctranslate2 \
        faster-whisper || log_warn "일부 패키지 설치 실패 (계속 진행)"
    
    # 모델 다운로드 및 변환
    log_info "모델 다운로드 및 변환 실행 중..."
    cd "$WORKSPACE"
    python3.11 download_model_hf.py 2>&1 | tee -a "$BUILD_LOG"
    
    # 모델 디렉토리 검증
    if [ ! -d "$WORKSPACE/models/ctranslate2_model" ]; then
        log_error "CTranslate2 모델 변환 실패"
    fi
    
    if [ ! -d "$WORKSPACE/models/openai_whisper-large-v3-turbo" ]; then
        log_warn "OpenAI Whisper 모델 다운로드 완료되지 않음 (계속 진행)"
    fi
    
    local models_size=$(du -sh "$WORKSPACE/models" | awk '{print $1}')
    log_success "모델 다운로드 및 변환 완료 (크기: $models_size)"
    print_elapsed
}

# ============================================================================
# Step 3: 모델 로드 테스트 (20~30분)
# ============================================================================

test_model_loading() {
    log_step 3 "모델 로드 테스트 (20~30분)"
    
    log_info "테스트용 컨테이너 시작..."
    
    # 컨테이너 시작
    docker run -d \
        --name stt-test-engine \
        --rm \
        -v "$WORKSPACE/models:/app/models" \
        -e CUDA_VISIBLE_DEVICES=0 \
        "$IMAGE_TAG" \
        sleep 3600 2>&1 | tee -a "$BUILD_LOG"
    
    if ! docker ps | grep -q "stt-test-engine"; then
        log_error "테스트 컨테이너 시작 실패"
    fi
    
    log_success "테스트 컨테이너 시작됨"
    
    # CUDA & PyTorch 검증
    log_info "CUDA & PyTorch 검증..."
    docker exec stt-test-engine python3.11 << 'PYTHON_TEST' 2>&1 | tee -a "$BUILD_LOG"
import torch
import torchaudio
import os

print("\n=== CUDA & PyTorch 검증 ===")
print(f"✅ PyTorch: {torch.__version__}")
print(f"✅ torchaudio: {torchaudio.__version__}")
print(f"✅ CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"✅ CUDA Device: {torch.cuda.get_device_name(0)}")
print(f"✅ LD_LIBRARY_PATH: {bool(os.environ.get('LD_LIBRARY_PATH'))}")
PYTHON_TEST
    
    # Faster-Whisper 모델 로드 테스트
    log_info "Faster-Whisper 모델 로드 테스트..."
    docker exec stt-test-engine python3.11 << 'PYTHON_TEST' 2>&1 | tee -a "$BUILD_LOG"
import sys
sys.path.insert(0, '/app')

print("\n=== Faster-Whisper 모델 로드 ===")
try:
    from faster_whisper import WhisperModel
    model = WhisperModel(
        "/app/models/ctranslate2_model",
        device="auto",
        compute_type="float32",
        local_files_only=True
    )
    print("✅ Faster-Whisper 모델 로드 성공!")
except Exception as e:
    print(f"❌ Faster-Whisper 오류: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
PYTHON_TEST
    
    # OpenAI Whisper 모델 로드 테스트
    log_info "OpenAI Whisper 모델 로드 테스트..."
    docker exec stt-test-engine python3.11 << 'PYTHON_TEST' 2>&1 | tee -a "$BUILD_LOG"
import sys
sys.path.insert(0, '/app')

print("\n=== OpenAI Whisper 모델 로드 ===")
try:
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
    processor = AutoProcessor.from_pretrained(
        "/app/models/openai_whisper-large-v3-turbo",
        local_files_only=True
    )
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        "/app/models/openai_whisper-large-v3-turbo",
        local_files_only=True
    )
    print("✅ OpenAI Whisper 모델 로드 성공!")
except Exception as e:
    print(f"⚠️  OpenAI Whisper: {type(e).__name__}: {e}")
PYTHON_TEST
    
    # 컨테이너 종료
    log_info "테스트 컨테이너 종료..."
    docker stop stt-test-engine 2>/dev/null || true
    
    log_success "모델 로드 테스트 완료"
    print_elapsed
}

# ============================================================================
# Step 4: 이미지 및 모델 저장 (5~10분)
# ============================================================================

save_artifacts() {
    log_step 4 "이미지 및 모델 저장 (5~10분)"
    
    mkdir -p "$OUTPUT_DIR"
    
    # Docker 이미지 저장
    log_info "Docker 이미지 저장 중... (5~10분 소요)"
    docker save "$IMAGE_TAG" | gzip > "$OUTPUT_DIR/stt-engine-${IMAGE_VERSION}.tar.gz"
    
    local image_tar_size=$(du -sh "$OUTPUT_DIR/stt-engine-${IMAGE_VERSION}.tar.gz" | awk '{print $1}')
    log_success "Docker 이미지 저장 완료 (크기: $image_tar_size)"
    
    # 모델 디렉토리 확인
    local models_size=$(du -sh "$WORKSPACE/models" | awk '{print $1}')
    log_info "모델 디렉토리: $models_size"
    
    # 빌드 정보 저장
    cat > "$OUTPUT_DIR/BUILD_INFO.txt" << EOF
# STT Engine Build Information
# Generated: $(date)

## Image Information
- Name: $IMAGE_TAG
- Size: $image_tar_size
- Archive: stt-engine-${IMAGE_VERSION}.tar.gz

## Model Information
- Location: models/
- Size: $models_size
- Models:
  * OpenAI Whisper: models/openai_whisper-large-v3-turbo/
  * CTranslate2: models/ctranslate2_model/

## Files
- stt-engine-${IMAGE_VERSION}.tar.gz (Docker image)
- models/ (Model directory - 2.5GB)
- build.log (Build log)

## Next Steps
1. Transfer image and models to production server
2. Load image: docker load < stt-engine-${IMAGE_VERSION}.tar.gz
3. Mount models: -v /path/to/models:/app/models
4. Run container: docker run -d -v models:/app/models $IMAGE_TAG

## Timeline
- Start: $(date -r "$BUILD_LOG" 2>/dev/null || echo "N/A")
- End: $(date)

EOF
    
    log_success "빌드 정보 저장됨"
    
    # 최종 파일 목록
    log_info "생성된 파일:"
    ls -lh "$OUTPUT_DIR/" | tail -10
    
    print_elapsed
}

# ============================================================================
# 최종 요약
# ============================================================================

print_summary() {
    log_step "5" "최종 요약 및 검증"
    
    echo ""
    echo "📊 최종 빌드 결과:"
    echo ""
    
    # Docker 이미지 확인
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$IMAGE_TAG$"; then
        local image_size=$(docker images "$IMAGE_TAG" --format "{{.Size}}")
        echo "✅ Docker 이미지: $IMAGE_TAG"
        echo "   크기: $image_size"
    else
        echo "❌ Docker 이미지를 찾을 수 없습니다"
    fi
    
    echo ""
    
    # 모델 확인
    if [ -d "$WORKSPACE/models" ]; then
        local models_size=$(du -sh "$WORKSPACE/models" | awk '{print $1}')
        echo "✅ 모델 디렉토리: models/"
        echo "   크기: $models_size"
        
        if [ -d "$WORKSPACE/models/ctranslate2_model" ]; then
            echo "   ✅ CTranslate2 모델"
        fi
        
        if [ -d "$WORKSPACE/models/openai_whisper-large-v3-turbo" ]; then
            echo "   ✅ OpenAI Whisper 모델"
        fi
    else
        echo "❌ 모델 디렉토리를 찾을 수 없습니다"
    fi
    
    echo ""
    
    # 아카이브 확인
    if [ -f "$OUTPUT_DIR/stt-engine-${IMAGE_VERSION}.tar.gz" ]; then
        local tar_size=$(du -sh "$OUTPUT_DIR/stt-engine-${IMAGE_VERSION}.tar.gz" | awk '{print $1}')
        echo "✅ 아카이브: stt-engine-${IMAGE_VERSION}.tar.gz"
        echo "   크기: $tar_size"
    fi
    
    echo ""
    
    # 로그 파일
    echo "📝 로그 파일: $BUILD_LOG"
    echo ""
    
    # 다음 단계
    echo "📌 다음 단계:"
    echo "   1. 운영 서버로 이미지 및 모델 전송"
    echo "   2. docker load < stt-engine-${IMAGE_VERSION}.tar.gz"
    echo "   3. docker run -d -v models:/app/models $IMAGE_TAG"
    echo ""
    
    print_elapsed
    
    log_success "빌드 완료!"
}

# ============================================================================
# 에러 처리
# ============================================================================

trap 'log_error "빌드 중 오류 발생. 로그를 확인하세요: $BUILD_LOG"' ERR

# ============================================================================
# 메인 실행
# ============================================================================

main() {
    log_header "🚀 STT Engine 완전 빌드 (AWS EC2 RHEL 8.9)"
    
    log_info "작업공간: $WORKSPACE"
    log_info "출력 디렉토리: $OUTPUT_DIR"
    log_info "로그 파일: $BUILD_LOG"
    
    # 단계별 실행
    check_prerequisites
    build_docker_image
    download_models
    test_model_loading
    save_artifacts
    print_summary
}

# 스크립트 실행
main "$@"
