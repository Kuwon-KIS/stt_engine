#!/bin/bash

# 백그라운드 빌드 로그 모니터링 (비파괴적)
# 기존 빌드 프로세스에 영향을 주지 않습니다

WORKSPACE="/Users/a113211/workspace/stt_engine"
BUILD_LOG="$WORKSPACE/build-progress.log"
PID_FILE="$WORKSPACE/.build-pid"

echo "════════════════════════════════════════════════════════════"
echo "📊 STT Engine 빌드 진행 상황 모니터링"
echo "════════════════════════════════════════════════════════════"
echo ""

# 빌드 프로세스 확인
if [ ! -f "$PID_FILE" ]; then
    echo "❌ 빌드가 시작되지 않았습니다."
    echo ""
    echo "🚀 백그라운드 빌드 시작:"
    echo "   bash $WORKSPACE/build-background.sh"
    exit 1
fi

BUILD_PID=$(cat "$PID_FILE")

if ! ps -p "$BUILD_PID" > /dev/null 2>&1; then
    echo "⚠️  빌드가 이미 완료되었습니다."
    echo ""
    echo "📝 최종 로그:"
    tail -30 "$BUILD_LOG"
    exit 0
fi

echo "✅ 빌드 프로세스 실행 중 (PID: $BUILD_PID)"
echo ""
echo "📋 최신 로그 (마지막 50줄):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

tail -50 "$BUILD_LOG"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⏳ 빌드가 진행 중입니다..."
echo ""
echo "💡 계속 모니터링:"
echo "   tail -f $BUILD_LOG"
echo ""
echo "💡 빌드 상태 확인:"
echo "   ps -p $BUILD_PID"
echo ""
echo "💡 이미지 확인:"
echo "   docker images | grep stt-engine"
