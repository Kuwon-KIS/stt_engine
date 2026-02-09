# 로깅 개선사항 및 디버깅 가이드

## 📝 요약

이전 대화에서 로깅 강화를 약속했으나 적용되지 않았던 문제를 해결했습니다.

**적용된 개선사항:**
1. ✅ `stt_engine.py`의 모든 메서드에 상세 로깅 추가
2. ✅ `api_server.py`의 `/transcribe` 엔드포인트에 포괄적인 에러 핸들링 추가
3. ✅ 모든 예외에 `exc_info=True`로 스택 트레이스 캡처
4. ✅ 응답에 `error_type` 필드 추가로 오류 진단 개선

---

## 🔍 로깅 구조

### 레벨별 로그

| 레벨 | 사용 사례 | 예시 |
|------|---------|------|
| `logger.info()` | 주요 작업 완료 | `✓ 파일 검증 완료` |
| `logger.debug()` | 중간 단계 정보 | `[transformers] 세그먼트 {idx} 처리 중...` |
| `logger.warning()` | 주의할 사항 | `⚠️ 토크나이저 파일 없음` |
| `logger.error()` | 오류 발생 | `❌ 파일 검증 실패: {error}` |

### stt_engine.py 로깅 흐름

```
📂 음성 파일 로드 시작: test.wav
  ├─ ✓ 파일 존재 확인
  ├─ 🔧 사용 중인 백엔드: WhisperModel
  ├─ → faster-whisper 백엔드로 변환 시작
  │   ├─ [faster-whisper] 변환 시작 (파일: test.wav)
  │   ├─ [faster-whisper] 모델 설정: beam_size=5, best_of=5
  │   ├─ ✓ faster-whisper 변환 완료
  │   └─ 결과: 128 글자, 언어: ko
  └─ ✅ 정상 완료
```

### api_server.py 로깅 흐름

```
[API] 음성 파일 업로드 요청: test.wav
  ├─ [API] 파일 크기: 0.05MB, 임시 경로: /tmp/tmpXXXXXX.wav
  ├─ ✓ 파일 검증 완료 (길이: 3.5초)
  ├─ ✓ 메모리 확인 완료 (사용 가능: 1024MB)
  ├─ [API] STT 처리 시작 (파일: test.wav, 길이: 3.5초, 언어: None)
  ├─ [API] STT 처리 완료 - 백엔드: faster-whisper, 성공: True
  ├─ [API] ✅ STT 처리 성공 - 텍스트: 128 글자
  └─ [API] 임시 파일 삭제: /tmp/tmpXXXXXX.wav
```

---

## 🚀 사용 방법

### 1. EC2에서 Docker 실행

```bash
# 최신 코드를 EC2로 푸시
cd /Users/a113211/workspace/stt_engine
git push origin main

# EC2에서 당길 기
ssh ec2-user@<EC2_IP>
cd ~/stt_engine
git pull origin main
docker build -t stt-engine:v1.5 -f docker/Dockerfile.engine.rhel89 .
docker run -d --name stt-engine -p 8003:8003 \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/models:/app/models \
  stt-engine:v1.5
```

### 2. API 테스트

#### 방법 A: 짧은 이름의 파일 사용 (추천)

```bash
# 파일 복사
cp "audio/samples/door_to_door_sales/1_Recording_20240712_140513_01041968444.wav" /tmp/test.wav

# API 호출
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' \
  -H "Accept: application/json" | python3 -m json.tool
```

#### 방법 B: 기존 샘플 파일 사용

```bash
# 사용 가능한 샘플 확인
ls -lh audio/samples/

# 짧은 이름의 파일 사용
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@audio/samples/short_0.5s.wav'
```

### 3. 로그 확인

#### 실시간 로그 모니터링

```bash
# 컨테이너 로그 실시간 확인
docker logs -f stt-engine

# 또는 호스트에서 로그 확인 (컨테이너 내 /app/logs 디렉토리 마운트 시)
tail -f logs/stt_engine.log
```

#### 특정 단계별 로그 필터

```bash
# 파일 검증 관련 로그만
docker logs stt-engine | grep "파일 검증"

# 에러만
docker logs stt-engine | grep "❌\|ERROR"

# 특정 백엔드 관련
docker logs stt-engine | grep "\[faster-whisper\]\|\[transformers\]\|\[openai-whisper\]"

# 메모리 관련
docker logs stt-engine | grep "메모리"
```

---

## 📊 응답 형식

### ✅ 성공 응답

```json
{
  "success": true,
  "text": "인식된 텍스트...",
  "language": "ko",
  "duration": 3.5,
  "backend": "faster-whisper",
  "file_size_mb": 0.05,
  "segments_processed": 1,
  "memory_info": {
    "available_mb": 1024.5,
    "used_percent": 50.2
  }
}
```

### ❌ 오류 응답 (파일 검증 실패)

```json
{
  "success": false,
  "error": "파일 검증 실패",
  "error_type": "FileValidationError",
  "message": "파일 형식을 알 수 없음",
  "file_size_mb": 0.05
}
```

### ❌ 오류 응답 (STT 처리 중 오류)

```json
{
  "success": false,
  "error": "transformers transcription failed: 오디오 로드 실패 - ModuleNotFoundError: No module named 'pkg_resources'",
  "error_type": "ModuleNotFoundError",
  "backend": "transformers",
  "segment_failed": 2,
  "partial_text": "첫 번째와 두 번째 세그먼트는 변환됨...",
  "suggestion": "CPU 모드로 전환하거나 -e STT_DEVICE=cpu 사용"
}
```

---

## 🔧 커밋 정보

최신 커밋:
- **Hash**: 972d7a9
- **메시지**: "Refactor: Enhance logging for debug in stt_engine and api_server"
- **변경사항**:
  - stt_engine.py: 모든 transcribe 메서드에 logger 추가
  - api_server.py: /transcribe 엔드포인트 에러 핸들링 개선
  - 모든 예외에 exc_info=True로 스택 트레이스 캡처
  - 응답에 error_type 필드 추가

---

## 📋 다음 단계

1. **EC2에 배포**
   ```bash
   git push origin main
   # EC2에서: git pull && docker build && docker run
   ```

2. **테스트 실행**
   ```bash
   curl -X POST http://localhost:8003/transcribe -F 'file=@/tmp/test.wav'
   docker logs stt-engine | tail -50
   ```

3. **로그 분석**
   - 모든 단계의 로그를 확인하여 어디서 실패하는지 파악
   - error_type 필드로 오류 유형 확인
   - partial_text로 부분 성공 여부 확인

---

## ⚠️ 주의사항

1. **파일 경로 길이**: curl에서 파일 경로가 너무 길면 처리 실패 가능
   - 해결: `/tmp/test.wav` 같은 짧은 경로 사용

2. **로그 드라이버 설정**: Docker 로그가 안 보인다면
   ```bash
   docker logs stt-engine --tail 100
   # 또는
   docker exec stt-engine tail -100 /app/logs/stt_engine.log
   ```

3. **메모리 이슈**: transformers 백엔드 사용 시 약 4GB 필요
   - 확인: docker logs에서 "메모리 부족" 메시지

4. **디버그 모드**: DEBUG 레벨 로그 보려면
   ```python
   # api_server.py 상단
   logging.basicConfig(level=logging.DEBUG)  # INFO에서 DEBUG로 변경
   ```

---

## 📞 문제 해결

### Q: 로그 메시지가 안 보이는데?
**A**: 
```bash
# 1. 컨테이너가 실행 중인지 확인
docker ps | grep stt-engine

# 2. 로그 확인
docker logs stt-engine

# 3. 로그가 여전히 안 보이면 컨테이너 재시작
docker restart stt-engine
```

### Q: "read function returned funny value" 에러가 계속 발생하면?
**A**: 파일 경로 문제. 다음 방법 시도:
```bash
# 방법 1: 절대 경로 사용
curl -X POST http://localhost:8003/transcribe \
  -F "file=@$(pwd)/audio/samples/short_0.5s.wav"

# 방법 2: 파일 이름 단축
cp audio/samples/door_to_door_sales/1_Recording_20240712_140513_01041968444.wav /tmp/t.wav
curl -X POST http://localhost:8003/transcribe -F 'file=@/tmp/t.wav'
```

### Q: transformers 백엔드에서 "ModuleNotFoundError: pkg_resources"?
**A**: 이는 Dockerfile의 setuptools 설치 문제. 최신 코드에서는 `--force-reinstall setuptools` 사용.
```bash
# 컨테이너 재빌드 필요
docker build -t stt-engine:v1.5 -f docker/Dockerfile.engine.rhel89 .
```
