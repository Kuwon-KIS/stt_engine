# 백엔드 추천 및 동적 메모리 관리 가이드

## 개요

STT API는 **동적 메모리 분석**을 통해 최적의 백엔드를 자동으로 선택합니다.

---

## 🎯 백엔드 선택 논리

### 메모리 요구사항 분석

```
faster-whisper:
  - 방식: 전체 파일을 메모리에 로드
  - 장점: ⚡ 최고 속도 (병렬 처리)
  - 필요 메모리: 파일크기 × 2.5배
  - 예: 100MB 파일 → 250MB 메모리 필요

transformers:
  - 방식: 30초 세그먼트 단위 처리
  - 장점: 📊 일정한 메모리 사용
  - 필요 메모리: ~3GB (세그먼트 단위)
  - 장점: 대용량 파일도 안정적 처리
```

### 자동 선택 로직

```
1️⃣ 사용 가능한 메모리 확인
   ↓
2️⃣ faster-whisper 필요 메모리 < 사용가능 메모리?
   ✅ YES → faster-whisper 선택 (⚡ 최고 속도)
   ❌ NO  → 다음 단계
   ↓
3️⃣ transformers 필요 메모리 < 사용가능 메모리?
   ✅ YES → transformers 선택 (📊 메모리 효율)
   ❌ NO  → transformers (필수, 제약적)
```

---

## 📊 응답 구조: backend_recommendation

### 성공 응답 예시

```json
{
  "success": true,
  "text": "인식된 텍스트...",
  "backend": "faster-whisper",
  "backend_recommendation": {
    "recommended": "faster-whisper",
    "reason": "파일 45.3MB, 필요메모리 113.2MB, 사용가능 11079MB → faster-whisper (⚡ 최고 속도)",
    "current": "faster-whisper",
    "is_optimal": true,
    "alternatives": [],
    "memory_check": {
      "file_size_mb": 45.3,
      "available_mb": 11079,
      "faster_whisper_required_mb": 113.2,
      "transformers_required_mb": 3000
    }
  },
  "file_size_mb": 45.3,
  "processing_time_seconds": 8.5,
  "memory_info": {
    "available_mb": 11079,
    "used_percent": 28.8
  }
}
```

---

## ⚠️ 에러 응답 구조: failure_reason

### 메모리 부족 에러 예시

```json
{
  "success": false,
  "error": "CUDA out of memory: tried to allocate 512.0 MB",
  "error_type": "cuda_out_of_memory",
  "backend": "faster-whisper",
  "file_size_mb": 500.5,
  "processing_time_seconds": 2.3,
  "memory_info": {
    "available_mb": 1024,
    "used_percent": 75.2
  },
  "failure_reason": {
    "error_type": "cuda_out_of_memory",
    "description": "CUDA out of memory: tried to allocate 512.0 MB",
    "suggestion": "메모리 부족. transformers 백엔드로 전환해보세요 (세그먼트 기반 처리)",
    "available_memory_mb": 1024,
    "try_next": {
      "current_backend": "faster-whisper",
      "recommended_backend": "transformers",
      "curl_command": "curl -X POST http://localhost:8003/transcribe -F 'file_path=/app/audio/samples/large_file.wav'"
    }
  }
}
```

### 파일 오류 예시

```json
{
  "success": false,
  "error": "File not found: /app/audio/samples/nonexistent.wav",
  "error_type": "file_not_found",
  "file_path": "/app/audio/samples/nonexistent.wav",
  "failure_reason": {
    "error_type": "file_not_found",
    "description": "File not found: /app/audio/samples/nonexistent.wav",
    "suggestion": "파일을 찾을 수 없습니다. 파일 경로를 확인하고 /app 디렉토리 내에 있는지 확인하세요",
    "available_memory_mb": 11079,
    "try_next": {
      "current_backend": "faster-whisper",
      "recommended_backend": "faster-whisper",
      "curl_command": "파일 경로를 확인하고 다시 시도하세요"
    }
  }
}
```

---

## 🔄 실패 시 대응 방법

### 1. 메모리 부족 오류

```bash
# 현재 상태 확인
curl http://localhost:8003/health | jq '.memory'

# transformers로 재시도
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/large_file.wav' \
  -F 'is_stream=true'  # 스트리밍 모드 활성화 (안정성 향상)
```

**권장사항:**
- transformers 백엔드는 내부적으로 30초 세그먼트 처리
- 스트리밍 모드(`is_stream=true`) 사용 권장
- 더 많은 메모리 할당이 필요하면 서버 메모리 증설

### 2. CUDA/GPU 오류

```bash
# CPU 모드로 실행 (Docker 컨테이너 재시작 필요)
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -e STT_DEVICE=cpu \
  -v $(pwd)/audio/samples:/app/audio/samples \
  -v $(pwd)/models:/app/models \
  stt-engine:latest
```

**권장사항:**
- GPU 메모리 부족 시 CPU 모드로 전환
- `STT_COMPUTE_TYPE=int8` 사용 (정량화, 메모리 절감)

### 3. 파일 오류

```bash
# 파일 확인
ls -lh /app/audio/samples/test.wav

# 파일 경로 검증
curl http://localhost:8003/health | jq .

# 올바른 경로로 재시도
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test.wav'
```

---

## 📈 성능 최적화 팁

### 파일 크기별 권장사항

| 파일 크기 | 권장 백엔드 | 메모리 | 처리시간 |
|----------|-----------|--------|----------|
| < 100MB | faster-whisper | 250MB | ⚡ 5-15초 |
| 100MB - 500MB | faster-whisper (충분한 메모리) | 1-1.5GB | 15-45초 |
| 500MB - 1GB | transformers | 3GB | 45-120초 |
| > 1GB | transformers (필수) | 3GB | 120초+ |

### 메모리 효율화

```bash
# 1. 메모리 확인
curl http://localhost:8003/health | jq '.memory'

# 2. 백엔드 추천 확인 (API 응답에서 backend_recommendation 참조)
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test.wav' | jq '.backend_recommendation'

# 3. 추천 백엔드가 현재 백엔드와 다르면 변경
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"backend": "transformers"}'
```

---

## 🔧 고급 설정

### 백엔드 수동 전환

```bash
# 현재 백엔드 확인
curl http://localhost:8003/backend/current | jq

# faster-whisper로 변경
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"backend": "faster-whisper"}'

# transformers로 변경
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"backend": "transformers"}'

# openai-whisper로 변경
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"backend": "openai-whisper"}'
```

### 메모리 제약이 있는 환경

```bash
# 1. Docker 실행 시 메모리 제한 설정
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -m 4g \  # 메모리 제한: 4GB
  -e STT_DEVICE=cpu \
  -e STT_COMPUTE_TYPE=int8 \
  -v $(pwd)/audio/samples:/app/audio/samples \
  -v $(pwd)/models:/app/models \
  stt-engine:latest

# 2. transformers 백엔드 권장 (세그먼트 처리)
curl -X POST http://localhost:8003/backend/reload \
  -H "Content-Type: application/json" \
  -d '{"backend": "transformers"}'

# 3. 스트리밍 모드 사용
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/samples/test.wav' \
  -F 'is_stream=true'
```

---

## ✅ 체크리스트

- [ ] API 응답의 `backend_recommendation` 필드 확인
- [ ] 메모리 부족 에러 발생 시 `failure_reason` 참조
- [ ] 제안된 `try_next` 명령으로 재시도
- [ ] 필요시 백엔드 수동 전환
- [ ] 메모리 상태 모니터링
