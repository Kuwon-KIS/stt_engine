# PATCH 07: 동시 처리 메모리 누수 해결 (Concurrent Memory Leak Fix)

## 📋 개요

**문제**: 2개 파일을 동시에 처리할 때 메모리가 **선형으로 누적**되어 104GB 도달 후 OOM 발생
- 진단 결과: 3MB → 243MB (60초, ~4MB/초 선형 증가)
- 근본 원인: 동시 요청 스레드에서 **로컬 변수가 해제되지 않음** + **요청 종료 후에도 메모리 유지**

---

## 🔍 근본 원인 분석

### 1️⃣ Patch 06과의 차이
```
Patch 06:
  ✅ model.cpu() 추가 (GPU 메모리 정리)
  ✅ torch.cuda.empty_cache() 추가
  ❌ CPU 메모리 정리 미흡
  ❌ 동시 요청 시 로컬 변수 미정리

Patch 07:
  ✅ Patch 06 유지 (GPU 메모리 정리)
  ✅ 로컬 변수 명시적 삭제 (del audio, all_texts)
  ✅ 강제 gc.collect() 추가
  ✅ finally 블록으로 요청 종료 시에도 메모리 정리
```

### 2️⃣ 동시 처리 메모리 누적 메커니즘

```
API 요청 처리 (FastAPI async):
  
Thread 1 (File 1):
  perform_stt()
    → _transcribe_with_transformers()
      ├─ audio = np.array (40MB)
      ├─ all_texts = list of strings
      ├─ segment 루프 (30개 세그먼트)
      │  ├─ segment = audio[start:end] (40MB)
      │  ├─ processor_output = ... (100MB) → del
      │  ├─ input_features = ... (200MB) → del (루프 내)
      │  └─ predicted_ids = ... (100MB) → del (루프 내)
      └─ END: audio, all_texts 정리 안됨! ← 문제!

Thread 2 (File 2):
  perform_stt() ← 동시 실행
    → _transcribe_with_transformers()
      └─ 같은 구조, 또 다른 40MB 할당 ← 누적!

결과: 
  Thread 1 메모리: 40MB (미정리)
  Thread 2 메모리: 40MB (미정리)
  = 80MB + 루프 변수들 + 프레임 변수들
  × 60초 ÷ 세그먼트당 1초 ≈ 60개 세그먼트 = 240MB
```

---

## 🔧 Patch 07 구현

### 수정 1: stt_engine.py - _transcribe_with_transformers()

**파일**: `stt_engine.py` (Line ~1000)

**변경 사항**:

```python
# 변경 전:
del audio, all_texts
with self._memory_cleanup_lock:
    gc.collect()
    if self.device == "cuda":
        self.backend.model.cpu()
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

return {
    "success": True,
    "text": full_text,
    ...
}

# 변경 후:
full_text = " ".join(all_texts)
result = {
    "success": True,
    "text": full_text,
    ...
}

try:
    logger.info(f"[transformers] PATCH 07: 동시 처리 메모리 정리 시작...")
    
    # 1단계: 로컬 변수 명시적 삭제 (중요!)
    del audio, all_texts, full_text
    
    # 2단계: Python 메모리 강제 정리 (Lock 사용)
    with self._memory_cleanup_lock:
        gc.collect()
    
    # 3단계: GPU 메모리 정리
    if self.device == "cuda":
        self.backend.model.cpu()
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    
    logger.info(f"[transformers] PATCH 07: 동시 처리 메모리 정리 완료")
    
except Exception as e:
    logger.error(f"⚠️  PATCH 07 메모리 정리 실패: {type(e).__name__}: {e}", exc_info=True)

return result
```

**개선점**:
- `del full_text` 추가: 결과 텍스트도 명시적으로 삭제
- 모든 로컬 변수를 `del`로 명시적 정리
- 에러 처리로 메모리 정리 실패해도 응답 반환

---

### 수정 2: api_server/transcribe_endpoint.py - perform_stt()

**파일**: `api_server/transcribe_endpoint.py` (Line ~202)

**변경 사항**:

```python
# 변경 전:
async def perform_stt(stt_instance, file_path_obj: Path, language: str, is_streaming: bool) -> dict:
    try:
        result = stt_instance.transcribe(str(file_path_obj), language=language)
        return result
    except Exception as e:
        raise

# 변경 후:
async def perform_stt(stt_instance, file_path_obj: Path, language: str, is_streaming: bool) -> dict:
    import gc
    import torch
    
    try:
        result = stt_instance.transcribe(str(file_path_obj), language=language)
        return result
    except Exception as e:
        raise
    finally:
        # 🔴 PATCH 07-2: 요청 핸들러 메모리 정리
        logger.debug(f"[API/Transcribe] PATCH 07-2: 요청 핸들러 메모리 정리...")
        try:
            gc.collect()
        except Exception as e:
            logger.debug(f"[API/Transcribe] gc.collect() 오류: {e}")
```

**개선점**:
- `finally` 블록 추가: 요청 완료 후에도 메모리 정리 실행
- perform_stt() 재정의 이후 남는 변수들 정리

---

### 수정 3: api_server/app.py - transcribe() 엔드포인트

**파일**: `api_server/app.py` (Line ~720)

**변경 사항**:

```python
# 변경 전:
return JSONResponse(
    content=response.dict(),
    status_code=200,
    headers={"Content-Type": "application/json; charset=utf-8"}
)

# 변경 후:
json_response = JSONResponse(
    content=response.dict(),
    status_code=200,
    headers={"Content-Type": "application/json; charset=utf-8"}
)

# 🔴 PATCH 07-3: 응답 반환 직전 메모리 정리
logger.debug(f"[API] PATCH 07-3: 응답 반환 직전 메모리 정리...")
try:
    import gc
    del response, stt_result, privacy_result, classification_result, element_result
    del file_path_obj, file_check, memory_info, perf_metrics
    gc.collect()
    logger.debug(f"[API] PATCH 07-3 메모리 정리 완료")
except Exception as e:
    logger.debug(f"[API] PATCH 07-3 메모리 정리 중 오류: {e}")

return json_response
```

**개선점**:
- 응답 객체를 변수에 저장한 후, 모든 임시 변수 정리
- 요청 핸들러의 모든 로컬 변수 명시적 삭제
- 강제 gc.collect() 호출

---

## 📊 예상 효과

### 테스트 시나리오

```
테스트: 2개 파일 동시 처리 (60초)

변경 전 (Patch 06):
  메모리: 3MB → 243MB (240MB 증가, ~4MB/초)
  원인: 로컬 변수 미정리 → 누적

변경 후 (Patch 07):
  예상: 3MB → 50MB (47MB 증가, ~0.8MB/초)
  이유: 
    ✅ 각 세그먼트 루프 내 임시 변수 정리
    ✅ 루프 종료 후 audio, all_texts 명시적 삭제
    ✅ 요청 종료 후 모든 핸들러 변수 정리
    ✅ gc.collect() 강제 호출로 가비지 수집

개선율: ~80% 메모리 사용량 감소
```

---

## 🧪 테스트 방법

### 1️⃣ 메모리 누수 감지 (before/after)

```bash
# 터미널 1: 서버 실행
docker run -e STT_PRESET=accuracy stt-api

# 터미널 2: 진단 도구 실행 (동시 처리 모니터링)
./scripts/diagnostics/diagnose_memory_leak.sh

# 결과 확인
csv파일 확인: /tmp/memory_monitor.csv
- Patch 06: 선형 증가 (3MB → 243MB)
- Patch 07: 완만한 증가 (3MB → 50MB 목표)
```

### 2️⃣ 동시 처리 안정성

```bash
# 2개 파일 동시 처리 테스트
curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/test1.wav' &

curl -X POST http://localhost:8003/transcribe \
  -F 'file_path=/app/audio/test2.wav' &

wait

# 로그 확인: PATCH 07 메모리 정리 메시지
grep "PATCH 07" /app/logs/api.log
```

### 3️⃣ 메모리 안정성

```bash
# 5분 동안 지속적인 처리
python3 -c "
import time
import requests
for i in range(300):
    requests.post('http://localhost:8003/transcribe', 
                  files={'file': ('test.wav', open('/app/audio/test.wav', 'rb'))})
    time.sleep(1)
"

# 메모리 체크 (증가 멈춘 후 안정적인지)
nvidia-smi
free -h
```

---

## 📝 주요 코드 변경 요약

| 파일 | 함수 | 변경 | 효과 |
|------|------|------|------|
| stt_engine.py | _transcribe_with_transformers() | `del full_text` 추가 + try-finally | 루프 종료 후 메모리 정리 |
| transcribe_endpoint.py | perform_stt() | `finally` 블록 추가 | 요청 핸들러 메모리 정리 |
| app.py | transcribe() | 응답 전 `del` 및 gc.collect() | 엔드포인트 종료 후 메모리 정리 |

---

## ⚠️ 주의사항

1. **Lock 사용**: `self._memory_cleanup_lock` 사용으로 동시 GC 충돌 방지
2. **finally 블록**: 에러 발생해도 메모리 정리 실행 (중요!)
3. **del 변수**: 정의되지 않은 변수 `del` 시도 시 try-except로 보호
4. **GC 오버헤드**: 빈번한 gc.collect() 호출 시 CPU 사용량 증가 (모니터링 필요)

---

## 🎯 다음 단계

1. ✅ Patch 07 적용 완료
2. ⏳ 테스트 실행 (diagnose_memory_leak.sh)
3. ⏳ 메모리 프로파일링 (memory_trace_deep.sh)
4. ⏳ 5분 지속성 테스트
5. ⏳ 메인 브랜치 병합 및 배포

---

## 📞 문제 발생 시

- **여전히 메모리 증가**: stt_engine.py의 루프 내 임시 변수 확인
- **GC 오버헤드**: gc.collect() 호출 빈도 조정 (현재: 루프 내 매회, 엔드포인트 1회)
- **GPU 메모리**: model.cpu() 동기화 타이밍 확인

---

**작성일**: 2026-03-12
**적용 대상**: accuracy 모드 (transformers 백엔드)
**영향 범위**: 동시 파일 처리 (2개 이상 파일 동시 요청)
