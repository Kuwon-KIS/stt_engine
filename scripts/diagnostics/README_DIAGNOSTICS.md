# STT Engine 진단 도구 가이드

로그 없이 메모리만 소모되는 문제와 동시 처리 Lock 문제를 진단하는 3가지 도구입니다.

---

## 🚀 빠른 시작

### 1️⃣ 종합 진단 (메모리 + Lock)
```bash
bash scripts/diagnose_memory_leak.sh
```
**소요 시간**: ~70초 (메모리 60초 모니터링 + 분석)

**확인 항목**:
- 메모리 누수 여부
- 스레드 상태 (병렬 처리 여부)
- Lock 경합 수준
- 데드락 위험
- GPU 메모리

---

### 2️⃣ 동시 처리 성능 테스트
```bash
# 2개 파일 동시 처리 (기본값)
bash scripts/test_concurrent_processing.sh

# N개 파일 동시 처리
bash scripts/test_concurrent_processing.sh 5
```
**소요 시간**: ~90초 (파일 크기에 따라 변동)

**확인 항목**:
- 실제 병렬 처리 여부
- Lock 경합 발생
- 병렬 처리 효율 (이상적: >80%)
- 메모리/CPU 사용률

---

### 3️⃣ 깊이있는 메모리 추적 (상세 분석)
```bash
bash scripts/trace_memory_deep.sh
```
**소요 시간**: ~10초

**확인 항목**:
- 메모리 할당 위치 (어디서 증가하는가)
- 가비지 컬렉션 상태
- 객체 타입별 개수
- PyTorch GPU 메모리
- 로드된 모듈

---

## 📋 수행 순서 (권장)

### ✅ 정상 흐름 (순서대로 실행)

```bash
# Step 1: 종합 진단
bash scripts/diagnose_memory_leak.sh

# Step 2: 동시 처리 테스트
bash scripts/test_concurrent_processing.sh

# Step 3: 필요시 상세 추적
bash scripts/trace_memory_deep.sh
```

**소요 시간**: ~180초 (약 3분)

---

## 🎯 진단 시나리오별 가이드

### 시나리오 A: 메모리가 계속 증가하는 경우

```bash
# Step 1
bash scripts/diagnose_memory_leak.sh
# ↓ 확인 사항:
# - "메모리 변화: XXX MB" 
#   * > 100MB → 누수 가능성
#   * < 100MB → 정상

# Step 2: 누수 확정 시 상세 분석
bash scripts/trace_memory_deep.sh
# ↓ 확인 사항:
# - "상위 메모리 할당 위치"에서 증가 항목 찾기
# - "GC 통계"에서 uncollectable 객체 확인
```

---

### 시나리오 B: 동시 처리 시 느린 경우

```bash
# Step 1: 병렬 처리 여부 확인
bash scripts/test_concurrent_processing.sh

# ↓ 결과 해석:
# - "병렬 처리 감지됨" → 병렬화 성공
# - "병렬 처리 미감지" → 순차 처리 (Lock 문제)
# - Lock 이벤트 > 10건 → Lock 경합 높음

# Step 2: 상세 진단
bash scripts/diagnose_memory_leak.sh
# ↓ 확인 사항:
# - "활성 스레드" 수 (>2 = 병렬)
# - "Lock 관련 메시지" 확인
# - "병렬 처리 효율" (>80% 정상)
```

---

### 시나리오 C: 로그 없이 메모리만 소모되는 경우

```bash
# Step 1: 먼저 종합 진단
bash scripts/diagnose_memory_leak.sh

# ↓ 다음 중 하나를 확인:
# A) 스레드 상태에 'D' 있음 → I/O hang (GPU 또는 디스크)
# B) 스레드 상태에 'Z' 있음 → 좀비 프로세스
# C) 파일 디스크립터 계속 증가 → FD 누수
# D) 메모리 계속 증가 → 메모리 누수

# Step 2: 메모리 누수 확정 시 상세 분석
bash scripts/trace_memory_deep.sh

# ↓ 분석 결과 사용:
# - "상위 메모리 할당" → 누수 위치 파악
# - "가비지 컬렉션" → 해제 안 된 객체 확인
```

---

## 📊 결과 해석 가이드

### diagnose_memory_leak.sh 결과

```
✅ 정상 신호:
- 메모리 변화: < 100MB
- 활성 스레드: > 2개
- Lock 이벤트: 0-5개
- 병렬 처리 효율: > 80%

⚠️  경고 신호:
- 메모리 변화: 100-500MB
- 활성 스레드: 2개 (경계선)
- Lock 이벤트: 5-10개
- 병렬 처리 효율: 20-80%

❌ 문제 신호:
- 메모리 변화: > 500MB
- 활성 스레드: 1개 (순차 처리)
- Lock 이벤트: > 10개
- 병렬 처리 효율: < 20%
```

### test_concurrent_processing.sh 결과

```
✅ 병렬 처리 성공:
- "병렬 처리 감지됨 (스레드: 3)"
- "Lock 이벤트: 0-5건"
- 처리 시간: 단일 파일 시간과 비슷

❌ 병렬 처리 실패:
- "병렬 처리 미감지 (스레드: 1)"
- "높은 Lock 경합 감지 (>10건)"
- 처리 시간: 단일 파일 시간 × N에 가까움
```

### trace_memory_deep.sh 결과

```
✅ 정상:
- 메모리 할당이 일정한 위치에서만 발생
- 가비지 컬렉션이 정기적으로 실행
- 객체 수가 안정적

❌ 누수:
- 특정 함수에서 메모리 계속 증가
- uncollectable 객체 많음
- 특정 타입의 객체 수 계속 증가
```

---

## 🔍 프로세스 상태 코드

| 코드 | 의미 | 정상? |
|------|------|-------|
| R | Running (실행 중) | ✅ |
| S | Sleeping (수면/대기) | ✅ |
| D | Disk sleep (I/O 대기, 중단 불가) | ⚠️ 지속되면 문제 |
| Z | Zombie (종료 안 됨) | ❌ 문제 |
| T | Traced (디버거) | ⚠️ 의외상황 |

---

## 🛠️ 문제별 해결 방법

### 메모리 누수 해결

```python
# ❌ 문제: 객체가 메모리에 계속 남음
processor_output = processor(...)
# 사용 후 삭제 안 함

# ✅ 해결: 명시적 삭제
processor_output = processor(...)
# ... 사용 ...
del processor_output  # 명시적 삭제
gc.collect()          # 가비지 컬렉션
```

### Lock 경합 해결

```python
# ❌ 문제: Lock 범위가 너무 큼
with lock:
    for i in range(1000):
        result = expensive_operation()
        # 모든 작업이 Lock 내부 → 병렬화 안 됨

# ✅ 해결: 필요한 부분만 Lock
for i in range(1000):
    result = expensive_operation()  # Lock 없이
    
with lock:
    shared_dict[key] = result  # 공유 자원만 Lock
```

### I/O Hang 해결

```python
# ❌ 문제: GPU 연산 완료 미확인
output = model(input)  # GPU에서 실행
# 즉시 CPU로 데이터 옮김 → race condition

# ✅ 해결: 동기화 포인트 추가
output = model(input)
torch.cuda.synchronize()  # GPU 연산 완료 대기
result = output.cpu()     # 이제 안전하게 옮김
```

---

## 💾 출력 파일 위치

```
/tmp/memory_monitor.csv
  → Excel/Sheets에서 열기 (그래프 생성 가능)

/tmp/concurrent_test_monitor_*.log
  → 실시간 리소스 사용률 (시계열 데이터)

/tmp/concurrent_test_report_*.txt
  → 분석 보고서 (권장사항 포함)

/tmp/stt_memory_diagnosis_*.txt
  → 종합 진단 보고서
```

---

## ⚡ 빠른 명령어 참고

```bash
# 컨테이너 로그 실시간 보기
docker logs -f stt-api

# GPU 상태 모니터링
watch -n 1 nvidia-smi

# 메모리 모니터링 (호스트)
watch -n 1 'free -h'

# 파일별 처리 시간만 추출
docker logs stt-api | grep "processing_time"

# Lock 관련 로그만 추출
docker logs stt-api | grep -i "lock\|wait\|acquire"
```

---

## 📞 스크립트 커스터마이징

### 컨테이너 이름 변경

```bash
# 기본: stt-api
# 변경 방법:
CONTAINER_NAME="다른-이름" bash scripts/diagnose_memory_leak.sh
```

### 모니터링 시간 변경

[scripts/diagnose_memory_leak.sh 파일에서]
```bash
DURATION=60   # 현재 60초 → 원하는 초 단위로 변경
INTERVAL=2    # 현재 2초 간격 → 원하는 간격으로 변경
```

### 동시 처리 파일 수 변경

```bash
# 기본: 2개
# 3개: 
bash scripts/test_concurrent_processing.sh 3

# 5개:
bash scripts/test_concurrent_processing.sh 5
```

---

## ✅ 체크리스트

문제 해결 후 다음을 확인하세요:

- [ ] diagnose_memory_leak.sh에서 메모리 변화 < 100MB
- [ ] 활성 스레드 > 2개 (병렬 처리)
- [ ] Lock 이벤트 < 5개 (경합 없음)
- [ ] test_concurrent_processing.sh에서 "병렬 처리 감지"
- [ ] 병렬 처리 효율 > 80%
- [ ] GPU 메모리 안정적 (파일마다 리셋)
- [ ] 4-5개 파일 순차 처리 시 모두 성공

---

## 🆘 문제 해결이 안 되는 경우

```bash
# 1. 로그 전체 수집
docker logs stt-api > /tmp/stt_full_logs.txt

# 2. 최근 30분 로그만
docker logs stt-api --since 30m > /tmp/stt_recent_logs.txt

# 3. Git 상태 확인
cd /Users/a113211/workspace/stt_engine
git log --oneline -10

# 4. Patch 버전 확인
git show HEAD --stat
```

위 파일들을 분석하면 근본 원인을 파악할 수 있습니다.
