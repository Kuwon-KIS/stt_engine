# 데이터베이스 마이그레이션

## 개요
`migrations/` 디렉토리에는 DB 스키마 변경을 위한 마이그레이션 스크립트들이 저장됩니다.

마이그레이션은 **선택적으로 실행**됩니다. Entrypoint에서 `RUN_MIGRATIONS=true` 환경변수가 설정되어 있을 때만 자동 실행됩니다.

## 마이그레이션 파일

### add_result_status.py
- **목적**: analysis_results 테이블에 status와 updated_at 컬럼 추가
- **변경사항**:
  - `status VARCHAR(20)` - 작업 상태 (pending, processing, completed, failed)
  - `updated_at DATETIME` - 최근 업데이트 시간
  - 기존 데이터의 status는 'completed'로 설정
  - status 컬럼에 인덱스 생성
- **멱등성**: 여러 번 실행해도 안전 (이미 적용되면 스킵)
- **실행 시기**: 첫 배포 또는 스키마 업그레이드 필요할 때

## 마이그레이션 실행 방법

### 방법 1: Docker 배포 시 (권장)
```bash
# 마이그레이션 포함 배포
docker run -d --name stt-web-ui \
  --network stt-network \
  -p 8100:8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -e RUN_MIGRATIONS=true \
  -v $(pwd)/web_ui/data:/app/data \
  -v $(pwd)/web_ui/logs:/app/logs \
  stt-web-ui:cuda129-rhel89-v1.2.3

# 마이그레이션 실행 확인
docker logs stt-web-ui | grep -E "✅|⏭️|Migration"
```

### 방법 2: 로컬 개발 환경
```bash
cd web_ui
python migrations/add_result_status.py
```

### 방법 3: 실행 중인 Docker 컨테이너에서 수동 실행
```bash
docker exec stt-web-ui python /app/migrations/add_result_status.py
```

## 마이그레이션 작성 가이드

새로운 마이그레이션을 추가할 때:

1. **파일명 규칙**: `<sequence>_<description>.py`
   - 예: `001_add_result_status.py`, `002_add_user_preferences.py`

2. **멱등성 구현** (매우 중요)
   ```python
   # 컬럼이 있으면 스킵
   cursor.execute("PRAGMA table_info(analysis_results);")
   columns = [row[1] for row in cursor.fetchall()]
   if 'status' in columns:
       print("✅ Column already exists. Skipping...")
       return
   ```

3. **구조 템플릿**
   ```python
   """
   Migration: [설명]
   """
   import sqlite3
   import os
   from datetime import datetime

   DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'db.sqlite')

   def migrate():
       """Apply the migration"""
       if not os.path.exists(DB_PATH):
           print(f"⏭️  DB 파일이 없습니다: {DB_PATH}")
           return
       
       conn = sqlite3.connect(DB_PATH)
       cursor = conn.cursor()
       
       try:
           print("🔄 Starting migration: [name]")
           # 마이그레이션 로직
           conn.commit()
           print("✅ Migration completed successfully")
       except Exception as e:
           conn.rollback()
           print(f"❌ Migration failed: {e}")
           raise
       finally:
           conn.close()

   if __name__ == "__main__":
       migrate()
   ```

4. **테스트**
   ```bash
   cd web_ui
   python migrations/your_migration.py
   ```

5. **Git 커밋**
   ```bash
   git add web_ui/migrations/your_migration.py
   git commit -m "feat: DB 마이그레이션 추가 - [설명]"
   ```

6. **배포 시 Entrypoint 업데이트**
   마이그레이션이 여러 개인 경우, entrypoint.sh에서 순서대로 실행하도록:
   ```bash
   # entrypoint.sh 내부
   if [ "${RUN_MIGRATIONS}" = "true" ]; then
       python /app/migrations/add_result_status.py || ...
       python /app/migrations/your_new_migration.py || ...
   fi
   ```

## 마이그레이션 전략

### 언제 RUN_MIGRATIONS=true를 사용할까?

| 상황 | 사용 | 설명 |
|------|------|------|
| 새로운 운영 환경 첫 배포 | ✅ 필수 | DB가 없거나 초기화 필요 |
| 스키마 업그레이드 필요 | ✅ 필수 | 새로운 마이그레이션 추가됨 |
| 일반적인 코드 업데이트 | ❌ 불필요 | DB 스키마 변경 없음 |
| 핫픽스/패치 배포 | ❌ 불필요 | DB 스키마 변경 없음 |

### 마이그레이션 없이 배포
```bash
docker run -d --name stt-web-ui \
  # ... 다른 옵션들 ...
  stt-web-ui:cuda129-rhel89-v1.2.3
  # RUN_MIGRATIONS 설정하지 않음 → 마이그레이션 스킵
```

## 주의사항

1. **항상 백업 후 마이그레이션 실행**
   ```bash
   cp web_ui/data/db.sqlite web_ui/data/db.sqlite.backup.$(date +%Y%m%d_%H%M%S)
   ```

2. **프로덕션 환경에서는 테스트 후 배포**
   - 테스트 환경에서 먼저 마이그레이션 실행
   - 데이터 손상 여부 확인
   - 그 후 프로덕션 배포

3. **롤백 계획 수립**
   - SQLite는 DDL 롤백이 제한적
   - 마이그레이션 전 반드시 백업 필요

4. **마이그레이션 로그 확인**
   ```bash
   docker logs stt-web-ui | grep -A5 "Migration"
   ```

