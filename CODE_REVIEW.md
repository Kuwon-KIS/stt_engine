# STT Engine 코드 검토 결과

## 🔍 발견된 이슈들

### 🔴 **중요 이슈 1: auto_extract_model_if_needed() 함수의 경로 로직 문제**

**위치:** `stt_engine.py` 라인 68-71

```python
# 모델이 압축되어 있으면 자동 해제
model_path = str(auto_extract_model_if_needed(
    Path(model_path).parent  # ❌ 문제: "models" 디렉토리 반환
))
```

**문제점:**
- `model_path`가 `models/openai_whisper-large-v3-turbo`일 때
- `Path(model_path).parent` → `models` 폴더
- 그러나 `auto_extract_model_if_needed()` 함수 내부에서 다시 `models_path / "openai_whisper-large-v3-turbo"` 추가
- 결과: 반환된 경로가 올바르지만, 호출 방식이 혼란스러움

**수정 권장:**
```python
# 방법 1: 전체 models_dir 경로 전달
model_path = str(auto_extract_model_if_needed("models"))

# 방법 2: 함수 인터페이스 명확화
# auto_extract_model_if_needed(model_folder_path) 로 변경
```

---

### 🔴 **중요 이슈 2: transcribe() 함수에서 audio 처리 후 GPU 메모리 누수**

**위치:** `stt_engine.py` 라인 100-120

```python
def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict:
    try:
        audio, sr = torchaudio.load(audio_path)
        
        if sr != 16000:
            resampler = torchaudio.transforms.Resample(sr, 16000)
            audio = resampler(audio)  # ❌ GPU 메모리 미정리
        
        # ...
        
        inputs = self.processor(
            audio.squeeze().numpy(),  # ❌ 메모리 문제
            sampling_rate=16000,
            return_tensors="pt"
        )
```

**문제점:**
1. `audio` Tensor가 GPU에 올라갔을 수 있음
2. `.numpy()` 호출 시 GPU Tensor는 CPU로 이동 필수
3. 메모리 정리 없음

**수정 권장:**
```python
# GPU Tensor를 CPU로 명시적으로 이동
audio_np = audio.squeeze().cpu().numpy()
inputs = self.processor(
    audio_np,
    sampling_rate=16000,
    return_tensors="pt"
)
```

---

### 🟡 **중간 이슈 3: 경로 문자열 vs Path 객체 혼용**

**위치:** `stt_engine.py` 라인 68-71, `api_server.py` 라인 19

```python
# api_server.py
model_path = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"
stt = WhisperSTT(str(model_path), device=device)  # Path를 문자열로 변환

# stt_engine.py
def __init__(self, model_path: str, device: str = "cpu"):
    model_path = str(auto_extract_model_if_needed(  # 다시 Path로 변환 후 문자열로
        Path(model_path).parent
    ))
```

**문제점:**
- Path ↔ str 변환이 반복됨
- 함수 인터페이스가 일관성 없음

**권장:**
- 함수 시그니처를 `Union[str, Path]` 타입힌트로 명시
- 또는 Path 객체로 통일

---

### 🟡 **중간 이슈 4: resampler Tensor 메모리 위치 불명확**

**위치:** `stt_engine.py` 라인 103-105

```python
if sr != 16000:
    print(f"🔄 샘플링 레이트 변환: {sr}Hz -> 16000Hz")
    resampler = torchaudio.transforms.Resample(sr, 16000)  # ❌ device 명시 없음
    audio = resampler(audio)  # audio가 어디에? GPU? CPU?
```

**문제점:**
- `Resample` transform이 어느 device에서 실행될지 명확하지 않음
- audio가 GPU에 있으면 resampler도 같은 device 필요

**수정 권장:**
```python
if sr != 16000:
    resampler = torchaudio.transforms.Resample(sr, 16000).to(self.device)
    audio = resampler(audio.to(self.device))
```

---

### 🟡 **중간 이슈 5: model_manager.py에서 import 위치 문제**

**위치:** `model_manager.py` 라인 194

```python
def download_from_s3(self, bucket: str, ...):
    try:
        import boto3  # ❌ 함수 내부 import
```

**문제점:**
- boto3를 함수 내부에서 import
- 모듈 로드 시간 지연
- 코드 상단에서 선택적 import가 더 나음

**권장:**
```python
try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

# 함수에서:
if not HAS_BOTO3:
    print("❌ boto3가 설치되지 않았습니다")
    return False
```

---

### 🟢 **경미한 이슈: vllm_client.py 선택적 임포트 누락**

**위치:** `api_server.py` 라인 11-12

```python
from vllm_client import VLLMClient, VLLMConfig

try:
    # ...
    vllm_client = VLLMClient(VLLMConfig())  # requests 임포트 오류 시 실패
except Exception as e:
```

**권장:** vllm_client.py에서 requests 임포트를 선택적으로 처리

---

## 📋 수정 체크리스트

### 우선순위: 높음
- [ ] auto_extract_model_if_needed() 경로 로직 정리
- [ ] transcribe()에서 audio.cpu().numpy() 명시
- [ ] Resample transform의 device 명시

### 우선순위: 중간
- [ ] Path/str 타입힌트 통일
- [ ] boto3 선택적 import 위치 변경
- [ ] vllm_client requests import 오류 처리

### 우선순위: 낮음
- [ ] 코드 주석 보충
- [ ] Error 메시지 명확화

---

## ✅ 정상인 부분

✅ 파일 임시 저장 및 삭제 로직 (api_server.py)
✅ 음성 포맷 지원 루프 (test_stt 함수)
✅ 모델 초기화 try-except 처리
✅ 음성 모노 변환 로직
✅ tar 압축/해제 로직
✅ Model Manager CLI 구조

---

## 🔧 권장 수정사항 (우선순위 순)
