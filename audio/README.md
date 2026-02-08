# 샘플 오디오 파일

이 디렉토리에는 STT Engine 테스트용 샘플 오디오 파일들이 있습니다.

## 파일 목록

| 파일명 | 길이 | 크기 | 설명 |
|--------|------|------|------|
| `short_0.5s.wav` | 0.5초 | 16KB | 짧은 오디오 테스트 |
| `medium_3s.wav` | 3초 | 94KB | 중간 길이 오디오 테스트 |
| `long_10s.wav` | 10초 | 313KB | 긴 오디오 테스트 |

## 파일 스펙

- **형식**: WAV (WAVE audio, Microsoft PCM)
- **비트율**: 16비트
- **샘플링 레이트**: 16000 Hz
- **채널**: Mono (1채널)
- **신호**: 음성 유사 신호 (다중 주파수 포먼트 + 시간 envelope)

## 사용 방법

### 1. 모델 다운로드 중 검증
```bash
python download_model_hf.py --skip-test  # 스킵
python download_model_hf.py              # 샘플로 검증 (기본값)
```

### 2. Docker 컨테이너에서 테스트
```bash
# 컨테이너 실행 (샘플 오디오 마운트)
docker run -it \
  -p 8003:8003 \
  -v $(pwd)/audio/samples:/app/audio/samples \
  -v $(pwd)/models:/app/models \
  stt-engine:latest

# 다른 터미널에서 API 테스트
curl -X POST http://localhost:8003/transcribe \
  -F "file=@audio/samples/short_0.5s.wav"

curl -X POST http://localhost:8003/transcribe \
  -F "file=@audio/samples/medium_3s.wav"

curl -X POST http://localhost:8003/transcribe \
  -F "file=@audio/samples/long_10s.wav"
```

### 3. Python에서 직접 테스트
```python
from faster_whisper import WhisperModel
import os

model = WhisperModel("path/to/ctranslate2_model", device="cpu", compute_type="float32")

# 샘플 오디오 테스트
audio_file = "audio/samples/short_0.5s.wav"
segments, info = model.transcribe(audio_file, language="ko")

for segment in segments:
    print(segment.text)
```

## 샘플 파일 다시 생성하기

샘플 파일이 없거나 손상된 경우, 다시 생성할 수 있습니다:

```bash
python generate_sample_audio.py
```

이 명령은 `audio/samples/` 디렉토리에 3개의 wav 파일을 생성합니다.

## 주의사항

- 이 샘플 파일들은 **음성이 아닌 합성 신호**입니다
- 다중 주파수 포먼트(200-300Hz, 500-900Hz, 1900-2500Hz)로 음성과 유사한 특성을 가집니다
- 모델의 동작 여부만 확인하는 용도입니다
- 실제 음성 인식 성능은 실제 음성 파일로 테스트하세요

## 실제 음성 파일 사용

실제 음성으로 테스트하려면:

```bash
# 자신의 음성 파일 사용
curl -X POST http://localhost:8003/transcribe \
  -F "file=@your_audio.wav"

# 또는 마이크 녹음 (예: 5초)
ffmpeg -f avfoundation -i ":0" -t 5 -acodec pcm_s16le -ar 16000 -ac 1 my_voice.wav
curl -X POST http://localhost:8003/transcribe \
  -F "file=@my_voice.wav"
```

## 음성 파일 변환

다른 형식의 음성 파일을 WAV로 변환:

```bash
# MP3 → WAV
ffmpeg -i audio.mp3 -acodec pcm_s16le -ar 16000 -ac 1 audio.wav

# M4A → WAV
ffmpeg -i audio.m4a -acodec pcm_s16le -ar 16000 -ac 1 audio.wav

# WebM → WAV
ffmpeg -i audio.webm -acodec pcm_s16le -ar 16000 -ac 1 audio.wav
```
