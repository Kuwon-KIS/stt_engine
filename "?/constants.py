"""
STT Engine API Constants 및 열거형 정의

이 파일은 전체 시스템에서 사용되는 상수, 열거형, 코드값을 정의합니다.
"""

from enum import Enum
from typing import Dict, List


# ============================================================================
# Processing Steps
# ============================================================================

class ProcessingStep(str, Enum):
    """음성 처리 단계 정의"""
    STT = "stt"                          # 필수: Speech-to-Text (faster-whisper)
    PRIVACY_REMOVAL = "privacy_removal"  # 선택: 개인정보 제거 (vLLM)
    CLASSIFICATION = "classification"    # 선택: 통화 카테고리 분류 (vLLM)
    AI_AGENT = "ai_agent"               # 선택: AI Agent 기반 정보 추출


# ============================================================================
# Privacy Existence
# ============================================================================

class PrivacyExistence(str, Enum):
    """개인정보 존재 여부"""
    YES = "Y"   # 개인정보 존재
    NO = "N"    # 개인정보 없음


class PrivacyType(str, Enum):
    """개인정보 유형 분류"""
    PHONE = "phone"              # 전화번호
    ADDRESS = "address"          # 주소
    IDENTITY = "identity"        # 신분증/ID
    ACCOUNT = "account"          # 계좌정보
    CREDIT_CARD = "credit_card"  # 신용카드
    EMAIL = "email"              # 이메일
    DATE_OF_BIRTH = "dob"        # 생년월일
    COMPANY = "company"          # 회사명
    PERSON_NAME = "person_name"  # 인명
    OTHER = "other"              # 기타


# ============================================================================
# Classification
# ============================================================================

class ClassificationCode(str, Enum):
    """통화 카테고리 분류 코드"""
    PRE_SALES = "CLASS_PRE_SALES"           # 사전판매 상담
    CUSTOMER_SERVICE = "CLASS_CUSTOMER_SVC"  # 고객 서비스
    TECHNICAL_SUPPORT = "CLASS_TECHNICAL"    # 기술 지원
    GENERAL = "CLASS_GENERAL"               # 일반 통화
    COMPLAINT = "CLASS_COMPLAINT"           # 불만/클레임
    SUPPORT = "CLASS_SUPPORT"               # 지원
    OTHER = "CLASS_OTHER"                   # 기타
    UNKNOWN = "CLASS_UNKNOWN"               # 분류 불가


class ClassificationCategory(str, Enum):
    """분류 카테고리명 (사용자 친화적)"""
    PRE_SALES = "사전판매"
    CUSTOMER_SERVICE = "고객 서비스"
    TECHNICAL_SUPPORT = "기술 지원"
    GENERAL = "일반 통화"
    COMPLAINT = "불만/클레임"
    SUPPORT = "지원"
    OTHER = "기타"
    UNKNOWN = "분류 불가"


# Mapping: ClassificationCode -> ClassificationCategory
CLASSIFICATION_CODE_TO_CATEGORY: Dict[str, str] = {
    ClassificationCode.PRE_SALES.value: ClassificationCategory.PRE_SALES.value,
    ClassificationCode.CUSTOMER_SERVICE.value: ClassificationCategory.CUSTOMER_SERVICE.value,
    ClassificationCode.TECHNICAL_SUPPORT.value: ClassificationCategory.TECHNICAL_SUPPORT.value,
    ClassificationCode.GENERAL.value: ClassificationCategory.GENERAL.value,
    ClassificationCode.COMPLAINT.value: ClassificationCategory.COMPLAINT.value,
    ClassificationCode.SUPPORT.value: ClassificationCategory.SUPPORT.value,
    ClassificationCode.OTHER.value: ClassificationCategory.OTHER.value,
    ClassificationCode.UNKNOWN.value: ClassificationCategory.UNKNOWN.value,
}


# ============================================================================
# Batch Processing
# ============================================================================

class BatchJobStatus(str, Enum):
    """배치 작업 상태"""
    PENDING = "pending"      # 대기 중
    RUNNING = "running"      # 실행 중
    COMPLETED = "completed"  # 완료
    FAILED = "failed"        # 실패


class BatchFileStatus(str, Enum):
    """배치 파일 처리 상태"""
    PENDING = "pending"      # 대기 중
    PROCESSING = "processing"  # 처리 중
    DONE = "done"            # 완료
    ERROR = "error"          # 오류


# ============================================================================
# Processing Options Profiles (선택 조합)
# ============================================================================

class ProcessingProfile(str, Enum):
    """사전정의된 처리 단계 조합"""
    STT_ONLY = "stt_only"                    # STT만 수행
    STT_WITH_PRIVACY = "stt_privacy"         # STT + Privacy Removal
    STT_WITH_CLASSIFICATION = "stt_classify" # STT + Classification
    STT_FULL = "stt_full"                    # STT + Privacy + Classification + AI Agent


# Profile 정의
PROFILE_STEPS: Dict[str, List[ProcessingStep]] = {
    ProcessingProfile.STT_ONLY.value: [
        ProcessingStep.STT,
    ],
    ProcessingProfile.STT_WITH_PRIVACY.value: [
        ProcessingStep.STT,
        ProcessingStep.PRIVACY_REMOVAL,
    ],
    ProcessingProfile.STT_WITH_CLASSIFICATION.value: [
        ProcessingStep.STT,
        ProcessingStep.PRIVACY_REMOVAL,  # Classification에 필요
        ProcessingStep.CLASSIFICATION,
    ],
    ProcessingProfile.STT_FULL.value: [
        ProcessingStep.STT,
        ProcessingStep.PRIVACY_REMOVAL,
        ProcessingStep.CLASSIFICATION,
        ProcessingStep.AI_AGENT,
    ],
}


# ============================================================================
# Error Codes
# ============================================================================

class ErrorCode(str, Enum):
    """시스템 에러 코드"""
    # STT 관련 에러
    STT_FILE_NOT_FOUND = "STT_FILE_NOT_FOUND"
    STT_INVALID_AUDIO = "STT_INVALID_AUDIO"
    STT_MEMORY_ERROR = "STT_MEMORY_ERROR"
    STT_CUDA_OUT_OF_MEMORY = "STT_CUDA_OUT_OF_MEMORY"
    STT_PROCESSING_ERROR = "STT_PROCESSING_ERROR"
    
    # Privacy Removal 관련 에러
    PRIVACY_SERVICE_UNAVAILABLE = "PRIVACY_SERVICE_UNAVAILABLE"
    PRIVACY_PROCESSING_ERROR = "PRIVACY_PROCESSING_ERROR"
    
    # Classification 관련 에러
    CLASSIFICATION_SERVICE_UNAVAILABLE = "CLASSIFICATION_SERVICE_UNAVAILABLE"
    CLASSIFICATION_PROCESSING_ERROR = "CLASSIFICATION_PROCESSING_ERROR"
    
    # AI Agent 관련 에러
    AI_AGENT_SERVICE_UNAVAILABLE = "AI_AGENT_SERVICE_UNAVAILABLE"
    AI_AGENT_PROCESSING_ERROR = "AI_AGENT_PROCESSING_ERROR"
    
    # 배치 관련 에러
    BATCH_FILE_NOT_FOUND = "BATCH_FILE_NOT_FOUND"
    BATCH_INVALID_REQUEST = "BATCH_INVALID_REQUEST"
    BATCH_PROCESSING_ERROR = "BATCH_PROCESSING_ERROR"
    
    # 일반 에러
    INVALID_REQUEST = "INVALID_REQUEST"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"


# ============================================================================
# Configuration Constants
# ============================================================================

# 기본 타임아웃 (초)
DEFAULT_STT_TIMEOUT = 600
DEFAULT_PRIVACY_TIMEOUT = 60
DEFAULT_CLASSIFICATION_TIMEOUT = 30
DEFAULT_AI_AGENT_TIMEOUT = 120

# 최대 배치 파일 개수
MAX_BATCH_FILES = 100

# 최대 파일 크기 (MB)
MAX_FILE_SIZE_MB = 500

# 스트리밍 청크 설정 (초)
STREAM_CHUNK_DURATION = 30
STREAM_OVERLAP_DURATION = 12

# 기본 언어
DEFAULT_LANGUAGE = "ko"
SUPPORTED_LANGUAGES = ["ko", "en", "ja", "zh", "es", "fr", "de", "it", "pt", "ru"]
