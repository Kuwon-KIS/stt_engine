# PyTorch CUDA 12.9 설치 - 최종 해결책

## 🚨 현재 상황

- **macOS 네트워크 문제**: PyTorch 공식 CDN 접근 불안정
- **CUDA 버전 문제**: PyTorch에서 cu129는 제공 안 함 (cu121, cu124만 가능)
- **권장 해결**: **Linux 서버에서 직접 온라인 설치**

---

## ✅ 최종 권장: Linux 서버에서 직접 설치

### 단계별 실행 (Linux 서버에서)

```bash
# 1️⃣ 프로젝트 추출
tar -xzf stt_engine_deployment_slim_v2.tar.gz
cd stt_engine

# 2️⃣ 가상환경 활성화
source venv/bin/activate

# 3️⃣ pip 업그레이드
pip install --upgrade pip setuptools wheel

# 4️⃣ 기존 wheels 설치 (PyTorch 제외)
ls deployment_package/wheels/*.whl > /dev/null 2>&1 && \
  pip install deployment_package/wheels/*.whl || echo "⚠️  wheels 없음"

# 5️⃣ PyTorch CUDA 12.9 설치
# 가장 최신 버전 자동 선택 (권장)
pip install torch torchaudio torchvision

# 또는 특정 CUDA 버전 명시:
# CUDA 12.4 (12.9와 호환)
pip install torch torchaudio torchvision \
    --index-url https://download.pytorch.org/whl/cu124

# 또는 CUDA 12.1 (보수적)
pip install torch torchaudio torchvision \
    --index-url https://download.pytorch.org/whl/cu121

# 6️⃣ 설치 검증
python3 << 'EOF'
import torch
import torchaudio
print(f"✅ PyTorch: {torch.__version__}")
print(f"✅ CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"✅ CUDA Device: {torch.cuda.get_device_name()}")
    print(f"✅ CUDA Version: {torch.version.cuda}")
EOF

# 7️⃣ 기타 패키지 및 모델 다운로드
bash deployment_package/post_deploy_setup.sh
```

---

## 🔍 CUDA 버전별 호환성

| 서버 CUDA | PyTorch 버전 | 작동 | 성능 |
|-----------|-------------|------|------|
| **CUDA 12.9** | 최신 (자동) | ✅ | ⭐⭐⭐ |
| CUDA 12.9 | cu124 | ✅ | ⭐⭐⭐ |
| CUDA 12.9 | cu121 | ✅ | ⭐⭐ |
| CUDA 12.9 | cu118 | ✅ | ⭐ |

**권장**: `pip install torch torchaudio` (자동으로 최적 버전 선택)

---

## 📋 예상 설치 시간

- 기존 wheels 설치: 1-2분
- PyTorch 다운로드: 5-10분 (네트워크 속도에 따라)
- 모델 다운로드 (Whisper Large): 15-30분
- **총 예상**: 30-45분

---

## 🎯 현재 상태 정리

### ✅ 이미 준비됨
- 44개 일반 Python 패키지 wheels (139MB)
- deployment_package/ 디렉토리 구조
- post_deploy_setup.sh 자동화 스크립트
- 배포용 tar.gz 파일 (stt_engine_deployment_slim_v2.tar.gz)

### ⏭️ Linux 서버에서 할 일
```bash
1. tar 파일 전송 및 추출
2. venv 활성화
3. pip install torch torchaudio (약 5-10분)
4. 기타 패키지 설치
5. 모델 다운로드
6. API 서버 실행
```

---

## 🚀 실행 명령어 (한 줄로)

```bash
tar -xzf stt_engine_deployment_slim_v2.tar.gz && \
cd stt_engine && \
source venv/bin/activate && \
pip install --upgrade pip && \
pip install torch torchaudio torchvision && \
pip install deployment_package/wheels/*.whl && \
bash deployment_package/post_deploy_setup.sh
```

---

## ❓ FAQ

**Q: PyTorch 12.9가 없는데 괜찮나?**
A: ✅ PyTorch에서 정확히 cu129는 제공 안 하지만, cu124/cu121은 backward compatible이라 CUDA 12.9에서 완벽하게 작동합니다. 최신 PyTorch를 설치하면 자동으로 최적 버전 선택됨.

**Q: cu124 vs cu121 중 뭐가 더 좋나?**
A: cu124 > cu121 > cu118 순으로 좋지만, CUDA 12.9에서는 둘 다 잘 작동합니다. cu124 권장.

**Q: 온라인 설치 안 되면?**
A: 현재 wheels 디렉토리의 44개 패키지는 오프라인 설치 가능. 필요하면:
```bash
pip install deployment_package/wheels/*.whl
# 그 다음 나머지만 온라인 설치
pip install torch torchaudio torchvision
```

---

## 🎁 보너스: 설치 스크립트 생성

Linux 서버에 SCP로 보낼 수 있는 자동 설치 스크립트를 만들고 싶으시면 요청주세요!
