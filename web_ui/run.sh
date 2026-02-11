#!/bin/bash
# STT Web UI 실행 스크립트

set -e

echo "================================"
echo "STT Web UI 시작"
echo "================================"

# 환경 변수 설정
export WEB_HOST=${WEB_HOST:-0.0.0.0}
export WEB_PORT=${WEB_PORT:-8001}
export STT_API_URL=${STT_API_URL:-http://localhost:8003}
export LOG_LEVEL=${LOG_LEVEL:-INFO}

# 의존성 설치 (필요시)
if [ "$1" == "--install" ]; then
    echo "의존성 설치 중..."
    pip install -r requirements.txt
fi

# 웹 UI 서버 시작
echo "웹 UI 서버 시작: http://$WEB_HOST:$WEB_PORT"
echo "STT API: $STT_API_URL"
echo ""

python -m uvicorn main:app \
    --host $WEB_HOST \
    --port $WEB_PORT \
    --reload \
    --log-level $LOG_LEVEL
