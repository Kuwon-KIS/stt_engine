#!/bin/bash

###############################################################################
# STT Engine 메모리 누수 진단 스크립트
#
# 용도: 연속 요청 시 메모리 누수 감지
#
# 사용법:
#   bash scripts/test_memory_leak.sh [요청_횟수] [파일_경로]
#
# 예제:
#   bash scripts/test_memory_leak.sh 10 /app/audio/samples/test_ko_1min.wav
#   bash scripts/test_memory_leak.sh 5  # 기본값: 5회
#
###############################################################################

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 파라미터
NUM_REQUESTS="${1:-5}"
TEST_FILE="${2:-/app/audio/samples/test_ko_1min.wav}"
API_URL="${API_URL:-http://localhost:8003}"

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# 함수: GPU 메모리 확인
get_gpu_memory() {
    nvidia-smi --query-gpu=memory.used --format=csv,nounits,noheader 2>/dev/null | head -1 || echo "N/A"
}

# 함수: 시스템 메모리 확인
get_system_memory() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//' | awk '{print int($1 * 4 / 1024 / 1024)}' || echo "N/A"
    else
        # Linux
        free | awk '/^Mem:/ {print int($7 / 1024)}' || echo "N/A"
    fi
}

# 함수: 단일 요청 실행
run_single_request() {
    local request_num=$1
    local start_time=$(date +%s%N)
    
    echo ""
    print_info "요청 #$request_num 시작..."
    
    # API 호출
    local response=$(curl -s -X POST "${API_URL}/transcribe" \
        -F "file_path=${TEST_FILE}" \
        -F "language=ko")
    
    local end_time=$(date +%s%N)
    local duration=$(echo "scale=2; ($end_time - $start_time) / 1000000000" | bc)
    
    # 결과 추출
    local success=$(echo "$response" | jq -r '.success' 2>/dev/null || echo "error")
    local processing_time=$(echo "$response" | jq -r '.processing_time_seconds' 2>/dev/null || echo "N/A")
    
    # GPU 메모리 확인
    local gpu_mem=$(get_gpu_memory)
    local sys_mem=$(get_system_memory)
    
    if [ "$success" = "true" ]; then
        print_success "요청 #$request_num 완료"
        echo "  ├─ 처리 시간: ${processing_time}초"
        echo "  ├─ 실제 응답 시간: ${duration}초"
        echo "  ├─ GPU 메모리: ${gpu_mem}MB"
        echo "  └─ 시스템 여유 메모리: ${sys_mem}MB"
        
        return 0
    else
        local error=$(echo "$response" | jq -r '.error' 2>/dev/null || echo "Unknown error")
        print_error "요청 #$request_num 실패: $error"
        echo "  └─ GPU 메모리: ${gpu_mem}MB"
        
        return 1
    fi
}

# 메인
main() {
    print_header "STT Engine 메모리 누수 진단 (${NUM_REQUESTS}회 요청)"
    
    # 1. API 연결 확인
    print_info "API 연결 확인 중 (${API_URL})..."
    if ! curl -s "${API_URL}/backend/current" > /dev/null; then
        print_error "API에 연결할 수 없습니다"
        return 1
    fi
    print_success "API 연결 확인 완료"
    
    # 2. 테스트 파일 확인
    if [ ! -f "$TEST_FILE" ]; then
        # 원격 서버일 수 있으므로 경고만 출력
        print_info "테스트 파일 확인 불가: $TEST_FILE (원격 서버일 수 있음)"
    else
        print_success "테스트 파일 확인: $(basename $TEST_FILE)"
    fi
    
    # 3. 초기 상태 로깅
    echo ""
    print_info "초기 상태:"
    echo "  ├─ GPU 메모리: $(get_gpu_memory)MB"
    echo "  ├─ 시스템 여유: $(get_system_memory)MB"
    echo "  └─ 백엔드: $(curl -s "${API_URL}/backend/current" | jq -r '.current_backend' 2>/dev/null || echo 'unknown')"
    
    # 4. 연속 요청 실행
    print_header "연속 요청 실행"
    
    local failed=0
    local total_time=0
    local gpu_mem_initial=$(get_gpu_memory)
    local sys_mem_initial=$(get_system_memory)
    
    for i in $(seq 1 $NUM_REQUESTS); do
        run_single_request $i || ((failed++))
        
        # 요청 간 잠시 대기
        if [ $i -lt $NUM_REQUESTS ]; then
            sleep 2
        fi
    done
    
    # 5. 최종 상태
    echo ""
    print_header "최종 진단 결과"
    
    local gpu_mem_final=$(get_gpu_memory)
    local sys_mem_final=$(get_system_memory)
    
    echo "요청 결과:"
    echo "  ├─ 성공: $((NUM_REQUESTS - failed))/${NUM_REQUESTS}"
    echo "  └─ 실패: ${failed}/${NUM_REQUESTS}"
    
    echo ""
    echo "메모리 변화:"
    echo "  ├─ GPU 메모리: ${gpu_mem_initial}MB → ${gpu_mem_final}MB"
    
    if [ "$gpu_mem_initial" != "N/A" ] && [ "$gpu_mem_final" != "N/A" ]; then
        local gpu_increase=$(($gpu_mem_final - $gpu_mem_initial))
        if [ $gpu_increase -gt 100 ]; then
            echo "  │   ${RED}⚠️  증가: ${gpu_increase}MB${NC} (누수 의심)"
        elif [ $gpu_increase -gt 0 ]; then
            echo "  │   ${YELLOW}경고: ${gpu_increase}MB 증가${NC}"
        else
            echo "  │   ${GREEN}정상 (감소)${NC}"
        fi
    fi
    
    echo "  └─ 시스템 메모리: ${sys_mem_initial}MB → ${sys_mem_final}MB"
    
    echo ""
    
    # 6. 결론
    if [ $failed -eq 0 ]; then
        print_success "모든 요청 성공"
    else
        print_error "${failed}개 요청 실패"
    fi
    
    # 7. 권장사항
    echo ""
    print_info "권장사항:"
    if [ "$gpu_mem_initial" != "N/A" ] && [ "$gpu_mem_final" != "N/A" ]; then
        local gpu_increase=$(($gpu_mem_final - $gpu_mem_initial))
        if [ $gpu_increase -gt 200 ]; then
            echo "  ├─ 심각한 메모리 누수 감지"
            echo "  ├─ → api_server.py에서 CUDA 캐시 정리 확인"
            echo "  ├─ → transformers 모델 언로드 확인"
            echo "  └─ → Docker 메모리 제한 설정 확인"
        elif [ $gpu_increase -gt 50 ]; then
            echo "  ├─ 경미한 메모리 누수 감지"
            echo "  ├─ → gc.collect() 호출 확인"
            echo "  └─ → torch.cuda.empty_cache() 호출 확인"
        else
            echo "  └─ 메모리 관리 양호"
        fi
    fi
    
    echo ""
}

main
