#!/usr/bin/env python3
"""
STT 모듈 - faster-whisper / OpenAI Whisper 자동 선택
faster-whisper 우선 시도 → 실패 시 OpenAI Whisper로 폴백
"""

import os
from pathlib import Path
from typing import Optional, Dict
import tarfile

# 두 가지 백엔드 시도
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False

try:
    import openai_whisper as whisper
    WHISPER_AVAILABLE = True
except ImportError:
    try:
        import whisper
        WHISPER_AVAILABLE = True
    except ImportError:
        WHISPER_AVAILABLE = False

if not FASTER_WHISPER_AVAILABLE and not WHISPER_AVAILABLE:
    raise ImportError("faster-whisper 또는 openai-whisper(whisper) 패키지가 설치되어야 합니다")


def validate_faster_whisper_model(model_path: str) -> bool:
    """
    faster-whisper 모델 유효성 검증 (CTranslate2 모델 형식)
    필수 파일: model.bin, config.json
    
    Args:
        model_path: 모델 폴더 경로
    
    Returns:
        True if 유효, False otherwise
    """
    model_dir = Path(model_path)
    
    required_files = ["model.bin", "config.json"]
    missing_files = []
    
    for file in required_files:
        file_path = model_dir / file
        if not file_path.exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"   ⚠️  faster-whisper 모델 파일 누락: {', '.join(missing_files)}")
        return False
    
    print(f"   ✓ faster-whisper 모델 구조 유효 (model.bin, config.json 확인됨)")
    return True


def validate_whisper_model(model_path: str) -> bool:
    """
    OpenAI Whisper 모델 유효성 검증 (PyTorch 모델 형식)
    필수 파일: pytorch_model.bin 또는 model.safetensors, config.json, vocab.json
    
    Args:
        model_path: 모델 폴더 경로
    
    Returns:
        True if 유효, False otherwise
    """
    model_dir = Path(model_path)
    
    # pytorch_model.bin 또는 model.safetensors 중 하나 필요
    has_pytorch = (model_dir / "pytorch_model.bin").exists()
    has_safetensors = (model_dir / "model.safetensors").exists()
    
    if not (has_pytorch or has_safetensors):
        print(f"   ⚠️  Whisper 모델 파일 누락: pytorch_model.bin 또는 model.safetensors 필요")
        return False
    
    # config.json, vocab.json 필수
    required_files = ["config.json", "vocab.json"]
    missing_files = []
    
    for file in required_files:
        file_path = model_dir / file
        if not file_path.exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"   ⚠️  Whisper 모델 파일 누락: {', '.join(missing_files)}")
        return False
    
    print(f"   ✓ Whisper 모델 구조 유효 (pytorch_model.bin/safetensors, config.json, vocab.json 확인됨)")
    return True


def auto_extract_model_if_needed(models_dir: str = "models") -> Path:
    """
    필요시 모델 자동 압축 해제
    
    Args:
        models_dir: 모델 디렉토리 (예: "models")
    
    Returns:
        모델 폴더 경로 (models/openai_whisper-large-v3-turbo)
    
    Raises:
        RuntimeError: 모델 압축 해제 실패
        FileNotFoundError: 모델을 찾을 수 없음
    """
    models_path = Path(models_dir)
    model_folder = models_path / "openai_whisper-large-v3-turbo"
    tar_file = models_path / "whisper-model.tar.gz"
    
    # 이미 해제되어 있으면 반환
    if model_folder.exists():
        return model_folder
    
    # 압축 파일이 있으면 자동 해제
    if tar_file.exists():
        print("📦 모델 압축 파일 감지, 자동 해제 중...")
        try:
            with tarfile.open(tar_file, "r:gz") as tar:
                # 안전성 검사: tar 멤버 검증
                for member in tar.getmembers():
                    if member.name.startswith('/') or '..' in member.name:
                        raise RuntimeError(f"보안 위험: 잘못된 경로 {member.name}")
                tar.extractall(path=models_path)
            print("✅ 모델 압축 해제 완료")
            
            # 압축 파일 삭제 (선택사항)
            tar_file.unlink()
            print("🗑️  압축 파일 삭제")
            
            return model_folder
        except tarfile.TarError as e:
            print(f"❌ 유효하지 않은 tar 파일: {e}")
            raise RuntimeError(f"모델 압축 해제 실패: {e}") from e
        except Exception as e:
            print(f"❌ 모델 압축 해제 실패: {e}")
            raise
    
    # 둘 다 없으면 경로 반환 (다운로드 프롬프트)
    return model_folder


class WhisperSTT:
    """faster-whisper / OpenAI Whisper 자동 선택 STT 클래스"""
    
    def __init__(self, model_path: str, device: str = "cpu", compute_type: str = "float16"):
        """
        Whisper STT 초기화
        
        Args:
            model_path: 모델 경로 (예: "models")
            device: 사용할 디바이스 ('cpu', 'cuda', 또는 'auto')
            compute_type: 계산 타입 (faster-whisper용, 'float32', 'float16', 'int8')
        
        Raises:
            FileNotFoundError: 모델을 찾을 수 없음
            RuntimeError: 모델 로드 실패
        """
        # 모델이 압축되어 있으면 자동 해제
        models_dir = str(Path(model_path).parent)
        self.model_path = str(auto_extract_model_if_needed(models_dir))
        
        # 모델 경로 유효성 최종 확인
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"모델 폴더를 찾을 수 없습니다: {self.model_path}\n"
                                  f"아래 중 하나를 확인하세요:\n"
                                  f"1. 모델이 다운로드되었는가? (download_model_hf.py 실행)\n"
                                  f"2. 모델 경로가 올바른가? (기본값: models/openai_whisper-large-v3-turbo)\n"
                                  f"3. 운영서버인가? (오프라인 배포인 경우 모델을 이미지에 포함시켜야 함)")
        
        self.device = device if device != "auto" else ("cuda" if self._is_cuda_available() else "cpu")
        self.compute_type = compute_type
        self.backend = None
        
        print(f"\n📊 모델 로드 시작")
        print(f"   모델 경로: {self.model_path}")
        print(f"   디바이스: {self.device}")
        print(f"   사용 가능한 백엔드: faster-whisper={FASTER_WHISPER_AVAILABLE}, whisper={WHISPER_AVAILABLE}\n")
        
        # faster-whisper 먼저 시도
        if FASTER_WHISPER_AVAILABLE:
            self._try_faster_whisper()
        
        # faster-whisper 실패하면 OpenAI Whisper 시도
        if self.backend is None and WHISPER_AVAILABLE:
            self._try_whisper()
        
        # 둘 다 실패하면 에러
        if self.backend is None:
            raise RuntimeError(
                "모델 로드 실패: faster-whisper와 whisper 모두 실패\n"
                "확인 사항:\n"
                f"1. 모델 경로 확인: {self.model_path}\n"
                "2. 모델 구조 확인:\n"
                "   - faster-whisper용: model.bin, config.json\n"
                "   - OpenAI Whisper용: pytorch_model.bin/safetensors, config.json, vocab.json\n"
                "3. 모델 파일이 손상되지 않았는지 확인"
            )
    
    def _try_faster_whisper(self):
        """faster-whisper로 모델 로드 시도 (로컬 모델만 사용)"""
        try:
            print(f"🔄 faster-whisper 모델 로드 시도... (디바이스: {self.device}, compute: {self.compute_type})")
            
            # 모델 구조 먼저 검증
            if not validate_faster_whisper_model(self.model_path):
                print(f"   → faster-whisper 모델 구조 검증 실패")
                return
            
            # 로컬 모델만 사용하도록 로드
            self.model = WhisperModel(
                self.model_path,
                device=self.device,
                compute_type=self.compute_type,
                num_workers=4,
                cpu_threads=4,
                download_root=None,
                local_files_only=True  # 🔒 운영서버에서 다운로드 방지
            )
            
            self.backend = "faster-whisper"
            print(f"✅ faster-whisper 모델 로드 성공")
            
        except FileNotFoundError as e:
            print(f"⚠️  faster-whisper: 모델 파일을 찾을 수 없음 - {e}")
            print(f"   → OpenAI Whisper로 폴백 시도...")
        except Exception as e:
            print(f"⚠️  faster-whisper 로드 실패: {e}")
            print(f"   → OpenAI Whisper로 폴백 시도...")
    
    def _try_whisper(self):
        """OpenAI Whisper로 모델 로드 시도 (로컬 모델만 사용)"""
        try:
            print(f"🔄 OpenAI Whisper 모델 로드 시도... (디바이스: {self.device})")
            
            model_path = Path(self.model_path)
            
            # 로컬 모델 경로 존재 확인
            if not model_path.exists():
                raise FileNotFoundError(f"모델 경로를 찾을 수 없음: {self.model_path}")
            
            # 모델 구조 먼저 검증
            if not validate_whisper_model(str(model_path)):
                print(f"   → Whisper 모델 구조 검증 실패")
                return
            
            # 로컬 모델 경로를 직접 사용
            # openai-whisper는 로컬 경로를 모델 이름으로 인식 가능
            print(f"   📂 로컬 모델 로드: {self.model_path}")
            
            self.model = whisper.load_model(
                str(model_path),
                device=self.device,
                in_memory=False,
                download_root=None  # 🔒 다운로드 방지
            )
            
            self.backend = "whisper"
            print(f"✅ OpenAI Whisper 모델 로드 성공")
            
        except FileNotFoundError as e:
            print(f"❌ OpenAI Whisper: 모델을 찾을 수 없음 - {e}")
        except Exception as e:
            print(f"❌ OpenAI Whisper 로드 실패: {e}")
    
    @staticmethod
    def _is_cuda_available() -> bool:
        """CUDA 가용성 확인"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def transcribe(self, audio_path: str, language: Optional[str] = None, **kwargs) -> Dict:
        """
        음성 파일을 텍스트로 변환합니다.
        
        Args:
            audio_path: 음성 파일 경로
            language: 음성 언어 코드 (예: 'ko', 'en')
            **kwargs: 추가 옵션
        
        Returns:
            변환 결과 딕셔너리
        """
        try:
            print(f"📂 음성 파일 로드: {audio_path}")
            
            # 파일 존재 확인
            if not Path(audio_path).exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {audio_path}")
            
            # 백엔드별 처리
            if self.backend == "faster-whisper":
                return self._transcribe_faster_whisper(audio_path, language, **kwargs)
            elif self.backend == "whisper":
                return self._transcribe_whisper(audio_path, language, **kwargs)
            else:
                raise RuntimeError(f"알 수 없는 백엔드: {self.backend}")
        
        except Exception as e:
            print(f"❌ 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "audio_path": audio_path
            }
    
    def _transcribe_faster_whisper(self, audio_path: str, language: Optional[str] = None, **kwargs) -> Dict:
        """faster-whisper로 변환"""
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=kwargs.get("beam_size", 5),
            best_of=kwargs.get("best_of", 5),
            patience=kwargs.get("patience", 1),
            temperature=kwargs.get("temperature", 0),
            verbose=False
        )
        
        # 모든 세그먼트 수집
        text = "".join([segment.text for segment in segments])
        detected_language = info.language if info else language or "unknown"
        
        return {
            "success": True,
            "text": text.strip(),
            "audio_path": audio_path,
            "language": detected_language,
            "duration": info.duration if info else None,
            "backend": "faster-whisper"
        }
    
    def _transcribe_whisper(self, audio_path: str, language: Optional[str] = None, **kwargs) -> Dict:
        """OpenAI Whisper로 변환"""
        result = self.model.transcribe(
            audio_path,
            language=language
        )
        
        text = result.get("text", "").strip()
        
        return {
            "success": True,
            "text": text,
            "audio_path": audio_path,
            "language": language or "unknown",
            "duration": None,
            "backend": "whisper"
        }


def test_stt(model_path: str, audio_dir: str = "audio", device: str = "cpu"):
    """
    STT 테스트 함수 (디버깅용, 실제 서비스에서는 사용 안 함)
    
    Args:
        model_path: 모델 경로
        audio_dir: 테스트할 음성 파일 디렉토리
        device: 사용할 디바이스
    
    참고: FastAPI 서비스 (api_server.py)에서 실제로 사용할 때는
         이 함수가 아닌 WhisperSTT 클래스를 직접 import해서 사용합니다.
    """
    # STT 초기화
    stt = WhisperSTT(
        model_path,
        device=device,
        compute_type="float16"
    )
    
    print(f"\n📊 사용 백엔드: {stt.backend}\n")
    
    # 음성 파일 디렉토리 확인
    audio_path = Path(audio_dir)
    if not audio_path.exists():
        print(f"⚠️  음성 파일 디렉토리가 없습니다: {audio_dir}")
        return
    
    # 지원하는 음성 파일 형식
    supported_formats = ("*.wav", "*.mp3", "*.flac", "*.ogg", "*.m4a")
    audio_files = []
    for fmt in supported_formats:
        audio_files.extend(audio_path.glob(fmt))
    
    if not audio_files:
        print(f"⚠️  음성 파일을 찾을 수 없습니다: {audio_dir}")
        return
    
    # 각 파일에 대해 STT 수행
    print(f"\n📊 총 {len(audio_files)}개의 음성 파일을 처리합니다\n")
    
    for idx, audio_file in enumerate(audio_files, 1):
        print(f"\n{'='*60}")
        print(f"[{idx}/{len(audio_files)}] 처리 중...")
        print(f"{'='*60}")
        
        result = stt.transcribe(str(audio_file))
        
        if result["success"]:
            print(f"✅ 파일: {audio_file.name}")
            print(f"📝 결과:\n{result['text']}")
            if result.get("duration"):
                print(f"⏱️  음성 길이: {result['duration']:.1f}초")
            print(f"🔧 사용 백엔드: {result.get('backend', 'unknown')}")
        else:
            print(f"❌ 파일: {audio_file.name}")
            print(f"🔴 오류: {result.get('error', 'Unknown error')}")


# ============================================================================
# 주의: 이 파일은 api_server.py의 FastAPI 서비스에서 import되어 사용됩니다.
# api_server.py:
#   from stt_engine import WhisperSTT
#   stt = WhisperSTT(model_path=..., device=...)
#   result = stt.transcribe(audio_path)
#
# 따라서 이 파일을 직접 실행할 필요는 없습니다.
# 만약 로컬에서 테스트하려면:
#   python stt_engine.py  (단, audio/ 디렉토리에 음성 파일이 있어야 함)
# ============================================================================
