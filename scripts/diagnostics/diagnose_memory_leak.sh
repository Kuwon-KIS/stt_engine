#!/bin/bash

#############################################################################
#                    STT Engine Memory Leak Diagnostic Tool                 #
#                                                                             #
# 로그없이 메모리만 소모되는 문제 진단                                         #
# - 컨테이너 메모리 모니터링                                                 #
# - GPU 메모리 추적                                                         #
# - 프로세스 상태 분석                                                      #
# - 리소스 누수 감지                                                        #
#############################################################################

set -e

CONTAINER_NAME="stt-api"
INTERVAL=2  # 수집 간격 (초)
DURATION=60 # 실행 시간 (초)
SAMPLES=$((DURATION / INTERVAL))

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Timestamp
timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

# Log levels
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

# Section header
section() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
}

# Check if container exists
check_container() {
    section "1️⃣  컨테이너 상태 확인"
    
    if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_error "컨테이너 '$CONTAINER_NAME' 를 찾을 수 없습니다"
        exit 1
    fi
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_error "컨테이너 '$CONTAINER_NAME' 가 실행 중이 아닙니다"
        exit 1
    fi
    
    log_success "컨테이너 '$CONTAINER_NAME' 실행 중"
    
    # Get container info
    CONTAINER_ID=$(docker ps --format '{{.ID}}' --filter "name=${CONTAINER_NAME}")
    echo "Container ID: $CONTAINER_ID"
    
    # Get container creation time
    CREATED=$(docker inspect --format='{{.Created}}' "${CONTAINER_NAME}")
    echo "Created: $CREATED"
}

# Check health endpoint
check_health() {
    section "2️⃣  서비스 상태 확인"
    
    HEALTH_STATUS=$(docker exec "${CONTAINER_NAME}" curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health 2>/dev/null || echo "000")
    
    if [ "$HEALTH_STATUS" == "200" ]; then
        log_success "STT API 정상 응답 (HTTP 200)"
    else
        log_warn "STT API 비정상 응답 (HTTP $HEALTH_STATUS)"
    fi
}

# Get initial process info
get_process_info() {
    local label="$1"
    
    log_info "$label"
    
    # Python 프로세스 찾기
    PYTHON_PID=$(docker exec "${CONTAINER_NAME}" ps aux 2>/dev/null | grep '[p]ython' | head -1 | awk '{print $2}' || echo "")
    
    if [ -z "$PYTHON_PID" ]; then
        log_warn "Python 프로세스를 찾을 수 없습니다"
        return
    fi
    
    echo "Python PID: $PYTHON_PID"
    
    # 프로세스 상태
    docker exec "${CONTAINER_NAME}" ps -p "$PYTHON_PID" -o pid,vsz,rss,stat,etime 2>/dev/null || true
}

# Monitor container memory
monitor_memory() {
    section "3️⃣  컨테이너 메모리 모니터링 (${DURATION}초)"
    
    echo "시간,Docker 메모리 (MB),사용 비율,GPU 메모리 (MB),상태" > /tmp/memory_monitor.csv
    
    log_info "수집 중... (샘플: $SAMPLES개, 간격: ${INTERVAL}초)"
    echo ""
    
    for i in $(seq 1 $SAMPLES); do
        # Docker 메모리
        DOCKER_STATS=$(docker stats --no-stream --format "{{.MemUsage}}" "${CONTAINER_NAME}" 2>/dev/null | head -1)
        DOCKER_MEM=$(echo "$DOCKER_STATS" | awk '{print $1}' | sed 's/MiB//' | sed 's/GiB/000/' | awk '{printf "%.0f", $1}')
        
        # 컨테이너 내부 메모리 (free 명령어)
        CONTAINER_FREE=$(docker exec "${CONTAINER_NAME}" free -b 2>/dev/null | grep Mem | awk '{print $3}' || echo "0")
        CONTAINER_MEM=$((CONTAINER_FREE / 1024 / 1024))
        
        # 메모리 사용률
        MEMORY_PERCENT=$(docker stats --no-stream --format "{{.MemPerc}}" "${CONTAINER_NAME}" 2>/dev/null | sed 's/%//')
        
        # GPU 메모리 (호스트에서만 가능)
        GPU_MEM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 || echo "N/A")
        
        # 프로세스 상태
        PYTHON_PID=$(docker exec "${CONTAINER_NAME}" ps aux 2>/dev/null | grep '[p]ython' | head -1 | awk '{print $2}' || echo "")
        PROC_STAT=$(docker exec "${CONTAINER_NAME}" ps -p "$PYTHON_PID" -o stat= 2>/dev/null || echo "?")
        
        # CSV 저장
        TIMESTAMP=$(timestamp)
        echo "$TIMESTAMP,$DOCKER_MEM,$MEMORY_PERCENT,$GPU_MEM,$PROC_STAT" >> /tmp/memory_monitor.csv
        
        # 화면 출력
        printf "[%2d/%d] Docker: %6s MB | Usage: %6.1f%% | GPU: %6s MB | PID: %6s | Stat: %s\n" \
            "$i" "$SAMPLES" "$DOCKER_MEM" "$MEMORY_PERCENT" "$GPU_MEM" "$PYTHON_PID" "$PROC_STAT"
        
        sleep "$INTERVAL"
    done
    
    echo ""
    log_success "메모리 모니터링 완료"
}

# Analyze memory trend
analyze_memory_trend() {
    section "4️⃣  메모리 트렌드 분석"
    
    # CSV에서 Docker 메모리값 추출
    DOCKER_VALUES=$(tail -n +2 /tmp/memory_monitor.csv | awk -F',' '{print $2}')
    
    if [ -z "$DOCKER_VALUES" ]; then
        log_warn "메모리 데이터가 없습니다"
        return
    fi
    
    # 첫 번째와 마지막 값
    FIRST_MEM=$(echo "$DOCKER_VALUES" | head -1)
    LAST_MEM=$(echo "$DOCKER_VALUES" | tail -1)
    MAX_MEM=$(echo "$DOCKER_VALUES" | sort -n | tail -1)
    MIN_MEM=$(echo "$DOCKER_VALUES" | sort -n | head -1)
    
    # 메모리 변화
    MEM_CHANGE=$((LAST_MEM - FIRST_MEM))
    MEM_CHANGE_PERCENT=$(echo "scale=1; ($MEM_CHANGE * 100) / $FIRST_MEM" | bc 2>/dev/null || echo "?")
    
    echo "메모리 변화:"
    echo "  - 시작: $FIRST_MEM MB"
    echo "  - 종료: $LAST_MEM MB"
    echo "  - 최대: $MAX_MEM MB"
    echo "  - 최소: $MIN_MEM MB"
    echo "  - 변화량: $MEM_CHANGE MB ($MEM_CHANGE_PERCENT%)"
    echo ""
    
    if [ "$MEM_CHANGE" -gt 100 ]; then
        log_warn "메모리가 ${MEM_CHANGE}MB 증가했습니다 (누수 가능성 있음)"
    elif [ "$MEM_CHANGE" -lt -100 ]; then
        log_info "메모리가 ${MEM_CHANGE}MB 감소했습니다"
    else
        log_success "메모리가 안정적입니다 (변화량: $MEM_CHANGE MB)"
    fi
}

# Check container processes
check_processes() {
    section "5️⃣  컨테이너 내부 프로세스 상태"
    
    log_info "상위 메모리 사용 프로세스:"
    docker exec "${CONTAINER_NAME}" ps aux --sort=-%mem | head -6 2>/dev/null || true
    
    echo ""
    log_info "Python 프로세스 상세 정보:"
    PYTHON_PID=$(docker exec "${CONTAINER_NAME}" ps aux 2>/dev/null | grep '[p]ython' | head -1 | awk '{print $2}' || echo "")
    
    if [ -n "$PYTHON_PID" ]; then
        docker exec "${CONTAINER_NAME}" ps -p "$PYTHON_PID" -o pid,ppid,vsz,rss,stat,etime,cmd 2>/dev/null | head -2 || true
    fi
}

# Check open files and sockets
check_file_handles() {
    section "6️⃣  파일 디스크립터 & 소켓 상태"
    
    PYTHON_PID=$(docker exec "${CONTAINER_NAME}" ps aux 2>/dev/null | grep '[p]ython' | head -1 | awk '{print $2}' || echo "")
    
    if [ -z "$PYTHON_PID" ]; then
        log_warn "Python PID를 찾을 수 없습니다"
        return
    fi
    
    log_info "열린 파일 디스크립터 수:"
    FD_COUNT=$(docker exec "${CONTAINER_NAME}" ls -1 /proc/"$PYTHON_PID"/fd 2>/dev/null | wc -l || echo "0")
    echo "  파일 디스크립터: $FD_COUNT개"
    
    log_info "네트워크 연결:"
    docker exec "${CONTAINER_NAME}" sh -c "(netstat -tupn 2>/dev/null || ss -tupn 2>/dev/null) | grep ESTABLISHED | wc -l" || true
    echo "  활성 연결 (ESTABLISHED)"
    
    log_info "소켓 상태:"
    docker exec "${CONTAINER_NAME}" sh -c "netstat -tupn 2>/dev/null || ss -tupn 2>/dev/null" | head -10 || true
}

# Check recent logs for errors
check_logs() {
    section "7️⃣  컨테이너 로그 확인 (최근 50줄)"
    
    log_info "오류 관련 로그:"
    docker logs "${CONTAINER_NAME}" 2>&1 | grep -i 'error\|exception\|hang\|stuck\|oom' | tail -10 || log_warn "오류 로그가 없습니다"
    
    echo ""
    log_info "최근 로그:"
    docker logs "${CONTAINER_NAME}" 2>&1 | tail -20 || true
}

# Check GPU status
check_gpu() {
    section "8️⃣  GPU 상태 확인"
    
    nvidia-smi --query-gpu=index,name,driver_version,memory.total,memory.used,memory.free --format=csv 2>/dev/null || log_warn "nvidia-smi를 실행할 수 없습니다"
    
    echo ""
    log_info "GPU 프로세스:"
    nvidia-smi pmon -c 1 2>/dev/null | grep -v "No running processes found" || true
}

# Generate report
generate_report() {
    section "9️⃣  진단 보고서 생성"
    
    REPORT_FILE="/tmp/stt_memory_diagnosis_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "STT Engine Memory Leak Diagnostic Report"
        echo "Generated: $(timestamp)"
        echo "Container: $CONTAINER_NAME"
        echo ""
        echo "=== Memory Monitor Data ==="
        cat /tmp/memory_monitor.csv
        echo ""
        echo "=== Summary ==="
        tail -n +2 /tmp/memory_monitor.csv | awk -F',' 'BEGIN {
            first=1
            for(i=1; i<=NF; i++) {
                if($i ~ /^[0-9]+$/) {
                    if(first) {first_mem=$i; first=0}
                    last_mem=$i
                    max_mem = (max_mem < $i) ? $i : max_mem
                    min_mem = (min_mem == 0 || min_mem > $i) ? $i : min_mem
                }
            }
        } END {
            print "Initial Memory: " first_mem " MB"
            print "Final Memory: " last_mem " MB"
            print "Change: " (last_mem - first_mem) " MB"
            print "Max: " max_mem " MB"
            print "Min: " min_mem " MB"
        }'
    } > "$REPORT_FILE"
    
    log_success "보고서 저장: $REPORT_FILE"
    cat "$REPORT_FILE"
}

# Check for lock contention
check_lock_contention() {
    section "🔒 동시 처리 Lock 상태 분석"
    
    log_info "프로세스 스레드 상태:"
    PYTHON_PID=$(docker exec "${CONTAINER_NAME}" ps aux 2>/dev/null | grep '[p]ython' | head -1 | awk '{print $2}' || echo "")
    
    if [ -z "$PYTHON_PID" ]; then
        log_warn "Python PID를 찾을 수 없습니다"
        return
    fi
    
    # 스레드 수 확인
    THREAD_COUNT=$(docker exec "${CONTAINER_NAME}" cat /proc/"$PYTHON_PID"/status 2>/dev/null | grep "Threads:" | awk '{print $2}' || echo "0")
    echo "  활성 스레드: $THREAD_COUNT개"
    
    if [ "$THREAD_COUNT" -gt 1 ]; then
        log_info "멀티스레드 처리 감지"
        
        # 스레드별 상태
        docker exec "${CONTAINER_NAME}" ls -1 /proc/"$PYTHON_PID"/task 2>/dev/null | wc -l | xargs -I {} echo "  스레드 파일: {}개"
        
        # 스레드별 상태 상세
        echo ""
        echo "  스레드별 상태:"
        docker exec "${CONTAINER_NAME}" bash -c "
            for tid in /proc/$PYTHON_PID/task/*/status; do
                [ -e \"\$tid\" ] && {
                    name=\$(grep '^Name:' \"\$tid\" | awk '{print \$2}')
                    state=\$(grep '^State:' \"\$tid\" | awk '{print \$2}')
                    printf '    - %s: %s\n' \"\$name\" \"\$state\"
                }
            done | sort | uniq -c
        " 2>/dev/null || true
    else
        log_warn "싱글 스레드 모드 (병렬 처리 미확인)"
    fi
}

# Analyze concurrent file processing
analyze_concurrent_processing() {
    section "⚙️  동시 파일 처리 패턴 분석"
    
    log_info "최근 로그에서 동시 처리 패턴 추출:"
    
    # 파일 처리 시작/종료 시간 추출
    TEMP_LOG="/tmp/processing_log.txt"
    docker logs "${CONTAINER_NAME}" 2>&1 | grep -E 'processing|파일|완료' | tail -50 > "$TEMP_LOG" || true
    
    if [ ! -s "$TEMP_LOG" ]; then
        log_warn "처리 로그가 없습니다"
        return
    fi
    
    echo ""
    log_info "파일 처리 순서:"
    cat "$TEMP_LOG" | head -20
    
    # 동시성 분석
    echo ""
    log_info "동시성 분석:"
    
    # 시간 순서로 시작/종료 확인
    grep -E 'start|begin|processing' "$TEMP_LOG" | wc -l | xargs -I {} echo "  파일 처리 시작: {} 건"
    grep -E 'complete|finish|done' "$TEMP_LOG" | wc -l | xargs -I {} echo "  파일 처리 완료: {} 건"
    
    # Lock 관련 로그 찾기
    echo ""
    log_info "Lock 관련 메시지:"
    docker logs "${CONTAINER_NAME}" 2>&1 | grep -i 'lock\|wait\|blocked\|timeout' | tail -10 || echo "  Lock 메시지 없음"
}

# Detect deadlock
detect_deadlock() {
    section "🚫 데드락 감지"
    
    PYTHON_PID=$(docker exec "${CONTAINER_NAME}" ps aux 2>/dev/null | grep '[p]ython' | head -1 | awk '{print $2}' || echo "")
    
    if [ -z "$PYTHON_PID" ]; then
        return
    fi
    
    log_info "스레드 상태 (Z 상태 = 좀비, D 상태 = I/O 대기):"
    
    docker exec "${CONTAINER_NAME}" bash -c "
        for tid in /proc/$PYTHON_PID/task/*/status; do
            [ -e \"\$tid\" ] && {
                state=\$(grep '^State:' \"\$tid\" | awk '{print \$2}')
                if [[ \"\$state\" == \"Z\" ]] || [[ \"\$state\" == \"D\" ]]; then
                    name=\$(grep '^Name:' \"\$tid\" | awk '{print \$2}')
                    echo \"  ⚠️  $name: \$state (문제 감지!)\"
                fi
            }
        done
    " 2>/dev/null || true
    
    # CPU 대기 시간 분석
    echo ""
    log_info "CPU 사용률 분석:"
    docker exec "${CONTAINER_NAME}" ps -p "$PYTHON_PID" -o %cpu,%mem,stat,etime 2>/dev/null | tail -1 || true
}

# Monitor lock release
monitor_lock_patterns() {
    section "🔄 Lock 해제 패턴 모니터링"
    
    log_info "Lock 획득/해제 로그 검색:"
    
    PYTHON_PID=$(docker exec "${CONTAINER_NAME}" ps aux 2>/dev/null | grep '[p]ython' | head -1 | awk '{print $2}' || echo "")
    
    if [ -z "$PYTHON_PID" ]; then
        return
    fi
    
    # strace로 lock 추적 (간단한 버전)
    echo "  Lock 호출 추적 (최근 30초):"
    
    # stt_engine.py의 Lock 관련 로그 확인
    docker logs "${CONTAINER_NAME}" --since 30s 2>&1 | grep -iE 'acquire|release|lock' | head -10 || echo "    Lock 추적 로그 없음"
}

# Check for parallel execution
check_parallel_execution() {
    section "⏱️  병렬 처리 효율성 분석"
    
    log_info "처리 시간 분석:"
    
    # 단일 파일 처리 시간과 다중 파일 처리 시간 비교
    TEMP_LOG="/tmp/processing_stats.txt"
    docker logs "${CONTAINER_NAME}" 2>&1 | grep -E 'processing_time|segments_processed' | tail -20 > "$TEMP_LOG" || true
    
    if [ -s "$TEMP_LOG" ]; then
        # 파일 개수와 총 시간 추출
        FILE_COUNT=$(grep -c "processing_time" "$TEMP_LOG" || echo "0")
        
        if [ "$FILE_COUNT" -gt 0 ]; then
            TOTAL_TIME=$(grep "processing_time" "$TEMP_LOG" | awk '{sum+=$NF} END {print sum}' 2>/dev/null || echo "0")
            AVG_TIME=$(echo "scale=2; $TOTAL_TIME / $FILE_COUNT" | bc 2>/dev/null || echo "?")
            
            echo "  파일 개수: $FILE_COUNT"
            echo "  평균 처리 시간: ${AVG_TIME}초"
            
            # 병렬화 효율 추정
            SEQUENTIAL_TIME=$(echo "scale=2; $AVG_TIME * $FILE_COUNT" | bc 2>/dev/null || echo "?")
            PARALLELISM=$(echo "scale=1; 100 - (($TOTAL_TIME / $SEQUENTIAL_TIME) * 100)" | bc 2>/dev/null || echo "?")
            
            echo "  예상 순차 시간: ${SEQUENTIAL_TIME}초"
            echo "  병렬 처리 효율: ${PARALLELISM}%"
            
            if (( $(echo "$PARALLELISM < 20" | bc -l) )); then
                log_warn "병렬 처리 효율이 낮습니다 (<20%)"
                log_warn "  → Lock 경합 가능성 높음"
                log_warn "  → 순차 처리로 변경 고려"
            elif (( $(echo "$PARALLELISM > 80" | bc -l) )); then
                log_success "병렬 처리 효율이 좋습니다 (>80%)"
            fi
        fi
    else
        log_warn "처리 통계 데이터 없음"
    fi
}

# Main
main() {
    clear
    
    echo -e "${BLUE}"
    cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║         STT Engine Memory Leak Diagnostic Tool             ║
║    로그 없이 메모리만 소모되는 문제 자동 진단               ║
║    + 동시 처리 Lock 상태 분석                             ║
╚════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    check_container
    check_health
    
    # 초기 프로세스 정보
    get_process_info "초기 상태:"
    
    # 동시 처리 분석 (메모리 모니터링 전)
    check_lock_contention
    analyze_concurrent_processing
    detect_deadlock
    monitor_lock_patterns
    
    # 메모리 모니터링
    monitor_memory
    
    # 분석
    analyze_memory_trend
    check_parallel_execution
    check_processes
    check_file_handles
    check_logs
    check_gpu
    
    # 보고서
    generate_report
    
    # 최종 요약
    section "🎯 최종 진단"
    echo ""
    echo "📊 CSV 파일 위치: /tmp/memory_monitor.csv"
    echo "   (Excel/Google Sheets에서 그래프로 시각화 가능)"
    echo ""
    echo "🔍 다음 단계:"
    echo "   1. 메모리 트렌드 확인 (증가/감소/안정)"
    echo "   2. 프로세스 상태 확인 (R/S/Z 상태)"
    echo "   3. 파일 디스크립터 확인 (누수 징후)"
    echo "   4. 동시성 분석 (Lock 경합 여부)"
    echo "   5. 병렬 처리 효율 확인 (>80% vs <20%)"
    echo "   6. 로그 검토 (오류/경고 메시지)"
    echo ""
    echo "🔒 Lock 문제 진단:"
    echo "   - 스레드 수 < 2 → 병렬 처리 안 됨"
    echo "   - 병렬 효율 < 20% → Lock 경합 높음"
    echo "   - 상태: Z 또는 D → Deadlock 위험"
    echo ""
}

main "$@"
