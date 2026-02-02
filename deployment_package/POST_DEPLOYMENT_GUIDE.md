# 🚀 STT Engine - Linux 서버 배포 후 설정 가이드

## 📋 배포 후 체크리스트

### Phase 1️⃣: 서버 준비 (5분)
```bash
# 1. 파일 전송 확인
ls -lh /tmp/stt_engine_deployment_slim.tar.gz

# 2. 압축 해제
cd /tmp
tar -xzf stt_engine_deployment_slim.tar.gz
cd stt_engine

# 3. 현재 디렉토리 확인
pwd
ls -la
```

### Phase 2️⃣: Python 환경 설정 (5분)

**RHEL 8.9에서:**
```bash
# 1. Python 3.11 설치 확인
python3.11 --version
# 출력: Python 3.11.5

# 2. Python 개발 패키지 설치 (필요시)
sudo yum install -y python3.11-devel

# 3. venv 생성
python3.11 -m venv venv

# 4. 가상환경 활성화
source venv/bin/activate

# 5. pip 업그레이드
pip install --upgrade pip setuptools wheel
```

### Phase 3️⃣: wheels 설치 (10-15분)

```bash
# 1. deployment_package 이동
cd deployment_package

# 2. 모든 wheels 설치
pip install wheels/*.whl

# 3. 설치 확인
pip list | grep -E "(torch|transformers|librosa)"

# 4. CUDA 지원 확인
python3 -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"

# 예상 출력:
# CUDA Available: True
# Device: cuda:0 (GPU 이름)

# 5. 프로젝트 디렉토리로 이동
cd ..
```

### Phase 4️⃣: 모델 다운로드 (10-20분, 네트워크 속도에 따라 다름)

**⚠️ 매우 중요: 이 단계는 인터넷 연결이 필요합니다!**

```bash
# 1. 모델 다운로드 스크립트 실행
python3 download_model.py

# 예상 출력:
# 📥 모델 다운로드를 시작합니다: openai/whisper-large-v3-turbo
# 💾 저장 경로: /path/to/stt_engine/models
# 1️⃣  모델 파일 다운로드 중...
# ⬇️  Downloading (진행상황)
# ✅ 모델 파일 다운로드 완료
# 2️⃣  Processor 다운로드 중...
# ✅ Processor 저장 완료
# ✨ 모든 다운로드가 완료되었습니다!

# 2. 모델 파일 확인
ls -lh models/
# 예상: 약 3-5GB 파일들

# 3. 모델 로드 테스트 (선택사항)
python3 -c "from transformers import pipeline; print('✅ 모델 로드 성공')"
```

### Phase 5️⃣: STT Engine 설치 (2-3분)

```bash
# 1. 프로젝트 패키지 설치
pip install -e .

# 2. 설치 확인
python3 -c "import stt_engine; print('✅ STT Engine 설치 완료')"
```

### Phase 6️⃣: API 서버 실행 및 테스트 (5분)

**옵션 A: 기본 실행**
```bash
# 1. API 서버 시작
python3 api_server.py

# 예상 출력:
# INFO:     Uvicorn running on http://0.0.0.0:8001
# INFO:     Application startup complete

# 2. 다른 터미널에서 테스트 (또는 curl로)
curl -X GET http://localhost:8001/health

# 예상 응답:
# {"status": "ok", "model": "whisper-large-v3-turbo"}
```

**옵션 B: Uvicorn으로 직접 실행 (권장)**
```bash
# 1. 백그라운드에서 실행
nohup uvicorn api_server:app --host 0.0.0.0 --port 8001 > api.log 2>&1 &

# 2. 로그 모니터링
tail -f api.log

# 3. 프로세스 확인
ps aux | grep uvicorn
```

**옵션 C: Systemd Service로 등록 (프로덕션)**
```bash
# 1. service 파일 생성
sudo tee /etc/systemd/system/stt-engine.service > /dev/null << 'EOF'
[Unit]
Description=STT Engine API Server
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/path/to/stt_engine
Environment="PATH=/path/to/stt_engine/venv/bin"
ExecStart=/path/to/stt_engine/venv/bin/python3 api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 2. 서비스 활성화 및 시작
sudo systemctl daemon-reload
sudo systemctl enable stt-engine
sudo systemctl start stt-engine

# 3. 상태 확인
sudo systemctl status stt-engine
```

### Phase 7️⃣: API 기본 테스트

```bash
# 1. 헬스체크
curl http://localhost:8001/health

# 2. 모델 정보 조회
curl http://localhost:8001/info

# 3. 음성 파일 전송 테스트 (audio.wav 필요)
curl -X POST \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.wav" \
  http://localhost:8001/transcribe

# 예상 응답:
# {
#   "text": "인식된 음성 텍스트",
#   "language": "ko",
#   "duration": 5.2
# }
```

---

## 🔧 문제 해결

### Q: ImportError: No module named 'torch'
```bash
# A: wheels 설치 확인
pip list | grep torch
pip install wheels/*.whl --force-reinstall
```

### Q: CUDA 관련 오류
```bash
# A: CUDA 호환성 확인
nvidia-smi
python3 -c "import torch; print(torch.cuda.is_available())"

# CUDA 사용 비활성화 (CPU 모드)
export CUDA_VISIBLE_DEVICES=""
python3 api_server.py
```

### Q: 메모리 부족
```bash
# A: 모델 양자화 설정
export WHISPER_DTYPE=float16
python3 api_server.py

# 또는 더 작은 모델 사용
# download_model.py에서 "whisper-large-v3-turbo" → "whisper-base" 변경
```

### Q: 모델 다운로드 실패
```bash
# A: 수동으로 다운로드 후 저장
mkdir -p models
cd models

# Hugging Face CLI 사용
huggingface-cli download openai/whisper-large-v3-turbo --repo-type model

# 또는 웹에서 직접 다운로드
# https://huggingface.co/openai/whisper-large-v3-turbo
```

---

## ✅ 최종 검증 체크리스트

```bash
# 1. 환경 확인
python3 --version              # 3.11.5
nvidia-smi                     # CUDA 버전 확인

# 2. 패키지 확인
pip list | head -20

# 3. 모델 파일 확인
ls -lh models/                 # 3-5GB 파일 존재

# 4. API 서버 실행
python3 api_server.py          # 포트 8001에서 실행

# 5. API 테스트 (새 터미널)
curl http://localhost:8001/health

# 6. 로그 확인
tail -f logs/api.log           # 에러 확인
```

---

## 📝 배포 후 권장 작업

1. **백업**: 모델 및 설정 파일 백업
2. **모니터링**: API 서버 로그 및 GPU 사용률 모니터링
3. **로드 테스트**: 여러 동시 요청 테스트
4. **성능 튜닝**: GPU 메모리 설정 최적화

---

**배포 완료! 🎉**
문제가 생기면 logs/ 디렉토리의 로그 파일을 확인하세요.
