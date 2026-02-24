"""
STT Engine API - 향상된 Transcribe 엔드포인트

단건 및 배치 음성 파일 처리 엔드포인트
"""

import logging
from typing import Optional, List
from pathlib import Path
import time
import json
import tempfile

from fastapi import Form, Query, HTTPException
from fastapi.responses import JSONResponse

from stt_utils import check_memory_available, check_audio_file
from utils.performance_monitor import PerformanceMonitor
from api_server.services.privacy_remover import get_privacy_remover_service
from api_server.constants import (
    ProcessingStep,
    ClassificationCode,
    PrivacyExistence,
    ErrorCode,
)
from api_server.models import (
    TranscribeResponse,
    PrivacyRemovalResult,
    ClassificationResult,
    ProcessingStepsStatus,
    MemoryInfo,
)

logger = logging.getLogger(__name__)


class TranscribeRequestParams:
    """Transcribe 요청 파라미터"""
    
    def __init__(
        self,
        file_path: str = Form(...),
        language: str = Form("ko"),
        is_stream: str = Form("false"),
        privacy_removal: str = Form("false"),
        classification: str = Form("false"),
        incomplete_elements_check: str = Form("false"),
        agent_url: str = Form(""),
        agent_request_format: str = Form("text_only"),
        export: Optional[str] = None,
        privacy_prompt_type: str = Form("privacy_remover_default_v6"),
        classification_prompt_type: str = Form("classification_default_v1"),
    ):
        self.file_path = file_path
        self.language = language
        self.is_stream = is_stream.lower() in ['true', '1', 'yes', 'on']
        self.privacy_removal = privacy_removal.lower() in ['true', '1', 'yes', 'on']
        self.classification = classification.lower() in ['true', '1', 'yes', 'on']
        self.incomplete_elements_check = incomplete_elements_check.lower() in ['true', '1', 'yes', 'on']
        self.agent_url = agent_url  # Agent 서버 URL
        self.agent_request_format = agent_request_format  # 'text_only' 또는 'prompt_based'
        self.export = export
        self.privacy_prompt_type = privacy_prompt_type
        self.classification_prompt_type = classification_prompt_type
    
    def get_processing_steps(self) -> List[ProcessingStep]:
        """필요한 처리 단계 목록 반환"""
        steps = [ProcessingStep.STT]
        
        # Classification은 Privacy Removal과 함께 수행 (전문 텍스트 기반)
        if self.privacy_removal:
            steps.append(ProcessingStep.PRIVACY_REMOVAL)
        
        if self.classification:
            if ProcessingStep.PRIVACY_REMOVAL not in steps:
                steps.append(ProcessingStep.PRIVACY_REMOVAL)
            steps.append(ProcessingStep.CLASSIFICATION)
        
        if self.ai_agent:
            if ProcessingStep.PRIVACY_REMOVAL not in steps:
                steps.append(ProcessingStep.PRIVACY_REMOVAL)
            if ProcessingStep.CLASSIFICATION not in steps:
                steps.append(ProcessingStep.CLASSIFICATION)
            steps.append(ProcessingStep.AI_AGENT)
        
        return steps


async def validate_and_prepare_file(file_path: str) -> tuple[Path, dict, dict]:
    """
    파일 검증 및 준비
    
    Returns:
        (file_path_obj, file_check, memory_info)
    """
    # 1. 파일 경로 검증
    file_path_obj = Path(file_path).resolve()
    allowed_dir = Path("/app").resolve() if Path("/app").exists() else Path.cwd().resolve()
    
    logger.info(f"[API/Transcribe] 파일 경로 검증: {file_path}")
    
    try:
        file_path_obj.relative_to(allowed_dir)
    except ValueError:
        error_msg = f"파일 경로가 허용된 디렉토리 외에 있음: {file_path}"
        logger.error(f"[API/Transcribe] ❌ {error_msg}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": ErrorCode.FORBIDDEN.value,
                "message": error_msg,
            }
        )
    
    # 파일 존재 확인
    if not file_path_obj.exists():
        error_msg = f"파일을 찾을 수 없음: {file_path_obj}"
        logger.error(f"[API/Transcribe] ❌ {error_msg}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": ErrorCode.STT_FILE_NOT_FOUND.value,
                "message": error_msg,
            }
        )
    
    if not file_path_obj.is_file():
        error_msg = f"경로가 파일이 아님: {file_path_obj}"
        logger.error(f"[API/Transcribe] ❌ {error_msg}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": ErrorCode.INVALID_REQUEST.value,
                "message": error_msg,
            }
        )
    
    file_size_mb = file_path_obj.stat().st_size / (1024**2)
    logger.info(f"[API/Transcribe] ✓ 파일 검증: {file_path_obj.name} ({file_size_mb:.2f}MB)")
    
    # 2. 오디오 파일 검증
    logger.debug(f"[API/Transcribe] 오디오 파일 검증 중...")
    try:
        file_check = check_audio_file(str(file_path_obj), logger=logger)
        if not file_check['valid']:
            error_msg = file_check['errors'][0] if file_check['errors'] else "알 수 없는 오류"
            logger.error(f"[API/Transcribe] 파일 검증 실패: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": ErrorCode.STT_INVALID_AUDIO.value,
                    "message": error_msg,
                }
            )
        
        logger.info(f"[API/Transcribe] ✓ 파일 검증 완료 (길이: {file_check['duration_sec']:.1f}초)")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API/Transcribe] 파일 검증 중 오류: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail={
                "error": ErrorCode.STT_INVALID_AUDIO.value,
                "message": str(e),
            }
        )
    
    # 경고 로깅
    for warning in file_check.get('warnings', []):
        logger.warning(f"[API/Transcribe] {warning}")
    
    # 3. 메모리 확인
    logger.debug(f"[API/Transcribe] 메모리 확인 중...")
    try:
        memory_info = check_memory_available(logger=logger)
        if memory_info['critical']:
            logger.error(f"[API/Transcribe] 메모리 부족: {memory_info['message']}")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": ErrorCode.STT_MEMORY_ERROR.value,
                    "message": memory_info['message'],
                }
            )
        
        logger.info(f"[API/Transcribe] ✓ 메모리 확인 완료 (사용 가능: {memory_info['available_mb']:.0f}MB)")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API/Transcribe] 메모리 확인 중 오류: {type(e).__name__}: {e}", exc_info=True)
        memory_info = {
            'critical': False,
            'available_mb': 0,
            'used_percent': 0,
            'message': 'Unknown'
        }
    
    return file_path_obj, file_check, memory_info


async def perform_stt(stt_instance, file_path_obj: Path, language: str, is_streaming: bool) -> dict:
    """
    STT 처리 수행
    
    Returns:
        STT 결과 딕셔너리
    """
    logger.info(f"[API/Transcribe] STT 처리 시작: {file_path_obj.name}")
    
    try:
        if is_streaming:
            # TODO: 스트리밍 모드 구현
            logger.info(f"[API/Transcribe] 스트리밍 모드 사용")
            result = stt_instance.transcribe(str(file_path_obj), language=language)
        else:
            result = stt_instance.transcribe(str(file_path_obj), language=language)
        
        logger.info(f"[API/Transcribe] ✅ STT 처리 완료: {len(result.get('text', ''))} 글자")
        return result
    
    except Exception as e:
        logger.error(f"[API/Transcribe] STT 처리 오류: {type(e).__name__}: {e}", exc_info=True)
        raise


async def perform_privacy_removal(
    text: str,
    prompt_type: str = "privacy_remover_default"
) -> Optional[PrivacyRemovalResult]:
    """
    Privacy Removal 수행
    
    STT 결과 텍스트에서 개인정보를 마스킹합니다.
    
    Args:
        text: 원본 텍스트
        prompt_type: 프롬프트 타입 ('privacy_remover_default' 또는 'privacy_remover_loosed_contact')
    
    Returns:
        PrivacyRemovalResult 또는 None
    """
    try:
        logger.info(f"[API/Transcribe] Privacy Removal 시작 (텍스트 길이: {len(text)})")
        
        # PrivacyRemoverService 초기화
        privacy_service = get_privacy_remover_service()
        await privacy_service.initialize()
        
        # 프롬프트 타입 정규화
        # 기본값: privacy_remover_default
        if not prompt_type or prompt_type.startswith('privacy_remover_default'):
            normalized_prompt_type = 'privacy_remover_default'
        elif prompt_type.startswith('privacy_remover_loosed'):
            normalized_prompt_type = 'privacy_remover_loosed_contact'
        else:
            normalized_prompt_type = 'privacy_remover_default'
        
        # 개인정보 제거 처리
        privacy_result = await privacy_service.remove_privacy_from_text(
            text=text,
            prompt_type=normalized_prompt_type
        )
        
        if privacy_result.get('success', True):
            logger.info(
                f"[API/Transcribe] ✅ Privacy Removal 완료 "
                f"(method={privacy_result.get('method')}, removed={privacy_result.get('removed_count')})"
            )
            
            # 개인정보 제거 결과 반환
            removed_items = privacy_result.get('removed_items', [])
            privacy_exist = PrivacyExistence.YES.value if removed_items else PrivacyExistence.NO.value
            
            return PrivacyRemovalResult(
                privacy_exist=privacy_exist,
                exist_reason=(
                    f"{privacy_result.get('removed_count')}개의 개인정보 항목 마스킹 ({privacy_result.get('method')})"
                    if removed_items else "개인정보 없음"
                ),
                text=privacy_result.get('text', text),
                privacy_types=removed_items
            )
        else:
            logger.warning(f"[API/Transcribe] Privacy Removal 실패")
            # 실패 시에도 원본 텍스트와 함께 반환
            return PrivacyRemovalResult(
                privacy_exist=PrivacyExistence.NO.value,
                exist_reason="Privacy removal processing failed",
                text=text,
                privacy_types=[]
            )
    
    except Exception as e:
        logger.error(
            f"[API/Transcribe] Privacy Removal 오류: {type(e).__name__}: {e}",
            exc_info=True
        )
        # 에러 발생 시에도 원본 텍스트 반환
        return PrivacyRemovalResult(
            privacy_exist=PrivacyExistence.NO.value,
            exist_reason=f"Error: {str(e)}",
            text=text,
            privacy_types=[]
        )


async def perform_classification(text: str, prompt_type: str) -> Optional[ClassificationResult]:
    """
    Classification 수행
    
    Returns:
        ClassificationResult 또는 None
    """
    try:
        logger.info(f"[API/Transcribe] Classification 시작 (텍스트 길이: {len(text)})")
        
        # TODO: Classification Service 구현
        # 현재는 임시로 UNKNOWN 반환
        logger.warning(f"[API/Transcribe] Classification Service가 구현되지 않음")
        
        return ClassificationResult(
            code=ClassificationCode.UNKNOWN.value,
            category="분류 불가",
            confidence=0.0,
            reason="Service not implemented"
        )
    
    except Exception as e:
        logger.error(f"[API/Transcribe] Classification 오류: {type(e).__name__}: {e}", exc_info=True)
        return None


def build_transcribe_response(
    stt_result: dict,
    file_check: dict,
    file_size_mb: float,
    memory_info: dict,
    perf_metrics: dict,
    processing_time: float,
    privacy_result: Optional[PrivacyRemovalResult] = None,
    classification_result: Optional[ClassificationResult] = None,
    file_path_obj: Optional[Path] = None,
    processing_mode: str = "normal",
) -> TranscribeResponse:
    """
    Transcribe 응답 구성
    """
    # Processing Steps 상태 결정
    processing_steps = ProcessingStepsStatus(
        stt=True,
        privacy_removal=privacy_result is not None,
        classification=classification_result is not None,
        ai_agent=False,
    )
    
    # 메모리 정보
    memory_info_obj = MemoryInfo(
        available_mb=memory_info.get('available_mb', 0),
        used_percent=memory_info.get('used_percent', 0),
    ) if memory_info else None
    
    # Performance Metrics
    perf_metrics_obj = None
    if perf_metrics and isinstance(perf_metrics, dict):
        # perf_metrics.to_dict() 또는 dict 형태
        perf_dict = perf_metrics if isinstance(perf_metrics, dict) else perf_metrics.to_dict()
        from api_server.models import PerformanceMetrics
        perf_metrics_obj = PerformanceMetrics(
            cpu_percent=perf_dict.get('cpu_percent'),
            memory_mb=perf_dict.get('memory_mb'),
            gpu_percent=perf_dict.get('gpu_percent'),
        )
    
    return TranscribeResponse(
        success=True,
        text=stt_result.get('text', ''),
        language=stt_result.get('language', 'unknown'),
        duration=file_check.get('duration_sec'),
        backend=stt_result.get('backend', 'unknown'),
        file_path=str(file_path_obj) if file_path_obj else None,
        file_size_mb=file_size_mb,
        privacy_removal=privacy_result,
        classification=classification_result,
        processing_steps=processing_steps,
        processing_time_seconds=processing_time,
        processing_mode=processing_mode,
        memory_info=memory_info_obj,
        performance=perf_metrics_obj,
    )


async def perform_incomplete_elements_check(
    call_transcript: str,
    agent_url: str,
    agent_request_format: str = "text_only",
    classification_result: dict = None,
    privacy_removal_result: dict = None,
) -> dict:
    """
    불완전판매요소 검증
    
    Args:
        call_transcript: 통화 전사 텍스트
        agent_url: Agent 서버 URL
        agent_request_format: "text_only" 또는 "prompt_based"
        classification_result: 분류 결과
        privacy_removal_result: 개인정보 제거 결과
    
    Returns:
        {
            'success': bool,
            'incomplete_elements': dict,      # 불완전판매요소 구조
            'analysis': str,                  # 상세 분석
            'agent_type': str,                # 'external' 또는 'vllm'
            'processing_time_sec': float,
            'error': str                      # 에러 메시지 (실패 시)
        }
    """
    try:
        from api_server.services.incomplete_sales_validator import get_incomplete_elements_validator
        from api_server.services.agent_backend import get_agent_backend
        
        logger.info(f"[Transcribe/IncompleteElements] 검증 시작 (transcript 길이: {len(call_transcript)})")
        
        # 정제된 텍스트 우선 사용
        check_text = privacy_removal_result.get('processed_text', call_transcript) if privacy_removal_result else call_transcript
        
        # Agent 설정
        agent_config = {
            "url": agent_url,
            "request_format": agent_request_format
        }
        
        # Validator 초기화 (AgentBackend 필요)
        agent_backend = get_agent_backend()
        validator = get_incomplete_elements_validator(agent_backend)
        
        result = await validator.validate(
            call_transcript=check_text,
            agent_config=agent_config,
            timeout=30
        )
        
        if result.get('success'):
            logger.info(f"[Transcribe/IncompleteElements] ✅ 검증 완료 (agent_type: {result.get('agent_type')})")
            return result
        else:
            logger.error(f"[Transcribe/IncompleteElements] 검증 실패: {result.get('error')}")
            return result
    
    except Exception as e:
        logger.error(f"[Transcribe/IncompleteElements] 검증 오류: {type(e).__name__}: {e}", exc_info=True)
        return {
            'success': False,
            'error': f"{type(e).__name__}: {str(e)}"
        }


async def perform_ai_agent(
    text: str,
    stt_result: dict = None,
    agent_type: str = "auto",
    classification_result: dict = None,
    privacy_removal_result: dict = None,
    agent_url: Optional[str] = None,
    chat_thread_id: Optional[str] = None
) -> dict:
    """
    AI Agent를 사용하여 텍스트 처리
    
    Args:
        text: 처리할 텍스트 (정제되거나 원본 STT 결과)
        stt_result: STT 처리 결과
        agent_type: Agent 타입 ("auto", "vllm", "dummy" 등)
        classification_result: 분류 결과
        privacy_removal_result: 개인정보 제거 결과
        agent_url: Agent 서버 URL (선택)
        chat_thread_id: 채팅 스레드 ID
    
    Returns:
        {
            'success': bool,
            'response': str,        # Agent 응답
            'agent_type': str,      # 실제 사용된 agent 타입
            'error': str           # 에러 발생시
        }
    """
    try:
        from api_server.services.ai_agent_service import get_ai_agent_service
        
        logger.info(f"[Transcribe/AIAgent] AI Agent 처리 시작 (agent_type={agent_type}, text_length={len(text)})")
        
        # AI Agent 서비스 인스턴스 획득
        ai_agent_service = await get_ai_agent_service()
        
        # Agent 처리 (Fallback 자동 처리)
        result = await ai_agent_service.process(
            user_query=text,
            agent_url=agent_url or ai_agent_service.agent_url or "",
            request_format="text_only",
            use_streaming=False,
            chat_thread_id=chat_thread_id
        )
        
        if result.get('success'):
            logger.info(f"[Transcribe/AIAgent] ✅ Agent 처리 완료 (agent_type={result.get('agent_type')})")
            return {
                'success': True,
                'response': result.get('response', ''),
                'agent_type': result.get('agent_type', agent_type),
                'chat_thread_id': result.get('chat_thread_id')
            }
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"[Transcribe/AIAgent] Agent 처리 실패: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'agent_type': 'failed'
            }
    
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"[Transcribe/AIAgent] AI Agent 처리 중 오류: {error_msg}", exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'agent_type': 'error'
        }
