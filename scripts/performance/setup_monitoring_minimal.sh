#!/bin/bash
#
# 기존 Docker에서 모니터링 활성화 (최소 세팅)
# 
# 사용법:
#   bash setup_monitoring_minimal.sh
#
# 효과:
#   - 성능 모니터링 파일을 컨테이너로 복사
#   - 로그 디렉토리 생성
#   - 애플리케이션 재시작
#

set -e

echo "🚀 기존 Docker에서 모니터링 활성화 시작..."
echo ""

# 1. 프로젝트 디렉토리 확인
if [ ! -d "web_ui" ] || [ ! -d "scripts/performance" ]; then
    echo "❌ 필요한 디렉토리를 찾을 수 없습니다"
    exit 1
fi

echo "✅ 프로젝트 디렉토리 확인"

# 2. 실행 중인 Docker 컨테이너 확인
echo "🔍 실행 중인 Docker 컨테이너 확인..."
docker ps --format "table {{.Names}}\t{{.Image}}"
echo ""

# stt-web-ui 컨테이너 찾기
CONTAINER=$(docker ps --filter "name=stt-web-ui" -q 2>/dev/null || echo "")

if [ -z "$CONTAINER" ]; then
    echo "❌ 'stt-web-ui' 컨테이너를 찾을 수 없습니다"
    echo ""
    echo "📋 사용 가능한 컨테이너:"
    docker ps --format "{{.Names}}" | nl
    echo ""
    echo "💡 컨테이너 이름을 명시하려면:"
    echo "   CONTAINER=<컨테이너_이름> bash setup_monitoring_minimal.sh"
    echo ""
    echo "예시:"
    echo "   CONTAINER=stt-api bash setup_monitoring_minimal.sh"
    echo "   또는"
    echo "   CONTAINER=stt-web-ui bash setup_monitoring_minimal.sh"
    exit 1
fi

echo "✅ stt-web-ui 컨테이너 선택: $CONTAINER"

# 3. 파일 존재 확인
echo ""
echo "📋 모니터링 파일 확인:"

files=(
    "web_ui/app/utils/db.py"
    "web_ui/main.py"
    "web_ui/utils/logger.py"
    "scripts/performance/quick_diagnostic.py"
    "scripts/performance/run_performance_test.py"
    "scripts/performance/diagnose_ui_performance.py"
    "scripts/performance/diagnose_backend_issues.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (없음)"
        exit 1
    fi
done

# 4. 모니터링 파일을 컨테이너로 복사
echo ""
echo "📝 파일을 컨테이너로 복사 중..."

docker cp web_ui/app/utils/db.py $CONTAINER:/app/app/utils/ 2>/dev/null && \
    echo "  ✅ db.py"

docker cp web_ui/main.py $CONTAINER:/app/ 2>/dev/null && \
    echo "  ✅ main.py"

docker cp web_ui/utils/logger.py $CONTAINER:/app/utils/ 2>/dev/null && \
    echo "  ✅ logger.py"

docker cp scripts/performance/quick_diagnostic.py $CONTAINER:/app/ 2>/dev/null && \
    echo "  ✅ quick_diagnostic.py"

docker cp scripts/performance/run_performance_test.py $CONTAINER:/app/ 2>/dev/null && \
    echo "  ✅ run_performance_test.py"

docker cp scripts/performance/diagnose_ui_performance.py $CONTAINER:/app/ 2>/dev/null && \
    echo "  ✅ diagnose_ui_performance.py"

docker cp scripts/performance/diagnose_backend_issues.py $CONTAINER:/app/ 2>/dev/null && \
    echo "  ✅ diagnose_backend_issues.py"

# 5. 로그 디렉토리 생성
echo ""
echo "📁 로그 디렉토리 생성..."

docker exec $CONTAINER mkdir -p /app/logs 2>/dev/null && \
    echo "  ✅ 로그 디렉토리 생성됨"

# 6. 애플리케이션 재시작
echo ""
echo "🔄 애플리케이션 재시작..."

docker restart $CONTAINER > /dev/null 2>&1
sleep 3

echo "  ✅ 애플리케이션 재시작됨"

# 7. 완료 메시지
echo ""
echo "============================================================"
echo "✅ 모니터링 활성화 완료!"
echo "============================================================"
echo ""
echo "📊 다음 단계:"
echo ""
echo "  1️⃣  진단 실행 (로그 거의 없음):"
echo "     docker exec $CONTAINER python /app/quick_diagnostic.py"
echo ""
echo "  2️⃣  본격 모니터링 (상세 분석):"
echo "     docker exec $CONTAINER python /app/run_performance_test.py"
echo ""
echo "  3️⃣  성능 로그 확인:"
echo "     docker exec $CONTAINER tail -50 /app/logs/performance.log"
echo ""
echo "📝 가이드:"
echo "  scripts/performance/MINIMAL_SETUP_EXISTING_DOCKER.md"
echo ""
