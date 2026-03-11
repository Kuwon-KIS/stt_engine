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
import logging
import json
import numpy as np
import threading
import gc

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        
        # 🔑 OpenAI Whisper용 심링크 자동 생성 (오프라인 환경 지원)
        self._create_whisper_symlinks()
        
        self.device = device if device != "auto" else ("cuda" if self._is_cuda_available() else "cpu")
        self.compute_type = compute_type
        self.backend = None
        self.preset = None  # 현재 선택된 프리셋 저장용
        
        # Custom preset용 세그먼트 설정 저장소
        self.custom_segment_config = {
            "chunk_duration": 30,
            "overlap_duration": 3
        }
        
        # 🔒 GPU 메모리 정리용 Lock (동시 요청 시 gc/cuda 충돌 방지)
        self._memory_cleanup_lock = threading.Lock()
        
        # 사용 가능한 백엔드 추적용 플래그
        self.faster_whisper_available = False
        self.transformers_available = False
        self.whisper_available = False
        
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
    
    def _create_whisper_symlinks(self) -> None:
        """
        OpenAI Whisper용 symlink 자동 생성
        
        whisper.load_model()은 다음 경로 구조를 기대함:
        {WHISPER_CACHE}/{model_name}/model.bin
        
        현재 경로:
        /app/models/openai_whisper-large-v3-turbo/model.bin
        
        필요한 경로:
        /app/models/large-v3-turbo/model.bin (symlink 또는 복사)
        """
        try:
            model_path = Path(self.model_path)
            model_name = model_path.name
            
            # 모델명 정규화
            # openai_whisper-large-v3-turbo → large-v3-turbo
            model_base_name = model_name.replace("openai_whisper-", "").replace("openai-whisper-", "")
            
            if model_base_name == model_name:
                # 이미 정규화된 이름 (예: large-v3-turbo)
                return
            
            # symlink 대상 경로
            parent_dir = model_path.parent
            symlink_path = parent_dir / model_base_name
            
            # 이미 존재하면 스킵
            if symlink_path.exists():
                print(f"ℹ️  심링크 이미 존재: {symlink_path}")
                return
            
            # symlink 생성 시도
            try:
                symlink_path.symlink_to(model_path)
                print(f"✅ Whisper용 심링크 생성: {model_base_name} → {model_name}")
            except (FileExistsError, OSError) as e:
                # symlink 실패: 복사로 대체
                import shutil
                print(f"⚠️  심링크 생성 실패 ({type(e).__name__}), 파일 복사로 대체...")
                shutil.copytree(model_path, symlink_path, dirs_exist_ok=True)
                print(f"✅ 파일 복사 완료: {model_base_name}")
        except Exception as e:
            print(f"⚠️  Whisper symlink/복사 실패: {type(e).__name__}: {e}")
            print(f"   → 계속 진행 (transformers/faster-whisper 사용 가능)")
    
    
    def _try_faster_whisper(self):
        """faster-whisper로 모델 로드 시도 (로컬 모델만 사용, 상세 진단 포함)"""
        try:
            logger.info(f"🔄 faster-whisper 모델 로드 시도... (디바이스: {self.device}, compute: {self.compute_type})")
            
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
            # faster-whisper가 tokenizer 파일을 이 디렉토리에서 찾음
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
            # WhisperModel 객체에 _backend_type 속성 추가
            if not hasattr(self.backend, '_backend_type'):
                self.backend._backend_type = 'faster-whisper'
            self.faster_whisper_available = True  # 플래그 설정
            logger.info(f"✅ faster-whisper 모델 로드 성공")
            
        except FileNotFoundError as e:
            logger.error(f"❌ faster-whisper: 파일을 찾을 수 없음", exc_info=True)
            logger.error(f"   경로: {self.model_path}")
            logger.error(f"   해결: download_model_hf.py 및 CTranslate2 변환 확인")
        except Exception as e:
            error_str = str(e)
            logger.error(f"❌ faster-whisper 로드 실패: {type(e).__name__}", exc_info=True)
            logger.error(f"   메시지: {error_str[:200]}")
            
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
                'transcribe': self._transcribe_with_transformers,
                '_backend_type': 'transformers'  # 백엔드 타입 식별자 추가
            })()
            self.transformers_available = True  # 플래그 설정
            
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
                    'transcribe': self._transcribe_with_transformers,
                    '_backend_type': 'transformers'  # 백엔드 타입 식별자 추가
                })()
                self.transformers_available = True  # 플래그 설정
                
                print(f"   ✅ HF 허브에서 모델 로드 성공!")
                
            except Exception as e2:
                print(f"   ❌ HF 허브 로드 실패: {type(e2).__name__}")
                
        except Exception as e:
            print(f"   ❌ transformers 로드 실패: {type(e).__name__}")
            print(f"      에러: {str(e)[:150]}")
    
    def _transcribe_with_transformers(self, audio_path: str, language: Optional[str] = None) -> Dict:
        """
        transformers를 사용한 음성 인식 (세그먼트 처리)
        
        Whisper는 최대 30초 음성만 처리 가능하므로,
        긴 음성은 30초 단위로 나눠서 처리 후 결합합니다.
        """
        import torch
        import numpy as np
        import gc
        from stt_utils import check_memory_available
        
        # 기본값: 한국어 (명시하지 않으면 "ko" 사용)
        language_to_use = language or "ko"
        
        if language_to_use.lower() in ['ko', 'korean']:
            language_to_use = 'ko'
        else:
            language_to_use = language_to_use.lower()
        
        logger.info(f"[transformers] 변환 시작 (파일: {Path(audio_path).name}, 언어: {language_to_use})")
        
        # 📊 처리 시작 메모리 상태
        start_memory = check_memory_available()
        logger.info(f"[transformers] 시작 메모리: {start_memory['available_mb']}MB ({start_memory['used_percent']:.1f}% 사용)")
        
        try:
            from stt_utils import check_memory_available, check_audio_file
            
            # 1. 파일 검증
            logger.debug(f"[transformers] 파일 검증 중...")
            file_check = check_audio_file(audio_path, logger=logger)
            if not file_check['valid']:
                error_msg = f"transformers transcription failed: 파일 검증 실패 - {file_check['errors'][0]}"
                logger.error(f"❌ {error_msg}")
                return {
                    "text": "",
                    "error": error_msg,
                    "backend": "transformers"
                }
            
            logger.info(f"✓ 파일 검증 완료 (길이: {file_check['duration_sec']:.1f}초)")
            
            # 경고 출력
            for warning in file_check['warnings']:
                logger.warning(f"⚠️  {warning}")
            
            # 2. 메모리 확인 (모델 크기 약 3GB + 처리용 1GB = 4GB)
            logger.debug(f"[transformers] 메모리 확인 중...")
            memory_check = check_memory_available(required_mb=4000, logger=logger)
            if memory_check['critical']:
                error_msg = f"transformers transcription failed: 메모리 부족 - {memory_check['message']}"
                logger.error(f"❌ {error_msg}")
                return {
                    "text": "",
                    "error": error_msg,
                    "backend": "transformers",
                    "memory_info": memory_check
                }
            
            logger.info(f"✓ 메모리 확인 완료 (사용 가능: {memory_check['available_mb']:.0f}MB)")
            
            # 3. 음성 로드 (scipy 사용 - librosa의 pkg_resources 의존성 제거)
            logger.info(f"[transformers] 음성 파일 로드 중: {Path(audio_path).name}")
            try:
                from scipy.io import wavfile as wav_file
                import soundfile as sf
                
                # soundfile이 있으면 사용 (더 안정적)
                try:
                    audio, sr = sf.read(audio_path, dtype='float32')
                    logger.debug(f"[transformers] soundfile로 오디오 로드 완료")
                except ImportError:
                    # soundfile 없으면 scipy 사용
                    sr, audio = wav_file.read(audio_path)
                    audio = audio.astype('float32')
                    # 스테레오일 경우 모노로 변환
                    if len(audio.shape) > 1:
                        audio = audio.mean(axis=1)
                    logger.debug(f"[transformers] scipy로 오디오 로드 완료")
                
                # 16kHz로 리샘플
                if sr != 16000:
                    logger.info(f"[transformers] 리샘플링: {sr}Hz → 16000Hz")
                    from scipy import signal
                    num_samples = int(len(audio) * 16000 / sr)
                    audio = signal.resample(audio, num_samples)
                    sr = 16000
                
                duration_seconds = len(audio) / sr
                logger.info(f"✓ 음성 로드 완료 (길이: {duration_seconds:.1f}초, 샘플: {len(audio):,}, SR: {sr}Hz)")
            except ModuleNotFoundError as e:
                error_msg = f"transformers transcription failed: 오디오 로드 실패 - {type(e).__name__}: {str(e)[:100]}"
                logger.error(f"❌ {error_msg}", exc_info=True)
                return {
                    "text": "",
                    "error": error_msg,
                    "backend": "transformers"
                }
            except MemoryError as e:
                error_msg = f"transformers transcription failed: 메모리 부족 - 오디오 로드 실패"
                logger.error(f"❌ {error_msg}", exc_info=True)
                return {
                    "text": "",
                    "error": error_msg,
                    "backend": "transformers"
                }
            except Exception as e:
                error_msg = f"transformers transcription failed: 오디오 로드 실패 - {type(e).__name__}: {str(e)[:100]}"
                logger.error(f"❌ {error_msg}", exc_info=True)
                return {
                    "text": "",
                    "error": error_msg,
                    "backend": "transformers"
                }
            
            # Whisper 최대 입력: 30초 (480,000 샘플 @ 16kHz)
            max_samples = 30 * sr  # 480,000 샘플
            
            # 프리셋에 따라 동적으로 오버랩 조정
            from api_server.constants import PRESET_SEGMENT_CONFIG
            
            # 현재 프리셋 또는 기본값(accuracy) 사용
            current_preset = self.preset or "accuracy"
            
            # ✅ Custom preset 처리: custom_segment_config 사용
            if current_preset == "custom":
                chunk_duration = self.custom_segment_config.get("chunk_duration", 30)
                overlap_seconds = self.custom_segment_config.get("overlap_duration", 3)
                logger.info(f"[transformers] 세그멘트 설정 (프리셋: CUSTOM)")
                logger.info(f"  - chunk_duration: {chunk_duration}초")
                logger.info(f"  - overlap_duration: {overlap_seconds}초")
            elif current_preset in PRESET_SEGMENT_CONFIG:
                # 표준 프리셋 사용
                preset_config = PRESET_SEGMENT_CONFIG[current_preset]
                overlap_seconds = preset_config["overlap_duration"]
                logger.info(f"[transformers] 세그멘트 설정 (프리셋: {current_preset})")
                logger.info(f"  - overlap_duration: {overlap_seconds}초")
            else:
                # ❌ 프리셋이 존재하지 않음 - 오류 처리
                error_msg = f"지원하지 않는 프리셋: {current_preset}. 사용 가능: {list(PRESET_SEGMENT_CONFIG.keys())} 또는 'custom'"
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)
            overlap_samples = int(overlap_seconds * sr)
            
            # hop_length 계산: 세그먼트 사이의 이동 거리
            hop_length = max_samples - overlap_samples
            
            logger.info(f"[transformers] 세그멘트 설정 (프리셋: {current_preset})")
            logger.info(f"  - 세그먼트 크기: 30초 ({max_samples:,} 샘플)")
            logger.info(f"  - 오버랩: {overlap_seconds}초 ({overlap_samples:,} 샘플)")
            logger.info(f"  - 이동거리(hop_length): {hop_length/sr:.1f}초 ({hop_length:,} 샘플)")
            
            all_texts = []
            start_idx = 0
            segment_idx = 0
            total_segments = (len(audio) + hop_length - 1) // hop_length
            
            logger.info(f"[transformers] 세그먼트 처리 시작 (총 {total_segments}개 세그먼트)")
            
            # 📊 세그먼트 루프 시작 전 메모리 정리
            logger.debug(f"[transformers] 세그먼트 루프 시작 전 메모리 정리")
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()
            pre_loop_memory = check_memory_available()
            logger.info(f"[transformers] 루프 시작 전 메모리: {pre_loop_memory['available_mb']}MB ({pre_loop_memory['used_percent']:.1f}%)")
            
            while start_idx < len(audio):
                try:
                    # 세그먼트 추출
                    end_idx = min(start_idx + max_samples, len(audio))
                    segment = audio[start_idx:end_idx]
                    segment_duration = len(segment) / sr
                    
                    logger.info(f"[transformers] 세그먼트 {segment_idx+1}/{total_segments}: {start_idx//sr:.1f}~{end_idx//sr:.1f}초 ({segment_duration:.1f}초)")
                    
                    # 프로세싱 (메모리 체크)
                    logger.info(f"[transformers] 세그먼트 {segment_idx} 프로세싱 중...")
                    try:
                        # ⚠️ CRITICAL: 임시 변수 사용으로 메모리 누수 방지
                        processor_output = self.backend.processor(
                            segment, 
                            sampling_rate=16000, 
                            return_tensors="pt"
                        )
                        input_features = processor_output.input_features
                        del processor_output  # 즉시 삭제 (메모리 누수 방지)
                        del segment  # segment도 삭제
                        logger.info(f"✓ 프로세싱 완료 (input_features shape: {input_features.shape})")
                    except MemoryError:
                        error_msg = f"transformers transcription failed: 메모리 부족 - 세그먼트 {segment_idx} 처리 중"
                        logger.error(f"❌ {error_msg}", exc_info=True)
                        return {
                            "text": "",
                            "error": error_msg,
                            "backend": "transformers",
                            "segment_failed": segment_idx,
                            "partial_text": " ".join(all_texts) if all_texts else ""
                        }
                    except Exception as e:
                        error_msg = f"transformers transcription failed: 프로세싱 실패 - {type(e).__name__}: {str(e)[:100]}"
                        logger.error(f"❌ {error_msg}", exc_info=True)
                        return {
                            "text": "",
                            "error": error_msg,
                            "backend": "transformers",
                            "segment_failed": segment_idx
                        }
                    
                    # 모델의 dtype에 맞추기 (float32 → float16)
                    model_dtype = self.backend.model.dtype
                    logger.info(f"[transformers] 모델 dtype: {model_dtype}, device: {self.device}")
                    input_features = input_features.to(model_dtype)
                    
                    if self.device == "cuda":
                        input_features = input_features.to(self.device)
                        torch.cuda.synchronize()  # 동기화 지점
                    
                    # 추론 (language 지정)
                    logger.info(f"[transformers] 세그먼트 {segment_idx} 추론 시작 (num_beams={1 if current_preset == 'speed' else 2})...")
                    try:
                        with torch.no_grad():
                            # 프리셋별 generate 파라미터 조정
                            if current_preset == "speed":
                                num_beams_val = 1
                                logger.info(f"[transformers] generate() 파라미터 (speed preset):")
                                logger.info(f"  - num_beams=1 (빠른 추론)")
                            else:
                                num_beams_val = 1  # accuracy preset도 1로 설정 (안정성 우선)
                                logger.info(f"[transformers] generate() 파라미터 ({current_preset} preset):")
                                logger.info(f"  - num_beams=1 (안정성 우선, hang 방지)")
                            
                            logger.info(f"  - early_stopping=True")
                            logger.info(f"  - temperature=0.0 (Greedy)")
                            logger.info(f"  - max_length=448")
                            
                            logger.info(f"[transformers] model.generate() 호출 중...")
                            predicted_ids = self.backend.model.generate(
                                input_features, 
                                language=language_to_use,
                                # === 안정성 우선 ===
                                num_beams=num_beams_val,
                                early_stopping=True,
                                length_penalty=1.0,
                                temperature=0.0,
                                # === 반복 방지 ===
                                repetition_penalty=1.2,
                                # === 선택사항 ===
                                max_length=448,
                                no_repeat_ngram_size=2
                            )
                            logger.info(f"✓ 추론 완료 (predicted_ids shape: {predicted_ids.shape})")
                    except RuntimeError as e:
                        if "out of memory" in str(e).lower() or "cuda" in str(e).lower():
                            error_msg = f"transformers transcription failed: GPU 메모리 부족 - 세그먼트 {segment_idx} 추론 중"
                            logger.error(f"❌ {error_msg}", exc_info=True)
                            return {
                                "text": "",
                                "error": error_msg,
                                "backend": "transformers",
                                "segment_failed": segment_idx,
                                "partial_text": " ".join(all_texts) if all_texts else "",
                                "suggestion": "CPU 모드로 전환하거나 -e STT_DEVICE=cpu 사용"
                            }
                        logger.error(f"❌ 추론 실패: {e}", exc_info=True)
                        raise
                    except MemoryError:
                        error_msg = f"transformers transcription failed: 메모리 부족 - 세그먼트 {segment_idx} 추론 중"
                        logger.error(f"❌ {error_msg}", exc_info=True)
                        return {
                            "text": "",
                            "error": error_msg,
                            "backend": "transformers",
                            "segment_failed": segment_idx,
                            "partial_text": " ".join(all_texts) if all_texts else ""
                        }
                    
                    # 디코딩
                    logger.info(f"[transformers] 세그먼트 {segment_idx} 디코딩 중...")
                    transcription = self.backend.processor.batch_decode(
                        predicted_ids, 
                        skip_special_tokens=True
                    )
                    logger.info(f"✓ 디코딩 완료")
                    
                    text = transcription[0] if transcription else ""
                    if text.strip():
                        all_texts.append(text)
                        logger.info(f"[TRANSCRIBE] 세그먼트 {segment_idx}: '{text[:60]}...'")
                    else:
                        logger.info(f"[TRANSCRIBE] 세그먼트 {segment_idx}: (무음)")
                    
                    # 메모리 정리 (Lock 제외 - 세그먼트 루프 내에서는 경합 피함)
                    logger.info(f"[transformers] 세그먼트 {segment_idx} 메모리 정리 중...")
                    del input_features, predicted_ids
                    gc.collect()  # Python 메모리만 정리 (빠름)
                    
                    # 🔒 CRITICAL: 매 세그먼트마다 GPU 캐시 정리 (메모리 누수 방지)
                    if self.device == "cuda":
                        torch.cuda.empty_cache()
                    
                    # 📊 메모리 상태 모니터링 (매 5개 세그먼트마다)
                    if segment_idx % 5 == 0:  # 5개 세그먼트마다 체크
                        current_memory = check_memory_available()
                        logger.info(f"[transformers] 세그먼트 {segment_idx} 후 메모리: "
                                   f"{current_memory['available_mb']}MB ({current_memory['used_percent']:.1f}%)")
                        
                        # 메모리가 위험 수준이면 경고
                        if current_memory['critical']:
                            logger.warning(f"⚠️  메모리 위험 상태: {current_memory['message']}")
                    
                except Exception as e:
                    if "out of memory" not in str(e).lower():
                        logger.warning(f"⚠️  세그먼트 {segment_idx} 처리 실패: {type(e).__name__}: {str(e)[:100]}")
                    raise
                
                # 다음 세그먼트 (50% 오버랩)
                logger.info(f"[transformers] 세그먼트 {segment_idx} 완료 → 다음 세그먼트로 이동")
                start_idx += hop_length
                segment_idx += 1
            
            # 결과 합치기
            logger.info(f"[transformers] 모든 세그먼트 처리 완료! (총 {segment_idx}개 처리됨)")
            full_text = " ".join(all_texts)
            
            # 📊 최종 메모리 상태
            end_memory = check_memory_available()
            memory_peak = start_memory['used_percent'] - end_memory['available_mb'] / start_memory['total_mb'] * 100
            
            logger.info(f"[TRANSCRIBE] 완료 - {segment_idx}개 세그먼트, 총 {duration_seconds:.1f}초 처리")
            logger.info(f"[TRANSCRIBE] 최종 메모리: {end_memory['available_mb']}MB ({end_memory['used_percent']:.1f}%)")
            logger.info(f"[TRANSCRIBE] 메모리 변화: {start_memory['available_mb']}MB → {end_memory['available_mb']}MB")
            
            # 최종 메모리 정리
            del audio, all_texts
            # 🔒 Lock으로 보호하여 동시 요청 중 GPU 메모리 정리 충돌 방지
            with self._memory_cleanup_lock:
                gc.collect()
                if self.device == "cuda":
                    torch.cuda.empty_cache()
            
            return {
                "success": True,
                "text": full_text,
                "language": language_to_use,
                "backend": "transformers",
                "duration": duration_seconds,
                "segments_processed": segment_idx
            }
        
        except MemoryError as e:
            error_msg = f"transformers transcription failed: 메모리 부족"
            logger.error(f"❌ {error_msg}")
            return {
                "text": "",
                "error": error_msg,
                "backend": "transformers",
                "memory_error": True
            }
        except Exception as e:
            error_msg = f"transformers transcription failed: {type(e).__name__}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error("Traceback:", exc_info=True)
            return {
                "text": "",
                "error": error_msg,
                "backend": "transformers"
            }

    
    def _try_whisper(self):
        """
        OpenAI Whisper로 모델 로드 시도 (원본 공식 구현)
        
        ✅ 공식 모델 지원: tiny, base, small, medium, large, large-v1, large-v2, large-v3, large-v3-turbo, turbo
        ✅ 오프라인 환경: /app/models 경로에서 자동 감지
        """
        try:
            print(f"🔄 OpenAI Whisper 시도... (공식 Whisper API)")
            
            import whisper
            import os
            
            # OpenAI Whisper 지원 모델 확인 (동적으로 호출)
            supported_models = whisper.available_models()
            
            model_path = Path(self.model_path)
            model_name = model_path.name
            
            # 모델명 정규화
            # openai_whisper-large-v3-turbo → large-v3-turbo
            model_base_name = model_name.replace("openai_whisper-", "").replace("openai-whisper-", "")
            
            # 지원 여부 확인
            is_supported = model_base_name in supported_models
            
            if not is_supported:
                print(f"   ⚠️  '{model_base_name}'은(는) OpenAI Whisper에서 지원하지 않음")
                print(f"       지원 모델: {', '.join(supported_models)}")
                return
            
            print(f"   📂 모델 경로: {model_path}")
            
            # 🔑 로컬 모델 경로 자동 감지 (인터넷 불필요)
            if model_path.exists():
                print(f"   ✓ 로컬 모델 파일 발견 (오프라인 모드)")
                
                # 검증: model.bin 파일 확인
                model_bin = model_path / "model.bin"
                if not model_bin.exists():
                    print(f"   ❌ model.bin 파일이 없음: {model_bin}")
                    return
                
                print(f"   ✓ model.bin 확인됨")
                
                # ✅ whisper.load_model()에 download_root 파라미터로 전달 (환경변수 아님!)
                cache_parent = str(model_path.parent)
                print(f"   → download_root 파라미터로 전달: {cache_parent}")
                
                # 심링크 생성 시도 (whisper.load_model()이 모델명으로 찾기 위해)
                cache_target = Path(cache_parent) / model_base_name
                if not cache_target.exists() and cache_target.parent == model_path.parent:
                    try:
                        cache_target.symlink_to(model_path)
                        print(f"   ✓ 심링크 생성: {model_base_name} → {model_path.name}")
                    except (FileExistsError, OSError, PermissionError) as e:
                        print(f"   ℹ️  심링크 생성 실패 ({type(e).__name__}), 파일 복사 시도...")
                        try:
                            import shutil
                            shutil.copytree(model_path, cache_target, dirs_exist_ok=True)
                            print(f"   ✓ 파일 복사 완료: {model_base_name}")
                        except Exception as copy_err:
                            print(f"   ⚠️  파일 복사도 실패: {copy_err}")
                
                # whisper.load_model() 호출 with download_root
                print(f"   → whisper.load_model('{model_base_name}', download_root='{cache_parent}')")
                model = whisper.load_model(model_base_name, device=self.device, download_root=cache_parent)
                print(f"   ✓ 로드 성공")
            else:
                # 모델 경로 없음: 기본 캐시 시도 (인터넷 필요)
                print(f"   🔗 로컬 모델 없음, whisper 기본 캐시 사용 (~/.cache/whisper)")
                model = whisper.load_model(model_base_name, device=self.device)
            
            self.backend = type('WhisperBackend', (), {
                'model': model,
                'device': self.device,
                'transcribe': self._transcribe_with_whisper,
                '_backend_type': 'openai-whisper'
            })()
            self.whisper_available = True
            
            print(f"   ✅ OpenAI Whisper 로드 성공! ({model_base_name})")
            
        except Exception as e:
            print(f"   ❌ OpenAI Whisper 로드 실패: {type(e).__name__}: {str(e)[:150]}")
            print(f"      → transformers 백엔드로 폴백 시도...")
    
    def _transcribe_with_whisper(self, audio_path: str, language: Optional[str] = None) -> Dict:
        """OpenAI Whisper를 사용한 음성 인식"""
        import torch
        import gc
        
        # 기본값: 한국어 (명시하지 않으면 "ko" 사용)
        language_to_use = language or "ko"
        
        if language_to_use.lower() in ['ko', 'korean']:
            language_to_use = 'ko'
        else:
            language_to_use = language_to_use.lower()
        
        logger.info(f"[openai-whisper] 변환 시작 (파일: {Path(audio_path).name}, 언어: {language_to_use})")
        
        try:
            logger.debug(f"[openai-whisper] 모델 호출: transcribe(audio_path, language={language_to_use})")
            result = self.backend.model.transcribe(audio_path, language=language_to_use)
            
            logger.info(f"✓ openai-whisper 변환 완료")
            
            text = result.get("text", "")
            detected_language = result.get("language", "unknown")
            logger.info(f"  결과: {len(text)} 글자, 언어: {detected_language}")
            
            # 🔒 메모리 정리 (동시 요청 시 Lock으로 보호)
            with self._memory_cleanup_lock:
                gc.collect()
                if self.device == "cuda":
                    torch.cuda.empty_cache()
            
            return {
                "success": True,
                "text": text.strip(),
                "language": detected_language,
                "backend": "openai-whisper"
            }
        except Exception as e:
            logger.error(f"❌ openai-whisper 변환 실패: {type(e).__name__}: {e}", exc_info=True)
            
            # 🔒 메모리 정리 (에러 발생 시에도 정리)
            with self._memory_cleanup_lock:
                gc.collect()
                if self.device == "cuda":
                    torch.cuda.empty_cache()
            
            return {
                "success": False,
                "text": "",
                "error": f"openai-whisper 변환 실패: {type(e).__name__}: {str(e)[:100]}",
                "backend": "openai-whisper"
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
    
    def get_backend_info(self) -> Dict:
        """
        현재 로드된 백엔드의 정보를 반환합니다.
        
        Returns:
            {
                "current_backend": "faster-whisper" | "transformers" | "openai-whisper",
                "backend_type": Python 클래스명,
                "device": "cpu" | "cuda",
                "compute_type": "float32" | "float16" | "int8",
                "model_path": 모델 경로,
                "available_backends": {
                    "faster-whisper": bool,
                    "transformers": bool,
                    "openai-whisper": bool
                },
                "loaded": True | False
            }
        """
        if self.backend is None:
            return {
                "current_backend": None,
                "backend_type": None,
                "device": self.device,
                "compute_type": self.compute_type,
                "model_path": self.model_path,
                "available_backends": {
                    "faster-whisper": FASTER_WHISPER_AVAILABLE,
                    "transformers": TRANSFORMERS_AVAILABLE,
                    "openai-whisper": WHISPER_AVAILABLE
                },
                "loaded": False
            }
        
        backend_type = type(self.backend).__name__
        current_backend = None
        
        if hasattr(self.backend, '_backend_type'):
            current_backend = self.backend._backend_type
        elif backend_type == 'WhisperModel':
            current_backend = "faster-whisper"
        elif backend_type == 'TransformersBackend':
            current_backend = "transformers"
        elif backend_type == 'WhisperBackend':
            current_backend = "openai-whisper"
        else:
            current_backend = "unknown"
        
        return {
            "current_backend": current_backend,
            "backend_type": backend_type,
            "device": self.device,
            "compute_type": self.compute_type,
            "model_path": self.model_path,
            "available_backends": {
                "faster-whisper": FASTER_WHISPER_AVAILABLE,
                "transformers": TRANSFORMERS_AVAILABLE,
                "openai-whisper": WHISPER_AVAILABLE
            },
            "loaded": True
        }
    
    def reload_backend(self, backend: Optional[str] = None, 
                       compute_type: Optional[str] = None,
                       device: Optional[str] = None,
                       preset: Optional[str] = None,
                       chunk_duration: Optional[float] = None,
                       overlap_duration: Optional[float] = None) -> Dict:
        """
        백엔드를 동적으로 재로드합니다.
        기존 백엔드를 언로드하고 새 백엔드를 로드합니다.
        
        Args:
            backend: 로드할 백엔드
                    - "faster-whisper": faster-whisper 사용
                    - "transformers": transformers 사용
                    - "openai-whisper": OpenAI Whisper 사용
                    - None (기본값): 기본 순서대로 자동 선택
            
            compute_type: 정확도/속도 설정 (faster-whisper만 적용)
                    - "int8" (기본): 양자화, 가장 빠름, 정확도 조금 낮음
                    - "float16": 중간, 정확도 좋음
                    - "float32": 최대 정확도, 가장 느림
                    - "auto": 자동 선택
            
            device: 연산 장치
                    - "cuda": NVIDIA GPU (기본)
                    - "cpu": CPU
            
            preset: 미리 설정된 프로필
                    - "speed": faster-whisper + int8 (가장 빠름)
                    - "balanced": faster-whisper + float16 (균형)
                    - "accuracy": transformers + float32 (최고 정확도) ⭐ 권장
                    - "custom": backend/compute_type/device를 사용자 지정값으로 사용
            
            chunk_duration: (custom preset용) 청크 크기 (초, 기본: 30)
            
            overlap_duration: (custom preset용) 오버랩 크기 (초, 기본: 3)
        
        Returns:
            {
                "status": "success" or "error",
                "current_backend": 로드된 백엔드 이름,
                "device": 사용 디바이스,
                "compute_type": 적용된 컴퓨트 타입,
                "preset": 적용된 프리셋,
                "custom_config": (custom preset 사용 시) 저장된 설정값,
                "message": 상세 메시지
            }
            
        예시:
            # 정확도 우선 모드 (transformers + float32)
            result = stt.reload_backend(preset="accuracy")
            
            # 속도 우선 모드 (faster-whisper + int8)
            result = stt.reload_backend(preset="speed")
            
            # 커스텀 설정 (세그먼트 크기 커스터마이징)
            result = stt.reload_backend(
                preset="custom",
                backend="transformers",
                compute_type="float32",
                chunk_duration=20,      # 20초 청크
                overlap_duration=2      # 2초 오버랩
            )
        """
        import gc
        
        # ✅ Custom preset용 세그먼트 설정 저장
        if chunk_duration is not None or overlap_duration is not None:
            if chunk_duration is not None:
                self.custom_segment_config["chunk_duration"] = chunk_duration
                logger.info(f"   → chunk_duration: {chunk_duration}초 저장")
            if overlap_duration is not None:
                self.custom_segment_config["overlap_duration"] = overlap_duration
                logger.info(f"   → overlap_duration: {overlap_duration}초 저장")
        
        # ✅ 반환값 생성 헬퍼 함수
        def _make_success_response(backend_name: str, msg: str):
            """성공 응답 생성 (preset 및 custom_config 포함)"""
            response = {
                "status": "success",
                "current_backend": backend_name,
                "preset": self.preset,
                "device": self.device,
                "compute_type": self.compute_type,
                "message": msg
            }
            if self.preset == "custom":
                response["custom_config"] = self.custom_segment_config.copy()
            return response
        
        # Preset 처리
        if preset:
            preset = preset.lower().strip()
            logger.info(f"📋 프리셋 모드: {preset}")
            
            # "custom"이 아니면 프리셋 설정 적용
            if preset != "custom":
                presets = {
                    "speed": {"backend": "faster-whisper", "compute_type": "int8", "device": self.device},
                    "balanced": {"backend": "faster-whisper", "compute_type": "float16", "device": self.device},
                    "accuracy": {"backend": "transformers", "compute_type": "float32", "device": self.device}
                }
                
                if preset not in presets:
                    error_msg = f"지원하지 않는 프리셋: {preset}. 사용 가능: {', '.join(presets.keys())} 또는 'custom'"
                    logger.error(f"❌ {error_msg}")
                    return {
                        "status": "error",
                        "message": error_msg,
                        "current_backend": self._get_current_backend_name()
                    }
                
                preset_config = presets[preset]
                backend = preset_config["backend"]
                compute_type = preset_config["compute_type"]
                device = preset_config["device"]
                
                # ✅ 선택된 프리셋 저장 (_transcribe_with_transformers에서 사용)
                self.preset = preset
                
                logger.info(f"   📌 {preset.upper()} 프리셋 설정:")
                logger.info(f"      backend={backend}")
                logger.info(f"      compute_type={compute_type}")
                logger.info(f"      device={device}")
            else:
                # custom: 사용자가 지정한 backend/compute_type/device 사용
                # ✅ custom preset 유지
                self.preset = "custom"
                self.preset = "custom"
                logger.info(f"   📌 CUSTOM 모드 (사용자 지정값 사용):")
                logger.info(f"      backend={backend}")
                logger.info(f"      compute_type={compute_type}")
        else:
            # ⚠️ Preset이 지정되지 않았을 때: backend 기반으로 자동 추론
            # backend만 지정된 경우 적절한 프리셋 결정
            if backend:
                backend_lower = backend.lower().strip()
                logger.info(f"📋 백엔드 기반 자동 프리셋 설정: {backend_lower}")
                
                if backend_lower == "transformers":
                    self.preset = "accuracy"  # transformers → accuracy preset
                    logger.info(f"   → transformers 감지: accuracy preset 적용")
                elif backend_lower == "faster-whisper":
                    # compute_type이 있으면 그에 맞는 프리셋, 없으면 balanced
                    if compute_type and compute_type.lower() == "int8":
                        self.preset = "speed"
                        logger.info(f"   → faster-whisper + int8 감지: speed preset 적용")
                    elif compute_type and compute_type.lower() == "float16":
                        self.preset = "balanced"
                        logger.info(f"   → faster-whisper + float16 감지: balanced preset 적용")
                    else:
                        self.preset = "balanced"  # 기본값
                        logger.info(f"   → faster-whisper 감지: balanced preset 적용 (기본값)")
                else:
                    self.preset = "accuracy"  # 기본값
                    logger.info(f"   → 기본값: accuracy preset 적용")
            else:
                # preset도 backend도 지정되지 않으면 기본값
                self.preset = "accuracy"
                logger.info(f"📋 기본값 적용: accuracy preset")
                logger.info(f"      device={device}")
        
        # 기존 백엔드 언로드 (메모리 정리)
        if self.backend is not None:
            logger.info(f"🔄 기존 백엔드 언로드 중...")
            try:
                # 메모리 명시적 해제
                if hasattr(self.backend, 'model'):
                    try:
                        del self.backend.model
                    except:
                        pass
                if hasattr(self.backend, 'processor'):
                    try:
                        del self.backend.processor
                    except:
                        pass
                if hasattr(self.backend, '_transformers_model'):
                    try:
                        del self.backend._transformers_model
                    except:
                        pass
                
                del self.backend
                self.backend = None
                
                # 모든 플래그 초기화 (이전 상태 제거)
                self.faster_whisper_available = False
                self.transformers_available = False
                self.whisper_available = False
                
                # GPU 메모리 정리 (🔒 Lock으로 보호)
                with self._memory_cleanup_lock:
                    gc.collect()
                    try:
                        import torch
                        torch.cuda.empty_cache()
                    except:
                        pass
                
                logger.info(f"✓ 기존 백엔드 언로드 완료 + 플래그 초기화")
            except Exception as e:
                logger.warning(f"⚠️  기존 백엔드 언로드 중 오류: {e}")
                # 강제 초기화
                self.backend = None
                self.faster_whisper_available = False
                self.transformers_available = False
                self.whisper_available = False
        
        # 옵션 적용
        if device:
            self.device = device.lower()
            logger.info(f"📍 Device 변경: {self.device}")
        
        if compute_type:
            self.compute_type = compute_type.lower()
            logger.info(f"🔢 Compute Type 변경: {self.compute_type}")
        
        # 새 백엔드 로드
        if backend:
            backend = backend.lower().strip()
            logger.info(f"📌 요청 백엔드: {backend}")
            
            # 백엔드 별칭 처리
            backend_aliases = {
                "faster-whisper": "faster-whisper",
                "faster_whisper": "faster-whisper",
                "transformers": "transformers",
                "openai-whisper": "openai-whisper",
                "openai_whisper": "openai-whisper",
                "whisper": "openai-whisper"
            }
            
            backend_canonical = backend_aliases.get(backend)
            if not backend_canonical:
                error_msg = f"지원하지 않는 백엔드: {backend}. 지원: faster-whisper, transformers, openai-whisper"
                logger.error(f"❌ {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "current_backend": self._get_current_backend_name()
                }
            
            # 요청된 백엔드만 로드 시도
            try:
                if backend_canonical == "faster-whisper":
                    if not FASTER_WHISPER_AVAILABLE:
                        raise RuntimeError("faster-whisper 패키지가 설치되지 않음")
                    logger.info(f"→ faster-whisper 로드 중... (compute_type={self.compute_type}, device={self.device})")
                    self._try_faster_whisper()
                    if self.backend is not None and self.faster_whisper_available:
                        logger.info(f"✅ faster-whisper 로드 성공")
                        return _make_success_response("faster-whisper", "faster-whisper 로드 완료")
                    raise RuntimeError("faster-whisper 로드 실패")
                
                elif backend_canonical == "transformers":
                    if not TRANSFORMERS_AVAILABLE:
                        raise RuntimeError("transformers 패키지가 설치되지 않음")
                    logger.info(f"→ transformers 로드 중... (device={self.device})")
                    self._try_transformers()
                    if self.backend is not None and self.transformers_available:
                        logger.info(f"✅ transformers 로드 성공")
                        return _make_success_response("transformers", "transformers 로드 완료")
                    raise RuntimeError("transformers 로드 실패")
                
                elif backend_canonical == "openai-whisper":
                    if not WHISPER_AVAILABLE:
                        raise RuntimeError("openai-whisper 패키지가 설치되지 않음")
                    logger.info(f"→ openai-whisper 로드 중...")
                    self._try_whisper()
                    if self.backend is not None and self.whisper_available:
                        logger.info(f"✅ openai-whisper 로드 성공")
                        return _make_success_response("openai-whisper", "openai-whisper 로드 완료")
                    raise RuntimeError("openai-whisper 로드 실패")
            
            except Exception as e:
                error_msg = f"{backend_canonical} 로드 실패: {type(e).__name__}: {str(e)[:100]}"
                logger.error(f"❌ {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "current_backend": self._get_current_backend_name()
                }
        
        else:
            # 기본 순서대로 자동 로드
            logger.info(f"→ 백엔드 자동 선택 (기본 순서)")
            
            if FASTER_WHISPER_AVAILABLE:
                try:
                    logger.info(f"→ faster-whisper 로드 중...")
                    self._try_faster_whisper()
                    if self.backend is not None:
                        logger.info(f"✅ faster-whisper 로드 성공")
                        return _make_success_response("faster-whisper", "faster-whisper 로드 완료 (자동 선택)")
                except Exception as e:
                    logger.warning(f"⚠️  faster-whisper 로드 실패: {e}")
            
            if self.backend is None and TRANSFORMERS_AVAILABLE:
                try:
                    logger.info(f"→ transformers 로드 중...")
                    self._try_transformers()
                    if self.backend is not None:
                        logger.info(f"✅ transformers 로드 성공")
                        return _make_success_response("transformers", "transformers 로드 완료 (자동 선택)")
                except Exception as e:
                    logger.warning(f"⚠️  transformers 로드 실패: {e}")
            
            if self.backend is None and WHISPER_AVAILABLE:
                try:
                    logger.info(f"→ openai-whisper 로드 중...")
                    self._try_whisper()
                    if self.backend is not None:
                        logger.info(f"✅ openai-whisper 로드 성공")
                        return _make_success_response("openai-whisper", "openai-whisper 로드 완료 (자동 선택)")
                except Exception as e:
                    logger.warning(f"⚠️  openai-whisper 로드 실패: {e}")
            
            # 모든 백엔드 로드 실패
            error_msg = "모든 백엔드 로드 실패"
            logger.error(f"❌ {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "current_backend": None
            }
    
    def _get_current_backend_name(self) -> Optional[str]:
        """현재 로드된 백엔드 이름 반환"""
        if self.faster_whisper_available:
            return "faster-whisper"
        elif self.transformers_available:
            return "transformers"
        elif self.whisper_available:
            return "openai-whisper"
        return None
    
    def transcribe(self, audio_path: str, language: Optional[str] = None, backend: Optional[str] = None, **kwargs) -> Dict:
        """
        음성 파일을 텍스트로 변환합니다.
        
        현재 로드된 백엔드를 사용합니다. 다른 백엔드를 사용하려면 reload_backend()를 호출하세요.
        모든 백엔드 실패 시 Dummy 응답을 반환합니다 (로깅 필수).
        
        Args:
            audio_path: 음성 파일 경로
            language: 음성 언어 코드 (예: 'ko', 'en')
            backend: 무시됨 (호환성 유지용, 사용하려면 reload_backend() 호출)
            **kwargs: 추가 옵션
        
        Returns:
            변환 결과 딕셔너리
            - success: True (성공) 또는 False (실패 또는 Dummy)
            - text: 변환된 텍스트 또는 빈 문자열
            - backend: 사용된 백엔드 이름 또는 'dummy'
            - is_dummy: Dummy 응답 여부
            - error: 에러 메시지 (실패/Dummy 시)
            
        예시:
            stt = WhisperSTT(model_path)  # faster-whisper 로드
            result = stt.transcribe("audio.wav", language="ko")
            
            # transformers로 변경하려면
            stt.reload_backend("transformers")
            result = stt.transcribe("audio.wav", language="ko")
        """
        audio_path_str = str(audio_path)
        
        try:
            logger.info(f"[STT] 음성 파일 로드 시작: {audio_path_str}")
            
            # 파일 존재 확인
            if not Path(audio_path_str).exists():
                logger.error(f"[STT] 파일을 찾을 수 없음: {audio_path_str}")
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {audio_path_str}")
            
            logger.info(f"[STT] 파일 존재 확인: {audio_path_str}")
            
            # 현재 로드된 백엔드 확인
            backend_type = type(self.backend).__name__
            if hasattr(self.backend, '_backend_type'):
                backend_name = self.backend._backend_type
                logger.info(f"[STT] 현재 로드된 백엔드: {backend_name}")
            else:
                backend_name = backend_type
                logger.info(f"[STT] 현재 로드된 백엔드: {backend_type}")
            
            # backend 파라미터는 무시 (reload_backend()를 사용해야 함)
            if backend:
                logger.warning(f"[STT] backend 파라미터는 무시됩니다. reload_backend()를 사용해주세요.")
            
            # 현재 로드된 백엔드로 변환 시작
            result = None
            if backend_name == "faster-whisper" or backend_type == 'WhisperModel':
                logger.info(f"[STT] faster-whisper 백엔드로 변환 시작")
                result = self._transcribe_faster_whisper(audio_path_str, language, **kwargs)
            elif backend_name == "transformers" or backend_type == 'TransformersBackend':
                logger.info(f"[STT] transformers 백엔드로 변환 시작")
                try:
                    result = self._transcribe_with_transformers(audio_path_str, language)
                except ValueError as e:
                    # Preset 설정 오류
                    logger.error(f"[STT] Preset 설정 오류: {e}")
                    return {
                        "success": False,
                        "error": f"Preset 설정 오류: {str(e)}",
                        "audio_path": audio_path_str,
                        "backend": "transformers",
                        "error_type": "InvalidPreset"
                    }
            elif backend_name == "openai-whisper" or backend_type == 'WhisperBackend':
                logger.info(f"[STT] openai-whisper 백엔드로 변환 시작")
                result = self._transcribe_with_whisper(audio_path_str, language)
            else:
                logger.info(f"[STT] 제네릭 백엔드 객체로 변환 시도 (타입: {backend_type})")
                if hasattr(self.backend, 'transcribe'):
                    result = self.backend.transcribe(audio_path_str, language)
                    logger.info(f"[STT] 제네릭 백엔드 변환 완료")
                else:
                    logger.error(f"[STT] 지원하지 않는 백엔드: {backend_type}")
                    raise RuntimeError(f"지원하지 않는 백엔드: {backend_type}")
            
            # 결과 반환
            if result and result.get('success'):
                logger.info(f"[STT] 변환 성공: {audio_path_str}")
                return result
            else:
                # 백엔드 실패 - Dummy로 fallback
                logger.warning(f"[STT] 백엔드 변환 실패, Dummy 응답으로 fallback")
                return self._create_dummy_response(
                    audio_path=audio_path_str,
                    language=language,
                    reason=result.get('error', '백엔드 변환 실패') if result else '백엔드 변환 실패'
                )
        
        except FileNotFoundError as e:
            logger.error(f"[STT] 파일 오류: {e}")
            logger.warning(f"[STT] Dummy 응답으로 fallback")
            return self._create_dummy_response(
                audio_path=audio_path_str,
                language=language,
                reason=str(e)
            )
        except ValueError as e:
            logger.error(f"[STT] 값 오류: {e}")
            logger.warning(f"[STT] Dummy 응답으로 fallback")
            return self._create_dummy_response(
                audio_path=audio_path_str,
                language=language,
                reason=str(e)
            )
        except RuntimeError as e:
            logger.error(f"[STT] 런타임 오류: {e}")
            logger.warning(f"[STT] Dummy 응답으로 fallback")
            return self._create_dummy_response(
                audio_path=audio_path_str,
                language=language,
                reason=str(e)
            )
        except Exception as e:
            logger.error(f"[STT] 예상치 못한 오류: {type(e).__name__}: {e}", exc_info=True)
            logger.warning(f"[STT] Dummy 응답으로 fallback")
            return self._create_dummy_response(
                audio_path=audio_path_str,
                language=language,
                reason=f"{type(e).__name__}: {str(e)}"
            )
    
    def _create_dummy_response(self, audio_path: str, language: Optional[str] = None, reason: str = "알 수 없는 오류") -> Dict:
        """
        Dummy STT 응답 생성
        
        Args:
            audio_path: 오디오 파일 경로
            language: 언어 코드
            reason: Dummy 사용 이유
        
        Returns:
            Dummy STT 응답
        """
        return {
            "success": False,
            "text": "",
            "text_en": "",
            "duration": 0,
            "language": language or "ko",
            "backend": "dummy",
            "is_dummy": True,
            "dummy_reason": reason,
            "error": reason,
            "error_type": "DummyFallback",
            "audio_path": audio_path
        }
    
    def _transcribe_faster_whisper(self, audio_path: str, language: Optional[str] = None, **kwargs) -> Dict:
        """faster-whisper (WhisperModel)로 변환
        
        주의: faster-whisper는 내부적으로 preprocessor_config.json에서 feature_size를 읽습니다.
        turbo 모델은 128 mel-bins을 필요로 합니다.
        """
        import locale
        import torch
        import gc
        
        logger.info(f"[faster-whisper] 변환 시작 (파일: {Path(audio_path).name})")
        
        # 로케일 설정 확인 및 로깅
        try:
            current_locale = locale.getlocale()
            logger.debug(f"[faster-whisper] 현재 로케일: {current_locale}")
            
            # UTF-8 로케일 설정 (한글 처리 개선)
            try:
                locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')
                logger.debug(f"[faster-whisper] 로케일 설정: ko_KR.UTF-8")
            except Exception as locale_e:
                logger.debug(f"[faster-whisper] ko_KR.UTF-8 설정 실패: {locale_e}, 기본값 사용")
        except Exception as e:
            logger.warning(f"[faster-whisper] 로케일 확인 실패: {e}")
        
        try:
            # language 파라미터 정규화 (한글 입력에 대한 alias 지원)
            # 기본값: 한국어 (명시하지 않으면 "ko" 사용)
            language_to_use = language or "ko"
            
            if language_to_use.lower() in ['ko', 'korean']:
                language_to_use = 'ko'
                logger.info(f"[faster-whisper] 언어 설정: ko (한국어)")
            else:
                language_to_use = language_to_use.lower()
                logger.info(f"[faster-whisper] 언어 설정: {language_to_use}")
            
            logger.info(f"[faster-whisper] 모델 설정: beam_size={kwargs.get('beam_size', 5)}, "
                        f"best_of={kwargs.get('best_of', 5)}, "
                        f"patience={kwargs.get('patience', 1)}, "
                        f"temperature={kwargs.get('temperature', 0)}")
            
            logger.debug(f"[faster-whisper] transcribe() 호출: language={language_to_use}")
            
            segments, info = self.backend.transcribe(
                audio_path,
                language=language_to_use,
                beam_size=kwargs.get("beam_size", 5),
                best_of=kwargs.get("best_of", 5),
                patience=kwargs.get("patience", 1),
                temperature=kwargs.get("temperature", 0)
            )
            
            logger.info(f"✓ faster-whisper 변환 완료")
            
            # 모든 세그먼트 수집
            text = "".join([segment.text for segment in segments])
            detected_language = info.language if info else language_to_use or "unknown"
            
            logger.info(f"  결과: {len(text)} 글자, 감지된 언어: {detected_language}")
            logger.debug(f"  변환된 텍스트 (처음 200자): {text[:200]}")
            
            # 🔒 메모리 정리 (동시 요청 시 Lock으로 보호)
            with self._memory_cleanup_lock:
                gc.collect()
                if self.device == "cuda":
                    torch.cuda.empty_cache()
            
            return {
                "success": True,
                "text": text.strip(),
                "audio_path": audio_path,
                "language": detected_language,
                "duration": info.duration if info else None,
                "backend": "faster-whisper"
            }
        except Exception as e:
            error_msg = str(e)[:200]
            logger.error(f"❌ faster-whisper 변환 실패: {type(e).__name__}", exc_info=True)
            logger.error(f"   요청 언어: {language_to_use}")
            logger.error(f"   메시지: {error_msg}")
            
            # 알려진 에러 진단
            if "vocabulary" in error_msg.lower() or "token" in error_msg.lower():
                logger.error(f"   분석: 토크나이저/어휘 오류 - 모델 설정 파일 누락 가능")
            elif "shape" in error_msg.lower() and "128" in error_msg:
                logger.error(f"   분석: mel-spectrogram 형상 오류 - preprocessor_config.json이 로드되지 않음")
            elif "model.bin" in error_msg.lower():
                logger.error(f"   분석: model.bin 로드 오류 - CTranslate2 변환 실패 가능")
            
            # 🔒 메모리 정리 (에러 발생 시에도 정리)
            with self._memory_cleanup_lock:
                gc.collect()
                if self.device == "cuda":
                    torch.cuda.empty_cache()
            
            return {
                "success": False,
                "error": f"faster-whisper 변환 실패: {type(e).__name__}: {error_msg}",
                "audio_path": audio_path,
                "backend": "faster-whisper",
                "requested_language": language_to_use
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
