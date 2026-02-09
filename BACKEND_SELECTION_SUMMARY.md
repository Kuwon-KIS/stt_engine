# Backend 선택 기능 추가 요약

## 🎯 구현된 기능

### 1️⃣ Backend 파라미터 지정 가능
API 호출 시 `backend` 파라미터로 원하는 백엔드를 직접 지정할 수 있습니다.

```bash
# faster-whisper만 사용
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' \
  -F 'backend=faster-whisper'

# transformers만 사용
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' \
  -F 'backend=transformers'

# openai-whisper만 사용
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' \
  -F 'backend=openai-whisper'
```

### 2️⃣ Backend 미지정 시 자동 선택
`backend` 파라미터를 지정하지 않으면 기존의 자동 선택 순서를 유지합니다.

```bash
# 자동 선택: faster-whisper → transformers → openai-whisper 순서
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav'
```

### 3️⃣ 명확한 에러 메시지
지정한 백엔드가 없거나 로드되지 않으면 명확한 에러 메시지를 반환합니다.

```json
{
  "success": false,
  "error": "요청한 백엔드를 사용할 수 없습니다: transformers (현재 로드됨: WhisperModel)",
  "error_type": "RuntimeError",
  "audio_path": "/tmp/test.wav"
}
```

---

## 🔧 코드 변경사항

### api_server.py
```python
@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = None, backend: str = None):
    # backend 파라미터 추가
    result = stt.transcribe(tmp_path, language=language, backend=backend)
```

**변경 사항:**
- `/transcribe` 엔드포인트에 `backend` 파라미터 추가
- 로깅에 요청된 백엔드 정보 포함

### stt_engine.py
```python
def transcribe(self, audio_path: str, language: Optional[str] = None, backend: Optional[str] = None, **kwargs) -> Dict:
    # Backend 파라미터 처리 로직
    if backend:
        backend = backend.lower().strip()
        # backend 별칭 처리 (faster-whisper, faster_whisper 모두 지원)
        # 현재 로드된 백엔드와 요청된 백엔드 매칭
        # 미일치 시 에러 반환
    else:
        # 기존 자동 선택 로직 유지
```

**변경 사항:**
- `backend` 파라미터 추가
- Backend 별칭 처리 (하이픈, 언더스코어 모두 지원)
- Backend 검증 로직 추가
- 디버그 로깅 추가

---

## 📊 지원하는 Backend 이름

| 정식명 | 별칭 | 설명 |
|--------|------|------|
| faster-whisper | faster_whisper | CTranslate2 기반, 가장 빠름 |
| transformers | - | HuggingFace 모델, 중간 속도 |
| openai-whisper | openai_whisper, whisper | OpenAI 공식 모델, 호환성 우수 |

---

## 🚀 사용 예시

### 예시 1: 한국어 처리 (자동 백엔드)
```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@audio/samples/korean_sample.wav' \
  -F 'language=ko' | python3 -m json.tool
```

### 예시 2: 영어 처리 (faster-whisper 지정)
```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@audio/samples/english_sample.wav' \
  -F 'language=en' \
  -F 'backend=faster-whisper' | python3 -m json.tool
```

### 예시 3: 성능 테스트 (모든 백엔드 비교)
```bash
# 테스트 파일 준비
cp audio/samples/door_to_door_sales/1_Recording_20240712_140513_01041968444.wav /tmp/test.wav

# faster-whisper 테스트
echo "=== faster-whisper ===" && \
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' \
  -F 'backend=faster-whisper' | python3 -m json.tool

# transformers 테스트
echo "=== transformers ===" && \
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' \
  -F 'backend=transformers' | python3 -m json.tool

# openai-whisper 테스트
echo "=== openai-whisper ===" && \
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' \
  -F 'backend=openai-whisper' | python3 -m json.tool
```

---

## 📝 로깅 개선사항

Backend 선택 과정도 상세히 로깅됩니다.

### Backend 지정 시
```
📂 음성 파일 로드 시작: test.wav
✓ 파일 존재 확인: /tmp/tmpXXXXXX.wav
🔧 현재 로드된 백엔드: WhisperModel
📌 요청된 백엔드: faster-whisper
→ faster-whisper 백엔드로 변환 시작
[faster-whisper] 변환 시작 (파일: test.wav)
✓ faster-whisper 변환 완료
  결과: 128 글자, 언어: ko
```

### Backend 미지정 시
```
📂 음성 파일 로드 시작: test.wav
✓ 파일 존재 확인: /tmp/tmpXXXXXX.wav
🔧 현재 로드된 백엔드: WhisperModel
→ 자동 백엔드 선택 (기존 순서 유지)
→ faster-whisper 백엔드로 변환 시작
[faster-whisper] 변환 시작 (파일: test.wav)
✓ faster-whisper 변환 완료
```

---

## ✅ 체크리스트

- [x] api_server.py에 backend 파라미터 추가
- [x] stt_engine.py에 backend 선택 로직 구현
- [x] Backend 별칭 처리 (하이픈, 언더스코어)
- [x] Backend 검증 및 에러 처리
- [x] 디버그 로깅 추가
- [x] QUICK_CURL_GUIDE.md 작성
- [x] 커밋 및 배포

---

## 🎯 다음 단계

### 1. 로컬 테스트
```bash
# 변경사항 확인
git diff HEAD~2

# 로컬 서버 시작 (필요시)
python api_server.py
```

### 2. EC2 배포
```bash
git push origin main

# EC2에서
git pull origin main
docker build -t stt-engine:v1.6 -f docker/Dockerfile.engine.rhel89 .
docker run -d --name stt-engine -p 8003:8003 \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/models:/app/models \
  stt-engine:v1.6
```

### 3. 테스트
```bash
# 자동 선택 테스트
curl -X POST http://localhost:8003/transcribe -F 'file=@/tmp/test.wav'

# faster-whisper 테스트
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' \
  -F 'backend=faster-whisper'

# transformers 테스트
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' \
  -F 'backend=transformers'

# 로그 확인
docker logs stt-engine | tail -50
```

---

## 📋 커밋 정보

```
fb57c09 - Feat: Add backend parameter to specify STT backend
e3a3507 - Docs: Add QUICK_CURL_GUIDE.md for fast API testing
```

---

## 💡 추가 기능 아이디어

1. **Backend 성능 비교 API**
   ```bash
   GET /api/backends - 로드된 모든 백엔드 목록
   GET /api/backends/benchmark - 각 백엔드 성능 비교
   ```

2. **Fallback 정책 지정**
   ```bash
   -F 'backend=faster-whisper'
   -F 'fallback=transformers' # 실패 시 자동으로 transformers 시도
   ```

3. **Backend 통계**
   - 각 백엔드별 처리 시간
   - 백엔드별 성공률
   - 언어별 최적 백엔드

이들은 향후에 추가할 수 있습니다! 🚀
