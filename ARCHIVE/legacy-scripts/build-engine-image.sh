#!/bin/bash
# ============================================================================
# STT Engine Docker Image Builder
#
# 목적: Docker 이미지를 빌드하고 tar 파일로 저장
# 사용법: bash scripts/build-engine-image.sh
#
# 기능:
# - Wheel 자동 감지
# - 온/오프라인 설치 자동 선택
# - Docker 이미지 빌드
# - tar 파일로 저장 (build/output/)
# ============================================================================

set -e

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHEELS_DIR="$WORKSPACE/deployment_package/wheels"
BUILD_DIR="/tmp/stt_engine_docker"
OUTPUT_DIR="$WORKSPACE/build/output"

echo "════════════════════════════════════════════════════════════"
echo "🐳 STT Engine Docker Image Builder"
echo "════════════════════════════════════════════════════════════"

# Step 1: Wheel 디렉토리 확인
echo ""
echo "Step 1: Checking wheels..."
WHEEL_COUNT=$(find "$WHEELS_DIR" -maxdepth 1 -name "*.whl" -type f 2>/dev/null | wc -l)

if [ $WHEEL_COUNT -eq 0 ]; then
    echo "⚠️  No wheels found - will use online installation"
    USE_WHEELS=false
else
    echo "✅ Found $WHEEL_COUNT wheel files"
    echo "   Location: $WHEELS_DIR"
    echo "   Size: $(du -sh "$WHEELS_DIR" 2>/dev/null | awk '{print $1}' || echo 'N/A')"
    USE_WHEELS=true
fi

# Step 2: Dockerfile 생성
echo ""
echo "Step 2: Creating Dockerfile..."

mkdir -p "$BUILD_DIR"

if [ "$USE_WHEELS" = true ]; then
    # Offline 모드
    cat > "$BUILD_DIR/Dockerfile" << 'EOF'
FROM --platform=linux/amd64 python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy wheel files
COPY wheels/ /wheels/

# Install packages from wheels (offline)
RUN python3.11 -m pip install --upgrade pip && \
    python3.11 -m pip install --no-index --find-links=/wheels/ \
    torch torchaudio faster-whisper \
    librosa scipy numpy fastapi uvicorn \
    requests pydantic huggingface-hub python-dotenv pyyaml && \
    rm -rf /wheels/

# Copy application files
COPY api_server.py stt_engine.py requirements.txt /app/

# Create directories
RUN mkdir -p /app/models /app/logs /app/audio

# Set environment
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/models

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Expose port
EXPOSE 8003

# Start API server
CMD ["python3.11", "api_server.py"]
EOF
else
    # Online 모드
    cat > "$BUILD_DIR/Dockerfile" << 'EOF'
FROM --platform=linux/amd64 python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python3.11 -m pip install --upgrade pip setuptools wheel

# Set working directory
WORKDIR /app

# Copy application files
COPY api_server.py stt_engine.py requirements.txt /app/

# Install Python dependencies (online from PyPI)
RUN python3.11 -m pip install \
    torch==2.1.2 \
    torchaudio==2.1.2 \
    faster-whisper==1.0.3 \
    librosa==0.10.0 \
    scipy==1.12.0 \
    numpy==1.24.3 \
    huggingface-hub==0.21.4 \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    requests==2.31.0 \
    pydantic==2.5.3 \
    python-dotenv==1.0.0 \
    pyyaml==6.0.1

# Create directories
RUN mkdir -p /app/models /app/logs /app/audio

# Set environment
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/models

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Expose port
EXPOSE 8003

# Start API server
CMD ["python3.11", "api_server.py"]
EOF
fi

echo "✅ Dockerfile created (MODE=$([ "$USE_WHEELS" = true ] && echo "OFFLINE" || echo "ONLINE"))"

# Step 3: 빌드 컨텍스트 준비
echo ""
echo "Step 3: Preparing build context..."

if [ "$USE_WHEELS" = true ]; then
    cp -r "$WHEELS_DIR" "$BUILD_DIR/"
fi
cp "$WORKSPACE/api_server.py" "$BUILD_DIR/" 2>/dev/null || true
cp "$WORKSPACE/stt_engine.py" "$BUILD_DIR/" 2>/dev/null || true
cp "$WORKSPACE/requirements.txt" "$BUILD_DIR/" 2>/dev/null || true

echo "✅ Build context ready"

# Step 4: Docker 이미지 빌드
echo ""
echo "Step 4: Building Docker image (stt-engine:linux-x86_64)..."
echo "    This may take 15-30 minutes on first build..."

docker build --platform=linux/amd64 \
    -t stt-engine:linux-x86_64 \
    -f "$BUILD_DIR/Dockerfile" \
    "$BUILD_DIR" 2>&1 | tail -100

echo "✅ Docker image built"

# Step 5: 이미지 저장
echo ""
echo "Step 5: Saving Docker image to tar..."

mkdir -p "$OUTPUT_DIR"
SAVE_PATH="$OUTPUT_DIR/stt-engine-linux-x86_64.tar"

docker save stt-engine:linux-x86_64 -o "$SAVE_PATH"

echo "✅ Image saved"
echo "   Path: $SAVE_PATH"
echo "   Size: $(du -sh "$SAVE_PATH" 2>/dev/null | awk '{print $1}' || echo 'N/A')"

# 정리
rm -rf "$BUILD_DIR"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ BUILD COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📦 Next steps:"
echo ""
echo "1️⃣  Transfer to Linux server:"
echo "    scp $SAVE_PATH user@server:/tmp/"
echo "    scp -r $WORKSPACE/deployment_package/ user@server:/home/user/"
echo ""
echo "2️⃣  Load on server:"
echo "    docker load -i /tmp/stt-engine-linux-x86_64.tar"
echo ""
echo "3️⃣  Run container:"
echo "    docker run -p 8003:8003 stt-engine:linux-x86_64"
echo ""
echo "Or use deployment_package:"
echo "    cd /home/user/deployment_package && ./deploy.sh"
echo ""
