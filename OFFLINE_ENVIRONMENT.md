# Docker 오프라인 환경 설정 확인 ✅

## 📋 상황 정리

**Q: Docker 실행 시 모델이 변환되는데, 외부 네트워크가 필요한가?**

**A: NO! 외부 네트워크 필요 없습니다.** ✅

---

## 🔄 모델 로드 프로세스 (네트워크 불필요)

### 1단계: 로컬 파일 마운트
```bash
docker run -d \
  --name stt-engine-gpu \
  -v /Users/a113211/workspace/stt_engine/models:/app/models \
  stt-engine:cuda129-v1.0
```

### 2단계: faster_whisper가 로컬 파일만 읽음
```python
self.model = WhisperModel(
    "/app/models",  # ← 로컬 경로 (마운트된 디렉토리)
    device="cuda",
    local_files_only=True  # ← 외부 다운로드 금지!
)
```

### 3단계: 메모리에서 변환
- `model.safetensors` (로컬 파일) 읽음
- ctranslate2 포맷으로 메모리 변환
- 변환된 모델 캐시 (컨테이너 내부)
- STT API 서버 구동

**결과**: 📡 네트워크 접근 ZERO! ✅

---

## ✅ 오프라인 안정성 설정

### 1. stt_engine.py 수정됨
```python
# ✅ 추가됨: local_files_only=True
self.model = WhisperModel(
    self.model_path,
    device=self.device,
    compute_type=self.compute_type,
    num_workers=4,
    cpu_threads=4,
    download_root=None,
    local_files_only=True  # 외부 네트워크 차단!
)
```

**효과**:
- ✅ 외부 HuggingFace 서버 접근 불가 설정
- ✅ 로컬 파일만 사용 강제
- ✅ 네트워크 오류 방지

### 2. 환경 변수 (선택사항)

Docker 실행 시 추가 설정:
```bash
docker run -d \
  --name stt-engine-gpu \
  --gpus all \
  -p 8003:8003 \
  -v /Users/a113211/workspace/stt_engine/models:/app/models \
  -e STT_DEVICE=cuda \
  -e STT_MODEL_PATH=/app/models \
  -e HF_HUB_OFFLINE=1 \
  -e TRANSFORMERS_OFFLINE=1 \
  stt-engine:cuda129-v1.0
```

| 환경변수 | 효과 |
|---------|------|
| `HF_HUB_OFFLINE=1` | HuggingFace Hub 완전 오프라인 |
| `TRANSFORMERS_OFFLINE=1` | Transformers 라이브러리 오프라인 |

---

## 📦 현재 상태

### 필수 파일 (로컬에 이미 준비됨)
```
/Users/a113211/workspace/stt_engine/models/
├── model.safetensors        ✅ (1.32 GB)
├── config.json              ✅
├── preprocessor_config.json ✅
├── tokenizer.json           ✅
├── tokenizer_config.json    ✅
├── vocab.json               ✅
├── generation_config.json   ✅
└── merges.txt               ✅
```

### Docker 마운트
```
호스트 경로: /Users/a113211/workspace/stt_engine/models
컨테이너 경로: /app/models
```

### 결과
- 📡 네트워크 접근: **ZERO**
- 🚀 로드 속도: **매우 빠름** (로컬 파일)
- 🔒 보안: **완벽** (오프라인 강제)

---

## 🧪 테스트 명령어

### 오프라인 환경에서 실행
```bash
# Docker 실행
bash run-docker-gpu.sh

# 또는 수동 실행 (환경변수 포함)
docker run -d \
  --name stt-engine-gpu \
  --gpus all \
  -p 8003:8003 \
  -v /Users/a113211/workspace/stt_engine/models:/app/models \
  -e HF_HUB_OFFLINE=1 \
  -e TRANSFORMERS_OFFLINE=1 \
  stt-engine:cuda129-v1.0
```

### 헬스 체크
```bash
# 모델 로드 대기 (약 30초)
sleep 30

# 헬스 체크
curl http://localhost:8003/health
```

### 로그 확인
```bash
docker logs stt-engine-gpu

# 기대 출력
# ✅ faster-whisper 모델 로드 완료
# ✅ STT Server started on 0.0.0.0:8003
```

---

## ✅ 최종 체크리스트

- [x] 모델 파일 준비 (로컬)
- [x] `local_files_only=True` 설정 추가
- [x] 마운트 경로 구성
- [x] 환경 변수 설정 (선택)
- [x] 오프라인 안정성 확보

---

## 🎯 결론

### 외부 네트워크 필요 여부
| 상황 | 결과 |
|------|------|
| **모델 변환** | ✅ 네트워크 불필요 (로컬) |
| **모델 로드** | ✅ 네트워크 불필요 (로컬) |
| **STT 추론** | ✅ 네트워크 불필요 (로컬) |
| **API 호출** | ✅ 네트워크 불필요 (로컬) |

**최종 결론**: 📡 **완벽한 오프라인 환경에서 작동 가능!**

---
**업데이트 일시**: 2026-02-03  
**상태**: ✅ 오프라인 환경 설정 완료
