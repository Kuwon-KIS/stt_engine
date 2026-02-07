# 🚀 EC2에서 STT Engine 빌드 가이드

**최신 업데이트**: 2026년 2월 7일

## 📋 필수 조건

- **EC2 인스턴스**: RHEL 8.9 (t3.xlarge 이상)
- **스토리지**: 100GB 이상 (모델 + 빌드)
- **메모리**: 16GB 이상 (권장)
- **인터넷**: 온라인 연결 필수
- **설치**: Docker 사전 설치

## 🛠️ EC2 빌드 순서

### Step 1: Repository Clone
```bash
cd /home/ec2-user
git clone https://github.com/Kuwon-KIS/stt_engine.git
cd stt_engine
```

### Step 2: 모델 다운로드
```bash
# 1.5GB 모델 다운로드 + CTranslate2 변환 + 압축
python3 download_model_hf.py
```

**결과:**
```
✅ models/openai_whisper-large-v3-turbo/
   ├── config.json
   ├── model.safetensors
   └── ctranslate2_model/
       ├── model.bin (1.5GB)
       ├── config.json
       └── vocabulary.json

✅ build/output/
   └── whisper-large-v3-turbo_models_[DATE].tar.gz (2.8GB)
   └── whisper-large-v3-turbo_models_[DATE].tar.gz.md5
```

### Step 3: Docker 이미지 빌드
```bash
# EC2용 스크립트 사용 (최신 상태)
bash scripts/build-server-image.sh
```

**옵션:**
```bash
bash scripts/build-server-image.sh v1.5        # v1.5로 빌드
bash scripts/build-server-image.sh cuda129     # CUDA 12.9 버전
```

**결과:**
```
✅ Docker 이미지: stt-engine:cuda129-rhel89-v1.4 (7.3GB)
✅ 저장 위치: build/output/stt-engine-cuda129-rhel89-v1.4.tar

소요시간: 20~40분
```

### Step 4: Docker 컨테이너 실행
```bash
# 이미지 로드 (필요시)
docker load -i build/output/stt-engine-cuda129-rhel89-v1.4.tar

# 컨테이너 실행
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/logs:/app/logs \
  -e CUDA_VISIBLE_DEVICES=0 \
  stt-engine:cuda129-rhel89-v1.4
```

### Step 5: 헬스 체크
```bash
# API 상태 확인
curl http://localhost:8003/health

# 컨테이너 로그 확인
docker logs -f stt-engine
```

---

## 📂 파일 구조 (EC2)

```
/home/ec2-user/stt_engine/
├── scripts/
│   ├── build-server-image.sh    ← Docker 이미지 빌드
│   ├── build-server-models.sh   ← 모델 다운로드 (옵션)
│   └── setup.sh                 ← 초기 설정
├── docker/
│   ├── Dockerfile               ← 기본 Dockerfile
│   ├── Dockerfile.engine.rhel89 ← RHEL 8.9용 (사용됨)
│   └── docker-compose.yml
├── models/                      ← 다운로드된 모델
│   └── openai_whisper-large-v3-turbo/
├── download_model_hf.py         ← 모델 다운로드 스크립트
├── main.py                      ← 진입점
├── api_server.py                ← API 서버
└── stt_engine.py                ← STT 엔진
```

---

## ⚠️ 문제 해결

### 모델 다운로드 시 OOM 발생
```
현상: 모델 로드 테스트에서 메모리 부족 (exit code -9)
해결책: 
  - 로드 테스트는 자동으로 스킵됨 (경고 표시)
  - 모델 파일은 정상적으로 생성됨
  - Docker에서 테스트 가능
```

### Docker 빌드 실패
```
확인사항:
  1. 인터넷 연결 확인: ping 8.8.8.8
  2. 디스크 공간 확인: df -h
  3. Docker 상태 확인: systemctl status docker
  4. 빌드 로그 확인: cat /tmp/build-image-*.log
```

### 컨테이너 시작 실패
```
확인사항:
  1. 포트 충돌: netstat -tlnp | grep 8003
  2. 모델 경로: ls -la models/
  3. Docker 로그: docker logs stt-engine
```

---

## 📊 리소스 요구사항

| 단계 | 메모리 | 시간 | 스토리지 |
|------|--------|------|---------|
| 모델 다운로드 | 2GB | 5분 | 1.5GB |
| CTranslate2 변환 | 6GB | 10분 | 3GB |
| Docker 이미지 빌드 | 4GB | 30분 | 7GB |
| 컨테이너 운영 | 2GB | - | - |
| **합계** | **16GB** | **45분** | **11.5GB** |

---

## 🔍 필수 스크립트 설명

### scripts/build-server-image.sh
- **목적**: Docker 이미지 빌드 (모델 제외)
- **선행작업**: 모델이 미리 다운로드되어야 함
- **사용법**: `bash scripts/build-server-image.sh [버전]`
- **산출물**: `stt-engine:cuda129-rhel89-v[버전]`

### scripts/build-server-models.sh
- **목적**: 모델 다운로드 및 변환
- **사용법**: `bash scripts/build-server-models.sh`
- **산출물**: `models/` 디렉토리

### scripts/setup.sh
- **목적**: 초기 환경 설정 (선택사항)
- **역할**: Python 환경, 의존성 설치

---

## 💡 팁

### 빠른 재빌드
```bash
# 모델이 이미 있으면, 이미지만 재빌드
bash scripts/build-server-image.sh v1.5
```

### 백그라운드 빌드
```bash
# 로그를 파일에 저장하고 백그라운드에서 실행
nohup bash scripts/build-server-image.sh > build.log 2>&1 &
tail -f build.log
```

### 멀티 버전 관리
```bash
# 여러 버전 빌드 가능
bash scripts/build-server-image.sh v1.4
bash scripts/build-server-image.sh v1.5
bash scripts/build-server-image.sh v2.0

# 확인
docker images | grep stt-engine
```

---

## 📚 추가 정보

더 자세한 정보는 다음 문서를 참고하세요:

- [docs/deployment/AWS_BUILD_GUIDE.md](../docs/deployment/AWS_BUILD_GUIDE.md) - AWS EC2 빌드 상세
- [docs/deployment/MODEL_DEPLOYMENT.md](../docs/deployment/MODEL_DEPLOYMENT.md) - 모델 배포
- [docs/deployment/DEPLOYMENT_CHECKLIST.md](../docs/deployment/DEPLOYMENT_CHECKLIST.md) - 배포 체크리스트
- [QUICKSTART.md](QUICKSTART.md) - 빠른 시작 (로컬용)

---

**작성일**: 2026년 2월 7일  
**상태**: 최신 상태 반영됨 ✅
