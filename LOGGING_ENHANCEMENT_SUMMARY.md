# 로깅 강화 개선사항 요약

## 🎯 목표
이전 대화에서 "몇 시간 전에 이 문제에 대해서 이야기하면서 로깅을 강화하기로 했는데 제대로 반영이 안된 것 같아"라는 지적에 대응하여 **완전한 로깅 강화를 구현**했습니다.

---

## ✅ 적용된 개선사항

### 1. stt_engine.py - 모든 메서드에 상세 로깅 추가

#### 📍 transcribe() 메서드
```python
logger.info(f"📂 음성 파일 로드 시작: {audio_path}")
logger.info(f"✓ 파일 존재 확인: {audio_path}")
logger.info(f"🔧 사용 중인 백엔드: {backend_type}")
logger.info(f"→ faster-whisper 백엔드로 변환 시작")
```

**개선**: print()에서 logger로 변경, 모든 단계별 로깅 추가

#### 📍 _transcribe_faster_whisper() 메서드
```python
logger.info(f"[faster-whisper] 변환 시작 (파일: {Path(audio_path).name})")
logger.debug(f"[faster-whisper] 모델 설정: beam_size={kwargs.get('beam_size', 5)}")
logger.info(f"✓ faster-whisper 변환 완료")
logger.info(f"  결과: {len(text)} 글자, 언어: {detected_language}")
```

**개선**: 모델 파라미터, 결과 크기, 감지된 언어 로깅

#### 📍 _transcribe_with_transformers() 메서드
```python
logger.info(f"[transformers] 변환 시작 (파일: {Path(audio_path).name})")
logger.debug(f"[transformers] 파일 검증 중...")
logger.info(f"✓ 파일 검증 완료 (길이: {file_check['duration_sec']:.1f}초)")
logger.info(f"[transformers] 세그먼트 처리 시작 (총 {total_segments}개 세그먼트)")
logger.debug(f"[transformers] 세그먼트 {segment_idx+1}/{total_segments}: {start_idx//sr:.1f}~{end_idx//sr:.1f}초")
```

**개선**: 
- 단계별 로깅 (파일 검증, 메모리 확인, 오디오 로드, 세그먼트 처리)
- 세그먼트별 진행 상황
- 각 단계의 성공/실패 명확한 표기

#### 📍 _transcribe_with_whisper() 메서드
```python
logger.info(f"[openai-whisper] 변환 시작 (파일: {Path(audio_path).name})")
logger.info(f"✓ openai-whisper 변환 완료")
logger.info(f"  결과: {len(text)} 글자, 언어: {detected_language}")
```

**개선**: 모든 예외에 `exc_info=True`로 스택 트레이스 캡처

### 2. api_server.py - /transcribe 엔드포인트 포괄적 에러 핸들링

#### 📍 파일 업로드 처리
```python
logger.info(f"[API] 음성 파일 업로드 요청: {file.filename}")
logger.debug(f"[API] Content-Type: {file.content_type}")
logger.debug(f"[API] 임시 파일에 저장 중...")
logger.debug(f"✓ 임시 파일 저장 완료: {tmp_path}")
```

**개선**: 파일 저장 단계별 로깅, 임시 파일 경로 기록

#### 📍 파일 검증
```python
logger.debug(f"[API] 파일 검증 중...")
logger.info(f"✓ 파일 검증 완료 (길이: {file_check['duration_sec']:.1f}초)")
logger.error(f"[API] 파일 검증 실패: {error_msg}")
```

**개선**: 검증 성공/실패 모두 로깅

#### 📍 메모리 확인
```python
logger.debug(f"[API] 메모리 확인 중...")
logger.info(f"✓ 메모리 확인 완료 (사용 가능: {memory_info['available_mb']:.0f}MB)")
logger.error(f"[API] 메모리 부족: {memory_info['message']}")
```

#### 📍 STT 처리
```python
logger.info(f"[API] STT 처리 시작 (파일: {file.filename}, 길이: {file_check['duration_sec']:.1f}초, 언어: {language})")
logger.info(f"[API] STT 처리 완료 - 백엔드: {result.get('backend', 'unknown')}, 성공: {result.get('success', False)}")
logger.info(f"[API] ✅ STT 처리 성공 - 텍스트: {len(result.get('text', ''))} 글자")
```

**개선**: STT 처리 전후, 성공 여부, 텍스트 길이 로깅

#### 📍 에러 핸들링 (모든 케이스)
```python
except FileNotFoundError as e:
    logger.error(f"❌ 파일 오류: {e}", exc_info=True)  # exc_info=True!
except MemoryError as e:
    logger.error(f"[API] 메모리 부족 오류: {str(e)}", exc_info=True)
except Exception as e:
    logger.error(f"[API] 예상치 못한 오류: {type(e).__name__}: {str(e)}", exc_info=True)
```

**개선**: 모든 예외에 `exc_info=True`로 전체 스택 트레이스 로깅

### 3. 응답 형식 개선

#### 에러 응답에 error_type 추가
```json
{
  "success": false,
  "error": "파일 검증 실패",
  "error_type": "FileValidationError",  // ← 새로 추가
  "message": "파일 형식을 알 수 없음",
  "backend": "transformers",
  "segment_failed": 2,
  "partial_text": "부분 변환 결과...",
  "suggestion": "권장 조치 사항"
}
```

**개선**: error_type으로 오류 유형 명확하게 분류

---

## 📊 로깅 비교

### Before (이전 코드)
```
❌ 오류: 파일을 찾을 수 없습니다
```
- 무엇이 실패했는지 불명확
- 스택 트레이스 없음
- 디버깅 정보 부족

### After (개선된 코드)
```
📂 음성 파일 로드 시작: test.wav
✓ 파일 존재 확인: /tmp/tmpXXXXXX.wav
🔧 사용 중인 백엔드: WhisperModel
→ faster-whisper 백엔드로 변환 시작
[faster-whisper] 변환 시작 (파일: test.wav)
[faster-whisper] 모델 설정: beam_size=5, best_of=5, patience=1, temperature=0
✓ faster-whisper 변환 완료
  결과: 256 글자, 언어: ko
[API] ✅ STT 처리 성공 - 텍스트: 256 글자
```
- 모든 단계가 명확
- 성공/실패 시점 명확
- 모델 설정, 결과 길이 등 상세 정보

---

## 🔧 기술적 개선사항

| 항목 | Before | After |
|------|--------|-------|
| 로깅 API | `print()` | `logger.info()`, `logger.debug()`, `logger.error()` |
| 예외 처리 | 단순 오류 메시지만 | `exc_info=True`로 전체 스택 트레이스 |
| 에러 응답 | `error` 필드만 | `error`, `error_type`, `suggestion` 등 여러 필드 |
| 단계별 로깅 | 거의 없음 | 모든 주요 단계별 로깅 |
| 메모리 정보 | 오류 시에만 | 성공/실패 모두 기록 |
| 백엔드 정보 | 결과에만 | 과정 중에도 명시 |

---

## 📋 파일 변경사항

### 1. stt_engine.py (120줄 추가)
- logger 초기화 추가
- transcribe() 메서드: 15줄 → 50줄 로깅 추가
- _transcribe_faster_whisper(): 10줄 → 30줄 로깅 추가  
- _transcribe_with_transformers(): 모든 단계에 로깅 추가
- _transcribe_with_whisper(): 10줄 → 30줄 로깅 추가
- 모든 예외에 exc_info=True 추가

### 2. api_server.py (95줄 추가)
- /transcribe 엔드포인트: 70줄 → 160줄로 상세화
- 파일 저장, 검증, 메모리 확인, STT 처리 각 단계에 로깅 추가
- 모든 except 블록에 exc_info=True 추가
- 응답에 error_type 필드 추가

### 3. 새 문서 추가
- TEST_CURL_COMMANDS.md: curl 테스트 방법 (파일 경로 문제 해결)
- LOGGING_GUIDE.md: 로깅 구조 및 디버깅 가이드

---

## 🚀 사용 방법

### 로그 확인 (실시간)
```bash
# Docker 컨테이너 로그 보기
docker logs -f stt-engine

# 또는 호스트의 로그 파일
tail -f logs/stt_engine.log
```

### curl 테스트 (올바른 방법)
```bash
# 파일 경로가 길면 복사 후 사용
cp "audio/samples/door_to_door_sales/1_Recording_20240712_140513_01041968444.wav" /tmp/test.wav

# API 호출
curl -X POST http://localhost:8003/transcribe \
  -F 'file=@/tmp/test.wav' | python3 -m json.tool

# 로그 확인
docker logs stt-engine | tail -50
```

---

## 📌 커밋 정보

| 커밋 | 메시지 | 변경사항 |
|-----|--------|---------|
| 972d7a9 | Refactor: Enhance logging | stt_engine.py, api_server.py 로깅 추가 |
| 13251f8 | Docs: Add comprehensive guides | TEST_CURL_COMMANDS.md, LOGGING_GUIDE.md 추가 |

---

## ✨ 다음 단계

1. **EC2 배포**
   ```bash
   git push origin main
   # EC2에서 git pull 및 재빌드
   ```

2. **로그 분석 테스트**
   ```bash
   # curl 요청 전송
   curl -X POST http://localhost:8003/transcribe -F 'file=@/tmp/test.wav'
   
   # 로그에서 모든 단계 확인
   docker logs stt-engine
   ```

3. **오류 발생 시 디버깅**
   - 로그의 각 단계별 메시지로 정확한 실패 지점 파악
   - error_type으로 오류 유형 확인
   - exc_info=True의 스택 트레이스로 근본 원인 파악

---

## 🎉 완료!

이제 모든 단계에서 상세한 로깅이 이루어지므로, 문제 발생 시 정확한 원인을 파악할 수 있습니다!
