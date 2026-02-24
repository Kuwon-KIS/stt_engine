#!/bin/bash
set -e

echo "🚀 STT Web UI Server Startup Script"
echo "===================================="

# 1. 마이그레이션 선택적 실행 (RUN_MIGRATIONS=true 환경변수로 제어)
if [ "${RUN_MIGRATIONS}" = "true" ]; then
    echo "🔄 실행 중: 데이터베이스 마이그레이션..."
    if [ -f /app/migrations/add_result_status.py ]; then
        python /app/migrations/add_result_status.py || {
            echo "⚠️  마이그레이션 경고 (무시하고 계속): $?"
        }
    else
        echo "⚠️  마이그레이션 파일이 없습니다: /app/migrations/add_result_status.py"
    fi
else
    echo "⏭️  마이그레이션 스킵 (RUN_MIGRATIONS=true로 설정하면 실행됨)"
fi

# 2. Uvicorn 서버 시작
echo "✅ Uvicorn 서버 시작 중..."
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8100 \
    --workers 1 \
    --log-level info
