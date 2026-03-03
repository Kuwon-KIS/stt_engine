# STT API 사용 가이드

## 개요

**주요 엔드포인트 제공:**

| 엔드포인트 | 방식 | 용도 | 추천 |
|-----------|------|------|------|
| `POST /transcribe` | 로컬 파일 경로 | 서버 내부 파일 처리 (일반 + 스트리밍 + 선택 단계) | ⭐⭐⭐ 권장 |
| `POST /transcribe_batch` | 배치 처리 | 여러 파일 일괄 처리 (NEW) | ⭐⭐⭐ 권장 |
| `POST /transcribe_by_upload` | 파일 업로드 | 클라이언트에서 파일 업로드 | 소규모 파일만 |
| `GET /health` | 헬스 체크 | 서버 상태 확인 | 모니터링 용 |

---

## 1️⃣ 로컬 파일 경로 기반 (권장) - `/transcribe` ⭐ 개선됨

### 주요 개선 사항 (NEW)

1. **처음 요청 시 처리 단계 선택**: 초기 요청에서 어느 단계까지 진행할지 선택 가능
   - `privacy_removal=true/false` - 개인정보 제거 처리 여부
   - `classification=true/false` - 통화 분류 처리 여부
   - `ai_agent=true/false` - AI Agent 처리 여부

2. **Processing Steps 메타데이터**: 응답에 각 단계의 완료 여부 표시
   - `processing_steps.stt` - STT 완료
   - `processing_steps.privacy_removal` - 개인정보 제거 완료
   - `processing_steps.classification` - 분류 완료
   - `processing_steps.ai_agent` - AI Agent 완료

### 처리 워크플로우

```
[사용자 요청]
    ↓
[처리 단계 선택] (privacy_removal, classification, ai_agent)
    ↓
[필수] STT 처리 → text, language, duration
    ↓
[조건] Privacy Removal (privacy_removal=true인 경우)
    ↓
[조건] Classification (classification=true인 경우)
    ↓
[조건] AI Agent (ai_agent=true인 경우)
    ↓
[응답] processing_steps 메타데이터 포함
```

### 1-1. 일반 모드 (메모리 로드)

**특징:**
- 전체 파일을 메모리에 로드 후 처리
- 빠른 처리 속도
- 일반적인 파일 크기 (< 1GB)에 적합

**명령:**

```bash
# 기본 사용 (STT만 수행)
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test.wav'

# STT + Privacy Removal 수행
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test.wav' \
  -F 'privacy_removal=true'

# STT + Privacy Removal + Classification 수행
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test.wav' \
  -F 'privacy_removal=true' \
  -F 'classification=true'

# 모든 단계 수행
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test.wav' \
  -F 'privacy_removal=true' \
  -F 'classification=true' \
  -F 'ai_agent=true'

# 영어로 처리
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test.wav' \
  -F 'language=en'

# 일본어로 처리
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test.wav' \
  -F 'language=ja'
```

**응답 예시 (모든 단계 수행 시):**

```json
{
  "success": true,
  "text": "안녕하세요, 제품 구매 문의입니다.",
  "language": "ko",
  "duration": 2.5,
  "backend": "faster-whisper",
  "file_path": "/app/audio/samples/test.wav",
  "file_size_mb": 0.015,
  
  "privacy_removal": {
    "privacy_exist": "N",
    "exist_reason": "",
    "text": "안녕하세요, 제품 구매 문의입니다.",
    "privacy_types": []
  },
  
  "classification": {
    "code": "CLASS_PRE_SALES",
    "category": "사전판매",
    "confidence": 92.3,
    "reason": "제품 구매 의사 표현"
  },
  
  "processing_steps": {
    "stt": true,
    "privacy_removal": true,
    "classification": true,
    "ai_agent": false
  },
  
  "processing_time_seconds": 8.5,
  "processing_mode": "normal",
  "segments_processed": 1,
  
  "memory_info": {
    "available_mb": 14000,
    "used_percent": 10.5
  }
}
```

**응답 예시 (STT만 수행 시):**

```json
{
  "success": true,
  "text": "안녕하세요. 어떻게 도와드릴까요?",
  "language": "ko",
  "duration": 2.5,
  "backend": "faster-whisper",
  "file_path": "/app/audio/samples/test.wav",
  "file_size_mb": 0.015,
  
  "processing_steps": {
    "stt": true,
    "privacy_removal": false,
    "classification": false,
    "ai_agent": false
  },
  
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
  
  "processing_steps": {
    "stt": true,
    "privacy_removal": false,
    "classification": false,
    "ai_agent": false
  },
  
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

## 2️⃣ 배치 처리 (다중 파일) - `/transcribe_batch` ⭐ NEW

### 기능
- 여러 파일을 한 번에 처리
- 배치 ID로 진행 상황 추적
- 실시간 진행률 표시
- 각 파일별 독립적 처리 및 에러 처리

### 2-1. 기본 배치 처리

**명령:**

```bash
# 여러 파일 처리
curl -X POST http://localhost:8003/transcribe_batch \
  -F 'file_paths=/app/audio/test1.wav' \
  -F 'file_paths=/app/audio/test2.wav' \
  -F 'file_paths=/app/audio/test3.wav'

# 처리 옵션과 함께
curl -X POST http://localhost:8003/transcribe_batch \
  -F 'file_paths=/app/audio/test1.wav' \
  -F 'file_paths=/app/audio/test2.wav' \
  -F 'language=ko' \
  -F 'privacy_removal=true' \
  -F 'classification=true'
```

**응답 예시:**

```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  
  "files": [
    {
      "filename": "test1.wav",
      "filepath": "/app/audio/test1.wav",
      "status": "done",
      "result": {
        "success": true,
        "text": "안녕하세요. 제품 구매 문의입니다.",
        "language": "ko",
        "duration": 3.2,
        "backend": "faster-whisper",
        "processing_steps": {
          "stt": true,
          "privacy_removal": true,
          "classification": true,
          "ai_agent": false
        },
        "classification": {
          "code": "CLASS_PRE_SALES",
          "category": "사전판매",
          "confidence": 92.3,
          "reason": "제품 구매 의사 표현"
        },
        "privacy_removal": {
          "privacy_exist": "N",
          "exist_reason": "",
          "text": "안녕하세요. 제품 구매 문의입니다."
        }
      },
      "processing_time_seconds": 5.2
    },
    {
      "filename": "test2.wav",
      "filepath": "/app/audio/test2.wav",
      "status": "done",
      "result": { ... },
      "processing_time_seconds": 4.8
    }
  ],
  
  "progress": {
    "total": 2,
    "completed": 2,
    "failed": 0,
    "in_progress": 0,
    "pending": 0,
    "progress_percent": 100.0
  },
  
  "created_at": "2024-02-20T10:30:00",
  "started_at": "2024-02-20T10:31:00",
  "completed_at": "2024-02-20T10:40:30",
  "total_processing_time_seconds": 570.5
}
```

### 2-2. 배치 처리 요청 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|-------|------|
| `file_paths` | list | 필수 | 처리할 파일 경로 (여러 번 지정) |
| `language` | str | `ko` | 음성 언어 |
| `is_stream` | bool | `false` | 스트리밍 모드 여부 |
| `privacy_removal` | bool | `false` | 개인정보 제거 처리 여부 |
| `classification` | bool | `false` | 통화 분류 처리 여부 |
| `ai_agent` | bool | `false` | AI Agent 처리 여부 |

### 2-3. 처리 단계 선택 옵션 (NEW)

각 단계를 독립적으로 선택할 수 있습니다:

```bash
# STT만 수행
curl -X POST http://localhost:8003/transcribe_batch \
  -F 'file_paths=/app/audio/test1.wav'

# STT + Privacy Removal
curl -X POST http://localhost:8003/transcribe_batch \
  -F 'file_paths=/app/audio/test1.wav' \
  -F 'privacy_removal=true'

# STT + Privacy Removal + Classification
curl -X POST http://localhost:8003/transcribe_batch \
  -F 'file_paths=/app/audio/test1.wav' \
  -F 'file_paths=/app/audio/test2.wav' \
  -F 'privacy_removal=true' \
  -F 'classification=true'

# 모든 단계 수행
curl -X POST http://localhost:8003/transcribe_batch \
  -F 'file_paths=/app/audio/test1.wav' \
  -F 'privacy_removal=true' \
  -F 'classification=true' \
  -F 'ai_agent=true'
```

---

## 3️⃣ 파일 업로드 기반 - `/transcribe_by_upload`

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

## 4️⃣ 백엔드 관리

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

## Web UI - 비동기 작업 큐 시스템

### 개요

**Web UI 포트 8100에서 제공하는 비동기 STT 처리**

장시간 소요되는 STT 처리(30분 이상)를 지원하기 위해 비동기 작업 큐 시스템을 구현했습니다:
- ✅ **UI 블로킹 없음**: 파일 처리 중 UI 반응성 유지
- ✅ **타임아웃 해결**: 동기식 대기 제거로 기한 없이 처리 가능  
- ✅ **상태 추적**: 실시간 진행률 및 상태 확인
- ✅ **동시 작업 제한**: 서버 과부하 방지 (최대 2개 동시 처리)

### 아키텍처 다이어그램

```
┌─────────────────────────────────────────┐
│    Web UI Server (FastAPI, :8100)       │
├─────────────────────────────────────────┤
│                                         │
│  POST /api/transcribe-async/            │
│  └─> TranscribeJobQueue.enqueue()       │
│      └─> job_id 즉시 반환 (블로킹 안함)│
│                                         │
│  GET /api/transcribe-status/{job_id}    │
│  └─> 클라이언트 폴링용 상태 조회       │
│                                         │
│  GET /api/transcribe-jobs/              │
│  └─> 모든 작업 목록 조회               │
│                                         │
│  [Async Worker Loop (백그라운드)]       │
│  └─> 2개까지 동시 처리 가능            │
│      └─> STT API 호출 (:8003)          │
│                                         │
└─────────────────────────────────────────┘
         │ (docker bridge network: stt-network)
         │
┌─────────────────────────────────────────┐
│    STT API Server (:8003)               │
│    (faster-whisper 또는 transformers)   │
└─────────────────────────────────────────┘
```

### 1️⃣ 비동기 작업 제출

**엔드포인트**: `POST /api/transcribe-async/`

**특징**:
- 즉시 응답 (job_id 반환)
- 백그라운드에서 처리 진행
- 클라이언트는 폴링으로 상태 확인

**요청**:

```bash
curl -X POST http://localhost:8100/api/transcribe-async/ \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "abc123.wav",
    "language": "ko"
  }'
```

**응답 (즉시)**:

```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "작업이 큐에 추가되었습니다. /api/transcribe-status/{job_id}로 상태를 확인하세요."
}
```

### 2️⃣ 작업 상태 조회 (폴링)

**엔드포인트**: `GET /api/transcribe-status/{job_id}`

**특징**:
- 실시간 진행률 확인 가능
- 처리 상태 추적 (PENDING → PROCESSING → COMPLETED)
- 1초 간격 폴링 권장

**요청**:

```bash
curl http://localhost:8100/api/transcribe-status/550e8400-e29b-41d4-a716-446655440000
```

**응답 (처리 중, 45% 진행)**:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_path": "/app/data/uploads/abc123.wav",
  "language": "ko",
  "is_stream": false,
  "status": "processing",
  "progress": 45,
  "created_at": "2026-02-12T10:00:00",
  "started_at": "2026-02-12T10:00:05",
  "completed_at": null,
  "result": null,
  "error": null
}
```

**응답 (완료)**:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_path": "/app/data/uploads/abc123.wav",
  "language": "ko",
  "is_stream": false,
  "status": "completed",
  "progress": 100,
  "created_at": "2026-02-12T10:00:00",
  "started_at": "2026-02-12T10:00:05",
  "completed_at": "2026-02-12T10:45:30",
  "result": {
    "success": true,
    "text": "안녕하세요... [full transcript]",
    "language": "ko",
    "duration": 2700.5,
    "processing_time_seconds": 2725.0
  },
  "error": null
}
```

### 3️⃣ 모든 작업 조회

**엔드포인트**: `GET /api/transcribe-jobs/`

**특징**:
- 현재 큐에 있는 모든 작업 확인
- 상태별 필터링 가능

**요청**:

```bash
curl http://localhost:8100/api/transcribe-jobs/
```

**응답**:

```json
{
  "total": 3,
  "jobs": [
    {
      "job_id": "...",
      "status": "completed",
      "progress": 100,
      "created_at": "...",
      "result": { ... }
    },
    {
      "job_id": "...",
      "status": "processing",
      "progress": 45,
      "created_at": "...",
      "result": null
    },
    {
      "job_id": "...",
      "status": "pending",
      "progress": 0,
      "created_at": "...",
      "result": null
    }
  ]
}
```

### 작업 상태 (JobStatus)

| 상태 | 설명 | 진행률 |
|------|------|--------|
| `pending` | 큐에 추가됨, 처리 대기 중 | 0-10% |
| `processing` | 워커가 처리 중 | 10-90% |
| `completed` | 처리 완료, 결과 가능 | 100% |
| `failed` | 처리 중 오류 발생 | - |
| `cancelled` | 사용자가 취소함 | - |

### 진행률 추적 (Progress Tracking)

```
제출 (0%)
  ↓
큐 대기 (PENDING, 0-10%)
  ↓
워커 시작 (PROCESSING, 10-15%)
  ↓
API 호출 (15-90%)
  ↓
API 응답 처리 (90%)
  ↓
완료 (COMPLETED, 100%)
```

### JavaScript 클라이언트 구현

#### 비동기 처리 + 폴링

```javascript
// 1. 작업 제출 (즉시 반환)
const submitResponse = await fetch('/api/transcribe-async/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
        file_id: 'abc123.wav', 
        language: 'ko' 
    })
});

const { job_id } = await submitResponse.json();
console.log(`작업 시작: ${job_id}`);

// 2. 폴링으로 상태 확인 (1초 간격)
const pollInterval = setInterval(async () => {
    const statusResponse = await fetch(`/api/transcribe-status/${job_id}`);
    const jobInfo = await statusResponse.json();
    
    console.log(`상태: ${jobInfo.status}, 진행률: ${jobInfo.progress}%`);
    
    // UI 업데이트
    updateProgressBar(jobInfo.progress);
    updateStatusText(jobInfo.status);
    
    if (jobInfo.status === 'completed') {
        clearInterval(pollInterval);
        
        if (jobInfo.result.success) {
            console.log('결과:', jobInfo.result.text);
            displayTranscription(jobInfo.result);
        } else {
            console.error('처리 실패:', jobInfo.result.error);
        }
    } else if (jobInfo.status === 'failed') {
        clearInterval(pollInterval);
        console.error('작업 실패:', jobInfo.error);
        showErrorMessage(jobInfo.error);
    }
}, 1000);  // 1초 간격 폴링
```

### Docker 실행 예시

```bash
# 1. 네트워크 생성 (STT API와 통신용)
docker network create stt-network

# 2. STT API 컨테이너 실행
docker run -d \
  --name stt-api \
  --network stt-network \
  -p 8003:8003 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/web_ui/data:/app/web_ui/data \
  stt-engine:cuda129-rhel89-v1.7

# 3. Web UI 컨테이너 실행
docker run -d \
  --name stt-web-ui \
  --network stt-network \
  -p 8100:8100 \
  -e STT_API_URL=http://stt-api:8003 \
  -v $(pwd)/web_ui/data:/app/data \
  -v $(pwd)/web_ui/logs:/app/logs \
  stt-web-ui:cuda129-rhel89-v1.0

# 4. 상태 확인
curl http://localhost:8100/api/transcribe-jobs/
```

### 성능 권장사항

| 파일 크기 | 예상 처리시간 | 권장 설정 |
|---------|------------|----------|
| < 1분 | 5~30초 | 일반 폴링 (1초) |
| 1~10분 | 30초~5분 | 일반 폴링 (1-2초) |
| 10~30분 | 5~15분 | 느슨한 폴링 (5초) |
| > 30분 | 15분+ | 느슨한 폴링 (10초) |

**폴링 간격 조정 팁**:
```javascript
// 진행률 기반 적응형 폴링
let pollInterval = 1000;  // 기본 1초
if (jobInfo.progress > 80) {
    pollInterval = 5000;  // 80% 이상일 때 5초로 완화
}
```

### 프로덕션 고려사항

#### 현재 in-memory 구현의 한계

- ✅ **프로토타입**: 간단함, 의존성 없음
- ⚠️ **문제점**: 
  - 서버 재시작 시 작업 손실
  - 분산 시스템 미지원
  - 메모리 누적

#### 프로덕션 개선 방안

**Option 1: Redis + Celery** (권장)
```bash
# Docker Compose로 Redis + Celery 추가
docker-compose -f docker/docker-compose.prod.yml up -d
```

**Option 2: PostgreSQL 저장** (대안)
```bash
# 작업 상태를 데이터베이스에 저장
# 서버 재시작 후에도 작업 복구 가능
```

### 문제 해결

#### Q: 작업이 계속 PENDING 상태인 경우

**원인**: 워커 루프가 시작되지 않음

**확인**:
```bash
# 로그에서 "워커 시작" 메시지 확인
docker logs stt-web-ui | grep "비동기 STT 처리 워커"
```

#### Q: 작업이 FAILED 상태로 변한 경우

**확인할 사항**:
```bash
# 에러 메시지 확인
curl http://localhost:8100/api/transcribe-status/{job_id} | jq '.error'

# 일반적인 에러:
# - "timeout": API 응답 초과 (600초 이상)
# - "api_error": 네트워크 연결 실패
# - "path_not_found": 파일을 찾을 수 없음
```

#### Q: 동시에 3개 이상의 작업을 제출하려면?

**동시 실행 제한**: 최대 2개

대기 중인 작업은 큐에서 순차적으로 처리됩니다:
```
제출 1 (즉시 처리)
제출 2 (즉시 처리)
제출 3 (대기, 제출 1 완료 후 시작)
제출 4 (대기, 제출 2 완료 후 시작)
```

---

## 최종 요약

✅ **STT API** (`/transcribe`, 포트 8003): 동기식 처리, 응답 대기  
✅ **Web UI 비동기** (`/api/transcribe-async/`, 포트 8100): 비동기식 처리, 폴링  
✅ **소규모 파일**: STT API 직접 사용  
✅ **장시간 파일**: Web UI 비동기 사용  
✅ **보안**: `/app` 디렉토리만 접근 가능  
✅ **확장성**: EC2 빌드 + on-prem 운영 지원  
✅ **성능 추적**: `progress`, `processing_time_seconds`로 추적
