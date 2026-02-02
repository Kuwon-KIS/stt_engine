# 📋 빠른 참조 가이드 (Quick Reference)

## 현재 배포 상태

```
✅ 완료됨          52개 wheel 파일 + 모든 의존성
✅ 압축 준비됨     wheels-all.tar.gz (212MB)
✅ 설치 가이드     3개 문서 준비 완료
⏳ 대기 중         PyTorch 2.4.1 또는 2.1.2 다운로드 (다른 환경에서)
```

---

## 📂 주요 파일 위치

| 파일/디렉토리 | 용도 | 위치 |
|------------|------|------|
| wheels/ | Wheel 파일 저장 | deployment_package/wheels/ |
| wheels-all.tar.gz | 압축 배포 파일 | deployment_package/wheels/ |
| DEPLOYMENT_STATUS.md | 최신 배포 상태 | deployment_package/ |
| INSTALL_GUIDE.md | 상세 설치 가이드 | deployment_package/ |
| QUICK_REFERENCE.md | 이 파일 | deployment_package/ |
| download-wheels.sh | wheels 다운로드 스크립트 | deployment_package/ |

---

## 🔄 다음 단계

### 1️⃣ PyTorch 다운로드 (인터넷 가능한 환경)

```bash
cd deployment_package/wheels

# 최신 권장 버전
python3.11 -m pip download torch==2.4.1 torchaudio==2.4.1 \
    --only-binary=:all: --platform manylinux_2_17_x86_64 \
    --python-version 311 --index-url https://download.pytorch.org/whl/cu124 -d .

# 또는 CUDA 12.1 버전
python3.11 -m pip download torch==2.1.2 torchaudio==2.1.2 \
    --only-binary=:all: --platform manylinux_2_17_x86_64 \
    --python-version 311 --index-url https://download.pytorch.org/whl/cu121 -d .
```

### 2️⃣ 전체 wheels 재압축

```bash
cd deployment_package/wheels
rm wheels-all.tar.gz
tar -czf wheels-all.tar.gz *.whl
```

### 3️⃣ RHEL 서버로 전송

```bash
# 방법 1: 전체 디렉토리 전송
scp -r deployment_package/ user@rhel-server:/opt/stt/

# 방법 2: tar 압축 후 전송 (더 빠름)
tar -czf stt_deployment.tar.gz deployment_package/
scp stt_deployment.tar.gz user@rhel-server:/opt/
```

### 4️⃣ RHEL 서버에서 설치

```bash
# 압축 해제
cd /opt/stt/deployment_package/wheels
tar -xzf wheels-all.tar.gz

# 오프라인 설치
python3.11 -m pip install --no-index --find-links=. *.whl
```

---

## 📦 현재 포함된 패키지 (52개)

- faster-whisper 1.0.3 (STT 엔진)
- librosa 0.10.0 (오디오 처리)
- numpy, scipy, scikit-learn
- fastapi 0.109.0 + uvicorn (REST API)
- pydantic 2.5.3 (데이터 검증)
- huggingface-hub, requests, pyyaml
- ctranslate2, onnxruntime (추론 최적화)
- 그 외 27개 의존성

**추가될 예정**: PyTorch 2.4.1 또는 2.1.2 + torchaudio

---

## ✅ 배포 체크리스트

- [x] faster-whisper 모든 의존성 준비
- [x] 압축 파일 생성 (wheels-all.tar.gz)
- [x] 설치 가이드 작성
- [ ] PyTorch 다운로드
- [ ] RHEL 서버 전송
- [ ] 서버에서 설치
- [ ] 설치 검증

---

## 🎯 최종 배포 구조

```
/opt/stt/ (RHEL 서버)
├── deployment_package/
│   ├── wheels/
│   │   ├── *.whl (52개 + PyTorch 포함)
│   │   └── wheels-all.tar.gz 또는 wheels-part*.tar.gz
│   ├── INSTALL_GUIDE.md
│   ├── requirements.txt
│   └── [API 설정 파일들]
│
└── stt_engine/ (메인 애플리케이션)
    ├── api_server.py
    ├── stt_engine.py
    ├── models/ (Whisper 모델)
    └── [기타 애플리케이션 파일]
```

---

더 자세한 정보는 `DEPLOYMENT_STATUS.md` 참고
