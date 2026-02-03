# 🔄 컨테이너 Python 파일 업데이트 가이드

**목적**: Docker 이미지 재빌드 없이 Python 파일만 수정하여 운영환경에서 테스트  
**소요시간**: ~10분  
**난이도**: 초급

---

## 📌 상황

- ✅ 서버에 이미 Docker 이미지 배포됨
- ⚠️ Python 코드에 버그 발견 (예: stt_engine.py 182줄 오류)
- 🚀 새 이미지 빌드까지는 시간이 오래 걸림
- 🎯 먼저 수정된 파일로 정상 동작하는지 빠르게 검증하고 싶음

---

## 🛠️ 방법 1: docker cp 사용 (권장)

가장 간단하고 빠른 방법

### Step 1: 수정된 Python 파일 준비

로컬 머신에서:
```bash
# 수정된 파일이 준비되어 있음 (예: stt_engine.py)
ls -lh stt_engine.py
```

### Step 2: 운영 서버로 전송

```bash
# 로컬 → 서버
scp stt_engine.py user@server:/tmp/

# 또는 이미 서버에 있으면 다음 단계로
```

### Step 3: 실행 중인 컨테이너로 파일 복사

서버에서:
```bash
# 1. 실행 중인 컨테이너 ID 확인
docker ps | grep stt-engine
# 예상 출력: CONTAINER_ID  stt-engine:linux-x86_64

# 2. 파일 복사
docker cp /tmp/stt_engine.py <CONTAINER_ID>:/app/stt_engine.py

# 또는 현재 경로에서
docker cp stt_engine.py <CONTAINER_ID>:/app/stt_engine.py

# 3. 복사 확인
docker exec <CONTAINER_ID> ls -lh /app/stt_engine.py
```

### Step 4: 컨테이너 재시작

```bash
# 파일 변경사항 적용을 위해 재시작
docker restart <CONTAINER_ID>

# 또는 docker-compose 사용 시
docker-compose restart stt-engine
```

### Step 5: 검증

```bash
# 로그 확인
docker logs <CONTAINER_ID> | tail -20

# 헬스 체크
curl http://localhost:8003/health

# 예상 응답:
# {"status":"ok","version":"1.0.0","engine":"faster-whisper"}
```

---

## 🛠️ 방법 2: 볼륨 마운트 사용 (개발/테스트용)

더 자주 업데이트할 경우, 호스트 파일 직접 참조

### Step 1: 컨테이너 중지

```bash
docker stop stt-engine
```

### Step 2: 볼륨 마운트로 재실행

```bash
docker run -d \
  --name stt-engine-test \
  -p 8003:8003 \
  -v /path/to/app:/app/app \
  -v /path/to/models:/app/models \
  stt-engine:linux-x86_64

# 상세 설명:
# -v /path/to/app:/app/app → 호스트의 app 폴더를 컨테이너의 /app/app에 마운트
# 이렇게 하면 호스트에서 파일을 수정할 때마다 자동으로 반영됨
```

### Step 3: 파일 수정

호스트에서:
```bash
# 호스트 파일 수정
vim /path/to/app/stt_engine.py

# 파일 저장 후 즉시 적용됨 (Python 모듈 리로드 필요시 컨테이너 재시작)
docker restart stt-engine-test
```

---

## 🛠️ 방법 3: 직접 컨테이너에서 편집 (긴급 상황)

```bash
# 실행 중인 컨테이너에서 쉘 접근
docker exec -it <CONTAINER_ID> /bin/bash

# 쉘 내에서 vim 설치 (필요시)
apt-get update && apt-get install -y vim

# 파일 직접 편집
vim /app/stt_engine.py

# 종료 후 컨테이너 재시작
docker restart <CONTAINER_ID>
```

⚠️ **주의**: 이 방법은 임시 방편이며, 컨테이너 삭제 시 변경사항이 소실됨

---

## ✅ 테스트 및 검증

### 1️⃣ 기본 검증

```bash
# 컨테이너 상태 확인
docker ps | grep stt-engine

# 로그 확인 (오류 메시지 확인)
docker logs stt-engine

# 헬스 체크
curl http://localhost:8003/health
```

### 2️⃣ API 기능 테스트

```bash
# 음성 파일 준비
wav_file="test_audio.wav"  # 또는 다른 지원 형식

# API 호출
curl -X POST -F "file=@${wav_file}" \
  http://localhost:8003/transcribe

# 예상 응답:
# {
#   "success": true,
#   "text": "인식된 텍스트",
#   "language": "ko",
#   "duration": 5.2
# }
```

### 3️⃣ 성능 모니터링

```bash
# 리소스 사용량 확인
docker stats stt-engine

# 예상 출력:
# CONTAINER   CPU %   MEM USAGE / LIMIT
# stt-engine  2.5%    2.1G / 8G
```

### 4️⃣ 로그 분석

```bash
# 마지막 100줄 로그
docker logs --tail 100 stt-engine

# 실시간 로그
docker logs -f stt-engine

# 타임스탬프 포함
docker logs -f --timestamps stt-engine

# 특정 시간 이후의 로그
docker logs --since 10m stt-engine
```

---

## 🎯 문제 해결

### 문제 1: `docker cp` 실패

```bash
# 오류: "Error response from daemon: No such container"

# 해결:
# 1. 컨테이너 ID 다시 확인
docker ps

# 2. 전체 ID로 시도
docker cp file.py <FULL_CONTAINER_ID>:/app/

# 3. 컨테이너 이름으로 시도
docker cp file.py stt-engine:/app/
```

### 문제 2: 재시작 후에도 파일이 반영 안 됨

```bash
# 원인: Python 캐시 (.pyc 파일)

# 해결: 캐시 삭제 후 재시작
docker exec <CONTAINER_ID> find /app -name "*.pyc" -delete
docker exec <CONTAINER_ID> find /app -name "__pycache__" -type d -exec rm -rf {} +
docker restart <CONTAINER_ID>
```

### 문제 3: 권한 오류

```bash
# 오류: "Permission denied"

# 해결: 파일 권한 조정
docker exec <CONTAINER_ID> chmod 644 /app/stt_engine.py
docker restart <CONTAINER_ID>
```

### 문제 4: 모듈 임포트 오류

```bash
# 오류: "ModuleNotFoundError: No module named 'faster_whisper'"

# 해결: 의존성 설치 확인
docker exec <CONTAINER_ID> pip list | grep faster-whisper

# 누락된 경우 설치
docker exec <CONTAINER_ID> pip install faster-whisper

# 또는 requirements.txt 사용
docker exec <CONTAINER_ID> pip install -r /app/requirements.txt
```

---

## 📊 테스트 결과 기록

변경사항을 테스트한 후 결과를 기록하세요:

```markdown
## 테스트 결과

### 변경사항
- [x] stt_engine.py 182줄 오류 수정
- [x] transcribe() 메서드 정규화

### 테스트 환경
- OS: RHEL 8.9
- Docker: 25.0.4
- 이미지: stt-engine:linux-x86_64
- 날짜: 2026-02-03

### 테스트 케이스

| 항목 | 상태 | 설명 |
|------|------|------|
| 헬스 체크 | ✅ | `/health` 엔드포인트 정상 |
| 한국어 음성 | ✅ | 5초 WAV 파일 인식 완료 |
| 영어 음성 | ✅ | 3초 MP3 파일 인식 완료 |
| 오류 처리 | ✅ | 지원되지 않는 형식 거부 |
| 메모리 사용 | ✅ | 안정적 (2.1GB) |

### 결론
✅ 정상 동작 확인됨, 새 이미지 빌드 권장
```

---

## 🚀 다음 단계

테스트 완료 후:

1. **정상 동작 확인**: 모든 테스트 케이스 통과
2. **새 이미지 빌드**: [SERVER_DEPLOYMENT_GUIDE.md](../SERVER_DEPLOYMENT_GUIDE.md) 참고
3. **배포**: 새 이미지로 운영환경 업데이트

---

## 💾 파일 목록

업데이트 가능한 주요 파일들:

| 파일 | 용도 | 우선순위 |
|------|------|---------|
| `stt_engine.py` | STT 엔진 로직 | 높음 |
| `api_server.py` | REST API 엔드포인트 | 높음 |
| `model_manager.py` | 모델 관리 | 중간 |
| `requirements.txt` | 패키지 버전 | 중간 |

---

## ⚡ 빠른 체크리스트

```
□ 수정된 파일 준비 완료
□ 서버로 파일 전송 완료
□ docker cp로 파일 복사 완료
□ docker restart 실행 완료
□ docker logs 확인 (오류 없음)
□ curl 헬스 체크 성공
□ 음성 파일 인식 테스트 성공
□ 테스트 결과 기록
□ 새 이미지 빌드 계획 수립
```

---

**상태**: 🟢 운영환경 핫픽스 완벽 가능 ✅
