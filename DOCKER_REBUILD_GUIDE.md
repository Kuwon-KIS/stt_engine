# Docker 이미지 재빌드 가이드

## 📌 현재 상황

### 수정된 파일
- ✅ `stt_engine.py` - `local_files_only=True` 추가됨

### 필요한 작업
- 🔄 새로운 코드를 포함한 Docker 이미지 재빌드

---

## 🚀 재빌드 방법

### 방법 1: 자동 빌드 스크립트 (권장)

```bash
cd /Users/a113211/workspace/stt_engine
bash build-stt-engine-cuda.sh
```

**소요 시간**: 약 15-20분
**예상 이미지 크기**: 약 8-10GB

### 방법 2: 수동 Docker 빌드

만약 자동 스크립트가 실패하면:

```bash
cd /Users/a113211/workspace/stt_engine

# 기존 이미지 확인
docker images | grep stt-engine

# 빌드 디렉토리 생성
mkdir -p /tmp/stt_rebuild
cp stt_engine.py api_server.py requirements.txt /tmp/stt_rebuild/

# Dockerfile 생성 및 빌드
cd /tmp/stt_rebuild
docker build -t stt-engine:cuda129-v1.0-updated .
```

---

## 📋 빌드 진행 상황 확인

빌드 중 다른 터미널에서 다음을 실행:

```bash
# Docker 빌드 상태 확인
docker ps -a | grep stt-engine

# 로그 확인
docker logs <container_id>

# 이미지 생성 확인
docker images | grep stt-engine
```

---

## ✅ 빌드 완료 확인

빌드가 완료되면:

```bash
docker images | grep stt-engine

# 예상 출력:
# stt-engine    cuda129-v1.0    <IMAGE_ID>    <DATE>    8.5GB
```

---

## 🔄 빌드 후 다음 단계

### 1. 컨테이너 실행

```bash
bash run-docker-gpu.sh
```

또는

```bash
docker run -d \
  --name stt-engine-gpu \
  --gpus all \
  -p 8003:8003 \
  -v /Users/a113211/workspace/stt_engine/models:/app/models \
  -e HF_HUB_OFFLINE=1 \
  -e TRANSFORMERS_OFFLINE=1 \
  stt-engine:cuda129-v1.0
```

### 2. 모델 초기화 대기

```bash
# 약 2-3분 대기
sleep 180

# 로그 확인
docker logs stt-engine-gpu
```

### 3. 헬스 체크

```bash
curl http://localhost:8003/health

# 예상 응답:
# {"status": "healthy", "model": "loaded"}
```

---

## ⚠️ 주의사항

### 빌드 시간
- 첫 빌드: 15-20분
- PyTorch 다운로드: 약 10분
- 나머지 의존성: 약 5-10분

### 시스템 요구사항
- 디스크 공간: 최소 50GB (빌드 임시 공간)
- 메모리: 최소 4GB
- 인터넷: 필수 (빌드 시에만)

### 네트워크 문제 발생 시
```bash
# 방화벽 확인
# apt가 차단되지 않았는지 확인
# PyTorch 저장소 접근 확인
```

---

## 🛠️ 문제 해결

### 빌드 실패

```bash
# 빌드 컨텍스트 정리
rm -rf /tmp/stt_engine_cuda_build

# 재시도
bash build-stt-engine-cuda.sh
```

### 디스크 공간 부족

```bash
# 사용하지 않는 이미지 제거
docker image prune -a

# 다시 빌드
bash build-stt-engine-cuda.sh
```

### 메모리 부족

```bash
# 다른 컨테이너 중지
docker stop <container_name>

# 빌드 재시작
bash build-stt-engine-cuda.sh
```

---

## 📊 빌드 정보

| 항목 | 정보 |
|------|------|
| **Base Image** | python:3.11-slim |
| **CUDA** | 12.4 호환성 (cu124) |
| **PyTorch** | 2.6.0 |
| **Python** | 3.11 |
| **이미지 태그** | stt-engine:cuda129-v1.0 |
| **예상 크기** | 8-10GB |

---

## ✅ 완료 체크리스트

- [ ] `stt_engine.py` 수정됨 (`local_files_only=True` 추가)
- [ ] Docker 이미지 재빌드 시작
- [ ] 빌드 완료 확인 (docker images)
- [ ] 컨테이너 실행
- [ ] 모델 로드 완료 (로그 확인)
- [ ] 헬스 체크 성공
- [ ] STT API 테스트 완료

---

**생성일**: 2026-02-03  
**상태**: 재빌드 가이드 작성 완료
