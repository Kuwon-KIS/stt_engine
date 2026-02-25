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
from api_server.llm_clients import LLMClientFactory
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
    prompt_type: str = "privacy_remover_default_v6",
    llm_type: str = "vllm",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None
) -> Optional[PrivacyRemovalResult]:
    """
    Privacy Removal 수행
    
    STT 결과 텍스트에서 개인정보를 마스킹합니다.
    privacy_remover.py의 PrivacyRemoverService.process_text() 호출
    
    프롬프트 처리 흐름:
    1. 프롬프트 파일(privacy_remover_default_v6.prompt)에서 템플릿 로드
    2. {usertxt} 플레이스홀더를 실제 텍스트로 대체
    3. 생성된 프롬프트를 LLM(vLLM/Ollama)에 전송
    4. LLM 응답 파싱 (JSON) 및 개인정보 제거 결과 추출
    5. 실패 시 regex fallback 적용
    
    Args:
        text: 원본 텍스트
        prompt_type: 프롬프트 타입
                    - 'privacy_remover_default' 또는 'privacy_remover_default_v6': 기본 프롬프트
                    - 'privacy_remover_loosed_contact' 또는 'privacy_remover_loosed_contact_v6': 로우즈드 프롬프트
                    (기본값: privacy_remover_default_v6)
        llm_type: LLM 타입 ('openai', 'vllm', 'ollama') (기본값: 'vllm')
        vllm_model_name: vLLM 사용 시 모델명
        ollama_model_name: Ollama 사용 시 모델명
    
    Returns:
        PrivacyRemovalResult 객체
    """
    try:
        logger.info(f"[API/Transcribe] Privacy Removal 시작: prompt_type={prompt_type}, llm_type={llm_type}, text_len={len(text)}")
        
        # PrivacyRemoverService 초기화
        privacy_service = get_privacy_remover_service()
        
        # 사용할 모델명 결정
        model_name = None
        if llm_type == "vllm" and vllm_model_name:
            model_name = vllm_model_name
            logger.debug(f"[API/Transcribe] vLLM 모델 사용: {model_name}")
        elif llm_type == "ollama" and ollama_model_name:
            model_name = ollama_model_name
            logger.debug(f"[API/Transcribe] Ollama 모델 사용: {model_name}")
        else:
            logger.debug(f"[API/Transcribe] 기본 모델 사용")
        
        # LLM 클라이언트 초기화
        await privacy_service.initialize(model_name)
        logger.debug(f"[API/Transcribe] PrivacyRemoverService 초기화 완료")
        
        # 프롬프트 타입 정규화
        if not prompt_type:
            normalized_prompt_type = 'privacy_remover_default_v6'
            logger.debug(f"[API/Transcribe] 빈 prompt_type → privacy_remover_default_v6으로 정규화")
        elif 'loosed' in prompt_type.lower():
            normalized_prompt_type = 'privacy_remover_loosed_contact_v6'
            logger.debug(f"[API/Transcribe] loosed 타입 감지 → privacy_remover_loosed_contact_v6으로 정규화")
        else:
            # default로 시작하면 v6으로 통일
            normalized_prompt_type = 'privacy_remover_default_v6'
            logger.debug(f"[API/Transcribe] 기본 타입 → privacy_remover_default_v6으로 정규화")
        
        logger.info(f"[API/Transcribe] process_text 호출: prompt_type={normalized_prompt_type}, model={model_name or 'default'}")
        
        # 개인정보 제거 처리 (process_text 함수 호출)
        result = await privacy_service.process_text(
            usertxt=text,
            prompt_type=normalized_prompt_type,
            max_tokens=32768,
            temperature=0.3,
            model_name=model_name  # 모델명 전달 추가
        )
        
        logger.debug(f"[API/Transcribe] process_text 결과: success={result.get('success')}, privacy_exist={result.get('privacy_exist')}")
        
        # 결과 처리
        privacy_exist_str = result.get('privacy_exist', 'N')
        privacy_exist_value = PrivacyExistence.YES.value if privacy_exist_str == 'Y' else PrivacyExistence.NO.value
        
        logger.info(
            f"[API/Transcribe] ✅ Privacy Removal 완료: "
            f"success={result.get('success')}, "
            f"privacy_exist={privacy_exist_str}, "
            f"tokens={result.get('input_tokens', 0)}+{result.get('output_tokens', 0)}"
        )
        
        # PrivacyRemovalResult 반환
        return PrivacyRemovalResult(
            privacy_exist=privacy_exist_value,
            exist_reason=result.get('exist_reason', ''),
            text=result.get('privacy_rm_usertxt', text),
            privacy_types=result.get('exist_reason', '').split(',') if result.get('exist_reason') else []
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


async def perform_classification(
    text: str,
    prompt_type: str,
    llm_type: str = "vllm",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None
) -> Optional[ClassificationResult]:
    """
    Classification 수행
    
    Args:
        text: 분류할 텍스트
        prompt_type: 프롬프트 타입
        llm_type: LLM 타입 ('openai', 'vllm', 'ollama') (기본값: 'openai')
        vllm_model_name: vLLM 사용 시 모델명
        ollama_model_name: Ollama 사용 시 모델명
    
    Returns:
        ClassificationResult 또는 None
    """
    try:
        logger.info(f"[API/Transcribe] Classification 시작 (텍스트 길이: {len(text)}, llm_type={llm_type})")
        
        # Classification 프롬프트 생성
        classification_prompt = f"""다음 텍스트를 분류하세요. 고객 상담 통화의 성격을 파악하고 다음 중 하나로 분류해주세요:
- TELEMARKETING: 텔레마케팅/영업 통화
- CUSTOMER_SERVICE: 고객 서비스/기술 지원
- SALES: 직판 영업
- SURVEY: 설문조사
- SCAM: 사기/불법
- UNKNOWN: 분류 불가

텍스트: {text}

분류 결과를 JSON 형식으로 반환하세요:
{{"category": "분류", "confidence": 0.0~1.0 사이의 신뢰도}}
"""
        
        # LLM 클라이언트 생성
        model_name = vllm_model_name if llm_type == "vllm" else (ollama_model_name if llm_type == "ollama" else None)
        llm_client = LLMClientFactory.create_client(
            llm_type=llm_type,
            model_name=model_name
        )
        
        # LLM 호출
        response = await llm_client.call(
            prompt=classification_prompt,
            temperature=0.3,
            max_tokens=500
        )
        
        logger.debug(f"[API/Transcribe] Classification LLM 응답: {response[:100]}...")
        
        # 응답 파싱
        try:
            import json
            result_json = json.loads(response)
            category = result_json.get("category", "UNKNOWN")
            confidence = float(result_json.get("confidence", 0.0))
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"[API/Transcribe] Classification 응답 파싱 실패: {response}")
            category = "UNKNOWN"
            confidence = 0.0
        
        logger.info(f"[API/Transcribe] Classification 완료: category={category}, confidence={confidence}")
        
        return ClassificationResult(
            code=category,
            category=category,
            confidence=confidence,
            reason="LLM-based classification"
        )
    
    except Exception as e:
        logger.error(f"[API/Transcribe] Classification 오류: {type(e).__name__}: {e}", exc_info=True)
        return ClassificationResult(
            code=ClassificationCode.UNKNOWN.value,
            category="분류 오류",
            confidence=0.0,
            reason=f"Error: {str(e)}"
        )


def build_transcribe_response(
    stt_result: dict,
    file_check: Optional[dict],
    file_size_mb: float,
    memory_info: dict,
    perf_metrics: dict,
    processing_time: float,
    privacy_result: Optional[PrivacyRemovalResult] = None,
    classification_result: Optional[ClassificationResult] = None,
    element_detection_result: Optional[dict] = None,
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
        element_detection=element_detection_result is not None,
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
    
    # 텍스트 입력의 경우 file_check가 None일 수 있음
    duration = None
    if file_check:
        duration = file_check.get('duration_sec')
    elif 'duration' in stt_result and stt_result['duration'] == 0:
        # 텍스트 입력: duration을 None으로 설정
        duration = None
    
    return TranscribeResponse(
        success=True,
        text=stt_result.get('text', ''),
        language=stt_result.get('language', 'unknown'),
        duration=duration,
        backend=stt_result.get('backend', 'unknown'),
        file_path=str(file_path_obj) if file_path_obj else None,
        file_size_mb=file_size_mb,
        privacy_removal=privacy_result,
        classification=classification_result,
        element_detection=element_detection_result.get('detection_results') if element_detection_result else None,
        element_detection_api_type=element_detection_result.get('api_type') if element_detection_result else None,
        element_detection_llm_type=element_detection_result.get('llm_type') if element_detection_result else None,
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


async def _call_external_api(
    text: str,
    detection_types: list,
    external_api_url: Optional[str]
) -> Optional[dict]:
    """
    외부 AI Agent API 호출 시도
    
    외부 API 응답 형식:
    {
        "detected_yn": "Y" or "N",
        "detected_sentences": list of string,
        "detected_reasons": list of string,
        "detected_keywords": list of string
    }
    
    Args:
        text: 처리할 텍스트
        detection_types: 탐지 대상 목록
        external_api_url: 외부 API 엔드포인트 URL
    
    Returns:
        성공 시 dict, 실패 시 None
    """
    if not external_api_url:
        logger.warning("[Transcribe/ElementDetection] 외부 API URL이 지정되지 않음")
        return None
    
    try:
        import httpx
        import json as json_lib
        
        logger.info(f"[Transcribe/ElementDetection] 외부 AI Agent 호출 시작 (url={external_api_url})")
        
        # 요청 준비
        payload = {
            "text": text,
            "detection_types": detection_types,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                external_api_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
        
        if response.status_code != 200:
            logger.warning(f"[Transcribe/ElementDetection] 외부 API 호출 실패 (status={response.status_code})")
            return None
        
        result = response.json()
        logger.info(f"[Transcribe/ElementDetection] ✅ 외부 API 호출 성공")
        
        # 외부 API 응답을 표준 형식으로 변환
        # 응답 형식: {"detected_yn": "Y"/"N", "detected_sentences": list, "detected_reasons": list, "detected_keywords": list}
        detection_results = []
        detected_yn = result.get("detected_yn", "N").upper()
        
        detection_results.append({
            "detected_yn": detected_yn,
            "detected_sentences": result.get("detected_sentences", []),
            "detected_reasons": result.get("detected_reasons", []),
            "detected_keywords": result.get("detected_keywords", [])
        })
        
        return {
            'detection_results': detection_results,
            'api_type': 'external'
        }
    
    except Exception as e:
        logger.warning(f"[Transcribe/ElementDetection] 외부 API 호출 중 오류: {type(e).__name__}: {str(e)}")
        return None


async def _call_local_llm(
    text: str,
    detection_types: list,
    llm_type: str = "vllm",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None
) -> Optional[dict]:
    """
    로컬 LLM (vLLM/Ollama)을 사용한 요소 탐지
    
    LLM 응답을 표준 형식으로 변환:
    {
        "detected_yn": "Y" or "N",
        "detected_sentences": list of string,
        "detected_reasons": list of string,
        "detected_keywords": list of string
    }
    
    Args:
        text: 처리할 텍스트
        detection_types: 탐지 대상 목록
        llm_type: LLM 타입 ('vllm', 'ollama')
        vllm_model_name: vLLM 모델명
        ollama_model_name: Ollama 모델명
    
    Returns:
        성공 시 dict, 실패 시 None
    """
    try:
        logger.info(f"[Transcribe/ElementDetection] 로컬 LLM 호출 시작 (llm_type={llm_type})")
        
        # LLM 클라이언트 생성
        model_name = vllm_model_name if llm_type == "vllm" else (ollama_model_name if llm_type == "ollama" else None)
        llm_client = LLMClientFactory.create_client(
            llm_type=llm_type,
            model_name=model_name
        )
        
        # 요소 탐지 프롬프트 생성 - 표준 형식으로 응답하도록 지시
        detection_prompt = f"""다음 고객 상담 통화 내용을 분석하여 요청된 요소들의 탐지 여부를 판단하세요.

감지 대상:
{', '.join(detection_types)}

상담 내용:
{text}

다음 JSON 형식으로 응답하세요:
{{
    "detected_yn": "Y" 또는 "N",
    "detected_sentences": ["탐지된 문장1", "탐지된 문장2", ...],
    "detected_reasons": ["근거1", "근거2", ...],
    "detected_keywords": ["키워드1", "키워드2", ...]
}}

검정 결과:
"""
        
        # LLM 호출
        response = await llm_client.call(
            prompt=detection_prompt,
            temperature=0.3,
            max_tokens=1000
        )
        
        logger.debug(f"[Transcribe/ElementDetection] LLM 응답: {response[:100]}...")
        
        # 응답 파싱
        detection_results = []
        try:
            import json as json_lib
            result_json = json_lib.loads(response)
            
            # 표준 형식으로 변환
            detected_yn = result_json.get("detected_yn", "N").upper()
            detected_sentences = result_json.get("detected_sentences", [])
            detected_reasons = result_json.get("detected_reasons", [])
            detected_keywords = result_json.get("detected_keywords", [])
            
            # 리스트가 아닌 경우 리스트로 변환
            if isinstance(detected_sentences, str):
                detected_sentences = [detected_sentences]
            if isinstance(detected_reasons, str):
                detected_reasons = [detected_reasons]
            if isinstance(detected_keywords, str):
                detected_keywords = [detected_keywords]
            
            detection_results.append({
                "detected_yn": detected_yn,
                "detected_sentences": detected_sentences,
                "detected_reasons": detected_reasons,
                "detected_keywords": detected_keywords
            })
            
        except (json_lib.JSONDecodeError, ValueError):
            logger.warning(f"[Transcribe/ElementDetection] LLM 응답 파싱 실패: {response}")
            return None
        
        logger.info(f"[Transcribe/ElementDetection] ✅ 로컬 LLM 처리 완료 (llm_type={llm_type}, 결과_수={len(detection_results)})")
        return {
            'detection_results': detection_results,
            'api_type': 'local',
            'llm_type': llm_type
        }
    
    except Exception as e:
        logger.warning(f"[Transcribe/ElementDetection] 로컬 LLM 호출 중 오류: {type(e).__name__}: {str(e)}")
        return None


def _get_dummy_results(detection_types: list) -> dict:
    """
    더미 결과 반환 (모든 요소 미탐지)
    
    표준 형식:
    {
        "detected_yn": "N",
        "detected_sentences": [],
        "detected_reasons": [],
        "detected_keywords": []
    }
    
    Args:
        detection_types: 탐지 대상 목록
    
    Returns:
        더미 결과 dict
    """
    logger.warning("[Transcribe/ElementDetection] 모든 fallback 방법 실패, 더미 결과 반환")
    detection_results = [
        {
            "detected_yn": "N",
            "detected_sentences": [],
            "detected_reasons": [],
            "detected_keywords": []
        }
    ]
    return {
        'detection_results': detection_results,
        'api_type': 'dummy',
        'llm_type': None
    }


async def perform_element_detection(
    text: str,
    detection_types: list = None,
    api_type: str = "external",
    llm_type: str = "vllm",
    vllm_model_name: Optional[str] = None,
    ollama_model_name: Optional[str] = None,
    classification_result: dict = None,
    privacy_removal_result: dict = None,
    external_api_url: Optional[str] = None
) -> dict:
    """
    요소 탐지 (불완전판매, 부당권유 판매 등)를 수행 - Fallback 메커니즘 포함
    
    Fallback 흐름:
    1. api_type이 'fallback'이면:
       - 1️⃣ 외부 AI Agent 호출 시도
       - 2️⃣ 실패 시 → 로컬 vLLM/Ollama 호출
       - 3️⃣ 그것도 실패 시 → Dummy 결과 반환
    2. api_type이 'external'이면:
       - 외부 AI Agent만 호출
    3. api_type이 'local'이면:
       - 로컬 LLM만 호출
    
    Args:
        text: 처리할 텍스트 (정제되거나 원본 STT 결과)
        detection_types: 탐지 대상 목록 (예: ["incomplete_sales", "aggressive_sales"])
        api_type: API 방식 ("external"=외부만, "local"=로컬만, "fallback"=자동 선택)
        llm_type: LLM 타입 ('vllm', 'ollama') - api_type이 "local"이나 "fallback"일 때 사용
        vllm_model_name: vLLM 사용 시 모델명
        ollama_model_name: Ollama 사용 시 모델명
        classification_result: 분류 결과
        privacy_removal_result: 개인정보 제거 결과
        external_api_url: 외부 API 엔드포인트 URL
    
    Returns:
        {
            'success': bool,
            'detection_results': list,  # 탐지된 요소 목록 (표준 형식)
            'api_type': str,           # 사용된 API 방식 ('external', 'local', 'dummy')
            'llm_type': str,           # 사용된 LLM (local/fallback 모드일 때)
            'fallback_chain': list,    # fallback 모드일 때 시도한 방법들
            'error': str               # 에러 발생시
        }
        
    응답 형식 (detection_results 요소):
        {
            "detected_yn": "Y" or "N",           # 탐지 여부
            "detected_sentences": list of string, # 탐지된 문장들
            "detected_reasons": list of string,   # 탐지 근거들
            "detected_keywords": list of string   # 탐지된 키워드들
        }
    """
    try:
        logger.info(f"[Transcribe/ElementDetection] 요소 탐지 시작 (api_type={api_type}, llm_type={llm_type}, detection_types={detection_types}, text_length={len(text)})")
        
        # detection_types가 지정되지 않았으면 기본값 사용
        if not detection_types:
            detection_types = ["incomplete_sales", "aggressive_sales"]
        
        # ============================================
        # Fallback 모드: 자동 선택 (추천 방식)
        # ============================================
        if api_type == "fallback":
            fallback_chain = []
            
            # 1️⃣ 단계 1: 외부 AI Agent 호출 시도
            if external_api_url:
                logger.info("[Transcribe/ElementDetection] [Fallback] 단계 1️⃣: 외부 AI Agent 호출 시도...")
                result = await _call_external_api(text, detection_types, external_api_url)
                fallback_chain.append("external_api")
                
                if result:
                    logger.info("[Transcribe/ElementDetection] [Fallback] ✅ 단계 1️⃣ 성공 (외부 API 사용)")
                    return {
                        'success': True,
                        'detection_results': result.get('detection_results', []),
                        'api_type': 'external',
                        'llm_type': None,
                        'fallback_chain': fallback_chain
                    }
            
            # 2️⃣ 단계 2: 로컬 LLM 호출
            logger.info(f"[Transcribe/ElementDetection] [Fallback] 단계 2️⃣: 로컬 LLM 호출 시도 (llm_type={llm_type})...")
            result = await _call_local_llm(
                text, detection_types, llm_type,
                vllm_model_name, ollama_model_name
            )
            fallback_chain.append(f"local_llm({llm_type})")
            
            if result:
                logger.info(f"[Transcribe/ElementDetection] [Fallback] ✅ 단계 2️⃣ 성공 (로컬 LLM 사용)")
                result['fallback_chain'] = fallback_chain
                result['success'] = True
                return result
            
            # 3️⃣ 단계 3: Dummy 결과 반환
            logger.warning("[Transcribe/ElementDetection] [Fallback] 단계 3️⃣: 모든 방법 실패, 더미 결과 반환")
            result = _get_dummy_results(detection_types)
            result['success'] = True
            result['fallback_chain'] = fallback_chain + ["dummy"]
            return result
        
        # ============================================
        # 외부 API만 사용
        # ============================================
        elif api_type == "external":
            logger.info(f"[Transcribe/ElementDetection] 외부 API 호출 시작 (url={external_api_url})")
            result = await _call_external_api(text, detection_types, external_api_url)
            
            if result:
                return {
                    'success': True,
                    'detection_results': result.get('detection_results', []),
                    'api_type': 'external',
                    'llm_type': None
                }
            else:
                return {
                    'success': False,
                    'error': 'External API call failed',
                    'api_type': 'external'
                }
        
        # ============================================
        # 로컬 LLM만 사용
        # ============================================
        elif api_type == "local":
            logger.info(f"[Transcribe/ElementDetection] 로컬 LLM 요소 탐지 시작 (llm_type={llm_type})")
            result = await _call_local_llm(
                text, detection_types, llm_type,
                vllm_model_name, ollama_model_name
            )
            
            if result:
                result['success'] = True
                return result
            else:
                return {
                    'success': False,
                    'error': 'Local LLM call failed',
                    'api_type': 'local',
                    'llm_type': llm_type
                }
        
        else:
            error_msg = f"Unknown api_type: {api_type}. Expected 'external', 'local', or 'fallback'"
            logger.error(f"[Transcribe/ElementDetection] {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'api_type': api_type
            }
    
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"[Transcribe/ElementDetection] 요소 탐지 중 오류: {error_msg}", exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'api_type': api_type
        }