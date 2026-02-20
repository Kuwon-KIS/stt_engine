"""
Batch Transcribe Endpoint
"""

import logging
from typing import List, Optional
from pathlib import Path
import time
import asyncio

from fastapi import Form
from fastapi.responses import JSONResponse

from api_server.constants import ErrorCode
from api_server.models import (
    BatchResponse,
    BatchFileResult,
    BatchProgress,
    TranscribeResponse,
)
from api_server.transcribe_endpoint import (
    validate_and_prepare_file,
    perform_stt,
    perform_privacy_removal,
    perform_classification,
    build_transcribe_response,
)
from utils.performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)


async def transcribe_batch(
    stt_instance,
    file_paths: List[str],
    language: str = "ko",
    is_stream: bool = False,
    privacy_removal: bool = False,
    classification: bool = False,
    ai_agent: bool = False,
    privacy_prompt_type: str = "privacy_remover_default_v6",
    classification_prompt_type: str = "classification_default_v1",
    batch_id: str = None,
) -> BatchResponse:
    """
    배치 음성인식 처리
    
    Args:
        stt_instance: STT 엔진 인스턴스
        file_paths: 처리할 파일 경로 리스트
        language: 언어 코드
        is_stream: 스트리밍 모드
        privacy_removal: 개인정보 제거 활성화
        classification: 분류 활성화
        ai_agent: AI Agent 활성화
        privacy_prompt_type: Privacy Removal 프롬프트 타입
        classification_prompt_type: Classification 프롬프트 타입
        batch_id: 배치 ID
    
    Returns:
        배치 처리 결과
    """
    
    import uuid
    from datetime import datetime
    
    batch_id = batch_id or str(uuid.uuid4())
    
    logger.info(f"[Batch] 배치 처리 시작: {batch_id} ({len(file_paths)}개 파일)")
    logger.info(f"  옵션: privacy_removal={privacy_removal}, classification={classification}, ai_agent={ai_agent}")
    
    start_time = time.time()
    created_at = datetime.now()
    started_at = datetime.now()
    
    files_result = []
    progress = BatchProgress(total=len(file_paths), completed=0, failed=0, in_progress=0, pending=len(file_paths), progress_percent=0.0)
    
    # 순차 처리 (병렬 처리는 리소스 제한으로 인해 추후 구현)
    for idx, file_path in enumerate(file_paths):
        logger.info(f"[Batch] 파일 {idx+1}/{len(file_paths)} 처리: {file_path}")
        
        file_start_time = time.time()
        
        try:
            # 파일 검증
            file_path_obj, file_check, memory_info = await validate_and_prepare_file(file_path)
            file_size_mb = file_path_obj.stat().st_size / (1024**2)
            
            # STT 처리
            stt_result = await perform_stt(
                stt_instance=stt_instance,
                file_path_obj=file_path_obj,
                language=language,
                is_streaming=is_stream
            )
            
            if not stt_result.get('success', False) or 'error' in stt_result:
                raise Exception(stt_result.get('error', 'STT processing failed'))
            
            # Privacy Removal
            privacy_result = None
            if privacy_removal:
                privacy_result = await perform_privacy_removal(
                    text=stt_result.get('text', ''),
                    prompt_type=privacy_prompt_type
                )
            
            # Classification
            classification_result = None
            if classification:
                classification_text = privacy_result.text if privacy_result else stt_result.get('text', '')
                
                from api_server.services.classification_service import get_classification_service
                classification_service = await get_classification_service()
                classification_response = await classification_service.classify_call(
                    text=classification_text,
                    prompt_type=classification_prompt_type
                )
                
                if classification_response.get('success', True):
                    from api_server.models import ClassificationResult
                    classification_result = ClassificationResult(
                        code=classification_response['code'],
                        category=classification_response['category'],
                        confidence=classification_response['confidence'],
                        reason=classification_response.get('reason')
                    )
            
            # 처리 시간
            file_processing_time = time.time() - file_start_time
            perf_monitor = PerformanceMonitor()
            perf_metrics = perf_monitor.stop() if hasattr(perf_monitor, 'stop') else None
            
            # 응답 구성
            transcribe_response = build_transcribe_response(
                stt_result=stt_result,
                file_check=file_check,
                file_size_mb=file_size_mb,
                memory_info=memory_info,
                perf_metrics=perf_metrics,
                processing_time=file_processing_time,
                privacy_result=privacy_result,
                classification_result=classification_result,
                file_path_obj=file_path_obj,
                processing_mode="streaming" if is_stream else "normal"
            )
            
            # 파일 결과 추가
            file_result = BatchFileResult(
                filename=file_path_obj.name,
                filepath=str(file_path_obj),
                status="done",
                result=transcribe_response,
                error=None,
                processing_time_seconds=file_processing_time
            )
            
            files_result.append(file_result)
            progress.completed += 1
            
            logger.info(f"[Batch] ✓ 파일 처리 완료: {file_path_obj.name} ({file_processing_time:.2f}초)")
        
        except Exception as e:
            logger.error(f"[Batch] ✗ 파일 처리 실패: {file_path} - {type(e).__name__}: {e}")
            
            from api_server.models import ErrorDetail
            file_result = BatchFileResult(
                filename=Path(file_path).name,
                filepath=file_path,
                status="error",
                result=None,
                error=ErrorDetail(
                    code=ErrorCode.BATCH_PROCESSING_ERROR.value,
                    message=str(e)[:200],
                    details=None
                ),
                processing_time_seconds=time.time() - file_start_time
            )
            
            files_result.append(file_result)
            progress.failed += 1
        
        # 진행률 업데이트
        progress.pending = len(file_paths) - progress.completed - progress.failed
        progress.in_progress = 0
        progress.progress_percent = (progress.completed + progress.failed) / len(file_paths) * 100.0
    
    # 배치 완료
    completed_at = datetime.now()
    total_processing_time = time.time() - start_time
    
    logger.info(f"[Batch] 배치 처리 완료: {batch_id}")
    logger.info(f"  결과: 성공={progress.completed}, 실패={progress.failed}, 전체 시간={total_processing_time:.2f}초")
    
    return BatchResponse(
        batch_id=batch_id,
        status="completed" if progress.failed == 0 else "partially_completed",
        files=files_result,
        progress=progress,
        created_at=created_at,
        started_at=started_at,
        completed_at=completed_at,
        total_processing_time_seconds=total_processing_time
    )
