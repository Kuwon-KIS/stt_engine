#!/bin/bash
#
# 성능 모니터링 배포 스크립트
# 운영 서버에서 성능 측정을 위한 자동 설치
#
# 사용법:
#   bash deploy_performance_monitoring.sh /path/to/deployment
#
# 예시:
#   bash deploy_performance_monitoring.sh /opt/stt_engine
#

set -e

# ============================================================================
# 설정
# ============================================================================

DEPLOYMENT_PATH="${1:-.}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# 함수
# ============================================================================

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo ""
    echo "============================================================================"
    echo "$1"
    echo "============================================================================"
}

check_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        log_success "$description 발견: $file"
        return 0
    else
        log_error "$description 없음: $file"
        return 1
    fi
}

copy_with_verify() {
    local source=$1
    local dest=$2
    local description=$3
    
    if [ ! -f "$source" ]; then
        log_error "소스 파일 없음: $source"
        return 1
    fi
    
    # 대상 디렉토리 생성
    mkdir -p "$(dirname "$dest")"
    
    # 파일 복사
    cp "$source" "$dest"
    
    if [ -f "$dest" ]; then
        log_success "$description 배포: $dest"
        return 0
    else
        log_error "$description 배포 실패: $dest"
        return 1
    fi
}

# ============================================================================
# 메인 스크립트
# ============================================================================

print_header "🚀 성능 모니터링 배포 시작"

# 배포 경로 확인
log_info "배포 경로: $DEPLOYMENT_PATH"
log_info "작업 디렉토리: $WORKSPACE_ROOT"

# 소스 파일 확인
print_header "📋 소스 파일 확인"

FAILED=0
ERRORS=()

# 필수 파일 체크
if ! check_file "$WORKSPACE_ROOT/web_ui/app/utils/db.py" "SQLAlchemy 쿼리 타이밍"; then
    ERRORS+=("$WORKSPACE_ROOT/web_ui/app/utils/db.py")
    FAILED=$((FAILED + 1))
fi

if ! check_file "$WORKSPACE_ROOT/web_ui/main.py" "FastAPI 응답 타이밍"; then
    ERRORS+=("$WORKSPACE_ROOT/web_ui/main.py")
    FAILED=$((FAILED + 1))
fi

if ! check_file "$WORKSPACE_ROOT/web_ui/utils/logger.py" "성능 로깅 설정"; then
    ERRORS+=("$WORKSPACE_ROOT/web_ui/utils/logger.py")
    FAILED=$((FAILED + 1))
fi

if ! check_file "$SCRIPT_DIR/run_performance_test.py" "성능 테스트 스크립트"; then
    ERRORS+=("$SCRIPT_DIR/run_performance_test.py")
    FAILED=$((FAILED + 1))
fi

if [ $FAILED -gt 0 ]; then
    log_error "필수 파일 $FAILED개 누락:"
    for error in "${ERRORS[@]}"; do
        echo "  - $error"
    done
    exit 1
fi

log_success "모든 필수 파일 확인됨"

# 배포
print_header "📦 파일 배포"

DEPLOY_ERRORS=0

# 성능 모니터링 파일 복사
if ! copy_with_verify "$WORKSPACE_ROOT/web_ui/app/utils/db.py" \
    "$DEPLOYMENT_PATH/web_ui/app/utils/db.py" \
    "SQLAlchemy 쿼리 타이밍"; then
    DEPLOY_ERRORS=$((DEPLOY_ERRORS + 1))
fi

if ! copy_with_verify "$WORKSPACE_ROOT/web_ui/main.py" \
    "$DEPLOYMENT_PATH/web_ui/main.py" \
    "FastAPI 응답 타이밍"; then
    DEPLOY_ERRORS=$((DEPLOY_ERRORS + 1))
fi

if ! copy_with_verify "$WORKSPACE_ROOT/web_ui/utils/logger.py" \
    "$DEPLOYMENT_PATH/web_ui/utils/logger.py" \
    "성능 로깅 설정"; then
    DEPLOY_ERRORS=$((DEPLOY_ERRORS + 1))
fi

if ! copy_with_verify "$SCRIPT_DIR/run_performance_test.py" \
    "$DEPLOYMENT_PATH/scripts/performance/run_performance_test.py" \
    "성능 테스트 스크립트"; then
    DEPLOY_ERRORS=$((DEPLOY_ERRORS + 1))
fi

if ! copy_with_verify "$SCRIPT_DIR/README.md" \
    "$DEPLOYMENT_PATH/scripts/performance/README.md" \
    "성능 측정 가이드"; then
    DEPLOY_ERRORS=$((DEPLOY_ERRORS + 1))
fi

if [ $DEPLOY_ERRORS -gt 0 ]; then
    log_error "파일 배포 중 $DEPLOY_ERRORS개 오류 발생"
    exit 1
fi

# 디렉토리 생성
print_header "📁 디렉토리 설정"

log_info "로그 디렉토리 생성: $DEPLOYMENT_PATH/web_ui/logs"
mkdir -p "$DEPLOYMENT_PATH/web_ui/logs"
log_success "로그 디렉토리 생성됨"

log_info "스크립트 디렉토리 생성: $DEPLOYMENT_PATH/scripts/performance"
mkdir -p "$DEPLOYMENT_PATH/scripts/performance"
log_success "스크립트 디렉토리 생성됨"

# 권한 설정
print_header "🔐 권한 설정"

log_info "스크립트 실행 권한 설정"
chmod +x "$DEPLOYMENT_PATH/scripts/performance/run_performance_test.py"
log_success "실행 권한 설정됨"

log_info "로그 디렉토리 쓰기 권한 설정"
chmod 755 "$DEPLOYMENT_PATH/web_ui/logs"
log_success "쓰기 권한 설정됨"

# 검증
print_header "✅ 배포 검증"

if [ -f "$DEPLOYMENT_PATH/web_ui/app/utils/db.py" ]; then
    if grep -q "perf_logger" "$DEPLOYMENT_PATH/web_ui/app/utils/db.py"; then
        log_success "SQLAlchemy 쿼리 타이밍 통합됨"
    else
        log_warning "SQLAlchemy 타이밍 설정 확인 필요"
    fi
else
    log_error "db.py 파일이 없습니다"
fi

if [ -f "$DEPLOYMENT_PATH/web_ui/main.py" ]; then
    if grep -q "PerformanceMiddleware" "$DEPLOYMENT_PATH/web_ui/main.py"; then
        log_success "FastAPI 응답 타이밍 통합됨"
    else
        log_warning "FastAPI 타이밍 설정 확인 필요"
    fi
else
    log_error "main.py 파일이 없습니다"
fi

if [ -f "$DEPLOYMENT_PATH/web_ui/utils/logger.py" ]; then
    if grep -q "perf_logger" "$DEPLOYMENT_PATH/web_ui/utils/logger.py"; then
        log_success "성능 로깅 설정됨"
    else
        log_warning "성능 로깅 설정 확인 필요"
    fi
else
    log_error "logger.py 파일이 없습니다"
fi

# 배포 완료
print_header "📊 배포 완료"

echo ""
log_success "성능 모니터링 배포 완료!"
echo ""
echo "다음 단계:"
echo "  1. 운영 서버에서 테스트 실행:"
echo "     cd $DEPLOYMENT_PATH/web_ui"
echo "     python ../scripts/performance/run_performance_test.py"
echo ""
echo "  2. 성능 로그 확인:"
echo "     tail -f $DEPLOYMENT_PATH/web_ui/logs/performance.log"
echo ""
echo "  3. 정기적인 로그 정리 (선택사항):"
echo "     find $DEPLOYMENT_PATH/web_ui/logs -name 'performance.log*' -mtime +7 -delete"
echo ""
echo "더 많은 정보는 다음을 참고하세요:"
echo "  $DEPLOYMENT_PATH/scripts/performance/README.md"
echo ""

exit 0
