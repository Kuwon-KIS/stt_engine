#!/bin/bash

# STT Engine Docker 재빌드 스크립트
# 수정된 코드를 포함한 새로운 이미지 빌드

echo "🔄 STT Engine Docker 이미지 재빌드"
echo "════════════════════════════════════════════"
echo ""

IMAGE_NAME="stt-engine"
OLD_TAG="cuda129-v1.0"
NEW_TAG="cuda129-v1.1"

echo "1️⃣ 기존 이미지 확인"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker images | grep "$IMAGE_NAME"

echo ""
echo "2️⃣ 빌드 스크립트 실행 중... (약 10-15분 소요)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 빌드 실행
cd /Users/a113211/workspace/stt_engine
bash build-stt-engine-cuda.sh

echo ""
echo "3️⃣ 빌드 완료 확인"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker images | grep "$IMAGE_NAME"

echo ""
echo "4️⃣ 새 이미지 태그 지정"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 최신 빌드된 이미지 찾기
LATEST_IMAGE=$(docker images | grep "$IMAGE_NAME" | grep "$OLD_TAG" | awk '{print $3}' | head -1)

if [ -z "$LATEST_IMAGE" ]; then
    echo "❌ 빌드된 이미지를 찾을 수 없습니다"
    exit 1
fi

echo "이미지 ID: $LATEST_IMAGE"

# 새 태그로 지정 (선택사항 - 기존 이미지 유지)
# docker tag "$LATEST_IMAGE" "$IMAGE_NAME:$NEW_TAG"
# echo "✅ 새 태그: $IMAGE_NAME:$NEW_TAG"

echo ""
echo "════════════════════════════════════════════"
echo "✅ Docker 이미지 재빌드 완료!"
echo "════════════════════════════════════════════"
echo ""
echo "📋 사용 가능한 이미지:"
docker images | grep "$IMAGE_NAME"
echo ""
echo "🚀 다음 명령어로 컨테이너 실행:"
echo "   docker run -d --name stt-engine-gpu --gpus all -p 8003:8003 \\"
echo "     -v /Users/a113211/workspace/stt_engine/models:/app/models \\"
echo "     $IMAGE_NAME:$OLD_TAG"
echo ""
