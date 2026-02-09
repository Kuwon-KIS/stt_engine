# STT API 테스트 명령어 (curl)

## 📋 문제점

이전 curl 명령어가 작동하지 않았습니다:
```bash
# ❌ 이 명령어는 작동 안 함 (파일 경로가 너무 길어서 curl이 처리 불가)
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@audio/samples/door_to_door_sales/1_Recording_20240712_140513_01041968444.wav'
```

**원인**: 파일 이름이 너무 길어서 curl의 경로 처리가 실패함

---

## ✅ 해결 방법

### 1️⃣ 파일을 임시 디렉토리로 복사하고 짧은 이름으로 rename

```bash
# EC2에서 실행
cp "audio/samples/door_to_door_sales/1_Recording_20240712_140513_01041968444.wav" /tmp/test.wav

# 그 다음 curl 실행
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav'
```

### 2️⃣ 절대 경로를 사용하되 이스케이프 처리

```bash
curl -X POST http://localhost:8003/transcribe \
  -F "file=@$(pwd)/audio/samples/door_to_door_sales/1_Recording_20240712_140513_01041968444.wav"
```

### 3️⃣ 다른 샘플 파일이 있으면 사용 (추천)

```bash
# 먼저 사용 가능한 파일 확인
ls -lh audio/samples/

# 짧은 이름의 파일 사용
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@audio/samples/short_0.5s.wav'
```

### 4️⃣ 상세 로깅과 함께 테스트 (추천)

```bash
# 임시 파일로 복사
cp "audio/samples/door_to_door_sales/1_Recording_20240712_140513_01041968444.wav" /tmp/test.wav

# curl 테스트 (상세 응답 포함)
echo "=== STT API 테스트 ===" && \
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' \
  -H "Accept: application/json" | python3 -m json.tool

# 컨테이너 로그 확인
docker logs stt-engine | tail -100
```

---

## 🔍 로깅 개선사항

최신 코드에는 다음과 같은 상세 로깅이 추가되었습니다:

### api_server.py
```
[API] 음성 파일 업로드 요청: test.wav
[API] 파일 크기: 0.05MB, 임시 경로: /tmp/tmpXXXXXX.wav
✓ 파일 검증 완료 (길이: 3.5초)
✓ 메모리 확인 완료 (사용 가능: 1024MB)
[API] STT 처리 시작 (파일: test.wav, 길이: 3.5초, 언어: None)
→ faster-whisper 백엔드로 변환 시작
[faster-whisper] 변환 시작 (파일: test.wav)
✓ faster-whisper 변환 완료
  결과: 128 글자, 언어: ko
[API] STT 처리 완료 - 백엔드: faster-whisper, 성공: True
[API] ✅ STT 처리 성공 - 텍스트: 128 글자
```

### stt_engine.py에서 백엔드별 상세 로깅
```
📂 음성 파일 로드 시작: test.wav
✓ 파일 존재 확인: /tmp/tmpXXXXXX.wav
🔧 사용 중인 백엔드: WhisperModel
→ faster-whisper 백엔드로 변환 시작
[faster-whisper] 변환 시작 (파일: test.wav)
[faster-whisper] 모델 설정: beam_size=5, best_of=5, ...
✓ faster-whisper 변환 완료
  결과: 128 글자, 언어: ko
```

---

## 📊 응답 형식

### ✅ 성공 응답
```json
{
  "success": true,
  "text": "인식된 텍스트 내용",
  "language": "ko",
  "duration": 3.5,
  "backend": "faster-whisper",
  "file_size_mb": 0.05,
  "segments_processed": 1,
  "memory_info": {
    "available_mb": 1024,
    "used_percent": 50.5
  }
}
```

### ❌ 오류 응답
```json
{
  "success": false,
  "error": "오류 메시지",
  "error_type": "FileNotFoundError",
  "backend": "faster-whisper",
  "file_size_mb": 0.05,
  "memory_info": {...},
  "segment_failed": null,
  "partial_text": "",
  "suggestion": "권장 조치 사항"
}
```

---

## 🐳 Docker에서 테스트

### 컨테이너 실행
```bash
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/models:/app/models \
  stt-engine:cuda129-rhel89-v1.5
```

### 테스트 파일 준비 및 실행
```bash
# 1. 컨테이너 내부에 파일 복사
docker exec stt-engine cp /app/audio/samples/door_to_door_sales/1_Recording_20240712_140513_01041968444.wav /tmp/test.wav

# 2. curl로 테스트
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav'

# 3. 로그 확인
docker logs -f stt-engine
```

---

## 🔧 트러블슈팅

### 문제: "read function returned funny value"
**원인**: 파일 경로 처리 오류
**해결**: `/tmp/test.wav`처럼 짧은 경로 사용

### 문제: 로그 메시지가 안 보임
**해결**: 
```bash
# 컨테이너 로그 확인 (실시간)
docker logs -f stt-engine

# 또는 api_server.py의 logging.basicConfig level을 DEBUG로 변경
```

### 문제: 파일 업로드 실패
**해결**: 먼저 파일 존재 확인
```bash
ls -lh audio/samples/short_0.5s.wav
```
