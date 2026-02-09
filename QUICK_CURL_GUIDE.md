# 간단 curl 명령어 가이드

## 🚀 빠른 시작

### 1️⃣ 파일 준비 (한 번만)
```bash
# 파일 경로가 길면 단축하기
cp audio/samples/door_to_door_sales/1_Recording_20240712_140513_01041968444.wav /tmp/test.wav

# 또는 짧은 샘플 사용
ls audio/samples/*.wav | head -1 | xargs -I {} cp {} /tmp/test.wav
```

### 2️⃣ API 호출 (단순)
```bash
# 기본 호출 (자동 백엔드 선택)
curl -X POST http://localhost:8003/transcribe -F 'file=@/tmp/test.wav'
```

### 3️⃣ 응답 보기 (보기 좋게)
```bash
# JSON으로 포맷팅
curl -X POST http://localhost:8003/transcribe -F 'file=@/tmp/test.wav' | python3 -m json.tool
```

---

## 📋 자주 쓸 명령어

### 특정 백엔드 지정
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

### 언어 지정
```bash
# 한국어로 지정
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' \
  -F 'language=ko'

# 영어로 지정
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' \
  -F 'language=en'
```

### 백엔드 + 언어 함께 지정
```bash
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' \
  -F 'backend=faster-whisper' \
  -F 'language=ko'
```

---

## 🔍 로그 보기

### 실시간 로그 보기
```bash
# Docker 로그 실시간
docker logs -f stt-engine

# 마지막 50줄만
docker logs stt-engine | tail -50

# 특정 키워드만
docker logs stt-engine | grep "faster-whisper\|ERROR\|✅"
```

### 한 줄 요약 (성공/실패 확인)
```bash
curl -s -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' | grep -o '"success":[^,]*' || echo "오류 발생"
```

---

## ⚡ 원라이너 (복사해서 바로 실행)

### 기본 테스트
```bash
cp audio/samples/door_to_door_sales/1_Recording_20240712_140513_01041968444.wav /tmp/t.wav && curl -X POST http://localhost:8003/transcribe -F 'file=@/tmp/t.wav' | python3 -m json.tool
```

### faster-whisper 테스트
```bash
cp audio/samples/short_0.5s.wav /tmp/t.wav && curl -X POST http://localhost:8003/transcribe -F 'file=@/tmp/t.wav' -F 'backend=faster-whisper' | python3 -m json.tool
```

### 로그와 함께
```bash
(curl -s -X POST http://localhost:8003/transcribe -F 'file=@/tmp/test.wav' | python3 -m json.tool) && echo "\n=== 로그 ===" && docker logs stt-engine | tail -20
```

---

## 🎯 자동 테스트 스크립트

```bash
#!/bin/bash

# 파일 준비
cp audio/samples/door_to_door_sales/1_Recording_20240712_140513_01041968444.wav /tmp/test.wav

echo "=== 백엔드 자동 선택 ==="
curl -X POST http://localhost:8003/transcribe -F 'file=@/tmp/test.wav' | python3 -m json.tool

echo -e "\n=== faster-whisper ==="
curl -X POST http://localhost:8003/transcribe -F 'file=@/tmp/test.wav' -F 'backend=faster-whisper' | python3 -m json.tool

echo -e "\n=== transformers ==="
curl -X POST http://localhost:8003/transcribe -F 'file=@/tmp/test.wav' -F 'backend=transformers' | python3 -m json.tool

echo -e "\n=== openai-whisper ==="
curl -X POST http://localhost:8003/transcribe -F 'file=@/tmp/test.wav' -F 'backend=openai-whisper' | python3 -m json.tool
```

저장: `test_all_backends.sh`
실행: `bash test_all_backends.sh`

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

### ❌ 오류 응답
```json
{
  "success": false,
  "error": "오류 메시지",
  "error_type": "FileNotFoundError",
  "backend": "faster-whisper",
  "file_size_mb": 0.05
}
```

---

## 🔧 문제 해결

| 문제 | 해결 방법 |
|------|---------|
| "read function returned funny value" | `/tmp/test.wav` 같이 짧은 경로 사용 |
| 요청한 백엔드를 사용할 수 없음 | 지원하는 백엔드인지 확인: `faster-whisper`, `transformers`, `openai-whisper` |
| 로그가 안 보임 | `docker logs stt-engine` 확인 또는 컨테이너 재시작 |
| 느린 응답 | CPU 모드인지 확인, `-e STT_DEVICE=cuda` 사용 |

---

## ✨ 팁

1. **자주 쓰는 명령어 단축키 설정**
   ```bash
   # ~/.bashrc 또는 ~/.zshrc에 추가
   alias stt='curl -X POST http://localhost:8003/transcribe -F file=@/tmp/test.wav'
   
   # 사용: stt | python3 -m json.tool
   ```

2. **파일 자동 복사 함수**
   ```bash
   stt_test() {
     cp "audio/samples/door_to_door_sales/1_Recording_20240712_140513_01041968444.wav" /tmp/test.wav
     curl -X POST http://localhost:8003/transcribe -F 'file=@/tmp/test.wav' | python3 -m json.tool
   }
   
   # 사용: stt_test
   ```

3. **전체 테스트 결과 저장**
   ```bash
   curl -s -X POST http://localhost:8003/transcribe -F 'file=@/tmp/test.wav' | python3 -m json.tool > result.json
   ```
