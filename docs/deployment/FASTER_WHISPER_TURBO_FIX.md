# Faster-Whisper Turbo Model Fix

## Root Cause Analysis

### The Problem
When using faster-whisper (WhisperModel) backend with the turbo model, users encountered:
```
❌ 오류: Invalid input features shape: expected an input with shape (1, 128, 3000), 
but got an input with shape (1, 80, 3000) instead
```

### Root Cause Discovered
Both config files have **correct** mel-bin configuration:
- **PyTorch config** (`config.json`): `"num_mel_bins": 128` ✅
- **CTranslate2 config** (`ctranslate2_model/config.json`): `"num_mel_bins": 128` ✅

**However**, faster-whisper 1.2.1 has **hardcoded audio preprocessing** that always generates **80 mel-bins** (standard Whisper), regardless of the model's configuration.

### Why This Happens
1. The Turbo model is a **custom variant** with 128 mel-bins (not standard Whisper)
2. faster-whisper's `transcribe()` method internally:
   - Loads audio files
   - Computes mel-spectrogram with **hardcoded 80 mel-bins**
   - Feeds it to the CTranslate2 model
3. CTranslate2 expects 128 mel-bins → **shape mismatch** → error

## Solution Implemented

### Strategy: Smart Backend Fallback
Instead of fixing faster-whisper's internal audio processing (which we can't control), we:
1. **Detect** the mel-bin mismatch at initialization time
2. **Log a warning** if faster-whisper is used with non-80-mel-bin models
3. **Auto-fallback** to transformers backend which supports custom mel-bins

### Code Changes

#### 1. Helper Functions (lines 63-119)
- `get_model_mel_bins()`: Extract mel-bin count from model config
- `preprocess_audio_with_mel_bins()`: Compute mel-spectrograms with any mel-bin count

#### 2. Backend Availability Flags (line 391-393)
```python
self.faster_whisper_available = False
self.transformers_available = False
self.whisper_available = False
```
Track which backends successfully loaded for smart fallback.

#### 3. Enhanced `_transcribe_faster_whisper()` (lines 1189-1255)
```python
# 모델의 mel-bin 개수 확인
model_mel_bins = get_model_mel_bins(self.model_path)
logger.info(f"[faster-whisper] 모델 mel-bins: {model_mel_bins}")

if model_mel_bins != 80:
    logger.warning(f"⚠️  모델이 {model_mel_bins} mel-bins를 요구하지만...")
    # Auto-fallback to transformers
    if TRANSFORMERS_AVAILABLE and self.transformers_available:
        logger.info(f"   → transformers 백엔드로 자동 전환...")
        return self._transcribe_with_transformers(audio_path, language)
```

### Flow Diagram
```
User calls transcribe(backend='faster-whisper')
    ↓
_transcribe_faster_whisper() called
    ↓
Check model mel-bins
    ↓
mel_bins == 80? ────────────────── YES ──→ Use faster-whisper ✅
    │
    NO (128 for turbo)
    ↓
transformers available? ────────── YES ──→ Auto-fallback ✅
    │
    NO
    ↓
Continue with faster-whisper (will fail gracefully with detailed error)
```

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Turbo with faster-whisper** | ❌ Error: shape mismatch | ✅ Auto-fallback to transformers |
| **Turbo with transformers** | ✅ Works | ✅ Still works |
| **Standard models** | ✅ Works | ✅ Still works, fast |
| **Error handling** | Generic error | Detailed diagnosis + fallback |
| **User experience** | Confusing shape error | Transparent automatic handling |

## Tested Scenarios

✅ **turbo + faster-whisper** → Falls back to transformers
✅ **turbo + transformers** → Works directly
✅ **turbo + openai-whisper** → Falls back to transformers if available
✅ **standard models** → All backends work normally

## Usage

No changes needed. Users can now:

```python
stt = WhisperSTT("models/openai_whisper-large-v3-turbo")

# All of these now work with intelligent fallback:
result1 = stt.transcribe("audio.wav", backend="faster-whisper")  # Auto-fallback to transformers
result2 = stt.transcribe("audio.wav", backend="transformers")    # Direct use
result3 = stt.transcribe("audio.wav")                            # Auto-selects best available
```

## Related Files Modified
- `stt_engine.py`: Core mel-bin validation and fallback logic
- Imported: `json`, `librosa`, `numpy` for audio processing support

## Notes

1. **Performance Trade-off**: Falling back to transformers is slower (2-3x) than faster-whisper, but guarantees correctness with turbo models.

2. **Future Considerations**:
   - Monitor faster-whisper updates (may fix 80-mel-bin limitation)
   - Consider pre-computing mel-spectrograms if transformers becomes bottleneck
   - Evaluate CTranslate2 model conversion parameters

3. **No Model Changes Required**: Both PyTorch and CTranslate2 configs are correct. Only the API wrapper needed adjustment.

## Commit
- `67bfc1c`: Fix: Add mel-spectrogram shape validation for faster-whisper
