# 📦 Deployment Package (배포 패키지)

이 디렉토리는 Linux 서버에서 STT Engine을 설치하고 실행하기 위한 모든 것을 포함합니다.

## 📂 구조

```
deployment_package/
├── README.md                     # 이 파일
├── START_HERE.sh                 # ⭐ 배포 시작 가이드
│
├── 🚀 배포 스크립트
│   ├── deploy.sh                 # 메인 배포 스크립트
│   ├── setup_offline.sh          # 수동 설치
│   ├── run_all.sh                # 서비스 실행
│   ├── post_deploy_setup.sh      # 사후 설정
│   └── verify-wheels.sh          # 휠 검증
│
├── 📦 의존성 (413MB)
│   └── wheels/                   # 59개 wheel 파일
│       ├── torch-2.1.2-...whl
│       ├── torchaudio-2.1.2-...whl
│       ├── faster_whisper-1.0.3-...whl
│       └── ... (기타 19개)
│
├── ⚙️ 설정 파일
│   ├── requirements.txt          # 표준 패키지 목록
│   └── requirements-cuda-12.9.txt # CUDA 최적화 버전
│
├── 📖 가이드 (로컬에서만 참고)
│   ├── DEPLOYMENT_STATUS.md
│   ├── INSTALL_GUIDE.md
│   ├── QUICK_REFERENCE.md
│   └── START_HERE.sh
│
└── 🔧 개발용 (무시)
    ├── _ARCHIVED/                # 아카이브
    ├── create_split_wheels.py    # 휠 분할 (사용 안 함)
    ├── Dockerfile.wheels-download # wheel 다운로드 (로컬용)
    ├── pytorch_packages/         # PyTorch 패키지 (사용 안 함)
    └── wheels_x86_64/            # 대체 휠 (사용 안 함)
```

---

## 🚀 빠른 시작 (3단계)

### Step 1: 로컬에서 패키지 전송
```bash
# 로컬 머신 (macOS/Linux)
scp -r deployment_package/ user@server:/home/user/stt_engine/
```

### Step 2: 서버에서 배포
```bash
# Linux 서버
ssh user@server
cd /home/user/stt_engine/deployment_package
chmod +x deploy.sh
./deploy.sh
```

### Step 3: API 실행
```bash
# 같은 서버에서
python3.11 api_server.py

# 테스트 (다른 터미널)
curl http://localhost:8003/health
```

**완료! 🎉**

---

## 📝 각 스크립트 설명

### ⭐ deploy.sh (메인)
**목적**: 자동 배포  
**기능**:
- 의존성 확인
- wheel 파일 설치
- 환경 구성
- 서비스 등록 (선택)

```bash
./deploy.sh
```

**사용자 입력**: 거의 없음 (자동)

---

### setup_offline.sh (대체)
**목적**: 수동 단계별 설치  
**기능**: deploy.sh의 각 단계를 수동으로 실행

```bash
./setup_offline.sh
```

**사용자 입력**: 각 단계마다 확인 필요

---

### run_all.sh (실행)
**목적**: STT Engine 서비스 시작  
**기능**:
- 모델 다운로드 (필요시)
- API 서버 실행
- 헬스 체크

```bash
./run_all.sh
```

---

### post_deploy_setup.sh (사후)
**목적**: 배포 후 추가 설정  
**기능**:
- systemd 서비스 등록
- 자동 시작 설정
- 로깅 설정

```bash
./post_deploy_setup.sh
```

---

### verify-wheels.sh (검증)
**목적**: wheel 파일 검증  
**기능**:
- 파일 수 확인
- 파일 크기 확인
- 무결성 확인

```bash
./verify-wheels.sh
```

---

## ⚙️ 설정 파일

### requirements.txt
표준 패키지 목록 (CPU 모드)

```bash
pip install -r requirements.txt
```

### requirements-cuda-12.9.txt
GPU 사용시 권장 (CUDA 12.9 최적화)

```bash
pip install -r requirements-cuda-12.9.txt
```

---

## 📦 Wheel 파일 (413MB)

59개의 사전 컴파일된 wheel 파일이 포함되어 있습니다.

| 패키지 | 버전 | 개수 |
|--------|------|------|
| PyTorch | 2.1.2 | 2 |
| TorchAudio | 2.1.2 | 1 |
| Faster-Whisper | 1.0.3 | 1 |
| 기타 의존성 | - | 55 |

**총 크기**: 413MB  
**설치 후**: ~2GB

---

## 🔍 배포 과정

```
사전 조건 확인
  ↓ (Python 3.11, 디스크 2GB+)
Wheel 검증
  ↓ (59개 파일, 413MB)
Wheel 설치
  ↓ (pip install --no-index)
환경 설정
  ↓ (.env, 경로 설정)
준비 완료
  ↓
python3.11 api_server.py
  ↓
API 실행 (http://localhost:8003)
```

---

## 🛠️ 문제 해결

### 배포 실패

```bash
# 로그 확인
tail -100 /tmp/stt_deploy.log

# wheel 검증
./verify-wheels.sh

# 수동 재설치
./setup_offline.sh
```

### API 시작 안 됨

```bash
# 1. 모델 다운로드 대기 (1-2분)
# 2. 로그 확인
python3.11 api_server.py

# 3. 디버그 정보
python3.11 -c "import torch; print(torch.__version__)"
```

### 메모리 부족

```bash
# 여유 메모리 확인
free -h

# 캐시 정리
rm -rf ~/.cache/huggingface
```

---

## 📊 시스템 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| Python | 3.11.0 | 3.11.5 |
| RAM | 2GB | 8GB |
| Disk | 2GB | 10GB |
| Network | 필요 없음 | 모델 다운로드시 |

---

## 🔐 보안

### 권장사항
- [ ] 데이터베이스 백업
- [ ] API 인증 추가 (필요시)
- [ ] 방화벽 설정
- [ ] HTTPS 설정 (프로덕션)

### .env 파일
```bash
# 생성 (선택)
cp .env.example .env
# 비밀번호 등 설정
```

---

## 📚 가이드

| 문서 | 내용 |
|------|------|
| START_HERE.sh | 단계별 배포 가이드 |
| INSTALL_GUIDE.md | 상세 설치 문서 |
| DEPLOYMENT_STATUS.md | 배포 상태 확인 |
| QUICK_REFERENCE.md | 빠른 참고 |

---

## 🚀 고급 사용법

### systemd 서비스로 등록

```bash
./post_deploy_setup.sh

# 또는 수동
sudo systemctl start stt-engine
sudo systemctl enable stt-engine
```

### 여러 포트에서 실행

```bash
# API_PORT 환경변수 변경
API_PORT=8004 python3.11 api_server.py
```

### GPU 사용

```bash
# CUDA 활성화
export CUDA_VISIBLE_DEVICES=0
python3.11 api_server.py

# GPU 확인
nvidia-smi
```

### 백그라운드 실행

```bash
nohup python3.11 api_server.py > api.log 2>&1 &
```

---

## 📞 지원

- **배포 실패**: 로그 확인 후 `verify-wheels.sh` 실행
- **성능 문제**: GPU 활성화 또는 메모리 증설
- **API 오류**: 모델 다운로드 완료 대기

---

## ✅ 체크리스트

배포 전:
- [ ] Python 3.11 설치 확인
- [ ] 디스크 2GB+ 여유
- [ ] Network 접근 가능 (모델 다운로드)

배포 중:
- [ ] deploy.sh 실행
- [ ] 오류 없음 확인
- [ ] wheel 검증 통과

배포 후:
- [ ] API 서버 시작
- [ ] 헬스 체크 성공
- [ ] 테스트 요청 정상

---

**버전**: 1.0  
**마지막 업데이트**: 2026-02-02  
**상태**: ✅ 배포 준비 완료
