#!/bin/bash

# STT Web UI 서버 시작 스크립트

cd /Users/a113211/workspace/stt_engine/web_ui || exit 1

echo "🛑 기존 서버 프로세스 종료..."
pkill -f "uvicorn main:app" 2>/dev/null
sleep 2

echo "✅ 서버 시작 중..."
/opt/homebrew/Caskroom/miniforge/base/envs/stt-py311/bin/python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8100 \
    --reload &

echo "✅ 서버가 백그라운드에서 시작되었습니다 (PID: $!)"
echo "📍 http://localhost:8100"
