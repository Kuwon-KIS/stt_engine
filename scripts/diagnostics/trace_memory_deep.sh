#!/bin/bash

#############################################################################
#                    STT Engine Deep Memory Tracer                           #
#                                                                             #
# 메모리 누수의 정확한 원인을 파악하기 위한 상세 추적 도구                    #
# - 파이썬 객체 메모리 사용량                                                #
# - 메모리 할당 경로 추적                                                   #
# - 가비지 컬렉션 상태                                                      #
# - 스레드 상태 모니터링                                                    #
#############################################################################

set -e

CONTAINER_NAME="stt-api"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

section() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
}

# Create memory trace script
create_trace_script() {
    cat > /tmp/memory_trace.py << 'PYEOF'
#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/app')

import gc
import tracemalloc
import psutil
import threading
import time

def get_memory_usage():
    """Get current process memory usage"""
    process = psutil.Process(os.getpid())
    return process.memory_info()

def get_top_allocations(top_n=10):
    """Get top memory allocations"""
    if not tracemalloc.is_tracing():
        tracemalloc.start()
    
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    print("\n📊 상위 메모리 할당 위치:")
    print(f"{'#':<3} {'Size':<12} {'Percent':<10} {'Location':<50}")
    print("-" * 75)
    
    total = sum(stat.size for stat in top_stats)
    
    for index, stat in enumerate(top_stats[:top_n], 1):
        frame = stat.traceback[0]
        size_mb = stat.size / 1024 / 1024
        percent = (stat.size / total * 100) if total > 0 else 0
        location = f"{frame.filename}:{frame.lineno}"
        print(f"{index:<3} {size_mb:>8.1f}MB  {percent:>6.1f}%  {location:<50}")

def get_gc_stats():
    """Get garbage collection statistics"""
    print("\n🗑️  가비지 컬렉션 상태:")
    
    gc.collect()
    stats = gc.get_stats()
    
    for i, stat in enumerate(stats):
        print(f"\nGeneration {i}:")
        print(f"  Collections: {stat.get('collections', 0)}")
        print(f"  Collected: {stat.get('collected', 0)}")
        print(f"  Uncollectable: {stat.get('uncollectable', 0)}")
    
    # Show objects by type
    gc.collect()
    obj_counts = {}
    
    for obj in gc.get_objects():
        obj_type = type(obj).__name__
        obj_counts[obj_type] = obj_counts.get(obj_type, 0) + 1
    
    print("\n📈 객체 타입별 개수 (상위 15):")
    sorted_counts = sorted(obj_counts.items(), key=lambda x: x[1], reverse=True)
    
    for obj_type, count in sorted_counts[:15]:
        size_estimate = sys.getsizeof(obj) * count / 1024 / 1024
        print(f"  {obj_type:<30} {count:>8} 개 (~{size_estimate:>6.1f}MB)")

def check_torch_memory():
    """Check PyTorch GPU memory if available"""
    try:
        import torch
        if torch.cuda.is_available():
            print("\n🎮 PyTorch GPU 메모리:")
            print(f"  Total: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
            print(f"  Used: {torch.cuda.memory_allocated(0) / 1024**3:.1f}GB")
            print(f"  Cached: {torch.cuda.memory_reserved(0) / 1024**3:.1f}GB")
            print(f"  Free: {(torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)) / 1024**3:.1f}GB")
    except ImportError:
        pass

def check_threads():
    """Check active threads"""
    print("\n🧵 활성 스레드:")
    print(f"  총 스레드: {threading.active_count()}")
    print(f"  스레드 목록:")
    
    for thread in threading.enumerate():
        status = "데몬" if thread.daemon else "일반"
        print(f"    - {thread.name:<30} ({status})")

def check_imports():
    """Check loaded modules"""
    print("\n📦 로드된 모듈 (메모리 관련, 상위 10):")
    
    import sys
    modules = sys.modules
    module_sizes = {}
    
    for name, module in modules.items():
        try:
            module_sizes[name] = sys.getsizeof(module)
        except:
            pass
    
    sorted_modules = sorted(module_sizes.items(), key=lambda x: x[1], reverse=True)
    
    for name, size in sorted_modules[:10]:
        size_kb = size / 1024
        print(f"  {name:<40} {size_kb:>8.1f}KB")

def main():
    print("=" * 75)
    print("STT Engine Memory Deep Trace")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 75)
    
    # Process memory
    mem = get_memory_usage()
    print(f"\n💾 프로세스 메모리:")
    print(f"  RSS (물리 메모리): {mem.rss / 1024 / 1024:.1f}MB")
    print(f"  VMS (가상 메모리): {mem.vms / 1024 / 1024:.1f}MB")
    
    # Top allocations
    get_top_allocations(15)
    
    # GC stats
    get_gc_stats()
    
    # Torch memory
    check_torch_memory()
    
    # Threads
    check_threads()
    
    # Modules
    check_imports()
    
    print("\n" + "=" * 75)

if __name__ == '__main__':
    main()
PYEOF
    
    chmod +x /tmp/memory_trace.py
}

# Check if container is running
check_container() {
    section "1️⃣  컨테이너 확인"
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_error "컨테이너 '$CONTAINER_NAME' 이 실행 중이 아닙니다"
        exit 1
    fi
    
    log_success "컨테이너 실행 중"
}

# Inject trace script
run_trace() {
    section "2️⃣  메모리 추적 실행"
    
    log_info "Python 메모리 분석 스크립트 실행 중..."
    
    docker cp /tmp/memory_trace.py "${CONTAINER_NAME}:/tmp/"
    
    docker exec "${CONTAINER_NAME}" python3 /tmp/memory_trace.py 2>/dev/null || {
        log_warn "Python 추적 실패, 기본 분석 수행"
    }
}

# System memory analysis
system_memory_analysis() {
    section "3️⃣  시스템 메모리 분석"
    
    log_info "컨테이너 내부 메모리:"
    docker exec "${CONTAINER_NAME}" free -h 2>/dev/null || true
    
    echo ""
    log_info "메모리 풀:"
    docker exec "${CONTAINER_NAME}" cat /proc/meminfo 2>/dev/null | grep -E 'MemTotal|MemFree|MemAvailable|Buffers|Cached' || true
}

# Process analysis
process_analysis() {
    section "4️⃣  프로세스 메모리 분석"
    
    log_info "상위 메모리 소비 프로세스:"
    docker exec "${CONTAINER_NAME}" ps aux --sort=-%mem | head -8 2>/dev/null || true
}

# File descriptor analysis
fd_analysis() {
    section "5️⃣  파일 디스크립터 누수 감지"
    
    PYTHON_PID=$(docker exec "${CONTAINER_NAME}" ps aux 2>/dev/null | grep '[p]ython' | head -1 | awk '{print $2}' || echo "")
    
    if [ -z "$PYTHON_PID" ]; then
        log_warn "Python PID를 찾을 수 없습니다"
        return
    fi
    
    FD_COUNT=$(docker exec "${CONTAINER_NAME}" ls -1 /proc/"$PYTHON_PID"/fd 2>/dev/null | wc -l || echo "0")
    
    echo "파일 디스크립터 수: $FD_COUNT"
    echo ""
    
    log_info "파일 디스크립터 타입 분석:"
    docker exec "${CONTAINER_NAME}" bash -c "
        for fd in /proc/$PYTHON_PID/fd/*; do
            [ -e \"\$fd\" ] && readlink \"\$fd\" | sed 's/^/  /'
        done | sort | uniq -c | sort -rn | head -20
    " 2>/dev/null || true
}

# Network connection analysis
network_analysis() {
    section "6️⃣  네트워크 연결 분석"
    
    log_info "활성 연결 (ESTABLISHED):"
    docker exec "${CONTAINER_NAME}" sh -c "(netstat -tupn 2>/dev/null || ss -tupn 2>/dev/null) | grep ESTABLISHED | wc -l" || echo "0"
    
    echo ""
    log_info "연결 상태 분포:"
    docker exec "${CONTAINER_NAME}" sh -c "(netstat -an 2>/dev/null || ss -an 2>/dev/null)" | awk 'NR>2 {print $6}' | sort | uniq -c | sort -rn || true
}

# Recent activity log
activity_log() {
    section "7️⃣  최근 활동 로그"
    
    log_info "최근 30초 로그:"
    docker logs "${CONTAINER_NAME}" --since 30s 2>&1 | tail -30 || true
}

# Generate summary report
generate_summary() {
    section "8️⃣  진단 요약"
    
    REPORT_FILE="/tmp/memory_trace_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "STT Engine Memory Deep Trace Report"
        echo "Generated: $(timestamp)"
        echo ""
        echo "=== 진단 항목 ==="
        echo "1. ✅ 파이썬 메모리 할당 (tracemalloc)"
        echo "2. ✅ 가비지 컬렉션 상태"
        echo "3. ✅ PyTorch GPU 메모리"
        echo "4. ✅ 스레드 상태"
        echo "5. ✅ 로드된 모듈"
        echo "6. ✅ 시스템 메모리"
        echo "7. ✅ 프로세스 분석"
        echo "8. ✅ 파일 디스크립터"
        echo "9. ✅ 네트워크 연결"
        echo ""
        echo "=== 권장사항 ==="
        echo ""
        echo "메모리가 계속 증가하면:"
        echo "  1. Top allocations를 확인 (어디서 메모리를 할당하는가)"
        echo "  2. GC 통계 확인 (수집되지 않은 객체가 있는가)"
        echo "  3. 파일 디스크립터 확인 (누수 징후)"
        echo "  4. 스레드 확인 (종료되지 않은 스레드)"
        echo "  5. stt_engine.py의 메모리 정리 코드 재검토"
        echo ""
    } > "$REPORT_FILE"
    
    log_success "보고서 저장: $REPORT_FILE"
}

# Main
main() {
    clear
    
    echo -e "${BLUE}"
    cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║      STT Engine Deep Memory Tracer                         ║
║    정확한 메모리 누수 원인 파악 도구                       ║
╚════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    # Create trace script
    create_trace_script
    
    # Run diagnostics
    check_container
    run_trace
    system_memory_analysis
    process_analysis
    fd_analysis
    network_analysis
    activity_log
    generate_summary
    
    section "🎯 다음 단계"
    echo ""
    echo "📍 로그 없이 메모리만 소모되는 경우 체크리스트:"
    echo ""
    echo "1️⃣  GPU 행 확인:"
    echo "   - nvidia-smi로 GPU 상태 확인"
    echo "   - model.to(cuda) 이후 torch.cuda.synchronize() 있는가?"
    echo ""
    echo "2️⃣  무한 루프 확인:"
    echo "   - 프로세스 상태가 'R' 인가? (CPU 사용 중)"
    echo "   - 코드의 loop/retry 로직 검토"
    echo ""
    echo "3️⃣  메모리 누수 확인:"
    echo "   - Top allocations에서 증가하는 항목 찾기"
    echo "   - GC 통계에서 uncollectable 객체 확인"
    echo ""
    echo "4️⃣  리소스 누수 확인:"
    echo "   - 파일 디스크립터 수 증가 추적"
    echo "   - 네트워크 연결 증가 추적"
    echo ""
    echo "5️⃣  스레드 확인:"
    echo "   - 데몬 스레드가 제대로 종료되는가?"
    echo "   - 스레드 갯수가 계속 증가하는가?"
    echo ""
}

main "$@"
