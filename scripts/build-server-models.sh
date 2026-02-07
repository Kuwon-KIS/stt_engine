#!/bin/bash

################################################################################
#
# 📦 STT Engine 모델 다운로드 & 검증 스크립트 (AWS EC2 RHEL 8.9)
#
# 목적: 모델 다운로드, CTranslate2 변환, 로드 테스트 (Docker 이미지 빌드 제외)
# 사용: bash scripts/build-server-models.sh
# 결과: models/ 디렉토리 (2.5GB), 검증 완료
#
# 소요시간: 50~90분 (Python 환경 포함)
#
# 선행조건:
#   1. Docker 이미지 빌드 완료: stt-engine:cuda129-rhel89-v1.2
#   2. RHEL 8.9 EC2 인스턴스
#   3. 인터넷 연결
#
################################################################################

set -e

# ============================================================================
# 설정
# ============================================================================

WORKSPACE="${PWD}"
OUTPUT_DIR="${WORKSPACE}/build/output"
BUILD_LOG="/tmp/build-models-$(date +%Y%m%d-%H%M%S).log"

# 버전 정보
IMAGE_TAG="stt-engine:cuda129-rhel89-v1.2"
PYTHON_BIN="python3.11"

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
    log_success "Docker 설치 확인"
    
    # Docker 이미지 확인
    if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$IMAGE_TAG$"; then
        log_error "Docker 이미지를 찾을 수 없습니다: $IMAGE_TAG"
    fi
    log_success "Docker 이미지 확인: $IMAGE_TAG"
    
    # 디스크 공간 확인 (50GB)
    available=$(df "$WORKSPACE" | tail -1 | awk '{print $4}')
    if [ "$available" -lt 51200000 ]; then
        log_warn "디스크 공간 부족 (필요: 50GB, 현재: $(($available / 1024 / 1024))GB)"
    else
        log_success "디스크 공간 확인: $(($available / 1024 / 1024))GB"
    fi
    
    # 인터넷 연결 확인
    if ! ping -c 1 8.8.8.8 &> /dev/null 2>&1; then
        log_error "인터넷 연결이 없습니다"
    fi
    log_success "인터넷 연결 확인: OK"
}

# ============================================================================
# Python 환경 설정 (환경 체크 포함)
# ============================================================================

setup_python_environment() {
    log_step 1 "Python 환경 설정 (5~15분)"
    
    # Python 확인
    if ! command -v $PYTHON_BIN &> /dev/null; then
        log_error "Python 3.11이 설치되어 있지 않습니다"
    fi
    log_success "Python 3.11 확인"
    
    # ============================================================================
    # 1. pip 확인 및 설치
    # ============================================================================
    
    log_info "pip 확인 중..."
    if ! $PYTHON_BIN -m pip --version &>/dev/null; then
        log_warn "pip이 설치되지 않았습니다. 설치 중..."
        
        # RHEL/CentOS 시도
        if command -v yum &> /dev/null; then
            log_info "yum으로 python3.11-pip 설치 중..."
            sudo yum install -y python3.11-pip || true
        fi
        
        # 여전히 없으면 ensurepip 사용
        if ! $PYTHON_BIN -m pip --version &>/dev/null; then
            log_info "ensurepip로 pip 설치 중..."
            $PYTHON_BIN -m ensurepip --upgrade
        fi
    fi
    
    pip_version=$($PYTHON_BIN -m pip --version | awk '{print $2}')
    log_success "pip 확인: v$pip_version"
    
    # ============================================================================
    # 2. 이미 설치된 패키지 확인
    # ============================================================================
    
    log_info "설치된 패키지 확인 중..."
    
    # 핵심 패키지 목록 (호환성 버전)
    declare -A packages=(
        ["torch"]="torch==2.6.0"
        ["torchaudio"]="torchaudio==2.6.0"
        ["transformers"]="transformers>=4.37.0"
        ["ctranslate2"]="ctranslate2>=4.0.0,<5.0.0"
        ["faster_whisper"]="faster-whisper>=0.10.0,<1.0.0"
        ["huggingface_hub"]="huggingface-hub>=0.20.0"
    )
    
    missing_packages=()
    
    for pkg_import in "${!packages[@]}"; do
        if ! $PYTHON_BIN -c "import $pkg_import" 2>/dev/null; then
            missing_packages+=("${packages[$pkg_import]}")
        fi
    done
    
    if [ ${#missing_packages[@]} -eq 0 ]; then
        log_success "모든 필수 패키지 이미 설치됨"
        return 0
    fi
    
    # ============================================================================
    # 3. pip 업그레이드
    # ============================================================================
    
    log_info "pip 업그레이드 중..."
    $PYTHON_BIN -m pip install --upgrade pip setuptools wheel -q 2>&1 | grep -v "already satisfied" || true
    
    # ============================================================================
    # 4. 누락된 패키지 설치
    # ============================================================================
    
    log_warn "누락된 패키지: ${missing_packages[*]}"
    log_info "패키지 설치 중... (5~15분 소요)"
    
    # 핵심 라이브러리 먼저 설치
    $PYTHON_BIN -m pip install --upgrade -q \
        setuptools wheel urllib3 requests
    
    # PyTorch 설치 (오래 걸림)
    log_info "PyTorch 설치 중... (3~8분)"
    $PYTHON_BIN -m pip install --upgrade -q \
        torch==2.6.0 torchaudio==2.6.0
    
    # 모델 처리 라이브러리
    log_info "모델 처리 라이브러리 설치 중..."
    $PYTHON_BIN -m pip install --upgrade -q \
        'transformers>=4.37.0' 'ctranslate2>=4.0.0,<5.0.0' 'faster-whisper>=0.10.0,<1.0.0' \
        'huggingface-hub>=0.20.0' scipy numpy librosa pydantic 2>&1 | tail -3
    
    log_success "Python 패키지 설치 완료"
}

# ============================================================================
# Step 2: 모델 다운로드 및 변환 (20~30분)
# ============================================================================

download_models() {
    log_step 2 "모델 다운로드 및 CTranslate2 변환 (20~30분)"
    
    if [ ! -f "$WORKSPACE/download_model_hf.py" ]; then
        log_error "download_model_hf.py를 찾을 수 없습니다"
    fi
    
    # 모델 디렉토리 초기화 (선택사항)
    if [ -d "$WORKSPACE/models" ]; then
        log_warn "기존 모델 디렉토리가 있습니다"
        log_info "옵션:"
        log_info "  1. 기존 모델 사용 (엔터 누르기)"
        log_info "  2. 새로 다운로드 (rebuild 입력)"
        
        read -p "선택 (기본: 사용): " choice
        
        if [ "$choice" = "rebuild" ]; then
            log_info "기존 모델 디렉토리 삭제 중..."
            rm -rf "$WORKSPACE/models" || true
        else
            log_info "기존 모델 사용"
            # 모델 검증만 수행
            validate_models
            return 0
        fi
    fi
    
    mkdir -p "$WORKSPACE/models"
    
    # 모델 다운로드 및 변환 실행
    log_info "모델 다운로드 및 변환 실행 중..."
    cd "$WORKSPACE"
    $PYTHON_BIN download_model_hf.py 2>&1 | tee -a "$BUILD_LOG"
    
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
# Step 3: 모델 검증
# ============================================================================

validate_models() {
    log_step 3 "모델 구조 검증"
    
    log_info "모델 파일 구조 확인 중..."
    $PYTHON_BIN << 'PYTHON_TEST'
from pathlib import Path
import sys

models_base = Path("models")
all_valid = True

print("\n" + "=" * 70)
print("🔍 모델 구조 검증")
print("=" * 70)

# CTranslate2 모델 확인
print("\n📂 CTranslate2 모델")
ct2_model = models_base / "ctranslate2_model"
required_files = {
    "config.json": "설정 파일",
    "model.bin": "모델 가중치",
    "vocabulary.json": "토크나이저 어휘"
}

for fname, desc in required_files.items():
    fpath = ct2_model / fname
    if fpath.exists():
        size = fpath.stat().st_size / (1024 * 1024)
        print(f"   ✅ {fname:20} ({size:6.1f} MB) - {desc}")
    else:
        print(f"   ❌ {fname:20} NOT FOUND")
        all_valid = False

# OpenAI Whisper 모델 확인
print("\n📂 OpenAI Whisper 모델")
whisper_model = models_base / "openai_whisper-large-v3-turbo"
required_whisper_files = {
    "config.json": "설정 파일",
    "pytorch_model.bin": "모델 가중치",
    "tokenizer.json": "토크나이저"
}

for fname, desc in required_whisper_files.items():
    fpath = whisper_model / fname
    if fpath.exists():
        size = fpath.stat().st_size / (1024 * 1024)
        print(f"   ✅ {fname:25} ({size:6.1f} MB) - {desc}")
    else:
        print(f"   ❌ {fname:25} NOT FOUND")
        all_valid = False

print("\n" + "=" * 70)

if all_valid:
    print("✅ 모든 모델 파일 검증 완료!")
    sys.exit(0)
else:
    print("❌ 일부 모델 파일이 누락되었습니다")
    sys.exit(1)

PYTHON_TEST
    
    if [ $? -ne 0 ]; then
        log_error "모델 검증 실패"
    fi
    
    log_success "모델 구조 검증 완료"
}

# ============================================================================
# Step 4: 모델 로드 테스트 (20~30분)
# ============================================================================

test_model_loading() {
    log_step 4 "Docker 컨테이너에서 모델 로드 테스트 (20~30분)"
    
    log_info "테스트용 컨테이너 시작 중..."
    
    # 기존 컨테이너 정리
    docker rm stt-test-engine 2>/dev/null || true
    
    # 컨테이너 시작
    docker run -d \
        --name stt-test-engine \
        -v "$WORKSPACE/models:/app/models" \
        -e CUDA_VISIBLE_DEVICES=0 \
        "$IMAGE_TAG" \
        sleep 3600 2>&1 | tee -a "$BUILD_LOG"
    
    if ! docker ps | grep -q "stt-test-engine"; then
        log_error "테스트 컨테이너 시작 실패"
    fi
    
    log_success "테스트 컨테이너 시작됨"
    
    # 잠시 대기 (컨테이너 초기화)
    sleep 3
    
    # CUDA & PyTorch 검증
    log_info "CUDA & PyTorch 검증 중..."
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
    log_info "Faster-Whisper 모델 로드 테스트 중..."
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
    log_info "OpenAI Whisper 모델 로드 테스트 중..."
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
    log_info "테스트 컨테이너 종료 중..."
    docker rm -f stt-test-engine 2>/dev/null || true
    
    log_success "모델 로드 테스트 완료"
    print_elapsed
}

# ============================================================================
# Step 5: 결과 저장 및 요약
# ============================================================================

print_summary() {
    log_step "Final" "모델 준비 완료"
    
    echo ""
    echo "✅ 모델 다운로드 및 검증 완료!"
    echo ""
    echo "📊 결과:"
    
    # 모델 확인
    if [ -d "$WORKSPACE/models" ]; then
        local models_size=$(du -sh "$WORKSPACE/models" | awk '{print $1}')
        echo "   모델 디렉토리: $WORKSPACE/models"
        echo "   크기: $models_size"
        
        if [ -d "$WORKSPACE/models/ctranslate2_model" ]; then
            echo "   ✅ CTranslate2 모델"
        fi
        
        if [ -d "$WORKSPACE/models/openai_whisper-large-v3-turbo" ]; then
            echo "   ✅ OpenAI Whisper 모델"
        fi
    fi
    
    echo ""
    echo "📝 로그 파일: $BUILD_LOG"
    echo ""
    
    echo "🎯 다음 단계:"
    echo "   1. 이미지와 모델을 운영 서버로 전송"
    echo "   2. 운영 서버에서 Docker 이미지 로드"
    echo "   3. 모델 디렉토리 마운트하여 컨테이너 실행"
    echo ""
    
    print_elapsed
}

# ============================================================================
# 에러 처리
# ============================================================================

trap 'log_error "실행 중 오류 발생. 로그를 확인하세요: $BUILD_LOG"' ERR

# ============================================================================
# 메인 실행
# ============================================================================

main() {
    log_header "📦 STT Engine 모델 다운로드 & 검증 (RHEL 8.9)"
    
    log_info "작업공간: $WORKSPACE"
    log_info "로그 파일: $BUILD_LOG"
    
    # 사전 확인
    check_prerequisites
    
    # Python 환경 설정
    setup_python_environment
    
    # 모델 다운로드
    download_models
    
    # 모델 검증
    validate_models
    
    # 모델 로드 테스트
    test_model_loading
    
    # 최종 요약
    print_summary
}

# 스크립트 실행
main "$@"
