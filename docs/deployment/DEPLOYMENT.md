# Linux 서버 배포 가이드

## 📋 사전 요구사항

### 필수 패키지
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    docker.io \
    docker-compose \
    nvidia-docker \
    git \
    curl

# RHEL/CentOS
sudo yum install -y \
    docker \
    docker-compose \
    nvidia-docker \
    git \
    curl
```

### NVIDIA GPU 드라이버 설치 (GPU 사용 시)
```bash
# NVIDIA 저장소 추가
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/ubuntu22.04/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# NVIDIA Container Toolkit 설치
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 현재 사용자를 Docker 그룹에 추가
```bash
sudo usermod -aG docker $USER
newgrp docker
```

## 🚀 배포 과정

### 1. 저장소 클론
```bash
cd /opt
sudo git clone https://github.com/Kuwon-KIS/stt_engine.git
cd stt_engine
sudo chown -R $USER:$USER .
```

### 2. 환경 변수 설정
```bash
cp .env.example .env
# nano .env  또는 vi .env로 필요한 설정 수정
```

### 3. Docker 이미지 빌드
```bash
docker build -t stt-engine:latest .
```

또는 모델을 미리 포함하여 빌드:
```bash
docker build -t stt-engine:with-model -f Dockerfile.full .
```

### 4. vLLM 서버 시작 (선택사항)
```bash
# GPU를 사용하는 경우
docker run -d \
    --name vllm-server \
    --gpus all \
    -p 8000:8000 \
    -v vllm-cache:/root/.cache \
    vllm/vllm-openai:latest \
    vllm serve meta-llama/Llama-2-7b-hf --host 0.0.0.0 --port 8000

# CPU만 사용하는 경우
docker run -d \
    --name vllm-server \
    -p 8000:8000 \
    vllm/vllm-openai:latest \
    vllm serve meta-llama/Llama-2-7b-hf --host 0.0.0.0 --port 8000
```

### 5. STT 엔진 컨테이너 시작
```bash
# GPU 사용
docker run -d \
    --name stt-engine \
    --gpus all \
    -p 8001:8001 \
    -v $(pwd)/models:/app/models \
    -v $(pwd)/audio:/app/audio \
    -v $(pwd)/logs:/app/logs \
    -e WHISPER_DEVICE=cuda \
    -e VLLM_API_URL=http://vllm-server:8000 \
    --link vllm-server \
    stt-engine:latest

# CPU 사용
docker run -d \
    --name stt-engine \
    -p 8001:8001 \
    -v $(pwd)/models:/app/models \
    -v $(pwd)/audio:/app/audio \
    -v $(pwd)/logs:/app/logs \
    -e WHISPER_DEVICE=cpu \
    -e VLLM_API_URL=http://vllm-server:8000 \
    stt-engine:latest
```

### 6. Docker Compose 사용 (권장)
```bash
# 환경 변수 파일 업데이트
cp .env.example .env
nano .env

# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 중지
docker-compose down

# 서비스 재시작
docker-compose restart
```

## 🔍 서버 상태 확인

### 헬스 체크
```bash
# STT 엔진
curl http://localhost:8001/health

# vLLM 서버 (vLLM을 사용하는 경우)
curl http://localhost:8000/health
```

### 로그 확인
```bash
# 실시간 로그
docker-compose logs -f stt-engine
docker-compose logs -f vllm-server

# 특정 라인 수만 확인
docker-compose logs --tail 100 stt-engine

# 컨테이너별 상태
docker ps
```

### 리소스 사용량
```bash
docker stats
```

## 📡 API 호출 예제

### STT만 사용
```bash
curl -X POST \
    -F "file=@/path/to/audio.wav" \
    http://localhost:8001/transcribe
```

### STT + vLLM 처리
```bash
curl -X POST \
    -F "file=@/path/to/audio.wav" \
    -F "language=ko" \
    -F "instruction=다음 텍스트를 요약해주세요:" \
    http://localhost:8001/transcribe-and-process
```

## 🔄 자동 재시작 설정

### Systemd 서비스 파일 생성
```bash
sudo tee /etc/systemd/system/stt-engine.service > /dev/null << EOF
[Unit]
Description=STT Engine Service
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/stt_engine
Restart=always
RestartSec=10
User=$USER
ExecStart=/usr/bin/docker-compose up
ExecStop=/usr/bin/docker-compose down

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable stt-engine
sudo systemctl start stt-engine
```

### 서비스 관리
```bash
# 상태 확인
sudo systemctl status stt-engine

# 서비스 시작
sudo systemctl start stt-engine

# 서비스 중지
sudo systemctl stop stt-engine

# 서비스 재시작
sudo systemctl restart stt-engine

# 로그 확인
sudo journalctl -u stt-engine -f
```

## 🛡️ 방화벽 설정

### UFW (Ubuntu)
```bash
# STT 엔진 포트 개방
sudo ufw allow 8001/tcp

# vLLM 포트 개방 (필요한 경우)
sudo ufw allow 8000/tcp

# 방화벽 활성화
sudo ufw enable
```

### firewalld (CentOS/RHEL)
```bash
# STT 엔진 포트 개방
sudo firewall-cmd --permanent --add-port=8001/tcp

# vLLM 포트 개방 (필요한 경우)
sudo firewall-cmd --permanent --add-port=8000/tcp

# 설정 적용
sudo firewall-cmd --reload
```

## 🚨 문제 해결

### 모델 다운로드 실패
```bash
# 컨테이너 내에서 모델 다운로드
docker-compose exec stt-engine python download_model.py

# Hugging Face 토큰 설정 (필요한 경우)
export HUGGINGFACE_HUB_TOKEN=your_token_here
docker-compose exec stt-engine python download_model.py
```

### 메모리 부족
```bash
# Swap 추가 (Linux)
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### GPU 인식 안 됨
```bash
# GPU 상태 확인
nvidia-smi

# Docker에서 GPU 인식 확인
docker run --gpus all nvidia/cuda:11.0-runtime nvidia-smi
```

## 📊 성능 최적화

### Docker 리소스 제한
```yaml
services:
  stt-engine:
    # ... 다른 설정 ...
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## 📝 백업 및 복구

### 모델 백업
```bash
# 백업
tar -czf stt-engine-models.tar.gz models/

# 복구
tar -xzf stt-engine-models.tar.gz
```

### 전체 백업
```bash
# 백업
docker-compose down
tar -czf stt-engine-backup.tar.gz .

# 복구
tar -xzf stt-engine-backup.tar.gz
docker-compose up -d
```

## 🔐 보안 권장사항

1. **방화벽**: 필요한 포트만 개방
2. **역프록시**: Nginx/Apache를 통한 HTTPS 구성
3. **인증**: API 엔드포인트에 인증 추가
4. **리소스 제한**: 컨테이너 리소스 제한 설정
5. **로그 모니터링**: 정기적인 로그 확인 및 분석

## 📞 추가 지원

문제 해결이 필요하시면:
1. 로그 확인: `docker-compose logs -f`
2. 이슈 생성: GitHub Issues
3. 커뮤니티 포럼에 질문
