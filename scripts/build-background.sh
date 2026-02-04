#!/bin/bash

# 백그라운드 STT Engine Docker 재빌드 스크립트
# 로그 파일로 진행 상황 기록, 기존 프로세스 보호

set -e

WORKSPACE="/Users/a113211/workspace/stt_engine"
BUILD_LOG="$WORKSPACE/build-progress.log"
PID_FILE="$WORKSPACE/.build-pid"

echo "════════════════════════════════════════════════════════════"
echo "🚀 STT Engine Docker 백그라운드 재빌드"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "� 설치될 패키지:"
echo "   - faster-whisper (CTranslate2 백엔드, model.bin)"
echo "   - openai-whisper (PyTorch 백엔드, model.safetensors)"
echo ""
echo "�📝 로그 파일: $BUILD_LOG"
echo "🔄 PID 파일: $PID_FILE"
echo ""

# 기존 빌드 프로세스 확인
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "⚠️  경고: 기존 빌드 프로세스가 실행 중입니다 (PID: $OLD_PID)"
        echo "   진행 상황: tail -f $BUILD_LOG"
        exit 1
    fi
fi

# 백그라운드에서 빌드 실행 (로그 파일로 리다이렉트)
nohup bash "$WORKSPACE/build-stt-engine-cuda.sh" > "$BUILD_LOG" 2>&1 &

BUILD_PID=$!
echo "$BUILD_PID" > "$PID_FILE"

echo "✅ 백그라운드 빌드 시작됨 (PID: $BUILD_PID)"
echo ""
echo "📋 진행 상황 확인 명령어:"
echo "   tail -f $BUILD_LOG"
echo ""
echo "📊 빌드 상태 확인:"
echo "   ps -p $BUILD_PID"
echo ""
echo "🛑 빌드 중지 (필요시):"
echo "   kill $BUILD_PID"
echo ""
echo "✅ 로그 모니터링을 시작합니다 (10초 후 Ctrl+C로 종료 가능)..."
echo ""

sleep 2

# 초기 로그 출력
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📄 빌드 로그:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
tail -20 "$BUILD_LOG"
echo ""
echo "⏳ 빌드가 백그라운드에서 진행 중입니다."
echo "   이 창을 닫아도 빌드는 계속됩니다."
echo "   로그는 다음 명령어로 모니터링할 수 있습니다:"
echo "   tail -f $BUILD_LOG"
