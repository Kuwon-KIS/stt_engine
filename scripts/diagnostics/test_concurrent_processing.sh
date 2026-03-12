#!/bin/bash

#############################################################################
#                   STT Engine Concurrent Processing Test                    #
#                                                                             #
# 동시 파일 처리 성능 테스트                                                 #
# - 여러 파일을 동시에 처리할 때 Lock 경합 확인                             #
# - 병렬 처리 효율성 측정                                                   #
# - 메모리/CPU 사용률 추적                                                  #
#############################################################################

set -e

API_URL="http://localhost:8003/transcribe"
CONTAINER_NAME="stt-api"
TEST_AUDIO_DIR="/tmp/test_audio"
CONCURRENT_JOBS=${1:-2}  # 동시 처리 파일 수 (기본값: 2)
INTERVAL=1               # 모니터링 간격

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

log_info() {
    echo -e "${BLUE}[$(timestamp)]${NC} ℹ️  $1"
}

log_warn() {
    echo -e "${YELLOW}[$(timestamp)]${NC} ⚠️  $1"
}

log_error() {
    echo -e "${RED}[$(timestamp)]${NC} ❌ $1"
}

log_success() {
    echo -e "${GREEN}[$(timestamp)]${NC} ✅ $1"
}

log_debug() {
    echo -e "${CYAN}[$(timestamp)]${NC} 🔍 $1"
}

section() {
    echo ""
    echo -e "${MAGENTA}════════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}  $1${NC}"
    echo -e "${MAGENTA}════════════════════════════════════════════════════════════${NC}"
}

# Get sample audio files
prepare_test_audio() {
    section "1️⃣  테스트 오디오 준비"
    
    mkdir -p "$TEST_AUDIO_DIR"
    
    # Docker 컨테이너에서 샘플 오디오 확인
    SAMPLE_AUDIO=$(docker exec "${CONTAINER_NAME}" find /app/audio/samples -name "*.wav" -o -name "*.mp3" 2>/dev/null | head -5 || echo "")
    
    if [ -z "$SAMPLE_AUDIO" ]; then
        log_error "샘플 오디오를 찾을 수 없습니다"
        log_info "다음 경로에 오디오 파일을 추가하세요: /app/audio/samples/"
        exit 1
    fi
    
    log_success "사용 가능한 샘플 오디오:"
    echo "$SAMPLE_AUDIO" | head -3 | xargs -I {} echo "  - {}"
    
    # 테스트용 파일 경로 준비
    TEST_FILES=()
    for file in $(echo "$SAMPLE_AUDIO" | head -$CONCURRENT_JOBS); do
        TEST_FILES+=("$file")
    done
    
    echo "  테스트 파일 수: ${#TEST_FILES[@]}"
}

# Monitor container during test
start_monitoring() {
    section "2️⃣  모니터링 시작"
    
    MONITOR_LOG="/tmp/concurrent_test_monitor_$(date +%s).log"
    
    log_info "모니터링 로그: $MONITOR_LOG"
    
    {
        echo "timestamp,container_cpu,container_mem_mb,container_mem_percent,gpu_mem_mb,thread_count,lock_waits"
        
        while [ -f /tmp/concurrent_test_running ]; do
            TIMESTAMP=$(timestamp)
            
            # Docker stats
            STATS=$(docker stats --no-stream "${CONTAINER_NAME}" 2>/dev/null | tail -1)
            CPU=$(echo "$STATS" | awk '{print $3}' | sed 's/%//')
            MEM=$(echo "$STATS" | awk '{print $4}' | sed 's/MiB//')
            MEM_PERCENT=$(echo "$STATS" | awk '{print $5}' | sed 's/%//')
            
            # GPU memory
            GPU=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 || echo "0")
            
            # Thread count
            PYTHON_PID=$(docker exec "${CONTAINER_NAME}" ps aux 2>/dev/null | grep '[p]ython' | head -1 | awk '{print $2}' || echo "")
            THREADS=$(docker exec "${CONTAINER_NAME}" cat /proc/"$PYTHON_PID"/status 2>/dev/null | grep "Threads:" | awk '{print $2}' || echo "0")
            
            # Lock waits (from logs)
            LOCK_WAITS=$(docker logs "${CONTAINER_NAME}" --since 5s 2>&1 | grep -ic "lock\|wait\|acquire" || echo "0")
            
            echo "$TIMESTAMP,$CPU,$MEM,$MEM_PERCENT,$GPU,$THREADS,$LOCK_WAITS"
            
            sleep "$INTERVAL"
        done
    } >> "$MONITOR_LOG" &
    
    MONITOR_PID=$!
    echo "$MONITOR_PID" > /tmp/concurrent_test_monitor.pid
    
    log_success "모니터링 프로세스 시작 (PID: $MONITOR_PID)"
}

# Run concurrent file processing
run_concurrent_test() {
    section "3️⃣  동시 파일 처리 시작 ($CONCURRENT_JOBS 개)"
    
    touch /tmp/concurrent_test_running
    
    TEST_RESULT="/tmp/concurrent_test_result_$(date +%s).json"
    PROCESSING_PIDS=()
    
    log_info "파일 처리 시작"
    echo ""
    
    # 각 파일마다 백그라운드에서 처리 요청
    for i in $(seq 1 ${#TEST_FILES[@]}); do
        FILE="${TEST_FILES[$((i-1))]}"
        
        log_debug "파일 $i/${#TEST_FILES[@]} 처리 요청: $FILE"
        
        # 백그라운드 처리
        (
            START_TIME=$(date +%s%N)
            
            RESPONSE=$(curl -s -X POST "$API_URL" \
                -F "file_path=$FILE" \
                -F "is_stream=false" \
                -w "\n%{time_total}" 2>/dev/null)
            
            END_TIME=$(date +%s%N)
            DURATION=$(echo "scale=3; ($END_TIME - $START_TIME) / 1000000000" | bc 2>/dev/null || echo "?")
            
            echo "File $i completed in ${DURATION}s" >> "$TEST_RESULT"
            
            # 결과 로깅
            if echo "$RESPONSE" | grep -q '"success"'; then
                log_success "파일 $i 처리 완료"
            else
                log_warn "파일 $i 처리 실패"
            fi
        ) &
        
        PROCESSING_PIDS+=($!)
        
        # 동시 처리를 위해 약간 시간차를 둠 (100ms)
        sleep 0.1
    done
    
    log_success "모든 처리 요청 발송 완료"
    echo "  PID: ${PROCESSING_PIDS[@]}"
    
    # 모든 백그라운드 작업이 완료될 때까지 대기
    log_info "처리 완료 대기 중..."
    echo ""
    
    local completed=0
    local total=${#PROCESSING_PIDS[@]}
    
    for pid in "${PROCESSING_PIDS[@]}"; do
        if wait $pid 2>/dev/null; then
            ((completed++))
            echo -ne "\r  진행: $completed/$total 완료"
        fi
    done
    
    echo ""
    echo ""
    
    log_success "모든 처리 완료"
    
    rm -f /tmp/concurrent_test_running
}

# Analyze results
analyze_results() {
    section "4️⃣  결과 분석"
    
    # 모니터링 프로세스 종료
    if [ -f /tmp/concurrent_test_monitor.pid ]; then
        MONITOR_PID=$(cat /tmp/concurrent_test_monitor.pid)
        kill $MONITOR_PID 2>/dev/null || true
        sleep 1
    fi
    
    # 처리 결과
    if [ -f "$TEST_RESULT" ]; then
        log_info "파일 처리 결과:"
        cat "$TEST_RESULT"
    fi
    
    # 모니터링 데이터 분석
    MONITOR_LOG=$(ls -t /tmp/concurrent_test_monitor_*.log 2>/dev/null | head -1)
    
    if [ -z "$MONITOR_LOG" ]; then
        log_warn "모니터링 데이터 없음"
        return
    fi
    
    log_info "리소스 사용률:"
    
    # CPU 사용률 분석
    CPU_MAX=$(tail -n +2 "$MONITOR_LOG" | awk -F',' '{print $2}' | sort -n | tail -1)
    CPU_AVG=$(tail -n +2 "$MONITOR_LOG" | awk -F',' '{sum+=$2; count++} END {print sum/count}')
    
    echo "  CPU 사용률:"
    echo "    - 평균: ${CPU_AVG}%"
    echo "    - 최대: ${CPU_MAX}%"
    
    # 메모리 분석
    MEM_MAX=$(tail -n +2 "$MONITOR_LOG" | awk -F',' '{print $3}' | sort -n | tail -1)
    MEM_INITIAL=$(tail -n 2 "$MONITOR_LOG" | head -1 | awk -F',' '{print $3}')
    MEM_FINAL=$(tail -n 1 "$MONITOR_LOG" | awk -F',' '{print $3}')
    MEM_CHANGE=$(echo "$MEM_FINAL - $MEM_INITIAL" | bc 2>/dev/null || echo "?")
    
    echo "  메모리 사용량:"
    echo "    - 최대: ${MEM_MAX}MB"
    echo "    - 변화: ${MEM_CHANGE}MB"
    
    # GPU 메모리
    GPU_MAX=$(tail -n +2 "$MONITOR_LOG" | awk -F',' '{print $5}' | sort -n | tail -1)
    
    echo "  GPU 메모리:"
    echo "    - 최대: ${GPU_MAX}MB"
    
    # 스레드 분석
    THREAD_MAX=$(tail -n +2 "$MONITOR_LOG" | awk -F',' '{print $6}' | sort -n | tail -1)
    
    echo "  스레드:"
    echo "    - 최대: ${THREAD_MAX}개"
    
    if [ "$THREAD_MAX" -gt 1 ]; then
        log_success "병렬 처리 감지됨 (스레드: $THREAD_MAX)"
    else
        log_warn "병렬 처리 미감지 (스레드: $THREAD_MAX)"
    fi
    
    # Lock 대기
    LOCK_EVENTS=$(tail -n +2 "$MONITOR_LOG" | awk -F',' '{sum+=$7} END {print sum}')
    
    echo "  Lock 이벤트:"
    echo "    - 총: ${LOCK_EVENTS}건"
    
    if [ "$LOCK_EVENTS" -gt 10 ]; then
        log_warn "높은 Lock 경합 감지 (${LOCK_EVENTS}건)"
    fi
}

# Check for lock contention patterns
check_lock_patterns() {
    section "5️⃣  Lock 경합 패턴 분석"
    
    log_info "최근 로그에서 Lock 관련 메시지:"
    
    docker logs "${CONTAINER_NAME}" --since 30s 2>&1 | \
        grep -iE 'lock|acquire|release|wait|blocked|contention' | \
        head -20 || echo "  Lock 메시지 없음"
    
    echo ""
    log_info "Python 스레드 상태:"
    
    PYTHON_PID=$(docker exec "${CONTAINER_NAME}" ps aux 2>/dev/null | grep '[p]ython' | head -1 | awk '{print $2}' || echo "")
    
    if [ -n "$PYTHON_PID" ]; then
        docker exec "${CONTAINER_NAME}" bash -c "
            for tid in /proc/$PYTHON_PID/task/*/status; do
                [ -e \"\$tid\" ] && {
                    name=\$(grep '^Name:' \"\$tid\" | awk '{print \$2}')
                    state=\$(grep '^State:' \"\$tid\" | awk '{print \$2}')
                    utime=\$(grep '^Utime:' \"\$tid\" | awk '{print \$2}')
                    printf '  %s: State=%s Utime=%s\n' \"\$name\" \"\$state\" \"\$utime\"
                }
            done | head -15
        " 2>/dev/null || true
    fi
}

# Generate detailed report
generate_detailed_report() {
    section "6️⃣  상세 분석 보고서"
    
    REPORT_FILE="/tmp/concurrent_test_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "=========================================="
        echo "STT Engine Concurrent Processing Test Report"
        echo "Generated: $(timestamp)"
        echo "=========================================="
        echo ""
        echo "테스트 설정:"
        echo "  - 동시 파일 수: $CONCURRENT_JOBS"
        echo "  - API URL: $API_URL"
        echo "  - 컨테이너: $CONTAINER_NAME"
        echo ""
        echo "결과 분석:"
        echo "=========================================="
        
        MONITOR_LOG=$(ls -t /tmp/concurrent_test_monitor_*.log 2>/dev/null | head -1)
        if [ -n "$MONITOR_LOG" ]; then
            echo ""
            echo "리소스 사용률 (상세):"
            echo "$(tail -20 "$MONITOR_LOG")"
        fi
        
        echo ""
        echo "진단:"
        echo "=========================================="
        
        # 진단 결과
        PYTHON_PID=$(docker exec "${CONTAINER_NAME}" ps aux 2>/dev/null | grep '[p]ython' | head -1 | awk '{print $2}' || echo "")
        THREAD_COUNT=$(docker exec "${CONTAINER_NAME}" cat /proc/"$PYTHON_PID"/status 2>/dev/null | grep "Threads:" | awk '{print $2}' || echo "0")
        
        if [ "$THREAD_COUNT" -le 1 ]; then
            echo ""
            echo "⚠️  병렬 처리가 활성화되지 않았습니다"
            echo "   원인:"
            echo "   1. Queue가 사용되지 않고 있음"
            echo "   2. ThreadPoolExecutor가 시작되지 않음"
            echo "   3. 요청이 순차적으로 처리되고 있음"
            echo ""
            echo "해결 방안:"
            echo "   1. api_server.py에서 Queue/ThreadPool 설정 확인"
            echo "   2. 동시 처리 활성화 확인 (concurrent_workers 설정)"
            echo "   3. 로그에서 동시 처리 메시지 확인"
        else
            echo ""
            echo "✅ 병렬 처리가 활성화되었습니다"
            echo "   스레드 수: $THREAD_COUNT"
            echo ""
            echo "다음 사항을 확인하세요:"
            echo "   1. Lock 경합이 성능을 저하시키는가?"
            echo "   2. CPU가 충분히 활용되는가?"
            echo "   3. 메모리가 과도하게 증가하는가?"
        fi
        
    } | tee "$REPORT_FILE"
    
    log_success "보고서 저장: $REPORT_FILE"
}

# Main
main() {
    clear
    
    echo -e "${CYAN}"
    cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║    STT Engine Concurrent Processing Test                  ║
║    동시 파일 처리 성능 테스트                              ║
╚════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    # 컨테이너 상태 확인
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_error "컨테이너 '$CONTAINER_NAME'이 실행 중이 아닙니다"
        exit 1
    fi
    
    log_success "컨테이너 확인 완료"
    
    # 테스트 시작
    prepare_test_audio
    start_monitoring
    sleep 2
    
    run_concurrent_test
    
    sleep 3  # 모니터링이 완료되도록 대기
    
    analyze_results
    check_lock_patterns
    generate_detailed_report
    
    # 최종 요약
    section "🎯 테스트 완료"
    echo ""
    echo "📊 데이터 위치:"
    echo "   - 모니터링 로그: /tmp/concurrent_test_monitor_*.log"
    echo "   - 처리 결과: /tmp/concurrent_test_result_*.json"
    echo "   - 분석 보고서: /tmp/concurrent_test_report_*.txt"
    echo ""
    echo "🔍 다음 단계:"
    echo "   1. 병렬 처리 여부 확인 (스레드 수 > 1)"
    echo "   2. Lock 경합 수준 확인"
    echo "   3. CPU/메모리 사용률 검토"
    echo "   4. 처리 시간 비교 (순차 vs 병렬)"
    echo ""
}

main "$@"
