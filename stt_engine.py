#!/usr/bin/env python3
"""
STT 모듈 - faster-whisper를 사용한 음성-텍스트 변환
더 빠른 추론 속도와 낮은 메모리 사용량으로 최적화됨
"""

import os
from pathlib import Path
from typing import Optional, Dict
import tarfile
from faster_whisper import WhisperModel


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
    """faster-whisper를 사용한 STT 클래스 (3-4배 빠른 추론)"""
    
    def __init__(self, model_path: str, device: str = "cpu", compute_type: str = "float16"):
        """
        Whisper STT 초기화
        
        Args:
            model_path: 모델 경로 (예: "models/openai_whisper-large-v3-turbo")
            device: 사용할 디바이스 ('cpu', 'cuda', 또는 'auto')
            compute_type: 계산 타입 ('float32', 'float16', 'int8')
                        - float16: 빠르고 메모리 효율적 (권장)
                        - float32: 더 정확하지만 느림
                        - int8: 가장 빠르고 메모리 효율적 (VRAM <2GB)
        
        Raises:
            FileNotFoundError: 모델을 찾을 수 없음
            RuntimeError: 모델 로드 실패
        """
        # 모델이 압축되어 있으면 자동 해제
        models_dir = str(Path(model_path).parent)
        self.model_path = str(auto_extract_model_if_needed(models_dir))
        
        self.device = device if device != "auto" else ("cuda" if self._is_cuda_available() else "cpu")
        self.compute_type = compute_type
        
        print(f"🔄 faster-whisper 모델 로드 중... (디바이스: {self.device}, compute: {compute_type})")
        
        # faster-whisper 모델 로드
        # model_size_or_path: 모델 폴더 경로 (로컬) 또는 모델 이름 (tiny, base, small, medium, large)
        try:
            self.model = WhisperModel(
                self.model_path,
                device=self.device,
                compute_type=self.compute_type,
                num_workers=4,
                cpu_threads=4,
                download_root=None
            )
            print(f"✅ faster-whisper 모델 로드 완료")
        except FileNotFoundError:
            print(f"❌ 모델을 찾을 수 없습니다: {self.model_path}")
            print(f"💡 다음 경로에 모델을 배치하세요: {self.model_path}")
            raise
        except Exception as e:
            print(f"❌ 모델 로드 실패: {e}")
            raise RuntimeError(f"모델 로드 실패: {e}") from e
    
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
            language: 음성 언어 코드 (예: 'ko' for Korean, 'en' for English)
                     None이면 자동 감지
            **kwargs: 추가 옵션
                - beam_size: 빔 서치 크기 (기본값: 5, 범위: 1-30)
                - best_of: 샘플링 최적화 (기본값: 5)
                - patience: 조기 종료 patience (기본값: 1)
                - temperature: 온도 (기본값: 0)
        
        Returns:
            변환 결과 딕셔너리
        """
        try:
            print(f"📂 음성 파일 로드: {audio_path}")
            
            # 파일 존재 확인
            if not Path(audio_path).exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {audio_path}")
            
            # faster-whisper transcribe (자동으로 오디오 로드 및 처리)
            # language: 언어 토큰 설정 (명시하면 더 빠름)
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
                "duration": info.duration if info else None
            }
        
        except Exception as e:
            print(f"❌ 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "audio_path": audio_path
            }


def test_stt(model_path: str, audio_dir: str = "audio", device: str = "cpu"):
    """
    STT 테스트 함수
    
    Args:
        model_path: 모델 경로
        audio_dir: 테스트할 음성 파일 디렉토리
        device: 사용할 디바이스
    """
    # STT 초기화 (float16으로 최적화, VRAM 3-4GB)
    stt = WhisperSTT(
        model_path,
        device=device,
        compute_type="float16"  # 빠르고 효율적
    )
    
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
        else:
            print(f"❌ 파일: {audio_file.name}")
            print(f"🔴 오류: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    import sys
    
    # 모델 경로 설정
    model_path = str(Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo")
    
    # 디바이스 설정
    device = "cuda"  # faster-whisper는 CUDA 자동으로 인식
    
    print(f"🖥️  사용 디바이스: {device}")
    
    # 테스트 실행
    test_stt(model_path, audio_dir="audio", device=device)
