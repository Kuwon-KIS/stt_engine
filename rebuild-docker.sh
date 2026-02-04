#!/bin/bash
# Docker 이미지 재빌드 및 배포 스크립트

set -e

WORKSPACE="/Users/a113211/workspace/stt_engine"

echo "=========================================="
echo "🚀 STT Engine Docker 재빌드 시작"
echo "=========================================="
echo ""

# 1단계: 빌드 스크립트 실행
echo "1️⃣  Docker 이미지 빌드 중..."
echo "   (약 15-20분 소요)"
echo ""

cd "$WORKSPACE"
bash scripts/build-stt-engine-cuda.sh

echo ""
echo "=========================================="
echo "✅ Docker 이미지 빌드 완료!"
echo "=========================================="
echo ""

# 2단계: 빌드된 이미지 확인
echo "2️⃣  빌드된 이미지 확인"
docker images | grep stt-engine

echo ""
echo "=========================================="
echo "📋 다음 단계:"
echo "=========================================="
echo ""
echo "운영서버에서 다음 명령어 실행:"
echo ""
echo "# 1. 수정된 파일 복사"
echo "docker cp /app/stt_engine.py CONTAINER_NAME:/app/"
echo "docker cp /app/api_server.py CONTAINER_NAME:/app/"
echo ""
echo "# 2. 컨테이너 재시작"
echo "docker restart CONTAINER_NAME"
echo ""
echo "# 3. 서비스 초기화 대기 (30초)"
echo "sleep 30"
echo ""
echo "# 4. 헬스 체크"
echo "curl http://localhost:8003/health"
echo ""
echo "예상 응답:"
echo '{"status":"ok","version":"1.0.0","backend":"faster-whisper 또는 whisper"}'
echo ""
