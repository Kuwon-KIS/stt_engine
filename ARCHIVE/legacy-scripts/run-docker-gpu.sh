#!/bin/bash

# STT Engine Docker 실행 스크립트 (GPU + 모델 마운트)
# 모델 자동 변환 지원

echo "🚀 STT Engine Docker 컨테이너 실행..."
echo "=========================================="

MODELS_DIR="/Users/a113211/workspace/stt_engine/models"
CONTAINER_NAME="stt-engine-gpu"
IMAGE_NAME="stt-engine:cuda129-v1.0"

# 컨테이너 중지 및 제거
echo "1️⃣ 기존 컨테이너 정리..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# 모델 파일 확인
echo "2️⃣ 모델 파일 확인..."
if [ ! -f "$MODELS_DIR/model.safetensors" ]; then
    echo "❌ 모델 파일을 찾을 수 없습니다: $MODELS_DIR/model.safetensors"
    exit 1
fi
echo "✅ 모델 파일 확인됨 ($(ls -lh $MODELS_DIR/model.safetensors | awk '{print $5}'))"

# Docker 이미지 확인
echo "3️⃣ Docker 이미지 확인..."
if ! docker images | grep -q "$IMAGE_NAME"; then
    echo "❌ Docker 이미지를 찾을 수 없습니다: $IMAGE_NAME"
    exit 1
fi
echo "✅ Docker 이미지 확인됨"

# 컨테이너 실행
echo "4️⃣ 컨테이너 실행..."
docker run -d \
    --name $CONTAINER_NAME \
    --gpus all \
    -p 8003:8003 \
    -v "$MODELS_DIR:/app/models" \
    -e STT_DEVICE=cuda \
    -e STT_MODEL_PATH=/app/models \
    -e HUGGINGFACE_HUB_CACHE=/app/models \
    $IMAGE_NAME

echo ""
echo "=========================================="
echo "✅ Docker 컨테이너 실행 완료!"
echo "=========================================="
echo ""
echo "📋 컨테이너 정보:"
echo "  - 이름: $CONTAINER_NAME"
echo "  - 이미지: $IMAGE_NAME"
echo "  - GPU: 활성화 (--gpus all)"
echo "  - 포트: 8003:8003"
echo "  - 모델: $MODELS_DIR → /app/models"
echo ""
echo "⏳ 모델 초기화 중... (처음 실행 시 약 2-3분 소요)"
sleep 5
echo ""
echo "📋 로그 확인:"
echo "  docker logs -f $CONTAINER_NAME"
echo ""
echo "🧪 헬스 체크 (약 30초 후 시도):"
echo "  curl http://localhost:8003/health"
echo ""
echo "🛑 컨테이너 중지:"
echo "  docker stop $CONTAINER_NAME"
