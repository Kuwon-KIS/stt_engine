# 📊 [2026-02-03 v1.0] 최종 빌드 설정 및 버전 정보

**버전**: v1.0 (2026-02-03)  
**목적**: STT Engine CUDA 12.9 빌드 - 최신 설정 및 검증 정보  
**상태**: ✅ 최신 (실제 배포 기준)

---

## 📋 시스템 정보

### 개발 머신 (Mac)

| 항목 | 정보 |
|------|------|
| OS | macOS (arm64 또는 x86_64) |
| Docker | Docker Desktop for Mac (최신) |
| 네트워크 | 온라인 필수 (pip install 사용) |
| 스토리지 | 15GB 여유 공간 필요 (빌드 중 임시 파일) |

### 타겟 서버 (Linux)

| 항목 | 정보 |
|------|------|
| OS | RHEL 8.9 (Linux x86_64) |
| GPU Driver | 575.57.08 ✅ |
| CUDA Runtime | 12.9 ✅ |
| CUDA Toolkit (nvcc) | 미설치 (필요 없음) |
| 네트워크 | 오프라인 가능 (tar 파일 사용) |
| 스토리지 | 10GB 여유 공간 필요 |
| Docker | 최신 버전 |

---

## 🐳 Docker 이미지 최신 설정

### 빌드 정보

```bash
# 이미지 이름
stt-engine:cuda129-v1.0

# Base Image
FROM --platform=linux/amd64 python:3.11-slim

# 용량
압축 전: ~8.5GB
압축 후: ~750MB (gzip)

# 빌드 시간
15~20분 (Mac에서 온라인 빌드 시)
```

### PyTorch 및 주요 패키지 버전

```bash
# PyTorch (CUDA 지원)
PyTorch: 2.1.2
CUDA: 12.4 (PyTorch 공식 제공)
cuDNN: 8.x (자동 설치)
Torchaudio: 2.1.2
Torchvision: 0.16.2

# Audio/ML 패키지
faster-whisper: 1.0.3
librosa: 0.10.0
scipy: 1.12.0
numpy: 1.24.3
huggingface-hub: 0.21.4

# Web Framework
fastapi: 0.109.0
uvicorn: 0.27.0
requests: 2.31.0
pydantic: 2.5.3

# 기타
python-dotenv: 1.0.0
pyyaml: 6.0.1
python-multipart: 0.0.6
```

### CUDA 호환성 주의사항

```
⚠️  중요: PyTorch CUDA 버전 호환성

상황:
- PyTorch 공식 제공: CUDA 12.4용 wheel
- 서버 환경: CUDA 12.9 Runtime

해결:
- CUDA Runtime은 forward compatible ✅
- PyTorch CUDA 12.4 wheel이 서버의 CUDA 12.9에서 실행 가능
- torch.version.cuda = "12.4" (또는 12.9로 업스트림)

검증:
docker exec <container> python3.11 -c \
  "import torch; print(f'CUDA: {torch.version.cuda}'); print(f'Available: {torch.cuda.is_available()}')"

# 예상 결과:
# CUDA: 12.4 (또는 12.9)
# Available: True ✅
```

---

## 🚀 빌드 스크립트 정보

### 스크립트 경로
```
/Users/a113211/workspace/stt_engine/build-stt-engine-cuda.sh
```

### 스크립트 기능

```bash
# 자동 수행 항목:
1. ✅ 환경 검사 (Docker, 인터넷)
2. ✅ Dockerfile 생성 (CUDA 12.9 최적화)
3. ✅ Docker 이미지 빌드 (온라인 PyTorch 설치)
4. ✅ 이미지 검증 (torch.cuda.is_available())
5. ✅ tar 파일로 저장
6. ✅ gzip 압축

# 스크립트 실행:
bash build-stt-engine-cuda.sh

# 실행 시간: 약 40분
# 최종 파일: stt-engine-cuda129-v1.0.tar.gz (750MB)
```

### 스크립트 옵션

```bash
# 상세 로그 보기
bash -x build-stt-engine-cuda.sh

# 빌드 후 디렉토리 정리 (자동)
# /tmp/stt_engine_cuda_build 자동 삭제
```

---

## 📁 생성 파일 위치 및 용량

| 파일 | 경로 | 크기 | 용도 |
|------|------|------|------|
| **최종 배포 파일** | `/Users/a113211/workspace/stt_engine/build/output/stt-engine-cuda129-v1.0.tar.gz` | 750MB | 서버로 전송 |
| tar 압축 해제 | (전송 후 서버에서) | 8.5GB | docker load 사용 |
| Docker 이미지 | `stt-engine:cuda129-v1.0` | 8.5GB | 컨테이너 실행 |

---

## ✅ 검증 체크리스트

### 빌드 전 (Mac)

- [ ] Docker Desktop이 실행 중인가?
- [ ] 인터넷이 연결되어 있는가?
- [ ] `/Users/a113211/workspace/stt_engine/` 경로 확인
- [ ] `api_server.py`, `stt_engine.py`, `requirements.txt` 존재 확인
- [ ] 15GB 여유 스토리지 확인

### 빌드 후 (Mac)

- [ ] 스크립트 실행 완료 (오류 없음)
- [ ] Docker 이미지 확인: `docker images | grep stt-engine`
- [ ] `stt-engine-cuda129-v1.0.tar.gz` 파일 생성 확인
- [ ] 파일 크기 확인 (약 750MB)

### 배포 전 (Linux 서버)

- [ ] 서버 인터넷 연결 확인 (docker load 중 의존성 다운로드)
- [ ] Docker 설치 확인: `docker --version`
- [ ] GPU 확인: `nvidia-smi` (드라이버 575.57.08 확인)
- [ ] CUDA 런타임 확인: `nvidia-smi` (CUDA 12.9 표시)
- [ ] 10GB 여유 스토리지 확인

### 배포 후 (Linux 서버)

- [ ] 이미지 로드 완료: `docker images | grep stt-engine`
- [ ] 컨테이너 실행: `docker run -d --gpus all ...`
- [ ] CUDA 가용성 검증: `docker exec ... torch.cuda.is_available()`
- [ ] API 헬스 체크: `curl http://localhost:8003/health`

---

## 📚 관련 문서

| 문서 | 목적 |
|------|------|
| [PYTORCH_INSTALL_METHODS_ANALYSIS.md](PYTORCH_INSTALL_METHODS_ANALYSIS.md) | 과거 방법 분석 + 최종 스크립트 |
| [CORRECT_FINAL_DEPLOYMENT.md](CORRECT_FINAL_DEPLOYMENT.md) | 서버 배포 가이드 |
| [DOCUMENT_VERSION_INDEX.md](DOCUMENT_VERSION_INDEX.md) | 전체 문서 인덱스 |

---

## 🔄 업데이트 이력

| 버전 | 날짜 | 변경사항 |
|------|------|---------|
| v1.0 | 2026-02-03 | 초기 배포 - CUDA 12.9 빌드 설정 정리 |

---

## 💡 자주 묻는 질문

**Q: 왜 PyTorch 2.1.2를 사용하나?**  
A: 안정적이고 CUDA 12.4 공식 지원, 서버 CUDA 12.9와 호환 가능

**Q: 빌드 중 인터넷이 끊기면?**  
A: 스크립트를 다시 실행하면 캐시에서 재개됨 (docker build layer 캐시)

**Q: tar 파일 압축을 풀지 말고 바로 사용할 수 있나?**  
A: 불가능. `docker load`는 tar 파일 필요 (압축 해제 필수)

**Q: 서버에서 CUDA 12.9가 아니라 12.4라면?**  
A: 동일하게 작동함 (역방향 호환성)

**Q: GPU가 여러 개면?**  
A: `CUDA_VISIBLE_DEVICES=0,1,2` 환경변수로 조정 가능

---

**최종 상태**: ✅ 2026년 2월 3일 검증 완료  
**다음 단계**: `build-stt-engine-cuda.sh` 실행 후 배포
