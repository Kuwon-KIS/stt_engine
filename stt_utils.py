#!/usr/bin/env python3
"""
STT 엔진 유틸리티 모듈 - 메모리 및 파일 검증 함수들
"""

from pathlib import Path
from typing import Optional
import logging


def check_memory_available(required_mb: int = 4000, logger: Optional[logging.Logger] = None) -> dict:
    """
    현재 메모리 상태 확인
    
    Args:
        required_mb: 필요한 메모리 크기 (MB)
        logger: 로거 객체 (선택사항)
    
    Returns:
        {
            'available_mb': int,
            'total_mb': int,
            'used_percent': float,
            'warning': bool,
            'critical': bool,
            'message': str
        }
    """
    try:
        import psutil
        vm = psutil.virtual_memory()
        
        status = {
            'available_mb': vm.available // (1024**2),
            'total_mb': vm.total // (1024**2),
            'used_percent': vm.percent,
            'warning': False,
            'critical': False,
            'message': ''
        }
        
        if vm.available < (required_mb * 1024**2):
            status['critical'] = True
            status['message'] = f"❌ 메모리 부족 (필요: {required_mb}MB, 사용 가능: {status['available_mb']}MB)"
            if logger:
                logger.error(status['message'])
        elif vm.percent > 85:
            status['warning'] = True
            status['message'] = f"⚠️  메모리 사용량 높음 ({vm.percent:.1f}%)"
            if logger:
                logger.warning(status['message'])
        else:
            status['message'] = f"✅ 메모리 양호 ({status['available_mb']}MB / {status['total_mb']}MB)"
        
        return status
    except Exception as e:
        if logger:
            logger.warning(f"메모리 확인 실패: {e}")
        return {
            'available_mb': -1,
            'total_mb': -1,
            'used_percent': -1,
            'warning': False,
            'critical': False,
            'message': f'메모리 확인 불가: {e}'
        }


def check_audio_file(audio_path: str, logger: Optional[logging.Logger] = None) -> dict:
    """
    오디오 파일 사전 검증
    
    Args:
        audio_path: 오디오 파일 경로
        logger: 로거 객체 (선택사항)
    
    Returns:
        {
            'valid': bool,
            'file_size_mb': float,
            'duration_sec': float (추정),
            'warnings': [str],
            'errors': [str]
        }
    """
    audio_path = Path(audio_path)
    
    status = {
        'valid': True,
        'file_size_mb': 0,
        'duration_sec': 0,
        'warnings': [],
        'errors': []
    }
    
    # 1. 파일 존재 및 크기 확인
    if not audio_path.exists():
        status['valid'] = False
        status['errors'].append(f"파일 없음: {audio_path}")
        if logger:
            logger.error(f"❌ {status['errors'][0]}")
        return status
    
    file_size_bytes = audio_path.stat().st_size
    status['file_size_mb'] = file_size_bytes / (1024**2)
    
    # 2. 파일 크기 검증 (너무 크면 경고)
    if status['file_size_mb'] > 1000:  # > 1GB
        status['errors'].append(f"파일 크기 초과 (최대 권장: 1GB, 현재: {status['file_size_mb']:.1f}MB)")
        status['valid'] = False
        if logger:
            logger.error(f"❌ {status['errors'][-1]}")
    elif status['file_size_mb'] > 500:  # > 500MB
        status['warnings'].append(f"파일 크기 큼 (> 500MB): {status['file_size_mb']:.1f}MB, 처리 시간 오래 걸릴 수 있음")
        if logger:
            logger.warning(f"⚠️  {status['warnings'][-1]}")
    
    # 3. 오디오 메타정보 읽기 (크기 기반 추정 또는 librosa 사용)
    try:
        import librosa
        audio, sr = librosa.load(str(audio_path), sr=16000)
        status['duration_sec'] = len(audio) / sr
        
        if status['duration_sec'] > 3600:  # > 1시간
            status['warnings'].append(f"음성 길이 매우 김 (1시간 이상): {status['duration_sec']/60:.1f}분")
            if logger:
                logger.warning(f"⚠️  {status['warnings'][-1]}")
    except Exception as e:
        # librosa 실패 시 파일 크기로 추정 (대략 샘플레이트 16kHz, 2바이트/샘플)
        estimated_duration = (file_size_bytes / 2) / 16000
        status['duration_sec'] = estimated_duration
        status['warnings'].append(f"음성 길이 추정 (정확도 낮음): ~{estimated_duration:.1f}초")
        if logger:
            logger.debug(f"음성 길이 추정: {estimated_duration:.1f}초")
    
    if logger and status['valid']:
        logger.info(f"✅ 파일 검증 OK - 크기: {status['file_size_mb']:.1f}MB, 길이: {status['duration_sec']:.1f}초")
    
    return status
