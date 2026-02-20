"""
STT API와의 통신을 담당하는 서비스
"""
import aiohttp
import asyncio
import logging
from typing import Optional
from config import STT_API_URL, STT_API_TIMEOUT

logger = logging.getLogger(__name__)


class STTService:
    """STT Engine API 통신 클래스"""
    
    def __init__(self):
        self.api_url = STT_API_URL
        self.timeout = STT_API_TIMEOUT
    
    async def health_check(self) -> bool:
        """STT API 헬스 체크"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/health",
                    timeout=aiohttp.ClientTimeout(total=10)  # 10초: Docker 네트워크 지연 고려
                ) as response:
                    is_healthy = response.status == 200
                    if is_healthy:
                        logger.debug(f"[STT Service] 헬스 체크 OK: {self.api_url}/health")
                    return is_healthy
        except asyncio.TimeoutError:
            logger.error(f"[STT Service] 헬스 체크 타임아웃 (10초): Docker 네트워크 지연 또는 API 미응답")
            return False
        except Exception as e:
            logger.error(f"[STT Service] 헬스 체크 실패: {e}")
            return False
    
    async def transcribe_local_file(
        self,
        file_path: str,
        language: str = "ko",
        is_stream: bool = False,
        backend: str = None,
        privacy_removal: bool = False,
        classification: bool = False,
        ai_agent: bool = False
    ) -> dict:
        """
        로컬 파일을 STT API에 전달 (파일 경로 방식)
        
        API가 접근 가능한 경로로 변환:
        - Web UI 경로: /app/data/uploads/... 
        - API 경로: /app/web_ui/data/uploads/... (마운트된 볼륨이 같음)
        
        Args:
            file_path: Web UI 컨테이너의 파일 경로 (/app/data/uploads/...)
            language: 언어 코드
            is_stream: 스트리밍 모드 사용 여부
            backend: 백엔드 선택 (faster-whisper, transformers, openai-whisper)
            privacy_removal: 개인정보 제거 여부
            classification: 통화 분류 여부
            ai_agent: AI Agent 처리 여부
        
        Returns:
            처리 결과 딕셔너리 (processing_steps 포함)
        """
        try:
            logger.info(f"[STT Service] 파일 처리 시작: {file_path}")
            logger.info(f"  - 언어: {language}, 스트림: {is_stream}, 백엔드: {backend}")
            logger.info(f"  - 처리 단계: Privacy={privacy_removal}, Classification={classification}, AI={ai_agent}")
            
            # 파일 경로 변환 (Web UI 볼륨 -> API 접근 경로)
            if file_path.startswith("/app/data/"):
                api_file_path = file_path.replace("/app/data/", "/app/web_ui/data/")
                logger.debug(f"[STT Service] 경로 변환 (레거시): {file_path} -> {api_file_path}")
            elif file_path.startswith("/app/web_ui/data/"):
                api_file_path = file_path
                logger.debug(f"[STT Service] 경로 확인 (배치): {file_path} (변환 불필요)")
            else:
                api_file_path = file_path
                logger.warning(f"[STT Service] 알 수 없는 경로 형식: {file_path}")
            
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field("file_path", api_file_path)
                data.add_field("language", language)
                data.add_field("is_stream", str(is_stream).lower())
                
                # 처리 단계 옵션 추가
                data.add_field("privacy_removal", str(privacy_removal).lower())
                data.add_field("classification", str(classification).lower())
                data.add_field("ai_agent", str(ai_agent).lower())
                
                # backend 지정
                if backend:
                    data.add_field("backend", backend)
                
                estimated_timeout = max(600, self.timeout)
                logger.info(f"[STT Service] API 타임아웃: {estimated_timeout}초")
                
                try:
                    logger.debug(f"[STT Service] POST 요청: {self.api_url}/transcribe")
                    async with session.post(
                        f"{self.api_url}/transcribe",
                        data=data,
                        timeout=aiohttp.ClientTimeout(total=estimated_timeout)
                    ) as response:
                        logger.info(f"[STT Service] API 응답 수신: status={response.status}")
                        
                        try:
                            result = await response.json()
                        except Exception as json_err:
                            logger.error(f"[STT Service] JSON 파싱 실패: {json_err}")
                            response_text = await response.text()
                            logger.error(f"[STT Service] 응답 원문: {response_text[:500]}")
                            return {
                                "success": False,
                                "error": "json_parse_error",
                                "message": f"응답 파싱 오류: {str(json_err)}"
                            }
                        
                        logger.info(f"[STT Service] JSON 파싱 완료")
                        
                        if response.status == 200:
                            success = result.get("success", False)
                            if success:
                                text_len = len(result.get('text', ''))
                                logger.info(f"[STT Service] STT 완료: {text_len} 글자")
                                
                                # processing_steps 로깅
                                steps = result.get("processing_steps", {})
                                logger.info(f"[STT Service] 처리 단계: STT={steps.get('stt')}, Privacy={steps.get('privacy_removal')}, Classification={steps.get('classification')}, AI={steps.get('ai_agent')}")
                                
                                if steps.get('privacy_removal'):
                                    privacy_result = result.get('privacy_removal', {})
                                    logger.info(f"[STT Service] Privacy Removal: 개인정보 존재={privacy_result.get('privacy_exist')}")
                                
                                if steps.get('classification'):
                                    class_result = result.get('classification', {})
                                    logger.info(f"[STT Service] Classification: {class_result.get('code')} (신뢰도: {class_result.get('confidence')}%)")
                            else:
                                logger.error(f"[STT Service] API 처리 실패: {result.get('error', 'Unknown error')}")
                        else:
                            logger.error(f"[STT Service] HTTP {response.status}: {result}")
                        
                        return result
                
                except asyncio.TimeoutError:
                    logger.error(f"[STT Service] API 타임아웃 ({estimated_timeout}초): {api_file_path}")
                    return {
                        "success": False,
                        "error": "timeout",
                        "error_code": "API_TIMEOUT",
                        "message": f"API 처리 시간 초과 ({estimated_timeout}초)"
                    }
                except aiohttp.ClientError as client_err:
                    logger.error(f"[STT Service] HTTP 클라이언트 오류: {type(client_err).__name__}: {client_err}")
                    return {
                        "success": False,
                        "error": "http_error",
                        "error_code": "HTTP_CLIENT_ERROR",
                        "message": f"HTTP 통신 오류: {str(client_err)}"
                    }
                except Exception as ae:
                    logger.error(f"[STT Service] API 통신 오류: {type(ae).__name__}: {ae}", exc_info=True)
                    return {
                        "success": False,
                        "error": "api_error",
                        "error_code": "API_ERROR",
                        "message": f"API 통신 오류: {str(ae)}"
                    }
        
        except Exception as e:
            logger.error(f"[STT Service] 파일 처리 오류: {type(e).__name__}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "unknown",
                "error_code": "UNKNOWN_ERROR",
                "message": str(e)
            }
    
    async def get_backend_info(self) -> dict:
        """STT API 백엔드 정보 조회"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/backend/current",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"[STT Service] 백엔드 정보 조회 실패: {e}")
            return {}
    
    async def process_transcribe_job(self, job, privacy_removal: bool = False, classification: bool = False, ai_agent: bool = False) -> dict:
        """
        비동기 작업 큐에서 호출되는 메서드
        job 객체의 상태를 업데이트하면서 처리
        
        Args:
            job: TranscribeJob 객체
            privacy_removal: 개인정보 제거 여부
            classification: 통화 분류 여부
            ai_agent: AI Agent 처리 여부
        
        Returns:
            처리 결과 딕셔너리
        """
        try:
            logger.info(f"[STT Service] 비동기 처리 시작: {job.job_id}")
            logger.info(f"  - 파일: {job.file_path}")
            logger.info(f"  - 처리 단계: Privacy={privacy_removal}, Classification={classification}, AI={ai_agent}")
            
            # 파일 경로 변환
            file_path = job.file_path
            if file_path.startswith("/app/data/"):
                api_file_path = file_path.replace("/app/data/", "/app/web_ui/data/")
            else:
                api_file_path = file_path
            
            logger.debug(f"[STT Service] 경로 변환: {file_path} -> {api_file_path}")
            
            # 진행률 업데이트: 준비 중
            job.progress = 15
            
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field("file_path", api_file_path)
                data.add_field("language", job.language)
                data.add_field("is_stream", str(job.is_stream).lower())
                data.add_field("privacy_removal", str(privacy_removal).lower())
                data.add_field("classification", str(classification).lower())
                data.add_field("ai_agent", str(ai_agent).lower())
                
                # 장시간 처리를 고려하여 충분한 타임아웃 설정
                estimated_timeout = max(600, self.timeout)
                logger.info(f"[STT Service] 비동기 처리 API 호출: job={job.job_id}, timeout={estimated_timeout}초")
                
                try:
                    async with session.post(
                        f"{self.api_url}/transcribe",
                        data=data,
                        timeout=aiohttp.ClientTimeout(total=estimated_timeout)
                    ) as response:
                        logger.info(f"[STT Service] API 응답 수신: status={response.status} (job: {job.job_id})")
                        
                        try:
                            result = await response.json()
                        except Exception as json_err:
                            logger.error(f"[STT Service] JSON 파싱 실패 (job: {job.job_id}): {json_err}")
                            return {
                                "success": False,
                                "error": "json_parse_error",
                                "error_code": "JSON_PARSE_ERROR",
                                "message": f"응답 파싱 오류: {str(json_err)}"
                            }
                        
                        logger.info(f"[STT Service] JSON 파싱 완료 (job: {job.job_id})")
                        
                        # 진행률 업데이트: API 처리 완료
                        job.progress = 90
                        
                        if response.status == 200:
                            success = result.get("success", False)
                            if success:
                                text_len = len(result.get('text', ''))
                                logger.info(f"[STT Service] 처리 완료: {text_len} 글자 (job: {job.job_id})")
                                
                                # processing_steps 로깅
                                steps = result.get("processing_steps", {})
                                logger.info(f"[STT Service] 처리 단계 (job: {job.job_id}): STT={steps.get('stt')}, Privacy={steps.get('privacy_removal')}, Classification={steps.get('classification')}")
                                
                                job.progress = 100
                            else:
                                logger.error(f"[STT Service] 처리 실패 (job: {job.job_id}): {result.get('error', 'Unknown error')}")
                        else:
                            logger.error(f"[STT Service] HTTP {response.status} (job: {job.job_id}): {result}")
                        
                        return result
                
                except asyncio.TimeoutError:
                    logger.error(f"[STT Service] API 타임아웃 ({estimated_timeout}초, job: {job.job_id})")
                    return {
                        "success": False,
                        "error": "timeout",
                        "error_code": "API_TIMEOUT",
                        "message": f"API 처리 시간 초과 ({estimated_timeout}초)"
                    }
                except aiohttp.ClientError as client_err:
                    logger.error(f"[STT Service] HTTP 클라이언트 오류 (job: {job.job_id}): {type(client_err).__name__}: {client_err}")
                    return {
                        "success": False,
                        "error": "http_error",
                        "error_code": "HTTP_CLIENT_ERROR",
                        "message": f"HTTP 통신 오류: {str(client_err)}"
                    }
                except Exception as ae:
                    logger.error(f"[STT Service] API 통신 오류 (job: {job.job_id}): {type(ae).__name__}: {ae}", exc_info=True)
                    return {
                        "success": False,
                        "error": "api_error",
                        "error_code": "API_ERROR",
                        "message": f"API 통신 오류: {str(ae)}"
                    }
        
        except Exception as e:
            logger.error(f"[STT Service] 비동기 처리 오류 (job: {job.job_id}): {type(e).__name__}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "unknown",
                "error_code": "UNKNOWN_ERROR",
                "message": str(e)
            }
    
    async def process_privacy_removal(
        self,
        text: str,
        prompt_type: str = "privacy_remover_default_v6"
    ) -> dict:
        """
        Privacy Removal 처리
        STT 결과에서 개인정보를 자동으로 탐지 및 마스킹
        
        Args:
            text: 처리할 텍스트 (STT 결과)
            prompt_type: 사용할 프롬프트 타입
        
        Returns:
            {
                "success": bool,
                "privacy_exist": "Y/N",
                "exist_reason": "발견된 개인정보 사유",
                "privacy_rm_text": "처리된 텍스트 (마스킹됨)"
            }
        """
        try:
            if not text or not text.strip():
                return {
                    "success": False,
                    "error": "텍스트가 비어있습니다",
                    "privacy_rm_text": ""
                }
            
            logger.info(f"[Privacy Removal] 처리 시작: {len(text)} 글자, 프롬프트: {prompt_type}")
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": text,
                    "prompt_type": prompt_type
                }
                
                headers = {
                    "Content-Type": "application/json"
                }
                
                # Privacy Removal은 시간이 더 소요될 수 있으므로 타임아웃 더 길게
                timeout_seconds = 600  # 10분
                
                try:
                    async with session.post(
                        f"{self.api_url}/api/privacy-removal/process",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout_seconds)
                    ) as response:
                        result = await response.json()
                        
                        if response.status == 200 and result.get("success"):
                            logger.info(f"[Privacy Removal] 처리 완료: 개인정보 포함={result.get('privacy_exist')}")
                            return result
                        else:
                            error_msg = result.get("error") or "알 수 없는 오류"
                            logger.error(f"[Privacy Removal] API 오류: {error_msg}")
                            return {
                                "success": False,
                                "error": error_msg,
                                "privacy_rm_text": text  # Fallback: 원본 반환
                            }
                
                except asyncio.TimeoutError:
                    logger.error(f"[Privacy Removal] 타임아웃 ({timeout_seconds}초)")
                    return {
                        "success": False,
                        "error": f"처리 타임아웃 ({timeout_seconds}초)",
                        "privacy_rm_text": text
                    }
                except Exception as api_error:
                    logger.error(f"[Privacy Removal] API 통신 오류: {api_error}")
                    return {
                        "success": False,
                        "error": f"API 통신 오류: {str(api_error)}",
                        "privacy_rm_text": text
                    }
        
        except Exception as e:
            logger.error(f"[Privacy Removal] 처리 오류: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "privacy_rm_text": text if 'text' in locals() else ""
            }

# 전역 인스턴스 생성
stt_service = STTService()