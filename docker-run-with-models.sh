#!/bin/bash

# ============================================================
# STT Engine Docker Run with Model Mount
# ============================================================

# 설정
IMAGE_NAME="stt-engine:cuda129-v1.0"
CONTAINER_NAME="stt-engine-test"
LOCAL_MODELS_DIR="/Users/a113211/workspace/stt_engine/models"
CONTAINER_MODELS_DIR="/app/models"
PORT=8003

echo "🐳 STT Engine Docker 설정"
echo "════════════════════════════════════════════════════════════════"
echo "✓ 이미지: $IMAGE_NAME"
echo "✓ 컨테이너: $CONTAINER_NAME"
echo "✓ 로컬 모델 경로: $LOCAL_MODELS_DIR"
echo "✓ 컨테이너 모델 경로: $CONTAINER_MODELS_DIR"
echo "✓ 포트: $PORT"
echo "════════════════════════════════════════════════════════════════"

# 1️⃣ 이전 컨테이너 정리
echo ""
echo "1️⃣ 이전 컨테이너 정리 중..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true
echo "✅ 완료"

# 2️⃣ 모델 디렉토리 확인
echo ""
echo "2️⃣ 모델 디렉토리 확인 중..."
if [ ! -d "$LOCAL_MODELS_DIR" ]; then
    echo "❌ 모델 디렉토리 없음: $LOCAL_MODELS_DIR"
    exit 1
fi

echo "   로컬 모델 파일:"
ls -lhS "$LOCAL_MODELS_DIR"/ | head -5
echo ""

# 3️⃣ Docker 이미지 확인
echo "3️⃣ Docker 이미지 확인 중..."
if ! docker images | grep -q "stt-engine"; then
    echo "❌ 이미지 없음: $IMAGE_NAME"
    exit 1
fi
docker images | grep stt-engine
echo "✅ 이미지 존재 확인"

# 4️⃣ 컨테이너 실행
echo ""
echo "4️⃣ 컨테이너 실행 중..."
docker run -d \
  --name $CONTAINER_NAME \
  -p $PORT:$PORT \
  -v "$LOCAL_MODELS_DIR:$CONTAINER_MODELS_DIR" \
  -e STT_DEVICE=cpu \
  -e HF_HOME=$CONTAINER_MODELS_DIR \
  $IMAGE_NAME

if [ $? -eq 0 ]; then
    echo "✅ 컨테이너 시작됨"
else
    echo "❌ 컨테이너 시작 실패"
    exit 1
fi

# 5️⃣ 컨테이너 상태 확인
echo ""
echo "5️⃣ 컨테이너 상태 확인 중..."
sleep 2
docker ps | grep $CONTAINER_NAME
echo ""

# 6️⃣ 로그 확인 (최근 30줄)
echo "6️⃣ 컨테이너 로그 (모델 로딩 상황):"
echo "════════════════════════════════════════════════════════════════"
docker logs --tail 30 $CONTAINER_NAME
echo "════════════════════════════════════════════════════════════════"
echo ""

# 7️⃣ Health Check (재시도 최대 30초)
echo "7️⃣ Health Check 실행 중... (최대 30초 대기)"
HEALTH_CHECK_URL="http://localhost:$PORT/health"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    RESPONSE=$(curl -s -w "\n%{http_code}" "$HEALTH_CHECK_URL" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Health Check 성공! (HTTP $HTTP_CODE)"
        echo "   응답: $BODY"
        HEALTH_OK=1
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            printf "⏳ 대기 중... ($RETRY_COUNT/$MAX_RETRIES)\r"
            sleep 1
        fi
    fi
done

echo ""

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Health Check 실패 (타임아웃)"
    echo ""
    echo "📋 최근 로그:"
    docker logs --tail 50 $CONTAINER_NAME
    echo ""
    echo "💡 조치:"
    echo "   1. 로그에서 에러 메시지 확인"
    echo "   2. 모델 경로 확인: docker exec $CONTAINER_NAME ls -lh /app/models/"
    echo "   3. 실시간 로그 보기: docker logs -f $CONTAINER_NAME"
    exit 1
fi

# 8️⃣ 모델 정보 확인
echo "8️⃣ 컨테이너 내부 모델 확인:"
docker exec $CONTAINER_NAME ls -lh $CONTAINER_MODELS_DIR/
echo ""

# 9️⃣ PyTorch 정보 확인
echo "9️⃣ PyTorch 정보:"
docker exec $CONTAINER_NAME python3 << 'PYTHON_EOF'
import torch
print(f'  PyTorch Version: {torch.__version__}')
print(f'  CUDA Available: {torch.cuda.is_available()}')
print(f'  CUDA Version: {torch.version.cuda}')
print(f'  Device: {"cuda" if torch.cuda.is_available() else "cpu"}')
PYTHON_EOF
echo ""

# 🔟 최종 정보
echo "════════════════════════════════════════════════════════════════"
echo "🎉 STT Engine 준비 완료!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📝 다음 단계:"
echo ""
echo "1️⃣ Health Check:"
echo "   curl http://localhost:$PORT/health"
echo ""
echo "2️⃣ STT 테스트 (음성 파일 업로드):"
echo "   curl -X POST http://localhost:$PORT/transcribe \\"
echo "     -F \"file=@/path/to/audio.wav\""
echo ""
echo "3️⃣ 실시간 로그 보기:"
echo "   docker logs -f $CONTAINER_NAME"
echo ""
echo "4️⃣ 컨테이너 중지:"
echo "   docker stop $CONTAINER_NAME"
echo ""
echo "5️⃣ 컨테이너 제거:"
echo "   docker rm $CONTAINER_NAME"
echo ""
echo "════════════════════════════════════════════════════════════════"
