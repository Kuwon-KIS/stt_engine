# 🚨 실시간 오류 해결: 서버 이미지 핫픽스

**상황**: 서버에 배포된 이미지가 구 버전 코드를 가지고 있음  
**오류**: 
1. stt_engine.py 182줄 문법 오류 (unterminated string literal)
2. python-multipart 패키지 누락

**소요시간**: ~15분

---

## 🔧 즉시 해결 방법

### Step 1: 수정된 stt_engine.py 서버로 전송

로컬 머신에서:
```bash
# 로컬에서 수정된 파일 확인
cat stt_engine.py | head -20

# 서버로 전송
scp stt_engine.py user@server:/tmp/
```

### Step 2: 서버에서 컨테이너로 파일 복사

서버에서:
```bash
# 1️⃣ 컨테이너 ID 확인
docker ps -a | grep stt-engine
# 예상 결과: 29534921b493

# 2️⃣ 파일 복사
docker cp /tmp/stt_engine.py 29534921b493:/app/stt_engine.py

# 3️⃣ 파일 복사 확인
docker exec 29534921b493 head -20 /app/stt_engine.py
```

### Step 3: python-multipart 패키지 설치

```bash
# 1️⃣ 방법 A: 컨테이너 내에서 직접 설치 (빠름)
docker exec 29534921b493 pip install python-multipart

# 2️⃣ 방법 B: wheel 파일에서 설치 (오프라인)
# python-multipart를 deployment_package/wheels/ 에서 찾기
docker exec 29534921b493 pip install --no-index --find-links=/wheels/ python-multipart

# 설치 확인
docker exec 29534921b493 pip list | grep python-multipart
```

### Step 4: 컨테이너 재시작

```bash
# 컨테이너 재시작
docker restart 29534921b493

# 로그 확인 (오류 없는지 확인)
docker logs 29534921b493

# 예상 로그:
# ✅ faster-whisper 모델 로드 완료
# INFO:     Uvicorn running on http://0.0.0.0:8003
```

### Step 5: 헬스 체크

```bash
# API 테스트
curl http://localhost:8003/health

# 예상 응답:
# {"status":"ok","version":"1.0.0","engine":"faster-whisper"}
```

---

## ✅ 문제 해결 확인 체크리스트

```
오류 1: unterminated string literal
□ docker cp로 수정된 stt_engine.py 복사
□ docker restart 실행
□ docker logs로 오류 확인 (없어야 함)

오류 2: python-multipart 누락
□ pip install python-multipart 실행
□ docker restart 실행
□ curl /health로 API 정상 확인

테스트
□ curl http://localhost:8003/health (성공)
□ 음성 파일로 /transcribe 테스트 (성공)
□ 메모리/CPU 모니터링 정상
```

---

## 🎯 모든 오류 설명

### 오류 1: "unterminated string literal at line 182"

**원인**: 서버의 이미지가 구 버전 stt_engine.py를 가지고 있음

**로그**:
```
File "/app/stt_engine.py", line 182
    stt = WhisperSTT(model_path, device=device)uda"):
                                                  ^
SyntaxError: unterminated string literal
```

**해결**:
```bash
docker cp /tmp/stt_engine.py 29534921b493:/app/stt_engine.py
docker restart 29534921b493
```

---

### 오류 2: "python-multipart" 설치되지 않음

**원인**: FastAPI의 File Upload 기능 사용에 필요한 패키지 누락

**로그**:
```
RuntimeError: Form data requires "python-multipart" to be installed.
```

**해결**:
```bash
docker exec 29534921b493 pip install python-multipart
docker restart 29534921b493
```

---

### 오류 3: "CUDA driver version is insufficient"

**원인**: GPU 드라이버 버전 불일치 (이미지는 CUDA 12.1이지만 서버는 낮은 버전)

**로그**:
```
❌ 모델 로드 실패: CUDA failed with error CUDA driver version is insufficient for CUDA runtime version
```

**해결방법**:

**방법 A: CPU 모드로 실행 (빠른 해결)**
```bash
# api_server.py 수정
docker exec 29534921b493 sed -i 's/device="cuda"/device="cpu"/' /app/api_server.py
docker restart 29534921b493

# 단점: 느림 (5배 이상 느림)
```

**방법 B: GPU 드라이버 업그레이드 (최적)**
```bash
# 서버에서 NVIDIA 드라이버 확인
nvidia-smi

# 드라이버 업그레이드 필요하면
sudo apt-get install nvidia-driver-550  # 또는 최신 버전

# 재부팅
sudo reboot

# 확인
nvidia-smi | head -5
```

**방법 C: 새 이미지 빌드 (CPU 최적화 버전)**
```bash
# 로컬에서 CPU 모드 이미지 생성
# Dockerfile.engine 수정: device="cuda" → device="cpu"
# 또는 docker-compose에서 환경변수 사용
```

---

## 📊 전체 순서 (추천)

### 즉시 (5분)
1. ✅ docker cp로 stt_engine.py 복사
2. ✅ pip install python-multipart
3. ✅ docker restart

### 테스트 (5분)
4. ✅ curl 헬스 체크
5. ✅ 음성 파일 테스트

### GPU 최적화 (10분)
6. ⏭️ GPU 드라이버 버전 확인
7. ⏭️ 필요시 업그레이드

### 최종 이미지 빌드 (30분)
8. ⏭️ 새 이미지 빌드 (scripts/build-engine-image.sh)
9. ⏭️ 새 이미지로 배포

---

## 🚀 완전 자동화 스크립트

서버에서 실행:

```bash
#!/bin/bash
set -e

CONTAINER_ID="29534921b493"
SCP_SOURCE="user@local:/path/to/stt_engine.py"
TEMP_PATH="/tmp/stt_engine.py"

echo "🔄 STT Engine 핫픽스 시작..."

# 1. 파일 복사
echo "📂 stt_engine.py 복사 중..."
scp $SCP_SOURCE $TEMP_PATH
docker cp $TEMP_PATH $CONTAINER_ID:/app/stt_engine.py

# 2. 패키지 설치
echo "📦 python-multipart 설치 중..."
docker exec $CONTAINER_ID pip install python-multipart

# 3. 컨테이너 재시작
echo "🔄 컨테이너 재시작 중..."
docker restart $CONTAINER_ID

# 4. 헬스 체크
echo "✅ 헬스 체크 중..."
sleep 3
curl http://localhost:8003/health

echo "🎉 핫픽스 완료!"
```

---

## 📝 테스트 결과 기록

핫픽스 후 테스트 결과:

```
## 핫픽스 결과

### 변경사항
- stt_engine.py: 손상된 구 버전 → 수정된 신 버전 (docker cp)
- python-multipart: 설치 완료

### 테스트
- [ ] docker logs: 오류 없음
- [ ] curl /health: OK
- [ ] 한국어 음성: 테스트 완료
- [ ] 메모리 사용: 정상

### 결론
- [ ] 정상 동작 확인, 새 이미지 빌드 준비 중
```

---

## 🔄 다음 단계

핫픽스로 검증 후:

1. **다른 환경에도 적용** (필요시)
   ```bash
   docker cp stt_engine.py <OTHER_CONTAINER>:/app/
   docker exec <OTHER_CONTAINER> pip install python-multipart
   docker restart <OTHER_CONTAINER>
   ```

2. **새 이미지 빌드**
   ```bash
   bash scripts/build-engine-image.sh
   ```

3. **새 이미지 배포**
   ```bash
   docker stop stt-engine
   docker rm stt-engine
   docker load -i build/output/stt-engine-linux-x86_64.tar
   docker run ... stt-engine:linux-x86_64
   ```

---

**상태**: 🟢 즉시 해결 가능 ✅
