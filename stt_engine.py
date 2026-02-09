#!/usr/bin/env python3
"""
STT 모듈 - 3가지 백엔드 자동 선택

우선순위:
1. faster-whisper + CTranslate2 (가장 빠름, 권장)
2. transformers WhisperForConditionalGeneration (HF 모델 직접 지원)
3. OpenAI Whisper (공식 모델만 지원, 대체용)

지원 모델 형식:
- CTranslate2: .tar.gz (변환됨)
- transformers: Hugging Face 형식 (PyTorch/SafeTensors)
- OpenAI Whisper: 공식 모델명만 (tiny, base, small, medium, large)
"""

import os
from pathlib import Path
from typing import Optional, Dict
import tarfile

# 세 가지 백엔드 시도
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False

try:
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import openai_whisper as whisper
    WHISPER_AVAILABLE = True
except ImportError:
    try:
        import whisper
        WHISPER_AVAILABLE = True
    except ImportError:
        WHISPER_AVAILABLE = False

if not (FASTER_WHISPER_AVAILABLE or TRANSFORMERS_AVAILABLE or WHISPER_AVAILABLE):
    raise ImportError(
        "다음 중 최소 하나의 패키지가 필요합니다:\n"
        "  1. faster-whisper + ctranslate2 (권장)\n"
        "  2. transformers (HF 모델 지원)\n"
        "  3. openai-whisper / whisper (공식 모델만 지원)"
    )


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
            compute_type: 계산 타입 ('float32', 'float16', 'int8')
        
        Raises:
            FileNotFoundError: 모델을 찾을 수 없음
            RuntimeError: 모든 백엔드 로드 실패
        
        지원 모델 형식:
        - CTranslate2: ctranslate2_model/ 폴더 (model.bin)
        - transformers: PyTorch/SafeTensors (pytorch_model.bin 또는 model.safetensors)
        - OpenAI Whisper: 공식 모델명만 (tiny, base, small, medium, large)
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
        
        print(f"\n📊 STT 모델 로드 시작")
        print(f"   모델 경로: {self.model_path}")
        print(f"   디바이스: {self.device}")
        print(f"   사용 가능한 백엔드:")
        print(f"     - faster-whisper: {FASTER_WHISPER_AVAILABLE}")
        print(f"     - transformers: {TRANSFORMERS_AVAILABLE}")
        print(f"     - openai-whisper: {WHISPER_AVAILABLE}\n")
        
        # 1️⃣ faster-whisper 시도 (CTranslate2 모델, 가장 빠름)
        if FASTER_WHISPER_AVAILABLE:
            self._try_faster_whisper()
        
        # 2️⃣ transformers 시도 (PyTorch/HF 모델)
        if self.backend is None and TRANSFORMERS_AVAILABLE:
            self._try_transformers()
        
        # 3️⃣ OpenAI Whisper 시도 (공식 모델만)
        if self.backend is None and WHISPER_AVAILABLE:
            self._try_whisper()
        
        # 모두 실패
        if self.backend is None:
            available = []
            if FASTER_WHISPER_AVAILABLE:
                available.append("faster-whisper")
            if TRANSFORMERS_AVAILABLE:
                available.append("transformers")
            if WHISPER_AVAILABLE:
                available.append("openai-whisper")
            
            raise RuntimeError(
                f"❌ 모든 백엔드 로드 실패 (사용 가능: {', '.join(available)})\n\n"
                "🔧 진단 체크리스트:\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"1. 모델 경로: {self.model_path}\n"
                f"2. 필요한 파일:\n"
                f"   - CTranslate2: {self.model_path}/ctranslate2_model/model.bin\n"
                f"   - PyTorch: {self.model_path}/pytorch_model.bin 또는 model.safetensors\n"
                f"3. 모델 다운로드: python download_model_hf.py\n"
                f"4. 로컬 캐시에서 복사: cp -r ~/.cache/huggingface/hub/models--openai--whisper-large-v3-turbo/snapshots/*/  {self.model_path}"
            )
        

        # faster-whisper 로드 실패하면 에러
        if self.backend is None:
            raise RuntimeError(
                "❌ faster-whisper 모델 로드 실패\n\n"
                "🔧 진단 체크리스트:\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"1. 모델 디렉토리 확인:\n"
                f"   경로: {self.model_path}\n"
                f"   필수: {self.model_path}/ctranslate2_model/model.bin (1.5GB+)\n\n"
                f"2. CTranslate2 변환 완료 확인:\n"
                f"   ls -lh {self.model_path}/ctranslate2_model/\n"
                f"   model.bin (1.5GB), config.json (2.2KB), vocabulary.json\n\n"
                "3. 모델 다운로드/변환:\n"
                "   python download_model_hf.py  # ~30-45분\n\n"
                "4. Docker 마운트 확인 (운영서버):\n"
                "   docker exec stt-engine ls -lh /app/models/ctranslate2_model/"
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
            
            # 모델 로드 시도 - CTranslate2 모델 서브디렉토리 사용
            # faster-whisper는 모델.bin과 tokenizer 파일들이 같은 디렉토리에 있어야 함
            ct2_model_dir = Path(self.model_path) / "ctranslate2_model"
            
            print(f"\n   📦 faster-whisper WhisperModel 로드 중...")
            print(f"   📁 모델 경로: {ct2_model_dir}")
            
            self.model = WhisperModel(
                str(ct2_model_dir),
                device=self.device,
                compute_type=self.compute_type,
                num_workers=4,
                cpu_threads=4,
                download_root=None,
                local_files_only=True
            )
            
            self.backend = self.model  # 실제 모델 객체를 backend에 저장
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
                print(f"      - 가능한 원인 1: model.bin 파일이 손상되었거나 불완전함")
                print(f"      - 가능한 원인 2: CTranslate2 변환이 제대로 되지 않음")
                print(f"      - 가능한 원인 3: config.json이 손상됨 (2.2KB 이상인지 확인)")
                print(f"\n   🔧 해결 방법:")
                print(f"      1. EC2에서 모델 재다운로드:")
                print(f"         rm -rf models/openai_whisper-large-v3-turbo")
                print(f"         python3 download_model_hf.py")
                print(f"      2. Docker 이미지 재빌드:")
                print(f"         bash scripts/build-server-image.sh")
                print(f"      3. 컨테이너 재실행 (모델 마운트)")
                print(f"         docker run -v $(pwd)/models:/app/models ...")
            elif "not found" in error_str.lower() or "no such file" in error_str.lower():
                print(f"\n   💡 분석: 파일 경로 오류")
                print(f"      - 모델 경로: {self.model_path}")
                print(f"      - ctranslate2_model 폴더가 존재하는지 확인")
                print(f"      - model.bin 파일이 있는지 확인")
                print(f"\n   🔧 해결 방법:")
                print(f"      1. 컨테이너 내부에서 확인:")
                print(f"         docker exec -it <container> ls -lh /app/models/openai_whisper-large-v3-turbo/ctranslate2_model/")
                print(f"      2. 마운트 확인:")
                print(f"         docker inspect <container> | grep -A 5 'Mounts'")
            else:
                print(f"\n   💡 상세 진단을 위해 다음을 확인하세요:")
                print(f"      1. {self.model_path}/ctranslate2_model/ 폴더 존재")
                print(f"      2. model.bin 파일 크기 (100MB 이상, 일반적으로 1.5GB)")
                print(f"      3. config.json 파일 크기 (2.2KB 이상)")
                print(f"      4. vocabulary.json 파일 존재")
                print(f"\n   📋 디버그 명령어:")
                print(f"      docker exec -it <container> bash")
                print(f"      ls -lh /app/models/openai_whisper-large-v3-turbo/ctranslate2_model/")
                print(f"      file /app/models/openai_whisper-large-v3-turbo/ctranslate2_model/config.json")

    
    def _try_transformers(self):
        """
        transformers WhisperForConditionalGeneration으로 모델 로드 시도
        
        특징:
        - Hugging Face 모델 직접 지원 (PyTorch/SafeTensors)
        - large-v3-turbo 포함 모든 HF Whisper 모델 지원
        - GPU 가속 가능
        - 더 느림 (faster-whisper 대비 2-3배)
        
        지원 파일:
        - pytorch_model.bin (PyTorch 형식)
        - model.safetensors (SafeTensors 형식, 더 빠름)
        - config.json, tokenizer.json 등
        """
        try:
            print(f"🔄 transformers로 모델 로드 시도... (디바이스: {self.device})")
            
            from transformers import WhisperProcessor, WhisperForConditionalGeneration
            import torch
            
            model_path = Path(self.model_path)
            
            # PyTorch 모델 파일 확인
            has_pytorch = (model_path / "pytorch_model.bin").exists()
            has_safetensors = (model_path / "model.safetensors").exists()
            
            if not (has_pytorch or has_safetensors):
                print(f"   ⚠️  PyTorch 모델 파일 없음 (pytorch_model.bin 또는 model.safetensors 필요)")
                return
            
            # 로컬 캐시에서 로드 (HF 허브 접근 방지)
            processor = WhisperProcessor.from_pretrained(str(model_path), local_files_only=True)
            model = WhisperForConditionalGeneration.from_pretrained(str(model_path), local_files_only=True)
            
            # GPU로 이동
            if self.device == "cuda" and torch.cuda.is_available():
                model = model.to(self.device)
            
            # 평가 모드
            model.eval()
            
            self.backend = type('TransformersBackend', (), {
                'processor': processor,
                'model': model,
                'device': self.device,
                'transcribe': self._transcribe_with_transformers
            })()
            
            print(f"   ✅ transformers 모델 로드 성공!")
            print(f"      타입: WhisperForConditionalGeneration")
            print(f"      파일: {'SafeTensors' if has_safetensors else 'PyTorch'}")
            
        except FileNotFoundError as e:
            print(f"   ⚠️  로컬 캐시 실패: {e}")
            print(f"      시도: Hugging Face 허브에서 다운로드...")
            
            try:
                from transformers import WhisperProcessor, WhisperForConditionalGeneration
                import torch
                
                processor = WhisperProcessor.from_pretrained("openai/whisper-large-v3-turbo")
                model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-large-v3-turbo")
                
                if self.device == "cuda" and torch.cuda.is_available():
                    model = model.to(self.device)
                
                model.eval()
                
                self.backend = type('TransformersBackend', (), {
                    'processor': processor,
                    'model': model,
                    'device': self.device,
                    'transcribe': self._transcribe_with_transformers
                })()
                
                print(f"   ✅ HF 허브에서 모델 로드 성공!")
                
            except Exception as e2:
                print(f"   ❌ HF 허브 로드 실패: {type(e2).__name__}")
                
        except Exception as e:
            print(f"   ❌ transformers 로드 실패: {type(e).__name__}")
            print(f"      에러: {str(e)[:150]}")
    
    def _transcribe_with_transformers(self, audio_path: str, language: Optional[str] = None) -> Dict:
        """
        transformers를 사용한 음성 인식
        """
        import librosa
        import torch
        
        try:
            # 음성 로드
            audio, sr = librosa.load(audio_path, sr=16000)
            
            # 프로세싱
            input_features = self.backend.processor(audio, sampling_rate=16000, return_tensors="pt").input_features
            
            if self.device == "cuda":
                input_features = input_features.to(self.device)
            
            # 추론
            with torch.no_grad():
                predicted_ids = self.backend.model.generate(input_features)
            
            # 디코딩
            transcription = self.backend.processor.batch_decode(predicted_ids, skip_special_tokens=True)
            
            return {
                "text": transcription[0] if transcription else "",
                "language": language or "auto",
                "backend": "transformers"
            }
        
        except Exception as e:
            return {
                "text": "",
                "error": f"transformers transcription failed: {e}",
                "backend": "transformers"
            }

    
    def _try_whisper(self):
        """
        OpenAI Whisper로 모델 로드 시도
        
        ⚠️ 공식 모델만 지원 (tiny, base, small, medium, large)
        large-v3-turbo는 OpenAI 공식 모델이 아니므로 불가능합니다.
        """
        try:
            print(f"🔄 OpenAI Whisper 시도... (공식 모델만 지원)")
            
            import whisper
            
            # OpenAI Whisper 지원 모델 확인
            supported_models = whisper.available_models()
            
            model_path = Path(self.model_path)
            model_name = model_path.name
            
            # large-v3-turbo는 OpenAI 공식 모델이 아님
            if "turbo" in model_name.lower() or "v3-turbo" in model_name.lower():
                print(f"   ⚠️  '{model_name}'은(는) OpenAI 공식 모델이 아님")
                print(f"       지원 모델: {supported_models}")
                return
            
            # 공식 모델인지 확인
            if not any(m in model_name for m in ['tiny', 'base', 'small', 'medium', 'large']):
                print(f"   ⚠️  '{model_name}'은(는) 공식 모델이 아님")
                print(f"       지원 모델: {supported_models}")
                return
            
            # 로드 시도
            model = whisper.load_model("large", device=self.device)
            
            self.backend = type('WhisperBackend', (), {
                'model': model,
                'device': self.device,
                'transcribe': self._transcribe_with_whisper
            })()
            
            print(f"   ✅ OpenAI Whisper 모델 로드 성공! (large)")
            
        except Exception as e:
            print(f"   ❌ OpenAI Whisper 로드 실패: {type(e).__name__}")
    
    def _transcribe_with_whisper(self, audio_path: str, language: Optional[str] = None) -> Dict:
        """OpenAI Whisper를 사용한 음성 인식"""
        try:
            result = self.backend.model.transcribe(audio_path, language=language)
            return {
                "text": result.get("text", ""),
                "language": result.get("language", ""),
                "backend": "whisper"
            }
        except Exception as e:
            return {
                "text": "",
                "error": f"whisper transcription failed: {e}",
                "backend": "whisper"
            }
    
    @staticmethod
    def _explain_openai_whisper_limitations():
        """
        OpenAI Whisper의 아키텍처 제한사항 설명
        (이 메서드는 참고 목적으로만 유지됨)
        
        ⚠️ OpenAI Whisper.load_model()의 제한사항:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        - 공식 모델만 지원: tiny, base, small, medium, large, turbo
        - 커스텀 모델 지원 안함: large-v3, large-v3-turbo 등
        - 로컬 PyTorch 모델 직접 로드 불가
        - 모델명 hardcoding: 화이트리스트에 없는 모델 거부
        
        따라서 faster-whisper + CTranslate2가 유일한 솔루션입니다.
        """
        print("\n❌ OpenAI Whisper 지원 불가 (아키텍처 제한):")
        print("━" * 60)
        print("OpenAI Whisper.load_model()은 공식 모델만 지원합니다:")
        print("  ✓ tiny.en, tiny, base.en, base")
        print("  ✓ small.en, small, medium.en, medium")
        print("  ✓ large, turbo (일부)")
        print("\nHugging Face 커스텀 모델 미지원:")
        print("  ✗ large-v3, large-v3-turbo (이 프로젝트의 모델)")
        print("  ✗ 로컬 PyTorch 모델 직접 로드 불가")
        print("\n💡 솔루션: faster-whisper + CTranslate2 또는 transformers 사용")
        print("━" * 60)

    
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
            
            # 백엔드 타입 확인 및 처리
            if self.backend is None:
                raise RuntimeError("모델이 로드되지 않았습니다")
            
            # 백엔드 타입에 따라 처리
            backend_type = type(self.backend).__name__
            print(f"🔧 사용 중인 백엔드: {backend_type} (객체: {self.backend})")
            
            if backend_type == 'WhisperModel':
                # faster-whisper
                return self._transcribe_faster_whisper(audio_path, language, **kwargs)
            elif backend_type == 'TransformersBackend':
                # transformers
                return self._transcribe_with_transformers(audio_path, language)
            elif backend_type == 'WhisperBackend':
                # OpenAI Whisper
                return self._transcribe_with_whisper(audio_path, language)
            elif backend_type == 'str':
                # 문자열이 저장된 경우 (버그)
                raise RuntimeError(f"❌ 버그: backend가 문자열로 저장됨: {self.backend}")
            else:
                # 제네릭 백엔드 객체 처리
                if hasattr(self.backend, 'transcribe'):
                    result = self.backend.transcribe(audio_path, language)
                    return result
                else:
                    raise RuntimeError(f"지원하지 않는 백엔드: {backend_type} (value: {self.backend})")
        
        except Exception as e:
            print(f"❌ 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "audio_path": audio_path
            }
    
    def _transcribe_faster_whisper(self, audio_path: str, language: Optional[str] = None, **kwargs) -> Dict:
        """faster-whisper (WhisperModel)로 변환"""
        segments, info = self.backend.transcribe(
            audio_path,
            language=language,
            beam_size=kwargs.get("beam_size", 5),
            best_of=kwargs.get("best_of", 5),
            patience=kwargs.get("patience", 1),
            temperature=kwargs.get("temperature", 0)
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
