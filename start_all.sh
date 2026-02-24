#!/bin/bash
# STT Engine - API 서버와 Web UI를 함께 시작

echo "=================================="
echo "STT Engine - Starting All Services"
echo "=================================="

# 1. API 서버 시작
echo ""
echo "🚀 Starting API Server (Port 8003)..."
cd /Users/a114302/Desktop/Github/stt_engine
nohup ./start_api_server.sh > /tmp/api_server.log 2>&1 &
API_PID=$!
echo "   API Server PID: $API_PID"
sleep 3

# API 서버 확인
if lsof -i :8003 | grep -q LISTEN; then
    echo "   ✅ API Server is running on port 8003"
else
    echo "   ⚠️  API Server may not have started correctly"
    echo "   Check logs: tail -f /tmp/api_server.log"
fi

# 2. Web UI 시작
echo ""
echo "🌐 Starting Web UI (Port 8100)..."
cd /Users/a114302/Desktop/Github/stt_engine/web_ui
source venv/bin/activate
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8100 --reload > /tmp/webui.log 2>&1 &
WEBUI_PID=$!
echo "   Web UI PID: $WEBUI_PID"
sleep 3

# Web UI 확인
if lsof -i :8100 | grep -q LISTEN; then
    echo "   ✅ Web UI is running on port 8100"
else
    echo "   ⚠️  Web UI may not have started correctly"
    echo "   Check logs: tail -f /tmp/webui.log"
fi

echo ""
echo "=================================="
echo "✅ All Services Started"
echo "=================================="
echo ""
echo "📍 Web UI:    http://localhost:8100"
echo "📍 API Docs:  http://localhost:8003/docs"
echo ""
echo "📋 Logs:"
echo "   API Server: tail -f /tmp/api_server.log"
echo "   Web UI:     tail -f /tmp/webui.log"
echo ""
echo "🛑 To stop all services:"
echo "   pkill -f 'start_api_server.sh'"
echo "   pkill -f 'uvicorn main:app'"
echo ""
