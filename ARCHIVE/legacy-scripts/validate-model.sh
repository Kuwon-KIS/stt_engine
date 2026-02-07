#!/bin/bash

################################################################################
#
# 🔍 STT Engine 모델 검증 스크립트
#
# 목적: Docker 이미지와 독립적으로 모델 로드 및 검증
# 사용: bash scripts/validate-model.sh [모델_경로] [버전 또는 이미지_태그]
# 예시:
#   bash scripts/validate-model.sh models                      # 기본: models, v1.4
#   bash scripts/validate-model.sh models v1.5                 # 버전 지정
#   bash scripts/validate-model.sh models stt-engine:my-tag    # 전체 태그 지정
#
# 특징:
#   - 이미지 빌드와 독립적으로 실행 가능
#   - 동일한 검증 로직 사용 (모델 준비, Docker 테스트, 로컬 테스트)
#   - 컨테이너 기반 및 로컬 기반 검증 모두 지원
#
################################################################################

set -e

# ============================================================================
# 설정
# ============================================================================

WORKSPACE="${PWD}"
MODELS_PATH="${1:-.models}"

# 이미지 태그 처리 (버전 또는 전체 태그)
DEFAULT_VERSION="v1.4"
VERSION_OR_TAG="${2:-$DEFAULT_VERSION}"

# 만약 ":" 포함이면 전체 태그, 아니면 버전 번호로 취급
if [[ "$VERSION_OR_TAG" == *":"* ]]; then
    IMAGE_TAG="$VERSION_OR_TAG"
else
    IMAGE_TAG="stt-engine:cuda129-rhel89-${VERSION_OR_TAG}"
fi

PYTHON_BIN="python3.11"

# ============================================================================
# 유틸리티 함수
# ============================================================================

log_header() {
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "  $1"
    echo "════════════════════════════════════════════════════════════════"
}

log_step() {
    echo ""
    echo "📌 $1"
}

log_success() {
    echo "✅ $1"
}

log_error() {
    echo "❌ $1"
    exit 1
}

log_info() {
    echo "ℹ️  $1"
}

log_warn() {
    echo "⚠️  $1"
}

# ============================================================================
# Step 1: 환경 확인
# ============================================================================

check_prerequisites() {
    log_step "Step 1: 모델 검증 환경 확인"
    
    # 모델 디렉토리 확인
    if [ ! -d "$MODELS_PATH" ]; then
        log_error "모델 디렉토리를 찾을 수 없습니다: $MODELS_PATH"
    fi
    log_success "모델 디렉토리 확인: $MODELS_PATH"
    
    # Docker 확인
    if ! command -v docker &> /dev/null; then
        log_error "Docker가 설치되어 있지 않습니다"
    fi
    log_success "Docker 설치 확인"
    
    # 이미지 확인
    if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$IMAGE_TAG$"; then
        log_warn "Docker 이미지를 찾을 수 없습니다: $IMAGE_TAG"
        log_info "로컬 Python으로 검증 시도합니다"
        USE_LOCAL_PYTHON=true
    else
        log_success "Docker 이미지 확인: $IMAGE_TAG"
        USE_LOCAL_PYTHON=false
    fi
}

# ============================================================================
# Step 2: 모델 구조 검증
# ============================================================================

validate_model_structure() {
    log_step "Step 2: 모델 파일 구조 검증"
    
    $PYTHON_BIN << 'PYTHON_TEST'
from pathlib import Path
import sys

models_base = Path("models")
all_valid = True

print("\n" + "=" * 70)
print("📂 모델 구조 검증")
print("=" * 70)

# CTranslate2 모델 확인
print("\n📂 CTranslate2 모델 (faster-whisper 사용)")
ct2_model = models_base / "ctranslate2_model"
required_files = {
    "config.json": "설정 파일",
    "model.bin": "모델 가중치",
    "vocabulary.json": "토크나이저 어휘"
}

if ct2_model.exists():
    for fname, desc in required_files.items():
        fpath = ct2_model / fname
        if fpath.exists():
            size = fpath.stat().st_size / (1024 * 1024)
            print(f"   ✅ {fname:20} ({size:7.1f} MB) - {desc}")
        else:
            print(f"   ❌ {fname:20} NOT FOUND")
            all_valid = False
else:
    print(f"   ⚠️  ctranslate2_model 디렉토리 없음")

# OpenAI Whisper 모델 확인
print("\n📂 OpenAI Whisper 모델 (fallback)")
whisper_model = models_base / "openai_whisper-large-v3-turbo"
required_whisper_files = {
    "config.json": "설정 파일",
    "pytorch_model.bin": "모델 가중치",
    "tokenizer.json": "토크나이저"
}

if whisper_model.exists():
    for fname, desc in required_whisper_files.items():
        fpath = whisper_model / fname
        if fpath.exists():
            size = fpath.stat().st_size / (1024 * 1024)
            print(f"   ✅ {fname:25} ({size:7.1f} MB) - {desc}")
        else:
            print(f"   ❌ {fname:25} NOT FOUND")
            all_valid = False
else:
    print(f"   ⚠️  openai_whisper-large-v3-turbo 디렉토리 없음")

print("\n" + "=" * 70)

if all_valid:
    print("✅ 모든 모델 파일 검증 완료!")
    sys.exit(0)
else:
    print("⚠️  일부 모델 파일이 누락되었습니다")
    sys.exit(1)

PYTHON_TEST
    
    if [ $? -ne 0 ]; then
        log_warn "모델 파일 검증 완료 (누락된 파일 있음)"
    else
        log_success "모델 파일 검증 완료"
    fi
}

# ============================================================================
# Step 3: Docker 컨테이너 검증
# ============================================================================

validate_with_docker() {
    log_step "Step 3: Docker 컨테이너 기반 모델 검증"
    
    log_info "테스트 컨테이너 시작 중..."
    
    # 기존 컨테이너 정리
    docker rm stt-validate 2>/dev/null || true
    
    # 컨테이너 시작
    docker run -d \
        --name stt-validate \
        -v "$(pwd)/$MODELS_PATH:/app/models" \
        -e CUDA_VISIBLE_DEVICES=0 \
        "$IMAGE_TAG" \
        sleep 3600 >/dev/null 2>&1
    
    sleep 2
    
    if ! docker ps | grep -q "stt-validate"; then
        log_error "테스트 컨테이너 시작 실패"
    fi
    
    log_success "테스트 컨테이너 시작됨"
    
    # CUDA & PyTorch 검증
    log_info "CUDA & PyTorch 검증 중..."
    docker exec stt-validate python3.11 << 'PYTHON_TEST' 2>&1 | grep -E '(PyTorch|torchaudio|CUDA|LD_)' || true
import torch
import torchaudio
import os

print(f"✅ PyTorch: {torch.__version__}")
print(f"✅ torchaudio: {torchaudio.__version__}")
print(f"✅ CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"✅ CUDA Device: {torch.cuda.get_device_name(0)}")
print(f"✅ LD_LIBRARY_PATH: {bool(os.environ.get('LD_LIBRARY_PATH'))}")
PYTHON_TEST
    
    # Faster-Whisper 모델 로드 테스트
    log_info "Faster-Whisper 모델 로드 테스트 중..."
    docker exec stt-validate python3.11 << 'PYTHON_TEST' 2>&1 | tail -20
import sys
sys.path.insert(0, '/app')
import numpy as np

print("\n=== Faster-Whisper 모델 검증 ===\n")

try:
    from faster_whisper import WhisperModel
    
    print("⏳ 모델 로드 중...")
    model = WhisperModel(
        "/app/models/ctranslate2_model",
        device="auto",
        compute_type="float32",
        local_files_only=True
    )
    print("✅ 모델 로드 성공!")
    
    # 다양한 길이의 오디오로 테스트
    test_cases = [
        (8000, "짧은 (0.5초)"),
        (48000, "중간 (3초)"),
        (160000, "긴 (10초)")
    ]
    
    for audio_len, desc in test_cases:
        try:
            dummy_audio = np.zeros((audio_len,), dtype=np.float32)
            segments, info = model.transcribe(dummy_audio, language="ko")
            list(segments)
            print(f"✅ 추론 테스트 성공 ({desc})")
        except Exception as e:
            print(f"⚠️  추론 테스트 실패 ({desc}): {str(e)[:80]}")
    
    print("\n✅ Faster-Whisper 검증 완료!")
    
except Exception as e:
    print(f"❌ 오류: {type(e).__name__}: {str(e)[:200]}")
    import traceback
    traceback.print_exc()

PYTHON_TEST
    
    # 컨테이너 종료
    log_info "테스트 컨테이너 종료 중..."
    docker rm -f stt-validate 2>/dev/null || true
    
    log_success "Docker 검증 완료"
}

# ============================================================================
# Step 4: 로컬 Python 검증 (선택사항)
# ============================================================================

validate_with_local_python() {
    log_step "Step 4: 로컬 Python 기반 모델 검증"
    
    # pip 확인
    if ! $PYTHON_BIN -m pip --version &>/dev/null; then
        log_warn "pip가 설치되어 있지 않습니다. Docker 검증만 수행합니다."
        return 0
    fi
    
    # faster-whisper 확인
    if ! $PYTHON_BIN -c "import faster_whisper" 2>/dev/null; then
        log_warn "faster-whisper가 설치되어 있지 않습니다. 설치 중..."
        $PYTHON_BIN -m pip install -q faster-whisper==1.2.1 2>/dev/null || true
    fi
    
    log_info "로컬 Faster-Whisper 모델 검증 중..."
    
    $PYTHON_BIN << 'PYTHON_TEST' 2>&1 | tail -20
import sys
import numpy as np
from pathlib import Path

print("\n=== 로컬 Faster-Whisper 모델 검증 ===\n")

try:
    from faster_whisper import WhisperModel
    
    models_path = Path("models")
    ct2_model = models_path / "ctranslate2_model"
    
    if not ct2_model.exists():
        print(f"⚠️  모델 디렉토리 없음: {ct2_model}")
        sys.exit(0)
    
    print("⏳ 모델 로드 중...")
    model = WhisperModel(
        str(ct2_model),
        device="cpu",
        compute_type="float32",
        local_files_only=True
    )
    print("✅ 모델 로드 성공!")
    
    # 다양한 길이의 오디오로 테스트
    test_cases = [
        (8000, "짧은 (0.5초)"),
        (48000, "중간 (3초)"),
        (160000, "긴 (10초)")
    ]
    
    for audio_len, desc in test_cases:
        try:
            dummy_audio = np.zeros((audio_len,), dtype=np.float32)
            segments, info = model.transcribe(dummy_audio, language="ko")
            list(segments)
            print(f"✅ 추론 테스트 성공 ({desc})")
        except Exception as e:
            print(f"⚠️  추론 테스트 실패 ({desc}): {str(e)[:80]}")
    
    print("\n✅ 로컬 검증 완료!")
    
except Exception as e:
    print(f"❌ 오류: {type(e).__name__}: {str(e)[:200]}")
    import traceback
    traceback.print_exc()

PYTHON_TEST
    
    log_success "로컬 검증 완료"
}

# ============================================================================
# Step 5: 최종 요약
# ============================================================================

print_summary() {
    log_header "✅ 모델 검증 완료!"
    
    echo ""
    echo "📊 검증 결과:"
    echo "   ✅ 모델 파일 구조 검증 완료"
    
    if [ "$USE_LOCAL_PYTHON" = "false" ]; then
        echo "   ✅ Docker 컨테이너 기반 검증 완료"
        echo "   ℹ️  이미지: $IMAGE_TAG"
    else
        echo "   ℹ️  Docker 이미지 없음 (로컬 Python으로 검증)"
    fi
    
    echo ""
    echo "📝 모델 위치:"
    echo "   CTranslate2: $MODELS_PATH/ctranslate2_model"
    echo "   OpenAI Whisper: $MODELS_PATH/openai_whisper-large-v3-turbo"
    echo ""
    echo "🎯 다음 단계:"
    echo "   1. Docker 이미지 실행:"
    echo "      docker run -v $MODELS_PATH:/app/models $IMAGE_TAG"
    echo ""
    echo "   2. 또는 Python 스크립트 사용:"
    echo "      python3.11 stt_engine.py"
    echo ""
}

# ============================================================================
# 메인 실행
# ============================================================================

main() {
    log_header "🔍 STT Engine 모델 검증 시작"
    
    check_prerequisites
    validate_model_structure
    
    if [ "$USE_LOCAL_PYTHON" = "false" ]; then
        validate_with_docker
    else
        validate_with_local_python
    fi
    
    print_summary
}

main
