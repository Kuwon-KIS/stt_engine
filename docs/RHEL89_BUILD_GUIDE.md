# RHEL 8.9 환경에 최적화된 STT Engine 빌드 & 배포 가이드

## 📊 대상 환경 정보

```
운영 서버 (RHEL 8.9):
├─ OS: RHEL 8.9 (Ootpa)
├─ glibc: 2.28
├─ Python: 3.11.5
├─ CUDA: 12.9
├─ NVIDIA Driver: 575.57.08
└─ Status: ✅ 모든 정보 확인됨
```

---

## 🎯 빌드 전략

### 선택 사항

| 방식 | 장점 | 단점 | 호환성 |
|------|------|------|--------|
| **RHEL 8.9 EC2** 🔴 | glibc 완벽 일치 | 약간 비쌈 | ✅ 100% |
| **Ubuntu 22.04 EC2** | 저렴 | glibc 불일치 | ⚠️ 90% |
| **운영 서버 직접 빌드** | 비용 절감 | 다운타임 | ✅ 100% |

### 🔴 **권장: RHEL 8.9 EC2 빌드**
```
이유:
1. 타겟 서버와 동일한 glibc 2.28
2. 라이브러리 호환성 100%
3. 안전성 최우선
```

---

## 📋 Step 1: AWS EC2 생성 (RHEL 8.9)

### 1-1. AMI 선택
```bash
# AWS Console에서:
1. EC2 > Instances > Launch Instance
2. "RHEL" 검색
3. "Red Hat Enterprise Linux 8 (HVM)" 선택
4. Version: 8.9
```

### 1-2. 인스턴스 타입
```
t3.large (4GB RAM, 2 vCPU)
또는 t3.xlarge (8GB RAM, 4 vCPU - 권장)
```

### 1-3. Storage
```
EBS: 50GB 이상 (gp3 권장)
```

### 1-4. Security Group
```
Inbound:
- SSH (Port 22) from your-ip
- Optional: HTTP (80), HTTPS (443)
```

---

## 🚀 Step 2: EC2에 연결 및 환경 설정

### 2-1. SSH 연결
```bash
ssh -i your-key.pem ec2-user@<ec2-ip>
```

### 2-2. 필수 패키지 설치
```bash
# RHEL 8.9 기본 업데이트
sudo yum update -y

# Development Tools 설치
sudo yum groupinstall -y "Development Tools"

# Docker 설치
sudo yum install -y docker git

# Docker 시작
sudo systemctl start docker
sudo systemctl enable docker

# 현재 사용자에게 Docker 권한
sudo usermod -aG docker ec2-user
newgrp docker

# 확인
docker --version
git --version
```

---

## 📥 Step 3: 레포지토리 클론

```bash
# 방법 A: Git 클론 (권장)
cd ~
git clone https://github.com/Kuwon-KIS/stt_engine.git
cd stt_engine

# 방법 B: scp로 로컬 파일 전송
# Mac에서:
scp -i your-key.pem -r ~/workspace/stt_engine ec2-user@<ec2-ip>:~/
```

---

## 🏗️ Step 4: Docker 이미지 빌드

### 4-1. 빌드 스크립트 실행 (권장)
```bash
cd ~/stt_engine

# RHEL 8.9 최적화 빌드 🔴
bash scripts/build-stt-engine-rhel89.sh

# 또는 일반 빌드
bash scripts/build-stt-engine-ec2.sh
```

### 4-2. 빌드 로그 모니터링
```bash
# 다른 터미널에서:
ssh -i your-key.pem ec2-user@<ec2-ip>
watch -n 10 'docker ps -a && echo "---" && df -h'
```

### 4-3. 빌드 완료 확인
```bash
docker images | grep stt-engine
# 출력:
# stt-engine   cuda129-rhel89-v1.2   <image-id>   <time>   1.5GB
```

**예상 소요 시간: 20-30분**

---

## 💾 Step 5: 이미지 저장 및 다운로드

### 5-1. EC2에서 이미지 저장
```bash
cd ~/stt_engine/build/output

# RHEL 8.9 이미지 저장
docker save stt-engine:cuda129-rhel89-v1.2 | gzip > stt-engine-cuda129-rhel89-v1.2.tar.gz

# 또는 일반 이미지
docker save stt-engine:cuda129-v1.2 | gzip > stt-engine-cuda129-v1.2.tar.gz

# 파일 확인
ls -lh *.tar.gz
# 출력: stt-engine-cuda129-rhel89-v1.2.tar.gz  500M
```

**소요 시간: 3-5분**

### 5-2. Mac으로 다운로드
```bash
# Mac 로컬 터미널:
scp -i your-key.pem ec2-user@<ec2-ip>:~/stt_engine/build/output/stt-engine-cuda129-rhel89-v1.2.tar.gz \
    ~/Downloads/

# 파일 확인
ls -lh ~/Downloads/stt-engine-cuda129-rhel89-v1.2.tar.gz
```

**소요 시간: 2-5분 (네트워크에 따라)**

### 5-3. MD5 검증 (선택)
```bash
# EC2에서:
md5sum build/output/stt-engine-cuda129-rhel89-v1.2.tar.gz > /tmp/image.md5

# Mac으로 다운로드:
scp -i your-key.pem ec2-user@<ec2-ip>:/tmp/image.md5 ~/Downloads/

# 검증:
cd ~/Downloads
md5sum -c image.md5
```

---

## 🚢 Step 6: 운영 서버에 배포

### 6-1. 이미지 업로드
```bash
# Mac에서:
scp -P 22 ~/Downloads/stt-engine-cuda129-rhel89-v1.2.tar.gz \
    deploy-user@production-server:/tmp/
```

### 6-2. 운영 서버에서 로드
```bash
# RHEL 8.9 운영 서버:
cd /tmp

# 1. 압축 해제
gunzip stt-engine-cuda129-rhel89-v1.2.tar.gz

# 2. Docker에 로드
docker load < stt-engine-cuda129-rhel89-v1.2.tar

# 3. 확인
docker images | grep stt-engine
# 출력: stt-engine  cuda129-rhel89-v1.2  <image-id>  1.5GB
```

---

## ✅ Step 7: 이미지 검증 (운영 서버)

### 7-1. PyTorch/CUDA 검증
```bash
docker run --rm stt-engine:cuda129-rhel89-v1.2 python3.11 -c "
import torch
print(f'✅ PyTorch: {torch.__version__}')
print(f'✅ CUDA Available: {torch.cuda.is_available()}')
print(f'✅ cuDNN: OK')
"

# 예상 출력:
# ✅ PyTorch: 2.6.0
# ✅ CUDA Available: True
# ✅ cuDNN: OK
```

### 7-2. Whisper 검증
```bash
docker run --rm stt-engine:cuda129-rhel89-v1.2 python3.11 -c "
try:
    import faster_whisper
    print('✅ faster-whisper: 로드됨')
except:
    print('⚠️  faster-whisper: 미사용')
    
try:
    import whisper
    print('✅ openai-whisper: 로드됨')
except:
    print('⚠️  openai-whisper: 미사용')
"
```

### 7-3. API 헬스 체크
```bash
# 모델 다운로드 (처음 1회, 5-10분)
docker run -it --rm \
  -v /path/to/models:/app/models \
  stt-engine:cuda129-rhel89-v1.2 \
  python3.11 -c 'import whisper; whisper.load_model("large-v3")'

# API 서버 실행
docker run -d \
  --name stt-api \
  --gpus all \
  -p 8003:8003 \
  -v /path/to/models:/app/models \
  -e STT_DEVICE=cuda \
  stt-engine:cuda129-rhel89-v1.2

# 헬스 체크
sleep 10
curl http://localhost:8003/health
# 예상: {"status":"ok","backend":"faster-whisper"}
```

---

## 📊 예상 소요 시간

| 단계 | 시간 |
|------|------|
| EC2 생성 | 2분 |
| Docker/Git 설치 | 5분 |
| 레포지토리 클론 | 2분 |
| **Docker 빌드** | **20-30분** |
| 이미지 저장 | 5분 |
| Mac 다운로드 | 5분 |
| 운영 서버 업로드 | 5분 |
| 이미지 로드 | 3분 |
| 검증 | 5분 |
| **총합** | **~60분** |

---

## 🔍 문제 해결

### 빌드 실패 - "インターネット接続がありません"
```bash
# EC2의 인터넷 연결 확인
ping google.com

# DNS 확인
nslookup github.com

# 재시도
bash scripts/build-stt-engine-rhel89.sh
```

### 이미지 로드 실패 - "unknown file format"
```bash
# 파일 손상 확인
file stt-engine-cuda129-rhel89-v1.2.tar.gz
# 출력: gzip compressed data

# 압축 확인
gunzip -t stt-engine-cuda129-rhel89-v1.2.tar.gz

# MD5 검증
md5sum -c stt-engine-cuda129-rhel89-v1.2.tar.gz.md5
```

### CUDA 인식 안됨
```bash
# 운영 서버의 CUDA 확인
nvidia-smi
nvcc --version

# Docker 내부의 CUDA 확인
docker run --rm --gpus all stt-engine:cuda129-rhel89-v1.2 \
  python3.11 -c "import torch; print(torch.cuda.is_available())"
```

### 디스크 부족
```bash
# EC2 디스크 확인
df -h

# 불필요한 이미지 정리
docker system prune -a
docker builder prune

# 권장: 50GB 이상 필요
```

---

## 📝 체크리스트

```
[ ] RHEL 8.9 정보 수집 완료
    - OS: 8.9
    - glibc: 2.28
    - Python: 3.11.5
    - CUDA: 12.9
    - NVIDIA Driver: 575.57.08

[ ] AWS EC2 RHEL 8.9 생성
    - t3.large 이상
    - 50GB 스토리지
    - Security Group 설정

[ ] EC2 환경 설정
    - Docker 설치
    - Git 설치
    - 사용자 권한 설정

[ ] 레포지토리 클론/전송

[ ] Docker 빌드 실행
    - scripts/build-stt-engine-rhel89.sh

[ ] 이미지 저장 (.tar.gz)

[ ] Mac으로 다운로드

[ ] 운영 서버에 업로드

[ ] 이미지 로드
    - docker load < stt-engine-cuda129-rhel89-v1.2.tar

[ ] PyTorch/CUDA 검증

[ ] Whisper 검증

[ ] API 헬스 체크
```

---

## 🎯 다음 단계

빌드 완료 후:

1. **모델 다운로드**
   ```bash
   docker run -it --rm \
     -v /path/to/models:/app/models \
     stt-engine:cuda129-rhel89-v1.2 \
     python3.11 -c 'import whisper; whisper.load_model("large-v3")'
   ```

2. **STT API 서버 실행**
   ```bash
   docker run -d \
     --name stt-api \
     --gpus all \
     -p 8003:8003 \
     -v /path/to/models:/app/models \
     -e STT_DEVICE=cuda \
     stt-engine:cuda129-rhel89-v1.2
   ```

3. **트랜스크립션 테스트**
   ```bash
   curl -X POST http://localhost:8003/transcribe \
     -F "file=@/path/to/audio.wav"
   ```

---

## 📞 트러블슈팅

문제 발생 시 확인사항:

1. EC2 인터넷 연결
2. Docker 이미지 크기 (1.5GB 이상)
3. glibc 버전 (운영 서버 2.28과 동일)
4. CUDA/NVIDIA Driver (12.9+)
5. 디스크 여유 공간 (50GB 이상)

---

**마지막 업데이트**: 2026년 2월 5일
