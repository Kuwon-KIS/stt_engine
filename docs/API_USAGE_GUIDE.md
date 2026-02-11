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
  "processing_time_seconds": 1.23,
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
  "processing_time_seconds": 45.67,
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

**응답:** `/transcribe`와 동일 (processing_time_seconds 포함)

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

## ⚠️ 주의사항 및 성능 팁

### 대용량 파일 처리 시 응답 지연

**문제**: 매우 큰 파일(> 100MB, 94분 이상)을 처리하면 텍스트가 매우 커져서 JSON 직렬화 시간이 증가할 수 있습니다.

**해결책**:

1. **transformers 백엔드 사용**
   ```bash
   curl -X POST http://localhost:8003/backend/reload \
     -H "Content-Type: application/json" \
     -d '{"backend": "transformers"}'
   ```
   - 내부적으로 30초 세그먼트 처리
   - 메모리 효율적
   - 응답 지연 없음

2. **로컬 파일 처리 방식 사용**
   ```bash
   # 업로드 방식 대신 파일 경로 사용
   curl -X POST http://localhost:8003/transcribe \
     -F 'file_path=/app/audio/samples/file.wav'
   ```

3. **응답 로깅 모니터링**
   ```bash
   docker logs -f stt-engine | grep "응답 직렬화"
   ```
   - `응답 직렬화` 로그로 JSON 변환 시간 확인
   - 응답 크기 모니터링

### 타임아웃 설정

curl에서 장시간 처리되는 경우:

```bash
# 30초 타임아웃 설정
curl --max-time 300 \
  -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/file.wav'

# 또는 무제한 타임아웃
curl --max-time 0 \
  -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/file.wav'
```

### 파일 크기별 권장사항

| 파일 크기 | 소요시간 | 추천 옵션 |
|---------|---------|----------|
| < 100MB | 10~30초 | faster-whisper + 일반 모드 |
| 100MB~1GB | 30~90초 | transformers + 일반 모드 |
| > 1GB | 90초+ | transformers **필수** |

---

## 🔄 스트리밍 모드 (대용량 파일 처리)

### 상태 및 권장사항

| 항목 | faster-whisper | transformers | openai-whisper |
|------|----------------|--------------|----------------|
| **파일 크기** | < 1GB | 무제한 | < 1GB |
| **처리 방식** | 메모리 로드 | 30초 세그먼트 | 메모리 로드 |
| **메모리 사용** | 높음 (파일 크기 기반) | 낮음 (고정 500MB) | 높음 |
| **속도** | ⭐⭐⭐ 빠름 | ⭐⭐ 중간 | ⭐⭐⭐ 빠름 |
| **권장 범위** | < 1GB | **1GB 이상** | < 1GB |

### 현재 구현 상태

❌ **API의 스트리밍 모드** (`is_stream=true`)
- WAV 파일 구조 손상으로 인한 버그
- 모든 청크에서 InvalidDataError 발생
- **현재 사용 불가** - 일반 모드만 사용

✅ **transformers 백엔드**
- 30초 단위 자동 세그먼트 분할 구현됨
- 50% 오버랩으로 컨텍스트 손실 방지
- 메모리 효율적 (500MB 고정)
- 대용량 파일 처리 가능

### 대용량 파일 처리 가이드

#### 권장: transformers 백엔드 사용

```bash
# 1. 현재 백엔드 확인
curl http://localhost:8003/backend/current | jq

# 2. transformers로 전환
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"backend": "transformers"}'

# 3. 대용량 파일 처리
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/customer_visit/1_Recording_20240617_145848_739209.wav' \
  -F 'language=ko' | jq .
```

**응답 예시**:
```json
{
  "success": true,
  "text": "긴 음성 파일의 변환 결과...",
  "language": "ko",
  "duration": 1017.963,
  "backend": "transformers",
  "processing_time_seconds": 45.23,
  "segments_processed": 34,
  "memory_info": {
    "available_mb": 8000,
    "used_percent": 37.5
  }
}
```

#### 세그먼트 처리 상세 정보

대용량 파일(> 1GB)은 자동으로 다음과 같이 처리됩니다:

```
예: 17분 오디오 (172MB)
↓
30초 세그먼트로 분할 (50% 오버랩)
↓
세그먼트 1: 0~30초
세그먼트 2: 15~45초 (15초 오버랩)
세그먼트 3: 30~60초 (15초 오버랩)
... (총 34개 세그먼트)
↓
각 세그먼트 개별 처리 (메모리 정리)
↓
결과 텍스트 병합
```

**처리 시간**: 약 45초 (GPU), 90초 (CPU)

### 파일 크기별 권장 백엔드

| 파일 크기 | 권장 백엔드 | 예상 처리시간 | 메모리 사용 |
|---------|-----------|------------|-----------|
| < 100MB | faster-whisper | 5~10초 | < 200MB |
| 100MB~1GB | transformers | 10~30초 | 500MB |
| > 1GB | **transformers 필수** | 30~90초 | 500MB |

### 백엔드 전환 방법

```bash
# faster-whisper로 전환 (소규모 파일)
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"backend": "faster-whisper"}'

# transformers로 전환 (대용량 파일)
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"backend": "transformers"}'

# 자동 선택 (우선순위: faster-whisper → transformers → openai-whisper)
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 주의사항

⚠️ **스트리밍 모드 (`is_stream=true`) 현재 작동 불가**
- API 레벨의 바이너리 청크 분할이 WAV 구조를 손상시킴
- 향후 업데이트에서 수정 예정
- 현재는 `is_stream=false` (기본값) 사용

✅ **대용량 파일이 필요하면 transformers 사용**
- 내부적으로 30초 세그먼트 처리
- 자동으로 메모리 효율적으로 동작
- API 수정 없이 안정적으로 작동

---

## 최종 요약

✅ **로컬 파일 처리 권장**: `/transcribe` 엔드포인트  
✅ **일반 파일**: 일반 모드 (메모리 로드)  
✅ **대용량 파일**: 스트리밍 모드  
✅ **보안**: `/app` 디렉토리만 접근 가능  
✅ **확장성**: EC2 빌드 + on-prem 운영 지원  
✅ **성능 추적**: `processing_time_seconds`로 성능 측정
