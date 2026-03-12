#!/bin/bash

# STT Engine 진단 도구 - 빠른 실행 가이드
# ==============================================

cat << 'EOF'

╔════════════════════════════════════════════════════════════╗
║   STT Engine 진단 도구 - 빠른 시작 가이드                  ║
╚════════════════════════════════════════════════════════════╝

📌 생성된 3가지 진단 도구:

1. diagnose_memory_leak.sh (18KB)
   - 메모리 + 동시 처리 Lock 종합 진단
   - 소요 시간: ~70초

2. test_concurrent_processing.sh (14KB)
   - 동시 파일 처리 성능 테스트
   - 기본값: 2개 파일 동시 처리
   - 소요 시간: ~90초

3. trace_memory_deep.sh (12KB)
   - 메모리 할당 위치 상세 추적
   - 소요 시간: ~10초

========================================

🚀 빠른 실행 (권장 순서):

[1단계] 종합 진단 (메모리 누수 + Lock)
$ bash scripts/diagnose_memory_leak.sh
(약 70초 소요)

[2단계] 동시 처리 테스트 (기본값: 2개 파일)
$ bash scripts/test_concurrent_processing.sh
(약 90초 소요)

[선택] 상세 메모리 추적 (필요시만)
$ bash scripts/trace_memory_deep.sh
(약 10초 소요)

========================================

📋 결과 확인:

• diagnose_memory_leak.sh 결과:
  ✅ 정상: 메모리 변화 < 100MB
  ⚠️  경고: 메모리 변화 100-500MB
  ❌ 문제: 메모리 변화 > 500MB

  ✅ 정상: 활성 스레드 > 2개
  ❌ 문제: 활성 스레드 = 1개 (순차 처리)

  ✅ 정상: Lock 이벤트 < 5개
  ❌ 문제: Lock 이벤트 > 10개

• test_concurrent_processing.sh 결과:
  ✅ 병렬 처리 성공: "병렬 처리 감지됨"
  ❌ 병렬 처리 실패: "병렬 처리 미감지"
  
  ✅ 정상: 병렬 효율 > 80%
  ❌ 문제: 병렬 효율 < 20%

• trace_memory_deep.sh 결과:
  ✅ 정상: 메모리 할당이 일정한 위치에서만
  ❌ 누수: 특정 함수에서 계속 증가

========================================

🎯 진단 시나리오:

[ 메모리가 계속 증가 ]
→ 1. diagnose_memory_leak.sh
→ 2. trace_memory_deep.sh (메모리 할당 위치 확인)

[ 동시 처리가 느림 ]
→ 1. test_concurrent_processing.sh
→ 2. diagnose_memory_leak.sh (Lock 확인)

[ 로그 없이 메모리만 소모 ]
→ 1. diagnose_memory_leak.sh (프로세스 상태 확인)
   - D 상태 있음? → I/O hang
   - Z 상태 있음? → 좀비 프로세스
   - 메모리 증가? → 메모리 누수
→ 2. trace_memory_deep.sh (누수 위치 추적)

========================================

💾 출력 파일:

/tmp/memory_monitor.csv
  → Excel/Sheets에서 열기 (그래프 생성 가능)

/tmp/concurrent_test_*.log, *.json, *.txt
  → 각 테스트별 결과 파일

========================================

⚙️  커스터마이징:

• 동시 처리 파일 수 변경:
  $ bash scripts/test_concurrent_processing.sh 5  (5개 파일)

• 컨테이너 이름 변경:
  $ CONTAINER_NAME="다른-이름" bash scripts/diagnose_memory_leak.sh

• 모니터링 시간 변경:
  [diagnose_memory_leak.sh에서]
  DURATION=120  (120초로 변경)
  INTERVAL=5    (5초 간격으로 변경)

========================================

📖 자세한 가이드:

cat scripts/README_DIAGNOSTICS.md

========================================

✅ 문제 해결 확인 체크리스트:

□ 메모리 변화 < 100MB
□ 활성 스레드 > 2개
□ Lock 이벤트 < 5개
□ 병렬 처리 감지됨
□ 병렬 처리 효율 > 80%
□ GPU 메모리 안정적
□ 4-5개 파일 순차 처리 모두 성공

========================================

🆘 문제 해결 팁:

# 컨테이너 로그 보기
docker logs -f stt-api

# GPU 실시간 모니터링
watch -n 1 nvidia-smi

# 최근 Lock 관련 로그
docker logs stt-api | grep -i "lock"

# 처리 시간 확인
docker logs stt-api | grep "processing_time"

========================================

EOF
