#!/usr/bin/env python3
"""
STT 테스트 모듈
음성 파일을 받아서 텍스트로 변환하는 기능을 제공합니다.
"""

import os
from pathlib import Path
from typing import Optional, Dict
import torch
import torchaudio
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
import tarfile


def auto_extract_model_if_needed(models_dir: str = "models") -> Path:
    """
    필요시 모델 자동 압축 해제
    
    Args:
        models_dir: 모델 디렉토리
    
    Returns:
        모델 폴더 경로
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
                tar.extractall(path=models_path)
            print("✅ 모델 압축 해제 완료")
            
            # 압축 파일 삭제 (선택사항)
            tar_file.unlink()
            print("🗑️  압축 파일 삭제")
            
            return model_folder
        except Exception as e:
            print(f"❌ 모델 압축 해제 실패: {e}")
            raise
    
    # 둘 다 없으면 경로 반환 (다운로드 프롬프트)
    return model_folder


class WhisperSTT:
    """Whisper 모델을 사용한 STT 클래스"""
    
    def __init__(self, model_path: str, device: str = "cpu"):
        """
        Whisper STT 초기화
        
        Args:
            model_path: 모델 경로
            device: 사용할 디바이스 ('cpu' 또는 'cuda')
        """
        # 모델이 압축되어 있으면 자동 해제
        model_path = str(auto_extract_model_if_needed(
            Path(model_path).parent
        ))
        
        self.device = device
        self.model_path = model_path
        
        print(f"🔄 모델 로드 중... (디바이스: {device})")
        
        # 모델과 프로세서 로드
        self.processor = AutoProcessor.from_pretrained(model_path)
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(model_path)
        self.model.to(device)
        self.model.eval()
        
        print("✅ 모델 로드 완료")
    
    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict:
        """
        음성 파일을 텍스트로 변환합니다.
        
        Args:
            audio_path: 음성 파일 경로
            language: 음성 언어 코드 (예: 'ko' for Korean, 'en' for English)
        
        Returns:
            변환 결과 딕셔너리
        """
        try:
            # 음성 파일 로드
            print(f"📂 음성 파일 로드: {audio_path}")
            audio, sr = torchaudio.load(audio_path)
            
            # 샘플링 레이트가 16kHz가 아니면 리샘플링
            if sr != 16000:
                print(f"🔄 샘플링 레이트 변환: {sr}Hz -> 16000Hz")
                resampler = torchaudio.transforms.Resample(sr, 16000)
                audio = resampler(audio)
            
            # 모노로 변환
            if audio.shape[0] > 1:
                audio = audio.mean(dim=0, keepdim=True)
            
            # 프로세서로 입력 처리
            inputs = self.processor(
                audio.squeeze().numpy(),
                sampling_rate=16000,
                return_tensors="pt"
            )
            
            # 모델로 추론
            with torch.no_grad():
                predicted_ids = self.model.generate(
                    inputs["input_features"].to(self.device),
                    language=language
                )
            
            # 결과 디코딩
            transcription = self.processor.batch_decode(
                predicted_ids,
                skip_special_tokens=True
            )
            
            return {
                "success": True,
                "text": transcription[0],
                "audio_path": audio_path,
                "language": language
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
    # STT 초기화
    stt = WhisperSTT(model_path, device=device)
    
    # 음성 파일 디렉토리 확인
    audio_path = Path(audio_dir)
    if not audio_path.exists():
        print(f"⚠️  음성 파일 디렉토리가 없습니다: {audio_dir}")
        return
    
    # 지원하는 음성 파일 형식
    supported_formats = ("*.wav", "*.mp3", "*.flac", "*.ogg")
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
        else:
            print(f"❌ 파일: {audio_file.name}")
            print(f"오류: {result['error']}")


if __name__ == "__main__":
    # 모델 경로 설정
    model_path = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"
    
    # GPU 사용 가능 확인
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🖥️  사용 디바이스: {device}")
    
    # STT 테스트 실행
    test_stt(str(model_path), device=device)
