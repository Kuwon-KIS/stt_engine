# 성능 측정 및 테스트 스크립트 가이드

## 📋 개요

STT Engine의 성능 측정 및 테스트를 위한 스크립트 패키지입니다.

### 🔍 주요 특징

- **비침습적 모니터링**: 기존 코드 수정 없이 성능 측정
- **자동 로깅**: SQLAlchemy 쿼리 타이밍, FastAPI 응답 시간
- **Docker 지원**: stt-web-ui, stt-api 컨테이너 선택 가능
- **상세 리포트**: 성능 평가 및 병목 분석

---

## 🚀 빠른 시작

### Docker 환경에서 설치

#### 1️⃣ stt-web-ui 컨테이너에 설치 (기본)

```bash
bash setup_monitoring_minimal.sh
```

자동으로 stt-web-ui를 선택하고 설치합니다.

#### 2️⃣ stt-api 컨테이너에 설치 (필요 시)

```bash
CONTAINER=stt-api bash setup_monitoring_minimal.sh
```

또는 다른 컨테이너:

```bash
CONTAINER=<컨테이너_이름> bash setup_monitoring_minimal.sh
```

### 로컬 환경에서 실행

```bash
# 환경 활성화
cd /app
conda activate stt-py311

# 모든 성능 테스트 실행
python quick_diagnostic.py

# 상세 분석 테스트
python run_performance_test.py

# 상세 로그 포함
python run_performance_test.py --verbose

# 특정 테스트만 실행
python run_performance_test.py --test history
```

---

## � 파일 목록

### 핵심 모니터링 파일

| 파일 | 용도 | 배포 |
|------|------|------|
| `quick_diagnostic.py` | 빠른 시스템 점검 (~5초) | 필수 |
| `run_performance_test.py` | 상세 성능 측정 (~30초) | 필수 |
| `diagnose_ui_performance.py` | UI 병목 진단 | 권장 |
| `diagnose_backend_issues.py` | 백엔드 병목 진단 (N+1, 메모리 등) | 권장 |

### 설정 및 문서

| 파일 | 용도 |
|------|------|
| `setup_monitoring_minimal.sh` | 자동 배포 스크립트 |
| `README.md` | 사용 가이드 (이 파일) |
| `DOCKER_MULTI_CONTAINER.md` | 다중 컨테이너 배포 |
| `BACKEND_DIAGNOSIS_GUIDE.md` | 백엔드 진단 방법 |
| `OPTIMIZATION_SOLUTIONS.py` | 성능 개선 코드 예시 |

### 통합 모니터링 파일 (web_ui/)

| 파일 | 기능 |
|------|------|
| `app/utils/db.py` | SQLAlchemy 쿼리 타이밍 |
| `main.py` | FastAPI 응답 시간 로깅 |
| `utils/logger.py` | 중앙화된 로깅 설정 |

---

## �📊 테스트 항목

### 1️⃣ 분석 이력 조회 (test_analysis_history)

**목적**: `get_analysis_history()` 성능 측정

**측정 항목**:
- 쿼리 응답 시간
- 반환된 이력 개수
- 응답 데이터 크기

**성능 기준**:
- ✅ GOOD: < 100ms
- ⚠️  FAIR: 100-500ms  
- ❌ SLOW: > 500ms

**예상 병목 원인**:
- N+1 Query 문제 (각 작업의 count() 쿼리)
- JSON 응답 크기

### 2️⃣ 진행률 조회 (test_get_progress)

**목적**: `get_progress()` 성능 측정

**측정 항목**:
- 쿼리 응답 시간
- 진행률 (%)
- 처리된 파일 수

**성능 기준**:
- ✅ GOOD: < 200ms
- ⚠️  FAIR: 200ms-1s
- ❌ SLOW: > 1s

**예상 병목 원인**:
- 전체 AnalysisResult 로드 (.all())
- 메타데이터 파싱

### 3️⃣ 분석 결과 조회 (test_get_results)

**목적**: `get_results()` 성능 측정

**측정 항목**:
- 쿼리 응답 시간
- 반환된 결과 개수
- 응답 데이터 크기

**성능 기준**:
- ✅ GOOD: < 200ms
- ⚠️  FAIR: 200ms-1s
- ❌ SLOW: > 1s

**예상 병목 원인**:
- 대량의 분석 결과 로드
- JSON 직렬화 오버헤드

### 📊 데이터베이스 통계 (test_database_stats)

**출력 정보**:
- 등록된 직원 수
- 총 분석 작업 수
- 총 분석 결과 수
- 작업당 평균 결과 수

---

## � 진단 스크립트 (심화 분석)

### 4️⃣ UI 성능 진단 (diagnose_ui_performance.py)

**목적**: 웹 UI에서 느린 이유 파악

**진단 항목**:
- API 응답 크기 분석
- 데이터 분포 (작업당 결과 수)
- 병목 지점 식별
- 성능 개선 권장사항

**실행**:
```bash
docker exec stt-web-ui python /app/diagnose_ui_performance.py

# 또는 로컬
python diagnose_ui_performance.py
```

**출력 예시**:
```
1️⃣ API 응답 크기 분석
   - API 응답 시간: 7.60ms
   - JSON 직렬화 크기: 2.5MB
   - 반환된 작업 수: 150개

❌ 응답이 상당히 큽니다 (> 1MB) → pagination 고려

2️⃣ 데이터 분포 분석
   평균 결과 수: 45.3개
   최대 결과 수: 520개 ⚠️ (많음)

💡 개선 방안:
  1. [필수] API Pagination 구현
  2. [필수] 테이블 가상 스크롤 구현
  3. [권장] 클라이언트 캐싱
```

### 5️⃣ 백엔드 병목 진단 (diagnose_backend_issues.py)

**목적**: N+1 쿼리, 메모리, 직렬화 오버헤드 측정

**진단 항목**:

#### 1. N+1 쿼리 문제
```
❌ 현재: 1 + N번 쿼리 (직원 100명 = 101개 쿼리)
✅ 개선: GROUP BY로 1번 쿼리
   개선 효과: 99% 쿼리 감소
```

#### 2. 메모리 오버헤드
```
📊 최근 작업별 결과 로드 비용:
   [1] 결과 245개 → 객체 메모리 512KB, JSON 1.2MB
   [2] 결과 512개 → 객체 메모리 1.1MB, JSON 2.8MB
   ⚠️ 결과가 많음 → 모든 필드 로드 시 메모리 낭비
```

#### 3. JSON 직렬화 오버헤드
```
model_dump() + JSON: 45.23ms
필드 선택 + JSON:    31.42ms
개선 효과: 30.5% 빨라짐
```

**실행**:
```bash
docker exec stt-web-ui python /app/diagnose_backend_issues.py

# 또는 로컬
python diagnose_backend_issues.py
```

---

## 📈 성능 모니터링 로그

성능 데이터는 자동으로 로깅됩니다:

### web_ui/logs/performance.log

```
[2024-01-15 10:30:45] SQL Query (12.34 ms): SELECT * FROM analysis_result...
[2024-01-15 10:30:45] API Response (145.67 ms): GET /api/analysis/history
```

**모니터링 대상**:
- 모든 SQLAlchemy 쿼리 (microsecond 단위)
- /api/* 엔드포인트 (millisecond 단위)

---

## 🔧 운영 서버 배포

### 1. 자동 설치

```bash
# 프로젝트 루트에서
bash scripts/performance/setup_monitoring_minimal.sh

# 또는 특정 컨테이너 지정
CONTAINER=stt-api bash scripts/performance/setup_monitoring_minimal.sh
```

자동으로 다음 파일들을 복사합니다:
- 모니터링 파일 (db.py, main.py, logger.py)
- 성능 테스트 스크립트 (quick_diagnostic.py, run_performance_test.py)
- 진단 스크립트 (diagnose_ui_performance.py, diagnose_backend_issues.py)
- 로그 디렉토리 생성 (/app/logs)

### 2. 수동 설정

```bash
# 필요한 파일 복사
docker cp web_ui/app/utils/db.py $CONTAINER:/app/app/utils/
docker cp web_ui/main.py $CONTAINER:/app/
docker cp web_ui/utils/logger.py $CONTAINER:/app/utils/

# 스크립트 복사
docker cp scripts/performance/run_performance_test.py $CONTAINER:/app/
docker cp scripts/performance/diagnose_ui_performance.py $CONTAINER:/app/
docker cp scripts/performance/diagnose_backend_issues.py $CONTAINER:/app/

# 로그 디렉토리 생성
docker exec $CONTAINER mkdir -p /app/logs

# 애플리케이션 재시작
docker exec $CONTAINER pkill -f "uvicorn main:app"
sleep 2
docker exec $CONTAINER python -m uvicorn main:app --host 0.0.0.0 --port 8100 &
```

### 3. 설정 확인

```bash
# web_ui/logs 디렉토리 자동 생성 (mkdir -p logs/)
# logger.py가 자동으로 rotatingFileHandler 설정

# 성능 로그 활성화 확인
docker exec $CONTAINER ls -lh /app/logs/performance.log
```

### 4. 운영 환경에서 실행


```bash
# 성능 테스트 실행
cd /path/to/stt_engine/web_ui
python ../scripts/performance/run_performance_test.py

# 최근 성능 로그 확인
tail -f logs/performance.log
```

---

## 🎯 성능 개선 로드맵

### 현재 식별된 병목

1. **N+1 Query Problem**
   - 위치: `analysis_service.py::get_analysis_history()`
   - 문제: 각 작업마다 count() 쿼리 실행
   - 영향: 100개 작업 = 101개 쿼리
   - 해결: SQLAlchemy `joinedload` 또는 단일 쿼리로 통합

2. **Full Result Loading**
   - 위치: `analysis_service.py::get_progress()`
   - 문제: `session.query(...).all()` 로 모든 결과 메모리에 로드
   - 영향: 대량 데이터셋에서 메모리 오버헤드
   - 해결: 필요한 필드만 선택적 로드 또는 pagination

3. **JSON Metadata Parsing**
   - 위치: `analysis_result.stt_metadata`, `improper_detection_results`
   - 문제: 각 결과마다 JSON 파싱
   - 영향: CPU 사용률 증가
   - 해결: 필요한 경우에만 파싱 또는 캐싱

4. **Missing Index**
   - 위치: `AnalysisResult.file_id`
   - 문제: 인덱스 없어 풀 테이블 스캔
   - 영향: 대량 결과 조회 시 느린 응답
   - 해결: DB 마이그레이션에서 인덱스 추가

### 예상 성능 개선량

- 분석 이력 조회: 500ms → 50ms (10배)
- 진행률 조회: 1000ms → 150ms (7배)
- 결과 조회: 1000ms → 100ms (10배)

---

## 🔐 보안 및 주의사항

### ✅ 안전한 모니터링

- 로그에는 민감한 데이터 포함 없음
- 성능 타이밍 정보만 기록
- 운영 환경에서도 안전하게 실행 가능

### ⚠️ 성능 영향

- 데이터베이스 쿼리: **<1% 오버헤드**
- API 응답: **<2% 오버헤드**
- 로깅 I/O: 로그 파일이 10MB에 도달하면 자동 아카이빙

### 🛑 주의사항

1. 성능 로그는 정기적으로 정리 (7일 주기 추천)
   ```bash
   find logs -name "performance.log*" -mtime +7 -delete
   ```

2. 대량 데이터 조회 시 timeout 설정
   ```bash
   # FastAPI 설정에서 timeout 조정
   uvicorn main:app --timeout-keep-alive 60
   ```

---

## 📝 사용 예시

### 예시 1: 성능 테스트 및 로그 확인

```bash
# 1. 성능 테스트 실행
$ python run_performance_test.py

📊 데이터베이스 통계
✓ 직원 수: 5명
✓ 분석 작업 수: 150개
✓ 분석 결과 수: 3250개

🔍 TEST 1: 분석 이력 조회
✓ 테스트 emp_id: EMP001
✓ 분석 이력 개수: 30개

📊 성능 결과:
  - 응답 시간: 523.45 ms
  - 반환된 이력 개수: 30개
  - 응답 데이터 크기: 245.67 KB
  ❌ SLOW: 523.45 ms    # < 성능 개선 필요

# 2. 성능 로그 확인
$ tail -20 logs/performance.log

[2024-01-15 10:30:45,234] performance - Query (234.12 ms): SELECT count...
[2024-01-15 10:30:45,467] performance - Query (5.67 ms): SELECT * FROM...
[2024-01-15 10:30:45,812] performance - API (523.45 ms): GET /api/analysis/history
```

### 예시 2: 특정 테스트 실행

```bash
# 진행률 조회 성능만 측정
$ python run_performance_test.py --test progress --verbose

📊 데이터베이스 통계
...

🔍 TEST 2: 진행률 조회
✓ 테스트 job_id: JOB12345
✓ 폴더: /home/user/documents
✓ 파일 개수: 45개
✓ 분석 결과 개수: 45개

📊 성능 결과:
  - 응답 시간: 187.34 ms
  - 진행률: 100%
  - 처리된 파일: 45/45
  - 응답 데이터 크기: 12.34 KB
  ✅ GOOD: 187.34 ms    # 성능 우수
```

---

## 📚 참고 자료

### 파일 위치
- 성능 측정 스크립트: `scripts/performance/`
- 성능 로그: `web_ui/logs/performance.log`
- 모니터링 통합: `web_ui/app/utils/db.py`, `web_ui/main.py`, `web_ui/utils/logger.py`

### 관련 문서
- [성능 최적화 가이드](../docs/PERFORMANCE_OPTIMIZATION.md)
- [배포 가이드](../docs/SERVER_DEPLOYMENT_GUIDE.md)
- [API 문서](../docs/API_USAGE_GUIDE.md)

### 추가 정보
- 성능 평가 기준: 동시 사용자 100명, 데이터 1000+개 기준
- 로그 보관 정책: 최대 50MB (5개 파일 × 10MB)
- 모니터링 활성화: 자동 활성화 (비활성화 불가)

---

## 💬 지원 및 문제 해결

### 자주 묻는 질문

**Q: 성능 로그가 너무 많이 생깁니다**
```bash
# 로그 레벨 조정 (logger.py에서 INFO → WARNING로 변경)
perf_logger.setLevel(logging.WARNING)
```

**Q: 특정 쿼리의 성능만 측정하고 싶습니다**
```bash
# SQLAlchemy event listener 활용
from sqlalchemy import event
# db.py 참고
```

**Q: 운영 환경에서 모니터링을 비활성화하려면**
```bash
# logger.py에서 성능 로거 비활성화
perf_logger.disabled = True
```

---

## ✅ 체크리스트

운영 서버 배포 전 확인:

- [ ] `web_ui/app/utils/db.py` 복사됨
- [ ] `web_ui/main.py` 복사됨
- [ ] `web_ui/utils/logger.py` 복사됨
- [ ] `scripts/performance/run_performance_test.py` 복사됨
- [ ] `web_ui/logs/` 디렉토리 생성됨
- [ ] 성능 테스트 실행 성공
- [ ] 로그 파일 생성 확인 (`logs/performance.log`)
- [ ] 정기적인 로그 정리 스케줄 설정

---

## 📞 연락처 및 피드백

성능 개선 관련 피드백이나 문제 발생 시:
1. 성능 로그 수집 (`tail -100 logs/performance.log`)
2. 테스트 출력 결과 저장
3. 관리자에게 보고

---

**마지막 업데이트**: 2024-01-15
**버전**: 1.0
