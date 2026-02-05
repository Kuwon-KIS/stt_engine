#!/bin/bash

# 🚀 운영 서버에서 STT Engine Docker 이미지 로드 및 배포
#
# 사용: bash deploy-image.sh [tar_file_path]
# 예:   bash deploy-image.sh /tmp/stt-engine-cuda129-v1.2.tar.gz

set -e

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

# ============================================================================
# 파라미터 확인
# ============================================================================

TAR_FILE="${1:-.}"

if [ ! -f "$TAR_FILE" ]; then
    print_error "tar.gz 파일을 찾을 수 없습니다: $TAR_FILE"
fi

if [[ ! "$TAR_FILE" =~ \.tar\.gz$ ]]; then
    print_error "유효한 tar.gz 파일이 아닙니다: $TAR_FILE"
fi

# ============================================================================
# 메인 프로세스
# ============================================================================

print_header "🚀 STT Engine Docker 이미지 로드 및 배포"

echo ""
echo "📦 tar 파일: $TAR_FILE"
echo "📊 파일 크기: $(ls -lh "$TAR_FILE" | awk '{print $5}')"

# ============================================================================
# Step 1: Docker 확인
# ============================================================================

print_step "Step 1: Docker 확인"

if ! command -v docker &> /dev/null; then
    print_error "Docker이 설치되어 있지 않습니다"
fi
print_success "Docker: $(docker --version)"

# ============================================================================
# Step 2: MD5 검증 (파일 무결성)
# ============================================================================

print_step "Step 2: 파일 무결성 검증"

MD5_FILE="${TAR_FILE}.md5"

if [ -f "$MD5_FILE" ]; then
    echo "MD5 체크섬 검증 중..."
    if md5sum -c "$MD5_FILE" > /dev/null 2>&1; then
        print_success "MD5 검증 성공"
    else
        print_error "MD5 검증 실패 - 파일이 손상되었을 수 있습니다"
    fi
else
    echo "⚠️  MD5 파일을 찾을 수 없습니다 ($MD5_FILE)"
    echo "   무결성 검증을 건너뜁니다"
fi

# ============================================================================
# Step 3: tar 파일 압축 해제
# ============================================================================

print_step "Step 3: tar 파일 압축 해제"

WORK_DIR=$(mktemp -d)
echo "작업 디렉토리: $WORK_DIR"

echo "압축 해제 중 (2-5분)..."
gunzip -c "$TAR_FILE" > "$WORK_DIR/stt-engine-image.tar"

print_success "압축 해제 완료"
echo "압축 해제 파일: $WORK_DIR/stt-engine-image.tar"

# ============================================================================
# Step 4: 기존 이미지 제거
# ============================================================================

print_step "Step 4: 기존 이미지 정리"

EXISTING=$(docker images | grep "stt-engine:cuda129" | awk '{print $3}')
if [ ! -z "$EXISTING" ]; then
    echo "기존 이미지 제거 중..."
    docker rmi -f $EXISTING || true
fi
print_success "정리 완료"

# ============================================================================
# Step 5: Docker 이미지 로드
# ============================================================================

print_step "Step 5: Docker 이미지 로드"

echo "로드 중 (2-3분)..."
docker load < "$WORK_DIR/stt-engine-image.tar"

print_success "Docker 이미지 로드 완료"

# ============================================================================
# Step 6: 이미지 검증
# ============================================================================

print_step "Step 6: 이미지 검증"

docker images | grep "stt-engine:cuda129" || print_error "이미지를 찾을 수 없습니다"

# PyTorch 검증
echo ""
echo "⏳ PyTorch 및 CUDA 검증 중..."
docker run --rm stt-engine:cuda129-v1.2 python3.11 -c "
import torch
print(f'✅ PyTorch: {torch.__version__}')
print(f'✅ CUDA Available: {torch.cuda.is_available()}')
print(f'✅ cuDNN: OK')
" || print_error "PyTorch 검증 실패"

# Whisper 검증
echo ""
echo "⏳ Whisper 검증 중..."
docker run --rm stt-engine:cuda129-v1.2 python3.11 -c "
try:
    import faster_whisper
    print('✅ faster-whisper: OK')
except:
    print('⚠️  faster-whisper: 미사용')
    
try:
    import whisper
    print('✅ openai-whisper: OK')
except:
    print('⚠️  openai-whisper: 미사용')
"

print_success "이미지 검증 완료"

# ============================================================================
# Step 7: 임시 파일 정리
# ============================================================================

print_step "Step 7: 임시 파일 정리"

rm -rf "$WORK_DIR"
print_success "정리 완료"

# ============================================================================
# Step 8: 최종 요약
# ============================================================================

print_header "✅ 배포 완료!"

echo ""
echo "🎯 다음 단계:"
echo ""
echo "1️⃣  환경 변수 설정:"
echo "   export HF_HOME=/path/to/models"
echo "   export CUDA_VISIBLE_DEVICES=0"
echo ""
echo "2️⃣  모델 다운로드 (처음 1회):"
echo "   docker run -it --rm \\"
echo "     -v \$HF_HOME:/app/models \\"
echo "     stt-engine:cuda129-v1.2 \\"
echo "     python3.11 -c 'import whisper; whisper.load_model(\"large-v3\")'"
echo ""
echo "3️⃣  STT API 서버 실행:"
echo "   docker run -d \\"
echo "     --name stt-api \\"
echo "     --gpus all \\"
echo "     -p 8003:8003 \\"
echo "     -v \$HF_HOME:/app/models \\"
echo "     -e STT_DEVICE=cuda \\"
echo "     stt-engine:cuda129-v1.2"
echo ""
echo "4️⃣  헬스 체크:"
echo "   curl http://localhost:8003/health"
echo ""
echo "✨ 배포 준비 완료!"
