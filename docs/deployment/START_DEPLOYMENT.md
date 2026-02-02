# 🚀 STT Engine 완전 배포 패키지

## 📌 상태: ✅ 배포 준비 완료

---

## 📦 배포 파일 (macOS에서)

### 위치
```
/Users/a113211/workspace/
```

### 선택할 파일
```
✅ stt_engine_deployment_slim_v2.tar.gz (137MB) ← 이것을 사용하세요!

기타:
- stt_engine_deployment_slim.tar.gz (137MB) - 구버전
- stt_engine_deployment.tar.gz (151MB) - venv 포함 (불필요)
```

---

## 🎯 배포 절차 (3단계)

### 1️⃣ Linux 서버로 전송
```bash
scp stt_engine_deployment_slim_v2.tar.gz user@your-server:/tmp/
```

### 2️⃣ 서버에서 압축 해제
```bash
cd /tmp
tar -xzf stt_engine_deployment_slim_v2.tar.gz
cd stt_engine
```

### 3️⃣ 자동 설정 스크립트 실행
```bash
chmod +x deployment_package/post_deploy_setup.sh
bash deployment_package/post_deploy_setup.sh
```

**이것이 다음을 자동으로 수행합니다:**
- ✅ Python 3.11 환경 설정
- ✅ venv 생성 및 활성화
- ✅ wheels 설치 (44개 패키지)
- ✅ 모델 다운로드 (약 10-20분)
- ✅ STT Engine 설치
- ✅ CUDA 호환성 확인
- ✅ API 서버 실행 준비

---

## 📋 포함된 내용

### 🔧 배포 패키지 (deployment_package/)
```
wheels/
  ├── transformers-4.37.2 (모델 로딩)
  ├── librosa-0.10.0 (음성 처리)
  ├── torch-2.2.0 (CUDA 12.1)
  ├── torchaudio-2.2.0
  ├── fastapi-0.109.0 (API 프레임워크)
  ├── scipy, numpy, pydantic 등
  └── ... (44개 전체)

가이드:
  ├── INSTALL_GUIDE.md (기본 설치)
  ├── POST_DEPLOYMENT_GUIDE.md (배포 후 상세)
  ├── post_deploy_setup.sh (자동 설정) ⭐
  └── READY_FOR_DEPLOYMENT.md (빠른 참조)
```

### 💻 소스 코드
```
stt_engine.py .................. STT 엔진 핵심
api_server.py .................. FastAPI 서버
download_model.py .............. 모델 다운로드 ⭐
model_manager.py ............... 모델 관리
api_client.py .................. Python 클라이언트
vllm_client.py ................. vLLM 통합
```

### 📚 문서
```
docs/
  ├── deployment/ ........... 배포 가이드
  ├── architecture/ ......... 아키텍처 설명
  └── ...

docker/ ..................... Dockerfile, docker-compose
scripts/ .................... setup.sh, download-model.sh 등
ARCHIVE/ .................... 과정 기록
```

---

## 🔑 핵심 작업

### 배포 후 즉시 해야 할 일

1. **파일 전송** (2분)
   ```bash
   scp stt_engine_deployment_slim_v2.tar.gz user@server:/tmp/
   ```

2. **압축 해제** (1분)
   ```bash
   tar -xzf stt_engine_deployment_slim_v2.tar.gz
   cd stt_engine
   ```

3. **자동 설정** (30-40분)
   ```bash
   bash deployment_package/post_deploy_setup.sh
   ```
   - 모델 다운로드가 가장 오래 걸림 (10-20분)
   - 네트워크 속도에 따라 다름

4. **API 실행** (1분)
   ```bash
   python3 api_server.py
   ```

5. **테스트** (1분)
   ```bash
   curl http://localhost:8001/health
   ```

---

## 📊 서버 요구사항

| 항목 | 요구사항 | 확인 방법 |
|------|---------|---------|
| **OS** | RHEL 8.9+ | `cat /etc/os-release` |
| **Python** | 3.11.5 | `python3.11 --version` |
| **CUDA** | 12.9 (또는 호환) | `nvidia-smi` |
| **Driver** | 575.57.08+ | `nvidia-smi` 상단 |
| **GPU 메모리** | 12GB+ | `nvidia-smi` |
| **디스크** | 50GB+ | `df -h /` |

---

## ⚡ 빠른 참조

### API 실행 옵션

**포그라운드 (개발/테스트)**
```bash
source venv/bin/activate
python3 api_server.py
```

**백그라운드 (프로덕션)**
```bash
nohup python3 api_server.py > api.log 2>&1 &
```

**Systemd로 등록 (권장)**
```bash
# 자동 설정 스크립트가 service 파일 제공
sudo systemctl start stt-engine
sudo systemctl status stt-engine
```

### 헬스체크
```bash
curl http://localhost:8001/health
# 예상: {"status": "ok", "model": "whisper-large-v3-turbo"}
```

### 음성 인식 테스트
```bash
curl -X POST \
  -F "file=@audio.wav" \
  http://localhost:8001/transcribe
```

---

## 🐛 문제 해결

### 모델 다운로드 실패
```bash
# 수동 다운로드
huggingface-cli download openai/whisper-large-v3-turbo
```

### CUDA 오류
```bash
# CPU 모드로 실행
export CUDA_VISIBLE_DEVICES=""
python3 api_server.py
```

### 메모리 부족
```bash
# Float16 양자화
export WHISPER_DTYPE=float16
python3 api_server.py
```

### 로그 확인
```bash
tail -f logs/api.log
tail -f api.log  # 백그라운드 실행 시
```

---

## 📝 주요 파일

| 파일 | 용도 |
|------|------|
| `post_deploy_setup.sh` | ⭐ 자동 설정 (권장) |
| `download_model.py` | 모델 다운로드 (필수) |
| `api_server.py` | API 서버 |
| `POST_DEPLOYMENT_GUIDE.md` | 상세 설정 가이드 |
| `deployment_package/wheels/*.whl` | 모든 의존성 |

---

## ✅ 최종 체크리스트

```
배포 전 (macOS):
☐ stt_engine_deployment_slim_v2.tar.gz 확인 (137MB)
☐ deployment_package/wheels/*.whl 확인 (44+ 파일)

배포 후 (Linux):
☐ 파일 전송 및 압축 해제
☐ post_deploy_setup.sh 실행
☐ python3 api_server.py로 API 실행
☐ curl http://localhost:8001/health로 테스트
☐ logs/api.log 확인
```

---

## 🎓 다음 단계

배포 후:

1. **모니터링**
   - GPU 메모리 사용률
   - API 응답 속도
   - 에러 로그

2. **성능 튜닝**
   - 배치 크기 조정
   - 양자화 설정
   - 동시 요청 테스트

3. **프로덕션 준비**
   - 로드 밸런싱 설정
   - 백업 전략 수립
   - 모니터링 시스템 연동

---

## 📞 참고 자료

- `deployment_package/POST_DEPLOYMENT_GUIDE.md` - 상세 설정
- `docs/deployment/` - 배포 관련 문서
- `docs/architecture/` - 시스템 아키텍처

---

**🎉 배포 준비가 모두 완료되었습니다!**

이제 Linux 서버로 `stt_engine_deployment_slim_v2.tar.gz`를 전송하고
`post_deploy_setup.sh`를 실행하면 됩니다!

---

**작성일**: 2026-01-30
**대상**: RHEL 8.9, Python 3.11.5, CUDA 12.9
