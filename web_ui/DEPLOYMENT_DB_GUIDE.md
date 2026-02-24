# 배포 체크리스트 및 DB 관리 가이드

## 개요
이 문서는 STT Web UI를 새로운 운영 환경에 배포할 때 필요한 DB 초기화 및 마이그레이션 절차를 설명합니다.

---

## 1. Docker Image 빌드 시 주의사항

### ✅ 마이그레이션 파일이 Docker Image에 포함되는지 확인

**Dockerfile.web_ui**의 `COPY` 명령어 확인:
```dockerfile
COPY web_ui/migrations/ ./migrations/
COPY web_ui/docker/entrypoint.sh ./
```

이 두 줄이 있어야 마이그레이션과 startup 스크립트가 Docker Image에 포함됩니다.

### 빌드 명령어
```bash
# 로컬 환경
docker build -t stt-web-ui:local -f web_ui/docker/Dockerfile.web_ui .

# EC2 환경
docker build -t stt-web-ui:cuda129-rhel89-v1.2.3 -f web_ui/docker/Dockerfile.web_ui .
```

---

## 2. 배포 후 초기 설정

### 시나리오 A: 새로운 운영 환경 (DB 0부터 시작)

```bash
# 1. Docker 컨테이너 실행
docker run -d --name stt-web-ui \
  --network stt-network \
  -p 8100:8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -e RUN_MIGRATIONS=true \
  -v $(pwd)/web_ui/data:/app/data \
  -v $(pwd)/web_ui/logs:/app/logs \
  stt-web-ui:cuda129-rhel89-v1.2.3

# 2. 자동 실행 확인 (Entrypoint가 마이그레이션 실행)
docker logs stt-web-ui | grep -E "migration|Database"
```

**자동 실행 흐름**:
1. ✅ `entrypoint.sh` 실행
2. ✅ `RUN_MIGRATIONS=true` 이므로 `add_result_status.py` 시도 (DB가 없으면 스킵)
3. ✅ Uvicorn 서버 시작

---

### 시나리오 B: 기존 운영 환경 (DB 있음, 스키마 업그레이드)

```bash
# 1. 새로운 image로 컨테이너 업데이트
docker stop stt-web-ui
docker rm stt-web-ui

# 2. 새로운 이미지로 실행 (마이그레이션 포함)
docker run -d --name stt-web-ui \
  --network stt-network \
  -p 8100:8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -e RUN_MIGRATIONS=true \
  -v $(pwd)/web_ui/data:/app/data \
  -v $(pwd)/web_ui/logs:/app/logs \
  stt-web-ui:cuda129-rhel89-v1.2.3

# 3. 마이그레이션 자동 실행 확인
docker logs stt-web-ui | grep -E "✅|⏭️|⚠️"
```

**자동 실행 흐름**:
1. ✅ `entrypoint.sh` 실행
2. ✅ `RUN_MIGRATIONS=true` 이므로 `add_result_status.py` 실행 (이미 마이그레이션됨 → 스킵)
3. ✅ Uvicorn 서버 시작

---

### 시나리오 C: 일반적인 배포 (마이그레이션 없음)

```bash
# 마이그레이션이 필요 없는 일반적인 배포
docker run -d --name stt-web-ui \
  --network stt-network \
  -p 8100:8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -v $(pwd)/web_ui/data:/app/data \
  -v $(pwd)/web_ui/logs:/app/logs \
  stt-web-ui:cuda129-rhel89-v1.2.3

# RUN_MIGRATIONS 설정 안 함 → 마이그레이션 스킵
docker logs stt-web-ui | head -20
```

**실행 흐름**:
1. ✅ `entrypoint.sh` 실행
2. ⏭️ `RUN_MIGRATIONS` 미설정 또는 false → 마이그레이션 스킵
3. ✅ Uvicorn 서버 시작

---

## 3. 문제 해결

### Docker 로그 확인
```bash
# 실시간 로그 보기
docker logs -f stt-web-ui

# 특정 키워드 찾기
docker logs stt-web-ui | grep "Migration\|ERROR\|✅"
```

### 마이그레이션 수동 실행
만약 자동 실행이 실패한 경우:

```bash
# 방법 1: 컨테이너 내에서 직접 실행
docker exec stt-web-ui python /app/migrations/add_result_status.py

# 방법 2: 로컬에서 실행 (host의 마이그레이션 파일 사용)
cd web_ui
python migrations/add_result_status.py
```

### DB 초기화 필요 시
```bash
# 주의: 모든 데이터가 삭제됩니다!
docker exec stt-web-ui rm /app/data/db.sqlite
docker restart stt-web-ui
```

---

## 4. 마이그레이션 파일 추가 시 절차

새로운 마이그레이션이 필요한 경우:

1. **마이그레이션 스크립트 작성**
   ```bash
   # 예: add_new_column.py 생성
   web_ui/migrations/add_new_column.py
   ```

2. **멱등성 구현** (중요)
   - 같은 스크립트를 여러 번 실행해도 에러가 나지 않도록 구현
   - 예: `IF NOT EXISTS` 또는 컬럼 존재 여부 확인

3. **테스트**
   ```bash
   # 로컬 테스트
   cd web_ui
   python migrations/add_new_column.py
   ```

4. **Git에 커밋**
   ```bash
   git add web_ui/migrations/add_new_column.py
   git commit -m "feat: 새로운 마이그레이션 추가"
   ```

5. **배포 시 자동 실행**
   - Entrypoint가 자동으로 모든 마이그레이션 스크립트를 찾아 실행하지는 않음
   - 각 마이그레이션을 `entrypoint.sh`에 명시적으로 추가:
     ```bash
     python /app/migrations/add_new_column.py || { echo "⚠️  경고: $?" }
     ```

---

## 5. 배포 체크리스트

배포 전 확인 사항:

- [ ] `git push`로 모든 변경사항이 커밋됨
- [ ] `web_ui/migrations/*.py`에 모든 마이그레이션 스크립트가 있음
- [ ] `Dockerfile.web_ui`에 `COPY web_ui/migrations/` 줄이 있음
- [ ] `entrypoint.sh`에 모든 마이그레이션이 명시됨
- [ ] Docker Image 빌드 완료
- [ ] EC2에서 테스트 배포 완료
- [ ] 로그에서 "✅ Migration completed successfully" 또는 "✅ Columns already exist" 확인

---

## 6. 자동화 스크립트

### deploy.sh (배포 자동화 - 마이그레이션 없음)

```bash
#!/bin/bash
set -e

echo "🚀 STT Web UI 배포 시작"

# 1. Image 빌드
echo "📦 Docker Image 빌드..."
docker build -t stt-web-ui:cuda129-rhel89-v1.2.3 -f web_ui/docker/Dockerfile.web_ui .

# 2. 기존 컨테이너 중지
echo "🛑 기존 컨테이너 중지..."
docker stop stt-web-ui || true
docker rm stt-web-ui || true

# 3. 새로운 컨테이너 실행 (마이그레이션 없음)
echo "▶️ 새로운 컨테이너 실행..."
docker run -d --name stt-web-ui \
  --network stt-network \
  -p 8100:8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -v $(pwd)/web_ui/data:/app/data \
  -v $(pwd)/web_ui/logs:/app/logs \
  stt-web-ui:cuda129-rhel89-v1.2.3

# 4. 서버 상태 확인
echo "⏳ 서버 시작 대기 (5초)..."
sleep 5

echo "📊 서버 상태 확인..."
if docker logs stt-web-ui | grep -q "Uvicorn running"; then
    echo "✅ 배포 성공!"
else
    echo "❌ 배포 실패"
    docker logs stt-web-ui
    exit 1
fi
```

사용:
```bash
bash deploy.sh
```

---

### deploy-with-migration.sh (마이그레이션 포함 배포)

```bash
#!/bin/bash
set -e

echo "🚀 STT Web UI 배포 시작 (마이그레이션 포함)"

# 1. Image 빌드
echo "📦 Docker Image 빌드..."
docker build -t stt-web-ui:cuda129-rhel89-v1.2.3 -f web_ui/docker/Dockerfile.web_ui .

# 2. 기존 컨테이너 중지
echo "🛑 기존 컨테이너 중지..."
docker stop stt-web-ui || true
docker rm stt-web-ui || true

# 3. 새로운 컨테이너 실행 (마이그레이션 포함)
echo "▶️ 새로운 컨테이너 실행..."
docker run -d --name stt-web-ui \
  --network stt-network \
  -p 8100:8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -e RUN_MIGRATIONS=true \
  -v $(pwd)/web_ui/data:/app/data \
  -v $(pwd)/web_ui/logs:/app/logs \
  stt-web-ui:cuda129-rhel89-v1.2.3

# 4. 마이그레이션 실행 대기
echo "⏳ 마이그레이션 실행 대기 (10초)..."
sleep 10

# 5. 마이그레이션 결과 확인
echo "📊 마이그레이션 상태 확인..."
if docker logs stt-web-ui | grep -E "✅.*Migration|⏭️.*Migration"; then
    echo "✅ 마이그레이션 성공!"
else
    echo "⚠️  마이그레이션 상태 미확인 (상세 로그 확인)"
fi

# 6. 서버 상태 확인
echo "📊 서버 상태 확인..."
if docker logs stt-web-ui | grep -q "Uvicorn running"; then
    echo "✅ 배포 성공!"
    docker logs stt-web-ui | grep -E "✅|⏭️|Migration"
else
    echo "❌ 배포 실패"
    docker logs stt-web-ui
    exit 1
fi
```

사용:
```bash
bash deploy-with-migration.sh
```

---

## 7. FAQ

**Q: 마이그레이션을 매번 실행해야 하나요?**
- A: 아니오. `RUN_MIGRATIONS=true` 환경변수를 설정할 때만 실행됩니다. 일반적인 배포에서는 설정하지 마세요.

**Q: 언제 RUN_MIGRATIONS=true를 설정하나요?**
- A: 다음 경우에만 설정:
  1. **새로운 운영 환경 첫 배포** (DB가 처음 생성됨)
  2. **스키마 업그레이드 필요** (새로운 마이그레이션 추가됨)
  - 일반적인 코드 업데이트: 설정하지 말 것 (불필요한 DB 체크)

**Q: Docker Image를 다시 빌드하면 마이그레이션이 또 실행되나요?**
- A: `RUN_MIGRATIONS` 환경변수를 설정하지 않으면 실행되지 않습니다. 마이그레이션 스크립트는 멱등성을 가지므로 여러 번 실행해도 안전합니다.

**Q: 마이그레이션 실행 여부를 어떻게 확인하나요?**
- A: 로그 확인:
  ```bash
  docker logs stt-web-ui | grep -E "✅.*Migration|⏭️.*Migration"
  ```

**Q: 컨테이너를 삭제하면 DB도 삭제되나요?**
- A: 아니오. `-v $(pwd)/web_ui/data:/app/data`로 volume을 mount했으므로 DB는 host에 저장되어 있습니다.

**Q: 마이그레이션이 실패하면 서버가 시작되지 않나요?**
- A: 마이그레이션 오류는 무시하고 서버가 시작됩니다 (entrypoint.sh의 에러 처리). 로그를 확인하세요.

**Q: 마이그레이션 롤백은 어떻게 하나요?**
- A: SQLite는 DDL 롤백이 제한적입니다. 백업 복구 또는 데이터 재생성 필요. 마이그레이션 전 항상 DB를 백업하세요.

**Q: 기존 운영 서버에 새 마이그레이션이 추가되면?**
- A: 
  1. git pull로 최신 코드 가져오기
  2. 새로운 image 빌드
  3. `RUN_MIGRATIONS=true`로 배포
  4. 마이그레이션 자동 실행

---

## 관련 파일

- [migrations/README.md](./README.md) - 마이그레이션 상세 설명
- [Dockerfile.web_ui](../docker/Dockerfile.web_ui) - Docker 빌드 설정
- [entrypoint.sh](../docker/entrypoint.sh) - Startup 스크립트
- [migrations/add_result_status.py](./add_result_status.py) - 현재 마이그레이션
