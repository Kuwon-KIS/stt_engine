# STT API 사용 가이드

## 개요

**3가지 엔드포인트 제공:**

| 엔드포인트 | 방식 | 용도 | 추천 |
|-----------|------|------|------|
| `POST /transcribe` | 로컬 파일 경로 | 서버 내부 파일 처리 (일반 + 스트리밍) | ⭐⭐⭐ 권장 |
| `POST /transcribe_by_upload` | 파일 업로드 | 클라이언트에서 파일 업로드 | 소규모 파일만 |
| `GET /health` | 헬스 체크 | 서버 상태 확인 | 모니터링 용 |

---

## 1️⃣ 로컬 파일 경로 기반 (권장) - `/transcribe`

### 1-1. 일반 모드 (메모리 로드)

**특징:**
- 전체 파일을 메모리에 로드 후 처리
- 빠른 처리 속도
- 일반적인 파일 크기 (< 1GB)에 적합

**명령:**

```bash
# 기본 사용 (기본 언어: 한국어)
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test.wav'

# 영어로 처리
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test.wav' \
  -F 'language=en'

# 일본어로 처리
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test.wav' \
  -F 'language=ja'
```

**응답 예시:**

```json
{
  "success": true,
  "text": "안녕하세요. 어떻게 도와드릴까요?",
  "language": "ko",
  "duration": 2.5,
  "backend": "faster-whisper",
  "file_path": "/app/audio/samples/test.wav",
  "file_size_mb": 0.015,
  "processing_mode": "normal",
  "segments_processed": 1,
  "memory_info": {
    "available_mb": 14000,
    "used_percent": 10.5
  }
}
```

---

### 1-2. 스트리밍 모드 (청크 처리)

**특징:**
- 10MB 청크 단위로 순차 처리
- 메모리 사용량 최소화
- 대용량 파일 (> 1GB) 처리 가능
- 느린 처리 속도 (메모리 효율성 교환)

**명령:**

```bash
# 기본 스트리밍 (한국어)
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/large_file.wav' \
  -F 'is_stream=true'

# 영어로 스트리밍 처리
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/large_file.wav' \
  -F 'is_stream=true' \
  -F 'language=en'
```

**응답 예시:**

```json
{
  "success": true,
  "text": "긴 음성 파일의 전체 내용...",
  "language": "ko",
  "duration": 300.0,
  "backend": "faster-whisper",
  "file_path": "/app/audio/samples/large_file.wav",
  "file_size_mb": 1500.5,
  "processing_mode": "streaming",
  "segments_processed": 150,
  "memory_info": {
    "available_mb": 8000,
    "used_percent": 48.5
  }
}
```

---

## 2️⃣ 파일 업로드 기반 - `/transcribe_by_upload`

### 특징:
- 로컬 파일을 클라이언트에서 전송
- 네트워크 대역폭 소비
- 소규모 파일 (< 100MB) 추천

**명령:**

```bash
# 로컬 파일 업로드 (한국어)
curl -X POST http://localhost:8003/transcribe_by_upload \
  -F 'file=@/Users/user/audio.wav'

# 영어로 처리
curl -X POST http://localhost:8003/transcribe_by_upload \
  -F 'file=@/Users/user/audio.wav' \
  -F 'language=en'
```

**응답:** `/transcribe`와 동일

---

## 3️⃣ 백엔드 관리

### 현재 백엔드 확인

```bash
curl http://localhost:8003/backend/current | jq
```

**응답 예시:**

```json
{
  "current_backend": "faster-whisper",
  "backend_type": "WhisperModel",
  "device": "cuda",
  "compute_type": "float16",
  "model_path": "/app/models/openai_whisper-large-v3-turbo",
  "available_backends": {
    "faster-whisper": true,
    "transformers": true,
    "openai-whisper": false
  },
  "loaded": true
}
```

### 백엔드 변경

```bash
# transformers로 변경
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"backend": "transformers"}'

# faster-whisper로 변경
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"backend": "faster-whisper"}'

# 자동 선택 (기본값: faster-whisper → transformers → openai-whisper)
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 4️⃣ 헬스 체크

```bash
curl http://localhost:8003/health | jq
```

**응답 예시:**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "backend": "faster-whisper",
  "backend_type": "WhisperModel",
  "model": "openai_whisper-large-v3-turbo",
  "device": "cuda",
  "compute_type": "float16",
  "memory": {
    "available_mb": 14000,
    "total_mb": 16000,
    "used_percent": 12.5,
    "status": "ok",
    "message": "✅ 메모리 양호 (14000MB / 16000MB)"
  }
}
```

---

## 5️⃣ 실전 활용 예시

### EC2 에서 로컬 파일 처리

```bash
# EC2에서 실행 (모든 sample 파일 처리)
for file in /app/audio/samples/*.wav; do
  echo "Processing: $file"
  curl -X POST http://localhost:8003/transcribe \
    -F "file_path=$file" \
    -F 'language=ko' | jq '.text'
done
```

### on-prem 서버에서 스트리밍 처리

```bash
# 대용량 파일 스트리밍 처리
curl -X POST http://your-server:8003/transcribe \
  -F 'file_path=/data/audio/large_meeting.wav' \
  -F 'is_stream=true' \
  -F 'language=ko' | jq '.'
```

### 언어별 처리

```bash
# 한국어 (기본)
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/korean.wav'

# 영어
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/english.wav' \
  -F 'language=en'

# 일본어
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/japanese.wav' \
  -F 'language=ja'

# 중국어
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/chinese.wav' \
  -F 'language=zh'
```

---

## 6️⃣ 에러 처리

### 파일을 찾을 수 없음

```json
{
  "detail": {
    "error": "파일 없음",
    "message": "파일을 찾을 수 없음: /app/audio/test.wav",
    "file_path": "/app/audio/test.wav"
  }
}
```

**해결:**
- 파일 경로가 정확한지 확인
- 파일이 실제로 서버에 존재하는지 확인
- 파일 권한 확인 (`ls -la /app/audio/samples/`)

### 메모리 부족

```json
{
  "detail": {
    "error": "메모리 부족",
    "message": "Available memory is critical",
    "suggestion": "서버 메모리를 늘리거나 더 작은 파일을 처리하세요. is_stream=true로 스트리밍 모드를 시도하세요."
  }
}
```

**해결:**
- 스트리밍 모드 사용: `-F 'is_stream=true'`
- 다른 프로세스 종료
- 서버 메모리 증설

### 경로가 허용 범위 밖

```json
{
  "detail": {
    "error": "접근 금지",
    "message": "파일 경로가 허용된 디렉토리 외에 있음: /etc/passwd",
    "allowed_directory": "/app"
  }
}
```

**해결:**
- `/app` 디렉토리 내의 파일만 접근 가능
- 필요한 파일을 `/app/audio/samples/` 등으로 복사

---

## 7️⃣ 성능 비교

| 항목 | 일반 모드 | 스트리밍 모드 |
|------|---------|-----------|
| **메모리 사용** | 파일 크기만큼 | 10MB (고정) |
| **처리 속도** | ⭐⭐⭐ 빠름 | ⭐⭐ 느림 |
| **최대 파일 크기** | ~5GB | 무제한 |
| **추천 용도** | < 1GB | > 1GB |
| **메모리 부족 시** | ❌ 실패 | ✅ 작동 |

---

## 8️⃣ 언어 코드

| 코드 | 언어 | 코드 | 언어 |
|------|------|------|------|
| `ko` | 한국어 | `en` | 영어 |
| `ja` | 일본어 | `zh` | 중국어 |
| `fr` | 프랑스어 | `de` | 독일어 |
| `es` | 스페인어 | `it` | 이탈리아어 |
| `ru` | 러시아어 | `pt` | 포르투갈어 |

기본값: `ko` (한국어)

---

## 9️⃣ 도커 실행 예시

### EC2 빌드 환경

```bash
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v $(pwd)/audio/samples:/app/audio/samples \
  -v $(pwd)/models:/app/models \
  stt-engine:cuda129-rhel89-v1.6
```

### on-prem 운영 환경

```bash
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -e STT_DEVICE=cuda \
  -e STT_COMPUTE_TYPE=int8 \
  -v /data/audio:/app/audio \
  -v /data/models:/app/models \
  stt-engine:prod
```

---

## 🔟 트러블슈팅

### 로그 확인

```bash
# 실시간 로그 확인
docker logs -f stt-engine

# 특정 문제별 로그 필터링
docker logs stt-engine | grep "ERROR"
docker logs stt-engine | grep "STREAM"
docker logs stt-engine | grep "메모리"
```

### 파일 권한 확인

```bash
# 파일 권한 확인
ls -lh /app/audio/samples/test.wav

# 권한 변경 (필요한 경우)
chmod 644 /app/audio/samples/test.wav
```

### 네트워크 연결 확인

```bash
# 로컬 테스트
curl http://localhost:8003/health | jq

# 원격 접근 테스트
curl http://<server-ip>:8003/health | jq
```

---

## 최종 요약

✅ **로컬 파일 처리 권장**: `/transcribe` 엔드포인트  
✅ **일반 파일**: 일반 모드 (메모리 로드)  
✅ **대용량 파일**: 스트리밍 모드  
✅ **보안**: `/app` 디렉토리만 접근 가능  
✅ **확장성**: EC2 빌드 + on-prem 운영 지원
