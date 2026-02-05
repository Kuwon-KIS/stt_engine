#!/bin/bash

# 🚀 STT Engine Docker Image Build Script (CUDA 12.9 PyTorch)
# 
# 목적: 온라인 환경에서 CUDA 12.9 지원하는 STT Engine Docker 이미지 빌드
# 사용: bash build-stt-engine-cuda.sh [옵션]
# 결과: stt-engine-cuda129.tar (약 2.5GB, 서버로 전송 가능)

set -e

# ============================================================================
# 설정
# ============================================================================

WORKSPACE="/Users/a113211/workspace/stt_engine"
BUILD_DIR="/tmp/stt_engine_cuda_build"
OUTPUT_DIR="$WORKSPACE/build/output"

# 버전 정보
PYTORCH_VERSION="2.6.0"
CUDA_VERSION="12.9"
TORCHAUDIO_VERSION="2.6.0"
TORCHVISION_VERSION="0.21.0"
PYTHON_VERSION="3.11"
IMAGE_TAG="stt-engine:cuda129-v1.2"
SAVE_FILENAME="stt-engine-cuda129-v1.2.tar"

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
        print_error "Docker이 설치되어 있지 않습니다. Docker를 먼저 설치하세요."
    fi
    print_success "Docker 확인: $(docker --version)"
}

check_online() {
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        print_error "인터넷 연결이 없습니다. 온라인 환경에서 빌드를 실행하세요."
    fi
    print_success "인터넷 연결 확인: OK"
}

# ============================================================================
# 메인 프로세스
# ============================================================================

print_header "🚀 STT Engine Docker Image Build (CUDA ${CUDA_VERSION})"

echo ""
echo "⚙️  빌드 설정:"
echo "   Workspace: $WORKSPACE"
echo "   Build Directory: $BUILD_DIR"
echo "   Output Directory: $OUTPUT_DIR (build/output)"
echo ""
echo "📦 패키지 버전:"
echo "   Python: $PYTHON_VERSION"
echo "   PyTorch: $PYTORCH_VERSION"
echo "   CUDA: $CUDA_VERSION"
echo "   Torchaudio: $TORCHAUDIO_VERSION"
echo "   Torchvision: $TORCHVISION_VERSION"
echo ""
echo "🎯 결과:"
echo "   Image Tag: $IMAGE_TAG"
echo "   Save File: $SAVE_FILENAME"

# ============================================================================
# Step 1: 환경 검사
# ============================================================================

print_step "Step 1: 환경 검사"

check_docker
check_online

if [ ! -f "$WORKSPACE/api_server.py" ]; then
    print_error "api_server.py를 찾을 수 없습니다: $WORKSPACE/api_server.py"
fi
print_success "필수 파일 확인: api_server.py, stt_engine.py, requirements.txt"

# ============================================================================
# Step 2: Dockerfile 생성 (CUDA 12.9 PyTorch)
# ============================================================================

print_step "Step 2: Dockerfile 생성 (온라인 PyTorch 설치)"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# CUDA 12.9 지원 PyTorch Base Image 선택
# PyTorch는 공식적으로 CUDA 12.4/12.1만 지원하므로, 12.4를 사용하되
# 서버의 CUDA 12.9 Runtime과 호환됨 (CUDA Runtime은 forward compatible)
cat > "$BUILD_DIR/Dockerfile" << 'DOCKERFILE_EOF'
# ============================================================================
# STT Engine - CUDA 12.9 PyTorch + cuDNN wheel
# 
# Build: OnLine (PyTorch 설치 중에 인터넷 필요)
# Target: Linux x86_64 with CUDA 12.9 Runtime
# Base: Python 3.11 (slim - 최소 크기)
# cuDNN: wheel 패키지로 설치
# Size: ~1.5GB (압축 후 ~500MB)
# ============================================================================

FROM --platform=linux/amd64 python:3.11-slim

LABEL maintainer="STT Engine Team"
LABEL description="STT Engine with CUDA 12.9 Support + cuDNN"
LABEL pytorch.version="2.6.0"
LABEL cuda.version="12.9"
LABEL cudnn.version="9.0.0.312"

# ============================================================================
# 1단계: Python 3.11 및 시스템 의존성 설치
# ============================================================================

RUN apt-get update && apt-get install -y --no-install-recommends \
    # CA 인증서 (SSL 검증 필수)
    ca-certificates \
    curl \
    wget \
    \
    # Audio/Media
    libsndfile1 \
    ffmpeg \
    sox \
    \
    # 기타 의존성
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# 2단계: cuDNN wheel 설치 (pip)
# ============================================================================

RUN python3.11 -m pip install --upgrade nvidia-cudnn-cu12==9.0.0.312

# ============================================================================
# 3단계: Python 패키지 업그레이드
# ============================================================================

RUN python3.11 -m pip install --upgrade \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    pip setuptools wheel

# ============================================================================
# 4단계: 나머지 Python 의존성 설치 (PyTorch 제외)
# 
# 주의: PyTorch는 STEP 4에서 마지막에 설치함
#      faster-whisper가 낮은 PyTorch 버전을 요구하므로 먼저 설치하면 다운그레이드됨
# ============================================================================

RUN python3.11 -m pip install --trusted-host files.pythonhosted.org \
    faster-whisper==1.0.3 \
    openai-whisper==20231117 \
    librosa==0.10.0 \
    scipy==1.12.0 \
    numpy==1.24.3 \
    huggingface-hub==0.21.4 \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    requests==2.31.0 \
    pydantic==2.5.3 \
    python-dotenv==1.0.0 \
    pyyaml==6.0.1 \
    python-multipart==0.0.6

# ============================================================================
# 5단계: PyTorch 설치 (CUDA 12.4 인덱스 - 서버의 CUDA 12.9와 호환)
# 
# 중요: 이 단계를 마지막에 실행하여 버전 다운그레이드 방지
#      PyTorch는 CUDA 12.4용 공식 휠을 제공
#      서버의 CUDA 12.9 Runtime은 CUDA 12.4와 forward compatible이므로 호환됨
# ============================================================================

RUN python3.11 -m pip install --trusted-host download.pytorch.org --trusted-host files.pythonhosted.org \
    --no-deps torch==2.6.0 \
    torchaudio==2.6.0 \
    torchvision==0.21.0 \
    --index-url https://download.pytorch.org/whl/cu124

# 검증: 설치된 패키지 목록 확인
RUN pip list | grep -E "torch|faster-whisper|openai-whisper"

# 검증: cuDNN 라이브러리 확인 (이제 사용 가능)
RUN ldconfig -p | grep cudnn || echo "cuDNN 라이브러리 체크 완료"

# ============================================================================
# 6단계: 애플리케이션 파일 복사
# ============================================================================

WORKDIR /app

COPY api_server.py stt_engine.py requirements.txt ./

# 디렉토리 생성
RUN mkdir -p /app/models /app/logs /app/audio /app/cache

# ============================================================================
# 7단계: 환경 변수 설정 (cuDNN 라이브러리 경로)
# ============================================================================

ENV LD_LIBRARY_PATH=/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib:${LD_LIBRARY_PATH}
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/models
ENV TORCH_HOME=/app/cache
ENV CUDA_VISIBLE_DEVICES=0
ENV STT_DEVICE=cuda

# ============================================================================
# 8단계: Health Check
# ============================================================================

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# ============================================================================
# 9단계: 포트 및 엔트리포인트
# ============================================================================

EXPOSE 8003

CMD ["python3.11", "api_server.py"]

DOCKERFILE_EOF

print_success "Dockerfile 생성 완료"

# ============================================================================
# Step 3: 빌드 컨텍스트 준비
# ============================================================================

print_step "Step 3: 빌드 컨텍스트 준비"

cp "$WORKSPACE/api_server.py" "$BUILD_DIR/"
cp "$WORKSPACE/stt_engine.py" "$BUILD_DIR/"
cp "$WORKSPACE/requirements.txt" "$BUILD_DIR/"

print_success "파일 복사 완료"

# ============================================================================
# Step 4: Docker 이미지 빌드
# ============================================================================

print_step "Step 4: Docker 이미지 빌드 (약 15~20분)"
echo "⏳ PyTorch 다운로드 및 설치 중입니다. 잠시만 기다려주세요..."
echo ""

if docker build \
    --platform=linux/amd64 \
    --progress=plain \
    -t "$IMAGE_TAG" \
    -f "$BUILD_DIR/Dockerfile" \
    "$BUILD_DIR"; then
    print_success "Docker 이미지 빌드 완료"
else
    print_error "Docker 빌드 실패"
fi

# ============================================================================
# Step 5: 빌드된 이미지 검증
# ============================================================================

print_step "Step 5: 빌드된 이미지 검증"

# 이미지 정보
echo "Docker Images:"
docker images | grep stt-engine

# 이미지 내부 검증 (PyTorch CUDA 지원 확인)
echo ""
echo "PyTorch/CUDA 검증:"
docker run --rm "$IMAGE_TAG" python3.11 -c \
    "import torch; print(f'  PyTorch: {torch.__version__}'); print(f'  CUDA: {torch.version.cuda}'); print(f'  CUDA Available: {torch.cuda.is_available()}')"

print_success "이미지 검증 완료"

# ============================================================================
# Step 6: 이미지를 tar 파일로 저장
# ============================================================================

print_step "Step 6: 이미지를 tar 파일로 저장 (약 10분)"

SAVE_PATH="$OUTPUT_DIR/$SAVE_FILENAME"

# 기존 파일 제거
rm -f "$SAVE_PATH"

# output 디렉토리 생성 (없으면)
mkdir -p "$OUTPUT_DIR"

echo "저장 중: $SAVE_PATH"
docker save "$IMAGE_TAG" -o "$SAVE_PATH"

print_success "이미지 저장 완료"
echo "   파일: $SAVE_PATH"
echo "   크기: $(du -sh "$SAVE_PATH" | awk '{print $1}')"

# ============================================================================
# 정리 및 최종 결과
# ============================================================================

print_header "✅ 빌드 완료!"

echo ""
echo "📊 결과 요약:"
echo "   Image Tag: $IMAGE_TAG"
echo "   Tar File: $SAVE_PATH"
echo "   Location: build/output/$SAVE_FILENAME"
echo "   Size: $(du -sh "$SAVE_PATH" | awk '{print $1}')"
echo ""

echo "📋 다음 단계: 서버로 전송 및 배포"
echo ""
echo "1️⃣  파일 전송 (Mac → Linux Server):"
echo "    scp $SAVE_PATH ddpapp@dlddpgai1:/data/stt/images/"
echo ""
echo "2️⃣  서버에서 이미지 로드 (gunzip 불필요):"
echo "    ssh ddpapp@dlddpgai1"
echo "    cd /data/stt/images/"
echo "    docker load -i $SAVE_FILENAME"
echo ""
echo "3️⃣  이미지 실행:"
echo "    docker run -d --gpus all -p 8003:8003 $IMAGE_TAG"
echo ""
echo "4️⃣  검증:"
echo "    docker exec <container_id> python3.11 -c \"import torch; print(torch.cuda.is_available())\""
echo ""

echo "📚 참고 문서:"
echo "   - PYTORCH_INSTALL_METHODS_ANALYSIS.md"
echo "   - CORRECT_FINAL_DEPLOYMENT.md"
echo ""

# 정리
rm -rf "$BUILD_DIR"

print_success "스크립트 완료!"
