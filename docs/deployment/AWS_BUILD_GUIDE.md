# AWS EC2에서 STT Engine Docker 이미지 빌드 가이드

## 목표
AWS EC2 (Linux x86_64) 인스턴스에서 STT Engine Docker 이미지를 빌드하고, 로컬로 다운로드 받기

---

## 📋 사전 준비

### EC2 인스턴스 요구사항
- **OS**: RHEL 8.9 AMI (🔴 **권장** - 100% 호환성) 또는 Ubuntu 22.04 LTS
- **인스턴스 타입**: `t3.large` 이상 (최소 4GB RAM)
- **스토리지**: 50GB 이상 (Docker 빌드용)
- **네트워크**: 인터넷 접속 가능 (pip 패키지 다운로드)

#### 🔴 RHEL 8.9 EC2 선택 이유
- 타겟 서버가 RHEL 8.9 (glibc 2.28)
- EC2도 RHEL 8.9이면 **호환성 100%**
- glibc 불일치 문제 없음
- ✅ **가장 안전한 선택**

### Security Group 설정
- 포트 8003 (STT API) - 선택사항
- SSH 포트 22 - 필수

---

## 🚀 빌드 프로세스

### Step 1: EC2에 연결
```bash
ssh -i your-key.pem ec2-user@<ec2-instance-ip>
# 또는
ssh -i your-key.pem ubuntu@<ec2-instance-ip>
```

### Step 2: 필수 도구 설치
```bash
# RHEL 8.9에서:
sudo yum update -y
sudo yum groupinstall -y "Development Tools"
sudo yum install -y docker

# 또는 Ubuntu에서:
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y docker.io

# Docker 권한 설정
sudo usermod -aG docker $USER
newgrp docker

# Git 설치
# RHEL:
sudo yum install -y git
# Ubuntu:
sudo apt-get install -y git

# Docker 확인
docker --version
```

### Step 3: 레포지토리 클론
```bash
cd /home/$USER
git clone https://github.com/Kuwon-KIS/stt_engine.git
cd stt_engine
```

**또는** scp로 파일 전송:
```bash
# 로컬 Mac에서:
scp -i your-key.pem -r /Users/a113211/workspace/stt_engine ubuntu@<ec2-ip>:/home/ubuntu/stt_engine
```

### Step 4: 빌드 실행
```bash
cd ~/stt_engine

# RHEL 8.9 호환 빌드 (권장 🔴)
bash scripts/build-stt-engine-rhel89.sh

# 또는 일반 Ubuntu 빌드:
bash scripts/build-stt-engine-ec2.sh

# 또는 수동 빌드 (RHEL 8.9):
docker build \
  --platform linux/amd64 \
  -t stt-engine:cuda129-rhel89-v1.2 \
  -f docker/Dockerfile.engine.rhel89 \
  .
```

### Step 5: 이미지 저장
```bash
# RHEL 8.9 빌드의 경우:
docker save stt-engine:cuda129-rhel89-v1.2 | gzip > stt-engine-cuda129-rhel89-v1.2.tar.gz

# 또는 일반 빌드:
docker save stt-engine:cuda129-v1.2 | gzip > stt-engine-cuda129-v1.2.tar.gz

# 파일 크기 확인
ls -lh stt-engine-cuda129-*.tar.gz

# 예상 크기: 500MB ~ 1GB (압축)
```

### Step 6: 로컬로 다운로드
```bash
# 로컬 Mac 터미널에서:
scp -i your-key.pem ubuntu@<ec2-ip>:/home/ubuntu/stt_engine/stt-engine-cuda129-v1.2.tar.gz \
    ~/Downloads/

# 압축 해제 (선택)
cd ~/Downloads
tar -xzf stt-engine-cuda129-v1.2.tar.gz
```

### Step 7: Linux 운영 서버에 업로드
```bash
# 로컬에서 운영 서버로 전송
scp -P 22 ~/Downloads/stt-engine-cuda129-v1.2.tar.gz \
    deploy-user@production-server:/tmp/

# 또는 AWS S3를 거쳐 전송 (선택)
aws s3 cp stt-engine-cuda129-v1.2.tar.gz \
    s3://your-bucket/stt-engine/
```

### Step 8: 운영 서버에서 로드
```bash
# 운영 서버에서:
cd /tmp
gunzip stt-engine-cuda129-v1.2.tar.gz
docker load < stt-engine-cuda129-v1.2.tar

# 확인
docker images | grep stt-engine
```

---

## 🔧 문제 해결

### 빌드 실패 - "cuDNN 라이브러리 설치 안됨"
**원인**: EC2 인스턴스가 오프라인 상태
**해결**: EC2가 인터넷 접속 가능한지 확인
```bash
ping google.com
ping files.pythonhosted.org
```

### 이미지 로드 실패 - "unknown file format"
**원인**: tar 파일이 손상됨
**해결**: 다시 다운로드하고 md5sum 검증
```bash
# EC2에서:
md5sum stt-engine-cuda129-v1.2.tar.gz > image.md5

# Mac에서 다운로드 후:
md5sum -c image.md5
```

### 디스크 부족
**해결**: 불필요한 Docker 이미지 정리
```bash
docker system prune -a
docker builder prune
```

---

## 📊 예상 소요 시간

| 단계 | 예상 시간 |
|------|---------|
| Docker 설치 | 5분 |
| 레포지토리 클론 | 2분 |
| Docker 이미지 빌드 | 15-30분 |
| 이미지 저장 (압축) | 3-5분 |
| 로컬 다운로드 | 2-5분 |
| **총합** | **~35-50분** |

---

## 📝 주의사항

1. **EC2 비용**: t3.large × 1시간 ≈ $0.10 ~ $0.15 (지역별 상이)
2. **네트워크 비용**: 데이터 전송량 (1GB 다운로드/업로드)
3. **보안**: SSH 키 파일 안전하게 보관
4. **저장소**: EC2 또는 S3에 이미지 백업 권장

---

## 🎯 최종 검증 (운영 서버)

```bash
# 이미지 로드 후:
docker run --rm stt-engine:cuda129-v1.2 python3.11 -c "
import torch
print(f'✅ PyTorch: {torch.__version__}')
print(f'✅ CUDA: {torch.cuda.is_available()}')
import whisper
print('✅ Whisper loaded')
"
```

---

## 📚 관련 파일

- 빌드 스크립트: `scripts/build-stt-engine-ec2.sh`
- Dockerfile: `docker/Dockerfile.engine.cuda`
- API 서버: `api_server.py`
- STT 엔진: `stt_engine.py`
