#!/bin/bash
# 빠른 시작: x86_64 wheels를 사용해서 STT engine Docker 이미지 빌드 및 저장

set -e

WORKSPACE="/Users/a113211/workspace/stt_engine"
WHEELS_DIR="$WORKSPACE/deployment_package/wheels"
BUILD_DIR="/tmp/stt_engine_docker"
OUTPUT_DIR="$WORKSPACE"

echo "════════════════════════════════════════════════════════════"
echo "STT Engine Docker Image Build & Save (Linux x86_64)"
echo "════════════════════════════════════════════════════════════"

# Step 1: wheels 디렉토리 확인 (있으면 사용, 없으면 온라인 설치)
echo ""
echo "Step 1: Checking wheels..."
WHEEL_COUNT=$(find "$WHEELS_DIR" -maxdepth 1 -name "*.whl" -type f 2>/dev/null | wc -l)

if [ $WHEEL_COUNT -eq 0 ]; then
    echo "⚠️  No wheels found - will use online installation instead"
    USE_WHEELS=false
else
    echo "✅ Found $WHEEL_COUNT wheel files"
    echo "   Size: $(du -sh $WHEELS_DIR | awk '{print $1}')"
    USE_WHEELS=true
fi

# Step 2: STT Engine Dockerfile 생성 (offline vs online)
echo ""
echo "Step 2: Creating Dockerfile for STT Engine..."

mkdir -p "$BUILD_DIR"

if [ "$USE_WHEELS" = true ]; then
    # Offline 설치 (wheels 사용)
    cat > "$BUILD_DIR/Dockerfile" << 'EOF'
FROM --platform=linux/amd64 python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app directory and user
RUN mkdir -p /app /app/models /app/logs /app/audio && \
    groupadd -g 2000 stt-user 2>/dev/null || true && \
    useradd -m -u 2000 -g 2000 -s /bin/bash stt-user 2>/dev/null || true

# Set working directory
WORKDIR /app

# Copy wheel files
COPY wheels/ /wheels/

# Install packages from wheels (offline)
RUN python3.11 -m pip install --no-index --find-links=/wheels/ \
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
    # Online 설치 (인터넷 사용)
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
COPY --chown=stt-user:stt-user main.py /app/
COPY --chown=stt-user:stt-user api_server.py /app/
COPY --chown=stt-user:stt-user stt_engine.py /app/
COPY --chown=stt-user:stt-user requirements.txt /app/

USER stt-user

# Install Python dependencies (from wheels)
RUN python3.11 -m pip install \
    --no-index \
    --find-links=/wheels \
    torch \
    torchaudio \
    faster-whisper \
    ctranslate2 \
    librosa \
    scipy \
    numpy \
    huggingface-hub \
    transformers \
    fastapi \
    uvicorn \
    requests \
    pydantic \
    python-multipart \
    python-dotenv \
    pyyaml

# Set environment
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/models
ENV STT_DEVICE=cpu

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Expose port
EXPOSE 8003

# Start application (main.py launches api_server.py)
CMD ["python3.11", "main.py"]
EOF
fi

echo "✅ Dockerfile created (USE_WHEELS=$USE_WHEELS)"

# Step 3: 빌드 컨텍스트 준비
echo ""
echo "Step 3: Preparing build context..."
if [ "$USE_WHEELS" = true ]; then
    cp -r "$WHEELS_DIR" "$BUILD_DIR/"
fi
cp "$WORKSPACE/main.py" "$BUILD_DIR/"
cp "$WORKSPACE/api_server.py" "$BUILD_DIR/"
cp "$WORKSPACE/stt_engine.py" "$BUILD_DIR/"
cp "$WORKSPACE/requirements.txt" "$BUILD_DIR/"

echo "✅ Build context ready"

# Step 4: Docker 이미지 빌드
echo ""
echo "Step 4: Building Docker image (stt-engine:linux-x86_64)..."
docker build --platform=linux/amd64 \
    -t stt-engine:linux-x86_64 \
    -f "$BUILD_DIR/Dockerfile" \
    "$BUILD_DIR" 2>&1 | grep -E "Step|Successfully|error" | head -50

echo "✅ Docker image built"

# Step 5: 이미지 저장
echo ""
echo "Step 5: Saving Docker image to tar..."
SAVE_PATH="$OUTPUT_DIR/stt-engine-linux-x86_64.tar"
docker save stt-engine:linux-x86_64 -o "$SAVE_PATH"

echo "✅ Image saved to: $SAVE_PATH"
echo "   Size: $(du -sh $SAVE_PATH | awk '{print $1}')"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "To use on Linux server:"
echo "  1. Transfer: scp stt-engine-linux-x86_64.tar user@server:/tmp/"
echo "  2. Load: docker load -i stt-engine-linux-x86_64.tar"
echo "  3. Run: docker run -p 8003:8003 stt-engine:linux-x86_64"
echo ""
