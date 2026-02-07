# 📚 모델 다운로드 및 배포 가이드

## 빠른 시작 (4단계)

모델을 깨끗하게 다운로드하고 오프라인 서버로 배포하는 전체 과정입니다.

### 현재 상황
- ✅ models/ 디렉토리 정리 완료 (기존 파일 제거됨)
- ✅ 모델 다운로드 완료 (huggingface-hub 사용)
- ✅ 모델 압축 완료
- ⏳ 서버로 전송 대기

---

## 단계별 실행

### ✅ 1단계: 모델 다운로드 (완료)

```bash
conda activate stt-py311
python download_model_hf.py
```

**소요 시간**: 약 5-10분 (인터넷 속도에 따라 다름)

**다운로드되는 파일**:
- `config.json` - 모델 설정
- `model.safetensors` - 모델 가중치 (~1.5GB)
- `generation_config.json` - 생성 설정
- `preprocessor_config.json` - 전처리 설정
- `tokenizer.json` - 토크나이저 (~2.6MB)
- `vocab.json`, `merges.txt` - 어휘 데이터

**완료 상태**:
```
✅ 모델 다운로드 완료!
📏 전체 크기: 1.5GB
📊 파일 수: 12개
```

---

### ✅ 2단계: 모델 압축 (완료)

다운로드된 모델을 tar.gz로 압축하여 서버 전송을 빠르게 합니다.

```bash
conda activate stt-py311
python scripts/analysis/compress_model.py
```

**소요 시간**: 약 2-5분

**압축 결과**:
```
✅ 모델 압축 완료!
📊 요약:
  원본 크기: 1.51GB
  압축 파일: 1.39GB
  압축률: 92.0%
  위치: whisper-large-v3-turbo-models.tar.gz
```

**생성 파일**: `whisper-large-v3-turbo-models.tar.gz` (1.4GB)

---

### ✅ 3단계: 서버로 전송 (온라인 필수)

압축된 모델을 Linux 서버로 전송합니다.

```bash
# Mac에서 실행
scp whisper-large-v3-turbo-models.tar.gz ddpapp@dlddpgai1:/data/stt/models/
```

**참고**: 
- 서버 주소와 경로는 상황에 맞게 수정하세요
- SSH 접속이 필요합니다
- 약 5-20분 소요 (네트워크 속도에 따라)

---

### ✅ 4단계: 서버에서 압축 풀기 (오프라인 가능)

Linux 서버에서 압축 파일을 풀고 사용합니다.

```bash
# 서버에서 실행
cd /app/models
tar -xzf whisper-large-v3-turbo-models.tar.gz

# 확인
ls -lh
# 출력:
# config.json
# model.safetensors
# generation_config.json
# preprocessor_config.json
# tokenizer.json
# ...
```

---

## 오프라인 환경에서 사용

서버에서 외부 인터넷 없이 모델을 사용하려면:

### Python 코드 (faster-whisper 사용)

```python
from faster_whisper import WhisperModel

# 로컬 경로 사용
model = WhisperModel(
    "/app/models",  # 압축을 푼 모델 경로
    device="cuda",
    compute_type="int8",
    local_files_only=True  # 🔑 중요: 오프라인 모드
)

# 음성 파일 변환
segments, info = model.transcribe("audio.mp3")
```

### Docker 환경

```bash
# models/ 폴더를 마운트하고 실행
docker run -d \
  --name stt-engine \
  --gpus all \
  -p 8003:8003 \
  -v /app/models:/app/models \
  -e HF_HUB_OFFLINE=1 \
  -e TRANSFORMERS_OFFLINE=1 \
  stt-engine:latest
```

---

## 트러블슈팅

### Q: 모델 다운로드 중 중단되었어요
A: 다시 실행하면 이어서 진행됩니다 (resume_download=True)

### Q: 모델이 로드되지 않아요
A: scripts/models/validate/validate_model.py를 실행해서 문제를 진단하세요

### Q: 서버로 전송이 느려요
A: 압축 파일을 사용하면 원본 크기의 약 50% 크기로 전송됩니다

### Q: 서버에서 오프라인으로 사용할 수 없어요
A: local_files_only=True 파라미터를 확인하세요

---

## 참고 문서

- [MODEL_STRUCTURE.md](docs/architecture/MODEL_STRUCTURE.md) - 모델 구조 설명
- [OFFLINE_ENVIRONMENT.md](docs/deployment/OFFLINE_ENVIRONMENT.md) - 오프라인 배포 가이드
- [stt_engine.py](stt_engine.py) - STT 엔진 코드

---

## 빠른 참조

```bash
# 전체 자동 실행 (대화형)
bash scripts/setup.sh

# 개별 실행
python download_model_hf.py                              # 1단계: 모델 다운로드
python scripts/models/validate/validate_model.py        # 2단계: 검증
python scripts/analysis/compress_model.py               # 3단계: 압축
scp *.tar.gz user@server:/path/                         # 4단계: 전송
# 서버에서: tar -xzf *.tar.gz                           # 5단계: 압축 해제
```

---

**마지막 업데이트**: 2026년 2월 4일
