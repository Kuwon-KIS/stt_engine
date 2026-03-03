# EC2 DB 클랜징 가이드

## 문제 상황

분석 작업이 중간에 중단되어 `pending` 또는 `processing` 상태로 DB에 남아있는 경우가 발생할 수 있습니다.

**원인:**
- 컨테이너 강제 종료
- 메모리 부족으로 인한 프로세스 종료
- 네트워크 연결 끊김
- 시스템 재부팅

## 클랜징 방법

### 1️⃣ 로컬에서 준비

```bash
cd /Users/a113211/workspace/stt_engine/web_ui
```

### 2️⃣ EC2에서 DB 확인

#### 방법 A: Docker 컨테이너 내에서 직접 실행

```bash
# 1. 현재 상태만 확인 (dry-run)
docker exec stt-web-ui python scripts/cleanup_stale_jobs.py --check

# 2. 통계 보기
docker exec stt-web-ui python scripts/cleanup_stale_jobs.py --stats

# 3. 실제 정리 (24시간 이상 중단된 작업)
docker exec stt-web-ui python scripts/cleanup_stale_jobs.py --apply

# 4. 12시간 이상 중단된 작업 정리
docker exec stt-web-ui python scripts/cleanup_stale_jobs.py --hours 12 --apply
```

#### 방법 B: SSH로 접속해서 실행

```bash
# EC2 접속
ssh -i "aws-stt-build.pem" ec2-user@ec2-3-34-45-91.ap-northeast-2.compute.amazonaws.com

# web_ui 폴더로 이동
cd stt_engine/web_ui

# 스크립트 실행
python scripts/cleanup_stale_jobs.py --check
python scripts/cleanup_stale_jobs.py --apply --hours 24
```

### 3️⃣ 확인 및 모니터링

```bash
# 정리 후 상태 재확인
docker exec stt-web-ui python scripts/cleanup_stale_jobs.py --stats

# DB 파일 크기 확인
docker exec stt-web-ui ls -lh /app/data/database.db

# 최근 로그 확인
docker logs stt-web-ui --tail 50
```

## 스크립트 옵션

| 옵션 | 설명 | 예시 |
|------|------|------|
| `--check` | Dry-run (조회만, 기본값) | `--check` |
| `--apply` | 실제 정리 수행 | `--apply` |
| `--stats` | 통계만 표시 | `--stats` |
| `--hours N` | N시간 이상 경과한 작업만 정리 | `--hours 12` |

## 출력 예시

```
======================================================================
📈 전체 작업 상태 통계
======================================================================

  pending      :    5개
  processing   :    2개
  completed    : 1250개
  ──────────────────────
  total        : 1257개

📅 7일 이상 된 작업: 45개
💾 정리 대상 (24시간 이상 중단): 7개

======================================================================
📊 중단된 작업 정리 리포트 (24시간 이상 경과)
======================================================================

1. Job ID: job_abc123def
   상태: processing → 정리 필요
   폴더: /data/uploads/emp001/2026-02-20
   생성일: 2026-02-20 14:30:15 (4일 10시간 전)
   파일 분석: 15개 (완료: 8개)

2. Job ID: job_xyz789ghi
   ...
```

## 자동화 (선택사항)

일주일마다 자동으로 정리하려면 crontab에 등록:

```bash
# EC2에서
crontab -e

# 매주 일요일 새벽 2시에 실행
0 2 * * 0 cd /home/ec2-user/stt_engine/web_ui && python scripts/cleanup_stale_jobs.py --apply --hours 24 >> /tmp/cleanup.log 2>&1
```

## 주의사항

⚠️ **--apply 사용 전 반드시 --check로 확인**
- 정리 대상 작업들이 정말 중단된 것인지 확인
- 분석 중인 장시간 작업이 오래된 작업으로 잘못 분류되지 않았는지 확인

## 트러블슈팅

### Q: 여전히 분석중으로 표시되는 작업이 있다면?

**상황별 대처:**

1. **작업이 실제로 진행 중인 경우**
   - `--hours` 값을 더 크게 설정 (예: `--hours 48`)
   - 분석이 완료될 때까지 기다림

2. **일부 파일만 분석된 경우**
   - 스크립트가 자동으로 감지하고 상태를 `completed`로 변경
   - 부분 완료된 상태로 표시됨

3. **DB가 손상된 경우**
   - 컨테이너 재시작: `docker restart stt-web-ui`
   - DB 마이그레이션 강제 실행: `docker run ... -e RUN_MIGRATIONS=true ...`

### Q: 정리 후 UI에 반영되지 않는다면?

```bash
# 브라우저 캐시 초기화
# 또는 개인정보 보호 모드에서 새로 접속

# 컨테이너 로그 확인
docker logs stt-web-ui --tail 100 | grep -E "ERROR|cleanup"
```

## 참고: DB 구조

```python
AnalysisJob (작업 정보)
├── job_id: 고유 ID
├── emp_id: 직원 ID
├── folder_path: 분석 대상 폴더
├── status: 'pending' | 'processing' | 'completed'
└── created_at: 생성 시간

AnalysisResult (각 파일 분석 결과)
├── job_id: 해당 작업 ID
├── file_id: 오디오 파일명
├── status: 'pending' | 'processing' | 'completed'
├── stt_text: STT 결과
└── improper_detection_results: 탐지 결과 (JSON)
```

정리 시 `AnalysisJob.status`만 변경되고, `AnalysisResult`는 유지됩니다.
