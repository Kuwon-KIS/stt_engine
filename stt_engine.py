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


def diagnose_faster_whisper_model(model_path: str) -> dict:
    """
    faster-whisper 모델 상세 진단 (디버깅용)
    
    CTranslate2 모델은 다음 파일들을 포함합니다:
    - model.bin (CTranslate2 변환된 모델 바이너리)
    - config.json (모델 설정)
    - vocabulary.json (또는 tokens.json) - 토크나이저 정보
    - shared_vocabulary.json (선택사항)
    
    Returns:
        {
            'valid': bool,
            'errors': [list of errors],
            'warnings': [list of warnings],
            'files': {detailed file structure},
            'model_bin_size_mb': float
        }
    """
    model_dir = Path(model_path)
    ct_model_dir = model_dir / "ctranslate2_model"
    
    diagnosis = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'files': {},
        'model_bin_size_mb': None
    }
    
    # 1. ctranslate2_model 폴더 존재 확인
    if not ct_model_dir.exists():
        diagnosis['errors'].append(f"ctranslate2_model 폴더 없음: {ct_model_dir}")
        diagnosis['valid'] = False
        return diagnosis
    
    # 2. ctranslate2_model 내 모든 파일 나열
    try:
        ct_files = list(ct_model_dir.rglob("*"))
        diagnosis['files']['total_count'] = len(ct_files)
        diagnosis['files']['list'] = []
        
        for file_path in sorted(ct_files)[:30]:  # 처음 30개
            if file_path.is_file():
                size_kb = file_path.stat().st_size / 1024
                diagnosis['files']['list'].append({
                    'name': file_path.name,
                    'relative_path': str(file_path.relative_to(ct_model_dir)),
                    'size_kb': size_kb
                })
    except Exception as e:
        diagnosis['errors'].append(f"파일 나열 실패: {e}")
        diagnosis['valid'] = False
        return diagnosis
    
    # 3. 필수 파일 확인 (CTranslate2 포맷)
    critical_files = {
        'model.bin': 'CTranslate2 변환된 모델 바이너리',
        'config.json': 'Whisper 모델 설정'
    }
    
    for file_name, description in critical_files.items():
        file_path = ct_model_dir / file_name
        if not file_path.exists():
            diagnosis['errors'].append(f"누락: {file_name} ({description})")
            diagnosis['valid'] = False
        else:
            size_kb = file_path.stat().st_size / 1024
            if size_kb < 10:
                diagnosis['warnings'].append(f"{file_name}이 너무 작음: {size_kb:.1f}KB (손상 가능성)")
    
    # 4. 토크나이저 파일 확인 (vocabulary.json 또는 tokens.json)
    # CTranslate2는 OpenAI Whisper의 tokenizer.json을 사용하지 않음
    vocab_files = ['vocabulary.json', 'tokens.json', 'tokenizer.json']
    has_vocab = False
    for vocab_file in vocab_files:
        if (ct_model_dir / vocab_file).exists():
            has_vocab = True
            size_kb = (ct_model_dir / vocab_file).stat().st_size / 1024
            if size_kb < 10:
                diagnosis['warnings'].append(f"{vocab_file}이 너무 작음: {size_kb:.1f}KB")
            break
    
    if not has_vocab:
        diagnosis['warnings'].append(f"토크나이저 파일 없음 (vocabulary.json, tokens.json, tokenizer.json 중 하나 필요)")
    
    # 5. model.bin 상세 검사
    model_bin = ct_model_dir / "model.bin"
    if model_bin.exists():
        size_bytes = model_bin.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        diagnosis['model_bin_size_mb'] = size_mb
        
        if size_mb < 100:
            diagnosis['warnings'].append(f"model.bin이 매우 작음: {size_mb:.1f}MB (손상 또는 변환 실패 가능성)")
            diagnosis['valid'] = False
        
        if size_mb > 5000:
            diagnosis['warnings'].append(f"model.bin이 매우 큼: {size_mb:.1f}MB (양자화 확인 필요)")
    
    return diagnosis


def validate_faster_whisper_model(model_path: str) -> bool:
    """
    faster-whisper 모델 유효성 검증
    diagnose_faster_whisper_model의 간단한 래퍼
    """
    diagnosis = diagnose_faster_whisper_model(model_path)
    
    print(f"   📂 faster-whisper 모델 검증: {model_path}")
    
    if diagnosis['files']['total_count'] > 0:
        print(f"   ✓ ctranslate2_model 폴더 있음 ({diagnosis['files']['total_count']}개 파일)")
    
    if diagnosis['model_bin_size_mb']:
        print(f"   ✓ model.bin: {diagnosis['model_bin_size_mb']:.1f}MB")
    
    for warning in diagnosis['warnings']:
        print(f"   ⚠️  {warning}")
    
    for error in diagnosis['errors']:
        print(f"   ❌ {error}")
    
    return diagnosis['valid']


def validate_whisper_model(model_path: str) -> bool:
    """
    OpenAI Whisper 모델 유효성 검증 (PyTorch 모델 형식)
    
    주의: OpenAI Whisper는 공식적으로 다음 모델만 지원합니다:
    - tiny, base, small, medium, large
    
    "large-v3", "large-v3-turbo" 같은 변형은 huggingface에서만 가능하므로
    운영서버 오프라인 환경에서는 사용 불가합니다.
    
    Args:
        model_path: 모델 폴더 경로 (참고용)
    
    Returns:
        True if 유효, False otherwise
    """
    model_dir = Path(model_path)
    
    if not model_dir.exists():
        print(f"   ⚠️  모델 경로를 찾을 수 없음: {model_path}")
        return False
    
    # pytorch_model.bin 또는 model.safetensors 중 하나 필요
    has_pytorch = (model_dir / "pytorch_model.bin").exists()
    has_safetensors = (model_dir / "model.safetensors").exists()
    
    if not (has_pytorch or has_safetensors):
        print(f"   ⚠️  Whisper 모델 파일 누락: pytorch_model.bin 또는 model.safetensors 필요")
        return False
    
    # config.json, tokens.json 필수
    required_files = ["config.json", "tokenizer.json"]
    missing_files = []
    
    for file in required_files:
        file_path = model_dir / file
        if not file_path.exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"   ⚠️  Whisper 모델 파일 누락: {', '.join(missing_files)}")
        return False
    
    print(f"   ✓ Whisper 모델 구조 유효")
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
                "모델 로드 실패: 두 백엔드 모두 실패\n\n"
                "🔧 운영서버 배포 체크리스트:\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "1. faster-whisper 모델:\n"
                f"   경로: {self.model_path}\n"
                f"   필수: {self.model_path}/ctranslate2_model/model.bin\n\n"
                "2. OpenAI Whisper 모델 (large-v3-turbo):\n"
                "   경로: /app/models (Docker 마운트 포인트)\n"
                "   구조: pytorch_model.bin, config.json, tokenizer.json\n\n"
                "3. 모델 배포 방법:\n"
                "   a) 로컬에서 다운로드: python download_model_hf.py\n"
                "   b) 운영서버로 복사: rsync -av models/ server:/models/\n"
                "   c) Docker 실행: docker run -v /models:/app/models stt-engine"
            )
    
    def _try_faster_whisper(self):
        """faster-whisper로 모델 로드 시도 (로컬 모델만 사용, 상세 진단 포함)"""
        try:
            print(f"🔄 faster-whisper 모델 로드 시도... (디바이스: {self.device}, compute: {self.compute_type})")
            
            # 모델 구조 상세 진단
            diagnosis = diagnose_faster_whisper_model(self.model_path)
            
            if not diagnosis['valid']:
                print(f"\n   ❌ 모델 구조 검증 실패:")
                for error in diagnosis['errors']:
                    print(f"      - {error}")
                
                # CTranslate2 변환 가이드
                if "tokenizer.json" in str(diagnosis['errors']):
                    print(f"\n   💡 CTranslate2 변환 정보:")
                    print(f"      OpenAI Whisper의 tokenizer.json은 CTranslate2로 변환되지 않습니다.")
                    print(f"      대신 다음 파일들을 확인하세요:")
                    print(f"      - vocabulary.json")
                    print(f"      - tokens.json")
                    print(f"      - tokenizer.json (원본 보존된 경우)")
                
                return
            
            # 경고 확인
            if diagnosis['warnings']:
                print(f"\n   ⚠️  주의사항:")
                for warning in diagnosis['warnings']:
                    print(f"      - {warning}")
            
            # 파일 목록 출력
            if diagnosis['files']['list']:
                print(f"\n   📂 CTranslate2 모델 파일 ({diagnosis['files']['total_count']}개):")
                for file_info in diagnosis['files']['list'][:10]:
                    print(f"      ✓ {file_info['name']} ({file_info['size_kb']:.1f}KB)")
                if len(diagnosis['files']['list']) > 10:
                    print(f"      ... 외 {len(diagnosis['files']['list']) - 10}개")
            
            # 모델 로드 시도
            print(f"\n   📦 faster-whisper WhisperModel 로드 중...")
            self.model = WhisperModel(
                self.model_path,
                device=self.device,
                compute_type=self.compute_type,
                num_workers=4,
                cpu_threads=4,
                download_root=None,
                local_files_only=True
            )
            
            self.backend = "faster-whisper"
            print(f"✅ faster-whisper 모델 로드 성공")
            
        except FileNotFoundError as e:
            print(f"\n   ❌ faster-whisper: 파일을 찾을 수 없음")
            print(f"      에러: {e}")
            print(f"      경로: {self.model_path}")
            print(f"\n   💡 해결 방법:")
            print(f"      1. download_model_hf.py 실행 상태 확인")
            print(f"      2. CTranslate2 변환 완료 여부 확인")
            print(f"      3. {self.model_path}/ctranslate2_model/model.bin 파일 크기 확인 (100MB 이상)")
        except Exception as e:
            error_str = str(e)
            print(f"\n   ❌ faster-whisper 로드 실패: {type(e).__name__}")
            print(f"      메시지: {error_str[:200]}")
            
            # 알려진 에러 진단
            if "vocabulary" in error_str.lower() or "token" in error_str.lower():
                print(f"\n   💡 분석: 토크나이저/어휘 오류")
                print(f"      - CTranslate2 변환이 올바르게 완료되지 않았을 수 있음")
                print(f"      - 필요한 파일: vocabulary.json, tokens.json 등")
                print(f"      - download_model_hf.py의 CTranslate2 변환 로그 확인")
            elif "model.bin" in error_str.lower():
                print(f"\n   💡 분석: model.bin 로드 오류")
                print(f"      - model.bin 파일이 손상되었을 가능성")
                print(f"      - CTranslate2 변환 재실행 필요")
            elif "not found" in error_str.lower() or "no such file" in error_str.lower():
                print(f"\n   💡 분석: 파일 경로 오류")
                print(f"      - 모델 경로 확인: {self.model_path}")
                print(f"      - ctranslate2_model 폴더 존재 여부 확인")
            else:
                print(f"\n   💡 상세 진단을 위해 다음을 확인하세요:")
                print(f"      1. {self.model_path}/ctranslate2_model/ 폴더")
                print(f"      2. model.bin 파일 (100MB 이상)")
                print(f"      3. config.json 파일")
                print(f"      4. vocabulary.json 또는 tokens.json 파일")

    
    def _try_whisper(self):
        """
        OpenAI Whisper로 모델 로드 시도 (로컬 경로만 사용)
        
        운영서버 배포:
        - 모델은 별도 볼륨으로 관리 (Docker와 분리)
        - 실행: docker run -v /models/large-v3-turbo:/app/models
        - 모델 파일은 Docker 이미지에 포함되지 않음
        """
        try:
            print(f"🔄 OpenAI Whisper 모델 로드 시도... (디바이스: {self.device})")
            
            model_path = Path(self.model_path)
            
            # 모델 경로 존재 확인
            if not model_path.exists():
                print(f"   ⚠️  모델 경로를 찾을 수 없음: {model_path}")
                print(f"   💡 확인사항:")
                print(f"      1. 운영서버에 모델이 있는가?")
                print(f"      2. Docker 실행 시 -v 옵션으로 마운트했는가?")
                print(f"         예: docker run -v /models/large-v3-turbo:/app/models ...")
                return
            
            # 로컬 경로에서 PyTorch 모델 직접 로드
            print(f"   📂 로컬 모델 로드: {model_path}")
            
            self.model = whisper.load_model(
                str(model_path),
                device=self.device,
                in_memory=False,
                download_root=None  # 🔒 다운로드 방지
            )
            
            self.backend = "whisper"
            print(f"✅ OpenAI Whisper 모델 로드 성공")
            
        except FileNotFoundError as e:
            print(f"❌ OpenAI Whisper: 모델 파일을 찾을 수 없음 - {e}")
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
