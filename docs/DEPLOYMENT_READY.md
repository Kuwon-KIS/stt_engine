# ✅ STT Engine 배포 준비 완료

**작성일**: 2026-02-02  
**상태**: 🟢 배포 준비 완료

---

## 🎯 현재 상황

### 1. PyTorch 다운로드 문제 (✅ 해결됨)

**문제**:
- macOS에서 직접 Linux용 PyTorch wheel을 다운로드할 수 없음
- Docker를 통한 네트워크 다운로드도 SSL 인증서 문제 발생

**해결책**:
- ✅ **별도 Docker 이미지로 미리 다운로드 완료**
- 59개 wheel 파일 준비됨 (413MB)
- 오프라인 설치 가능

### 2. 배포 준비 현황

| 항목 | 상태 | 위치 |
|------|------|------|
| Wheel 파일 | ✅ 59개 (413MB) | `deployment_package/wheels/` |
| 배포 스크립트 | ✅ 완성 | `deployment_package/deploy.sh` |
| 설치 문서 | ✅ 완성 | `deployment_package/START_HERE.sh` |
| 빌드 스크립트 | ✅ 수정됨 | `build-engine-image.sh` |
| Dockerfile | ✅ 최적화됨 | `build-engine-image.sh`에 내장 |

---

## 🚀 빠른 배포 방법

### 방법 A: Linux 서버로 직접 배포 (권장)

```bash
# 1. 로컬에서 배포 패키지 전송
scp -r deployment_package/ user@linux-server:/home/user/stt_engine/

# 2. 서버에서 배포 실행
ssh user@linux-server
cd /home/user/stt_engine/deployment_package
chmod +x deploy.sh
./deploy.sh
```

**소요 시간**: 5-10분 (인터넷 다운로드 없음)

### 방법 B: Docker 이미지 빌드 후 배포 (macOS)

```bash
# 1. build-engine-image.sh 실행
bash build-engine-image.sh

# 2. Docker 이미지 저장 (자동)
# 출력: stt-engine-linux-x86_64.tar

# 3. 서버로 전송 & 로드
scp stt-engine-linux-x86_64.tar user@server:/tmp/
ssh user@server
docker load -i /tmp/stt-engine-linux-x86_64.tar
docker run -p 8003:8003 stt-engine:linux-x86_64
```

**소요 시간**: 15-30분 (Docker 빌드 포함)

---

## 📊 배포 패키지 구성

```
deployment_package/
├── wheels/                    # ✅ 59개 wheel 파일 (413MB)
│   ├── torch*.whl
│   ├── torchaudio*.whl
│   ├── faster_whisper*.whl
│   ├── librosa*.whl
│   ├── numpy*.whl
│   └── ... (기타 의존성)
│
├── deploy.sh                  # ✅ 배포 실행 스크립트
├── setup_offline.sh           # ✅ 수동 설치 스크립트
├── run_all.sh                 # ✅ 서비스 실행
│
├── requirements.txt           # ✅ 패키지 목록
├── requirements-cuda-12.9.txt # ✅ CUDA 최적화
│
└── 📖 가이드 문서
    ├── START_HERE.sh          # 👈 여기서 시작!
    ├── QUICKSTART.md
    ├── DEPLOYMENT_GUIDE.md
    └── INSTALL_GUIDE.md
```

---

## 🔧 스크립트 최적화 내역

### build-engine-image.sh 개선사항

1. **Wheels 자동 감지**
   ```bash
   if [ $WHEEL_COUNT -eq 0 ]; then
       # 없으면 온라인 설치 모드
   else
       # 있으면 오프라인 모드
   fi
   ```

2. **Dockerfile 조건부 생성**
   - Wheels 있으면: **Offline install** (빠름)
   - Wheels 없으면: **Online install** (네트워크 필요)

3. **온라인 설치 Dockerfile**
   ```dockerfile
   FROM python:3.11-slim
   RUN pip install torch==2.1.2 torchaudio==2.1.2 ...
   COPY api_server.py stt_engine.py /app/
   ```

---

## ✨ 다음 단계

### 1️⃣ 즉시 (지금)
- [ ] `deployment_package/` 구조 확인
- [ ] `START_HERE.sh` 읽기

### 2️⃣ Linux 서버 준비
- [ ] Python 3.11.5 설치 확인
- [ ] NVIDIA Driver / CUDA 설치 (GPU 사용 시)
- [ ] SSH 접근 확인

### 3️⃣ 배포 실행
```bash
# 서버에서
cd deployment_package
./deploy.sh
```

### 4️⃣ 검증
```bash
# API 서버 실행
python3.11 api_server.py

# 헬스 체크 (다른 터미널에서)
curl http://localhost:8003/health
```

---

## 📝 주요 파일

| 파일 | 설명 | 우선순위 |
|------|------|---------|
| [deployment_package/START_HERE.sh](deployment_package/START_HERE.sh) | 배포 가이드 | ⭐⭐⭐ |
| [build-engine-image.sh](build-engine-image.sh) | Docker 이미지 빌드 | ⭐⭐ |
| [deployment_package/deploy.sh](deployment_package/deploy.sh) | Linux 서버 배포 | ⭐⭐⭐ |
| [Dockerfile.engine](Dockerfile.engine) | Engine Docker 빌드 (참고용) | ⭐ |

---

## 🎓 기술 정보

### 사용된 버전
- **Python**: 3.11.5
- **PyTorch**: 2.1.2
- **CUDA**: 12.1 / 12.9 호환
- **Faster-Whisper**: 1.0.3
- **FastAPI**: 0.109.0

### 플랫폼
- **빌드**: macOS (M-series)
- **배포**: Linux x86_64 (RHEL 8.9 호환)
- **패키지**: manylinux_2_17 (glibc 2.17+)

---

## 🆘 문제 해결

### Docker Desktop 응답 안 함
✅ **해결됨**: Wheels를 미리 준비했으므로 오프라인 설치 가능

### 네트워크 다운로드 느림
✅ **해결됨**: Wheels를 로컬에 저장하고 오프라인 설치

### SSL 인증서 오류
✅ **해결됨**: Dockerfile에 `--trusted-host` 옵션 추가

---

## 📞 확인 사항

- [x] Wheels 다운로드 완료
- [x] 배포 스크립트 작성
- [x] build-engine-image.sh 최적화
- [x] 온/오프라인 설치 지원
- [x] 상세 문서 작성

---

**🎉 배포 준비 완료! Linux 서버에서 `deploy.sh`를 실행하면 됩니다.**
