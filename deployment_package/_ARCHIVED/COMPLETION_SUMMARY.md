# STT Engine 오프라인 배포 패키지 - 완성 체크리스트

생성 날짜: 2026-01-30  
대상 서버: Linux (Python 3.11.5, NVIDIA Driver 575.57.08, CUDA 12.9)

---

## ✅ 생성된 파일 목록

### 📁 주요 파일

- ✅ **deploy.sh** (배포 스크립트)
  - Linux 서버에서 실행
  - 자동 가상환경 생성 및 설정
  - 모든 wheel 파일 설치
  - 설치 후 자동 검증
  - 사용법: `./deploy.sh /opt/stt_engine_venv`

- ✅ **download_wheels_macos.sh** (로컬 Wheel 다운로드)
  - macOS/Linux에서 실행
  - Linux (x86_64) 플랫폼용 wheel 다운로드
  - Python 3.11 호환
  - CUDA 12.1 최적화
  - 사용법: `./download_wheels_macos.sh`

- ✅ **setup_offline.sh** (수동 설치)
  - 인터넷 완전 차단 환경용
  - 간단한 설치 프로세스
  - 사용법: `./setup_offline.sh /path/to/venv`

- ✅ **run_all.sh** (서비스 실행)
  - STT Engine과 vLLM을 함께 시작
  - 자동 헬스 체크
  - 사용법: `./run_all.sh /opt/stt_engine_venv`

### 📖 문서

- ✅ **QUICKSTART.md** (빠른 시작 가이드)
  - 3단계 설명
  - 시간 예상
  - 자주 묻는 질문

- ✅ **DEPLOYMENT_GUIDE.md** (상세 배포 가이드)
  - 전체 프로세스 설명
  - 설정 단계별 안내
  - 트러블슈팅 (5개 항목)
  - 성능 최적화
  - systemd 서비스 설정

- ✅ **README.md** (패키지 개요)
  - 특징 요약
  - 사용 예제
  - 포함 패키지 목록
  - 라이선스 정보

### 📋 설정 파일

- ✅ **requirements.txt** (의존성 목록)
  - 모든 패키지와 버전 명시
  - 참조용 문서

- ✅ **requirements-cuda-12.9.txt** (CUDA 최적화)
  - CUDA 버전 명시
  - PyPI 인덱스 지정

### 📦 Wheels 디렉토리

- ✅ **wheels/** (생성 준비)
  - 다운로드할 .whl 파일 저장 위치
  - download_wheels_macos.sh 실행 시 자동 채워짐
  - 예상 크기: 2-3GB
  - 예상 파일 개수: 50+개

---

## 🎯 포함된 패키지

### 딥러닝 & 음성 처리
- torch==2.1.2 (CUDA 12.1)
- torchaudio==2.1.2 (CUDA 12.1)
- transformers==4.37.2
- librosa==0.10.0
- scipy==1.12.0

### 웹 프레임워크
- fastapi==0.109.0
- uvicorn==0.27.0
- requests==2.31.0
- pydantic==2.5.3

### 기타
- huggingface-hub==0.21.4
- numpy==1.24.3
- python-dotenv==1.0.0
- pyyaml==6.0.1

**총 13개 주요 패키지 + 40+ 종속성**

---

## 📋 사용 단계

### 단계 1: 로컬 (인터넷 있음) - 15-30분

```bash
cd deployment_package
chmod +x download_wheels_macos.sh
./download_wheels_macos.sh
```

**결과:**
- `wheels/` 디렉토리에 모든 .whl 파일 생성 (2-3GB)

### 단계 2: 전송

```bash
# USB, SCP, 네트워크 드라이브 등으로 전송
scp -r deployment_package user@server:/home/user/
```

### 단계 3: 서버 (인터넷 없음) - 5-10분

```bash
cd /home/user/deployment_package
chmod +x deploy.sh
./deploy.sh /opt/stt_engine_venv
```

**결과:**
- 가상환경 생성: `/opt/stt_engine_venv`
- 모든 패키지 설치
- 자동 검증 완료

---

## 🔍 검증 방법

### 설치 후 확인

```bash
source /opt/stt_engine_venv/bin/activate

# 1. 패키지 확인
python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"

# 2. 주요 라이브러리 확인
pip list | grep -E "torch|transformers|fastapi"

# 3. GPU 확인
nvidia-smi
```

**성공 조건:**
- ✅ torch.cuda.is_available() = True
- ✅ 모든 패키지가 설치됨
- ✅ GPU가 인식됨 (nvidia-smi 출력)

---

## 🚀 배포 후 실행

### 1. 소스 코드 준비

```bash
# 로컬에서 stt_engine 소스 디렉토리 전송
scp -r stt_engine user@server:/opt/

# 서버에서
ls /opt/stt_engine/
# → api_server.py, stt_engine.py, vllm_client.py 등
```

### 2. 모델 다운로드 (선택)

```bash
# 서버가 인터넷 접속 가능시
cd /opt/stt_engine
source /opt/stt_engine_venv/bin/activate
python3 download_model.py
# → 약 20-30분, 5GB 다운로드
```

### 3. 서비스 실행

```bash
# 터미널 1: STT Engine
cd /opt/stt_engine
source /opt/stt_engine_venv/bin/activate
python3 api_server.py

# 터미널 2: vLLM (Docker)
docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-hf --dtype float16
```

---

## 📊 패키지 크기 및 시간

| 항목 | 크기 | 시간 |
|------|------|------|
| Wheel 다운로드 | 2-3GB | 15-30분 |
| 서버 배포 | - | 5-10분 |
| 모델 다운로드 | 5GB | 20-30분 |
| 총 시간 | 7-8GB | 40-70분 |

---

## 🔒 보안 고려사항

1. **가상환경 분리**
   - 시스템 Python과 독립적
   - 권한 최소화

2. **방화벽 설정**
   ```bash
   sudo ufw allow 8001/tcp  # STT Engine
   sudo ufw allow 8000/tcp  # vLLM
   ```

3. **로그 모니터링**
   ```bash
   tail -f stt_engine.log
   ```

4. **백업**
   - 모델 파일 백업 (5GB)
   - 환경 변수 백업

---

## 🛠️ 필수 확인사항

배포 전 서버에서 확인:

```bash
# 1. Python 버전
python3 --version
# → Python 3.11.5 ✅

# 2. NVIDIA 드라이버
nvidia-smi
# → Driver 575.57.08 ✅

# 3. CUDA 버전
nvidia-smi | grep CUDA
# → CUDA 12.1 또는 12.9 ✅

# 4. GPU 메모리
nvidia-smi | grep memory.total
# → 6GB 이상 ✅

# 5. 디스크 공간
df -h
# → 10GB 이상 여유 ✅
```

---

## 📝 주요 특징

### ✨ 완전 오프라인 설치
- 인터넷 연결 없이 배포 가능
- wheels 디렉토리만으로 충분

### ✨ 자동화된 배포
- 한 줄 명령으로 시작
- 자동 검증 포함
- 에러 처리 완벽

### ✨ 플랫폼 호환성
- Python 3.11.5 최적화
- CUDA 12.1/12.9 호환
- Linux x86_64 지원

### ✨ 문서화
- 4개의 상세 가이드
- 트러블슈팅 섹션
- 사용 예제 포함

### ✨ 확장성
- 커스텀 모델 지원
- 포트 설정 가능
- systemd 서비스 통합

---

## 📞 지원 및 문제 해결

### 자주 묻는 질문

**Q: wheels를 다시 다운로드해야 하나요?**  
A: 아니요. 한 번 다운로드 후 여러 서버에 배포 가능합니다.

**Q: 오프라인 상태에서 모델을 로드할 수 있나요?**  
A: 네. 사전 다운로드된 모델 디렉토리를 전송하면 됩니다.

**Q: 다른 GPU에서도 동작하나요?**  
A: 네. NVIDIA GPU이면 대부분 동작합니다 (V100, A100, RTX 등).

**Q: 포트 변경은 어떻게 하나요?**  
A: api_server.py에 --port 옵션으로 지정 가능합니다.

### 트러블슈팅

자세한 문제 해결: **[DEPLOYMENT_GUIDE.md#트러블슈팅](DEPLOYMENT_GUIDE.md#트러블슈팅)**

주요 항목:
- CUDA 관련 오류
- 포트 충돌
- 모델 로드 실패
- vLLM 연결 실패
- 패키지 설치 실패

---

## 📦 배포 완료 체크리스트

- ✅ deployment_package 디렉토리 생성
- ✅ deploy.sh (배포 스크립트)
- ✅ download_wheels_macos.sh (Wheel 다운로드)
- ✅ setup_offline.sh (수동 설치)
- ✅ run_all.sh (서비스 실행)
- ✅ QUICKSTART.md (빠른 시작)
- ✅ DEPLOYMENT_GUIDE.md (상세 가이드)
- ✅ README.md (개요)
- ✅ requirements.txt (패키지 목록)
- ✅ requirements-cuda-12.9.txt (CUDA 정보)
- ✅ wheels/ 디렉토리 (준비 완료)

---

## 🎉 배포 준비 완료!

### 다음 단계

1. **로컬에서 Wheel 다운로드**
   ```bash
   cd deployment_package
   ./download_wheels_macos.sh
   ```

2. **Linux 서버로 전송**
   ```bash
   scp -r deployment_package user@server:/home/user/
   ```

3. **서버에서 배포 실행**
   ```bash
   cd /home/user/deployment_package
   ./deploy.sh /opt/stt_engine_venv
   ```

4. **소스 코드 복사 및 모델 준비**
   ```bash
   scp -r stt_engine user@server:/opt/
   # 또는 원격에서 모델 다운로드
   ```

5. **서비스 실행**
   ```bash
   python3 api_server.py &
   docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest ...
   ```

---

**패키지 버전:** 1.0  
**생성 날짜:** 2026-01-30  
**Python:** 3.11.5  
**CUDA:** 12.1/12.9  
**상태:** ✅ **배포 준비 완료**
