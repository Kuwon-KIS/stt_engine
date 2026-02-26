"""
STT API와의 통신을 담당하는 서비스
"""
import aiohttp
import asyncio
import logging
import random
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
        ai_agent: bool = False,
        element_detection: bool = True,
        agent_url: str = "",
        agent_request_format: str = "text_only"
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
            element_detection: 요소 탐지 여부 (항상 enabled)
            agent_url: Agent 서버 URL
            agent_request_format: Agent 요청 형식 (text_only 또는 prompt_based)
        
        Returns:
            처리 결과 딕셔너리 (processing_steps 포함)
        """
        try:
            logger.info(f"[STT Service] 파일 처리 시작: {file_path}")
            logger.info(f"  - 언어: {language}, 스트림: {is_stream}, 백엔드: {backend}")
            logger.info(f"  - 처리 단계: Privacy={privacy_removal}, Classification={classification}, AI={ai_agent}, ElementDetection={element_detection}")
            if element_detection and agent_url:
                logger.info(f"  - Agent URL: {agent_url}, Format: {agent_request_format}")
            
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
            
            logger.info(f"[STT Service] API 파일 경로: {api_file_path}")
            
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field("file_path", api_file_path)
                data.add_field("language", language)
                data.add_field("is_stream", str(is_stream).lower())
                
                # 처리 단계 옵션 추가
                data.add_field("privacy_removal", str(privacy_removal).lower())
                data.add_field("classification", str(classification).lower())
                data.add_field("ai_agent", str(ai_agent).lower())
                data.add_field("element_detection", str(element_detection).lower())
                
                # Agent 관련 설정
                if element_detection and agent_url:
                    data.add_field("agent_url", agent_url)
                    data.add_field("agent_request_format", agent_request_format)
                
                # backend 지정
                if backend:
                    data.add_field("backend", backend)
                
                estimated_timeout = max(600, self.timeout)
                logger.info(f"[STT Service] API URL: {self.api_url}/transcribe")
                logger.info(f"[STT Service] API 타임아웃: {estimated_timeout}초")
                logger.info(f"[STT Service] 요청 파라미터: language={language}, is_stream={is_stream}, backend={backend}")
                
                try:
                    logger.debug(f"[STT Service] POST 요청: {self.api_url}/transcribe")
                    logger.info(f"[STT Service] API 호출 대기 중... (타임아웃: {estimated_timeout}초)")
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
                            logger.info(f"[STT Service] API 성공 여부: {success}")
                            if success:
                                text_len = len(result.get('text', ''))
                                logger.info(f"[STT Service] STT 완료: {text_len} 글자")
                                
                                # processing_steps 로깅
                                steps = result.get("processing_steps", {})
                                logger.info(f"[STT Service] 처리 단계: STT={steps.get('stt')}, Privacy={steps.get('privacy_removal')}, Classification={steps.get('classification')}, AI={steps.get('ai_agent')}, ElementDetection={steps.get('element_detection')}")
                                
                                # 요소 탐지 결과 로깅
                                if element_detection and result.get('element_detection'):
                                    element_result = result.get('element_detection', {})
                                    logger.info(f"[STT Service] 요소 탐지 완료: agent_type={element_result.get('agent_type')}")
                                logger.error(f"[STT Service] 전체 응답: {result}")
                            return result
                        else:
                            logger.error(f"[STT Service] HTTP {response.status} 에러")
                            logger.error(f"[STT Service] 응답 내용: {result}")
                            logger.info(f"[STT Service] Dummy 응답 반환 (API 에러)")
                            return await self._get_dummy_response(language, file_path)
                
                except asyncio.TimeoutError:
                    logger.error(f"[STT Service] API 타임아웃 ({estimated_timeout}초): {api_file_path}")
                    logger.info(f"[STT Service] Dummy 응답 반환 (타임아웃)")
                    return await self._get_dummy_response(language, file_path)
                except aiohttp.ClientError as client_err:
                    logger.error(f"[STT Service] HTTP 클라이언트 오류: {type(client_err).__name__}: {client_err}")
                    logger.info(f"[STT Service] Dummy 응답 반환 (연결 실패)")
                    return await self._get_dummy_response(language, file_path)
                except Exception as ae:
                    logger.error(f"[STT Service] API 통신 오류: {type(ae).__name__}: {ae}", exc_info=True)
                    logger.info(f"[STT Service] Dummy 응답 반환 (예외 발생)")
                    return await self._get_dummy_response(language, file_path)
        
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
    
    async def process_transcribe_job(self, job, privacy_removal: bool = False, classification: bool = False, ai_agent: bool = False, element_detection: bool = True, agent_url: str = "", agent_request_format: str = "text_only") -> dict:
        """
        비동기 작업 큐에서 호출되는 메서드
        job 객체의 상태를 업데이트하면서 처리
        
        Args:
            job: TranscribeJob 객체
            privacy_removal: 개인정보 제거 여부
            classification: 통화 분류 여부
            ai_agent: AI Agent 처리 여부
            element_detection: 요소 탐지 여부 (항상 enabled)
            agent_url: Agent 서버 URL
            agent_request_format: Agent 요청 형식 (text_only 또는 prompt_based)
        
        Returns:
            처리 결과 딕셔너리
        """
        try:
            logger.info(f"[STT Service] 비동기 처리 시작: {job.job_id}")
            logger.info(f"  - 파일: {job.file_path}")
            logger.info(f"  - 처리 단계: Privacy={privacy_removal}, Classification={classification}, AI={ai_agent}, ElementDetection={element_detection}")
            if element_detection and agent_url:
                logger.info(f"  - Agent URL: {agent_url}, Format: {agent_request_format}")
            
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
                data.add_field("element_detection", str(element_detection).lower())
                
                # Agent 관련 설정
                if element_detection and agent_url:
                    data.add_field("agent_url", agent_url)
                    data.add_field("agent_request_format", agent_request_format)
                
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
                                logger.info(f"[STT Service] 처리 단계 (job: {job.job_id}): STT={steps.get('stt')}, Privacy={steps.get('privacy_removal')}, Classification={steps.get('classification')}, ElementDetection={steps.get('element_detection')}")
                                
                                # 요소 탐지 결과 로깅
                                if element_detection and result.get('element_detection'):
                                    logger.info(f"[STT Service] 요소 탐지 완료 (job: {job.job_id})")
                                
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
    
    async def _get_dummy_response(self, language: str = "ko", file_path: str = "") -> dict:
        """
        STT API 연결 실패 시 Dummy 응답 반환 (개발 및 테스트 용도)
        랜덤 sleep을 추가하여 실제 STT 처리 시간을 시뮬레이션
        """
        # 0~30 초 사이의 랜덤 sleep으로 다양한 응답 시간 시뮬레이션
        sleep_duration = random.uniform(0, 30)
        logger.info(f"[STT Service] Dummy 응답 대기 중... ({sleep_duration:.1f}초)")
        await asyncio.sleep(sleep_duration)
        
        dummy_texts = {
            "ko": [
                # Dummy text 1 - 기본 판매 대화
                """상담원: 안녕하세요 고객님, 한국투자증권 상담실입니다. 오늘 통화하신 목적이 무엇인가요?
고객: 네, 최근에 펌드 투자를 생각하고 있는데 어떤 상품이 좋을까요?
상담원: 좋은 선택입니다. 현재 저희가 추천드리는 상품은 글로벌 성장 펌드입니다. 연 5-7% 수익률을 기대할 수 있으며, 매우 안정적인 상품입니다.
고객: 위험도는 어떻게 되나요?
상담원: 거의 없다고 보셔도 됩니다. 지난 5년간 한 번도 마이너스 수익률을 기록한 적이 없습니다. 그리고 원금 손실 가능성은 거의 0%에 가깝습니다.
고객: 그렇군요. 수수료는 얼마나 나가나요?
상담원: 수수료는 연 1.5%이고, 판매수수료는 별도로 없습니다. 매우 합리적인 수준이죠.
고객: 알겠습니다. 좌 더 생각해보고 연락드리겠습니다.
상담원: 네, 언제든지 연락주세요. 감사합니다.""",
                
                # Dummy text 2 - 공격적 판매 대화
                """상담원: 안녕하세요 고객님, 오늘 특별히 좌은 기회를 말려드리려고 전화드렸습니다.
고객: 무슨 기회인가요?
상담원: 저희 VIP 고객님들께만 제공되는 프리미엄 펌드 상품입니다. 연 10% 이상의 수익을 보장합니다. 단, 오늘까지만 가입하실 수 있습니다.
고객: 수익을 보장한다고요? 그게 가능한가요?
상담원: 물론입니다. 저희 회사는 30년 전통의 투자 회사이고, 이 상품은 절대 손해를 보지 않습니다. 제가 보증합니다.
고객: 그래도 좌 위험하지 않을까요?
상담원: 전혀 위험하지 않습니다. 은행 예금보다 더 안전하다고 보시면 됩니다. 그리고 지금 가입하시면 추가 수수료 할인 혜택도 받으실 수 있습니다. 어떻습니까, 바로 신청하시겠어요?
고객: 글쎈요... 조금 부담스럽네요.
상담원: 부담가지실 필요 없습니다. 저희 고객님들 모두 만족하시고 많은 수익을 내고 계십니다. 지금 바로 결정하시면 특별 혜택도 드리겠습니다.
고객: 좌 더 생각해볼게요.
상담원: 아, 오늘까지만 가능한 상품이라 내일은 다시 제공할 수 없습니다. 정말 후회하실 겁니다.""",
                
                # Dummy text 3 - 불완전 판매 대화
                """상담원: 안녕하세요, 고객님. 오늘 투자 상담 예약을 하셨더라구요.
고객: 네, 맞습니다. 펌드 투자에 대해 알고 싶어서요.
상담원: 좋습니다. 고객님께 딱 맞는 상품이 있습니다. 하이일드 부동산 펌드인데요, 연 12-15% 수익률을 목표로 하고 있습니다.
고객: 수익률이 높네요. 위험은 없나요?
상담원: 위험은 거의 없다고 보시면 됩니다. 부동산에 투자하는 것이니 안전하고, 하락할 일이 없습니다. 원금 보장도 됩니다.
고객: 정말요? 그러면 좋네요.
상담원: 네, 그리고 요즘 투자자들 사이에서 엄청 인기가 많아서 빨리 결정하셔야 합니다. 다음 주면 모집이 마감될 수도 있어요.
고객: 중도 환매는 가능한가요?
상담원: 물론입니다. 언제든 가능합니다. 하지만 이 상품은 장기 투자할수록 더 좋은 수익을 낼 수 있어요. 그리고 3년 이내에 환매하시면 수수료가 조금 발생합니다.
고객: 수수료가 얼마나 되나요?
상담원: 그건 나중에 설명드리겠습니다. 지금은 일단 가입하시는 게 중요합니다. 오늘 안에 결정하시면 가입 선물도 드리고요.
고객: 좌 더 상세한 설명을 들고 싶은데요.
상담원: 다 설명하려면 시간이 오래 걸립니다. 일단 가입하시고 나중에 자세히 설명서를 보내드리겠습니다. 지금 바로 서명하시면 됩니다.""",
                
                # Dummy text 4 - 기본 짧은 버전
                "안녕하세요. 저는 금융상품 판매자입니다. 오늘 좋은 펌드 상품을 소개하고 싶습니다. 이 상품은 연 5% 수익률을 기대할 수 있으며 매우 안정적입니다."
            ],
            "en": "Hello. I am a financial product sales representative. Today I want to introduce you to a great fund product. This product is expected to deliver 5% annual returns and is very stable.",
            "ja": "こんにちは。私は金融商品営業担当者です。本日は優れたファンド商品をご紹介したいと思います。この商品は年5%のリターンが期待でき、非常に安定しています。",
        }
        
        # Select random Korean text if language is Korean
        if language == "ko":
            dummy_text = random.choice(dummy_texts["ko"])
        else:
            dummy_text = dummy_texts.get(language, dummy_texts["ko"][3])  # Use short version as fallback
        
        logger.warning(f"[STT Service] 🔴 STT API 미응답 - Dummy 응답 반환 (언어: {language})")
        logger.warning(f"[STT Service] 📝 Dummy 텍스트 ({len(dummy_text)} 글자): {dummy_text[:50]}...")
        
        return {
            "success": True,
            "text": dummy_text,
            "duration_sec": 60,
            "backend": "dummy",
            "language": language,
            "processing_steps": {
                "stt": True,  # ✅ boolean으로 수정
                "privacy_removal": False,
                "classification": False,
                "ai_agent": False
            },
            "file_path": file_path,
            "_note": "⚠️ STT API 미응답으로 Dummy 응답이 반환되었습니다. STT 엔진이 실행 중인지 확인하세요.",
        }

# 전역 인스턴스 생성
stt_service = STTService()