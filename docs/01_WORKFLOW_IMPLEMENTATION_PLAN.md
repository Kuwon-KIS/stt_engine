# STT Engine Workflow 개선 계획

## 현재 상황

### 기존 문제점
1. **단건 transcribe 처리**: Audio → Text 변환 후 개인정보 제거 여부를 별도로 선택
   - 사용자가 최초 요청 시점에 원하는 처리 단계를 미리 선택하지 못함
   
2. **배치 처리 미지원**: 여러 파일/폴더 선택 시 일괄 처리 불가능
   - 현재는 파일 단위로만 처리 가능
   
3. **Processing Level 구조의 문제**
   - 일괄적인 레벨 선택이 아닌 각 단계별 독립적 선택 필요
   - 현재: "processing_level" (문자열) → 변경: "privacy_removal", "classification" 등 (boolean)

4. **응답 구조 미정의**
   - 어느 단계까지 진행되었는지 명확하지 않음
   - Classification 코드값이 표준화되지 않음

## 개선 대상 Workflow

```
Audio Input
    ↓
[1] STT (faster-whisper) → text, language, duration
    ↓
[2] Privacy Removal (vLLM-based)* → privacy_exist, exist_reason, privacy_rm_text
    ↓
[3] Classification (vLLM-based)* → classification_code, confidence, category
    ↓
[4] AI Agent (if needed)* → extracted_info, action_items
    ↓
Final Output with processing_steps metadata
```

**\* 선택사항**

## 구현 계획

### Phase 1: 데이터 구조 및 상수 정의

#### 1.1 Processing Steps 정의
```python
class ProcessingStep(str, Enum):
    STT = "stt"                          # 필수
    PRIVACY_REMOVAL = "privacy_removal"  # 선택
    CLASSIFICATION = "classification"    # 선택  
    AI_AGENT = "ai_agent"               # 선택

class ClassificationCode(str, Enum):
    """Classification 결과 코드"""
    PRE_SALES = "CLASS_PRE_SALES"           # 사전판매 상담
    GENERAL = "CLASS_GENERAL"               # 일반 통화
    CUSTOMER_SERVICE = "CLASS_CUSTOMER_SVC"  # 고객 서비스
    TECHNICAL_SUPPORT = "CLASS_TECHNICAL"    # 기술 지원
    OTHER = "CLASS_OTHER"                   # 기타
    UNKNOWN = "CLASS_UNKNOWN"               # 분류 불가

class PrivacyExistence(str, Enum):
    """Privacy 존재 여부"""
    YES = "Y"   # 개인정보 존재
    NO = "N"    # 개인정보 없음
```

#### 1.2 응답 데이터 구조 (Pydantic Models)
```python
class ProcessingStatusMetadata(BaseModel):
    """각 단계별 처리 상태"""
    stt: bool                    # 완료 여부
    privacy_removal: bool        # 완료 여부
    classification: bool         # 완료 여부
    ai_agent: bool              # 완료 여부

class TranscribeResponse(BaseModel):
    """단건/배치 transcribe 응답"""
    success: bool
    
    # STT 결과 (항상 포함)
    text: str
    language: str
    duration: float
    backend: str
    
    # Privacy Removal 결과 (선택적)
    privacy_removal: Optional[Dict] = None
    # {
    #     'privacy_exist': str,      # Y/N
    #     'exist_reason': str,       # 개인정보 유형
    #     'text': str               # 개인정보 제거된 텍스트
    # }
    
    # Classification 결과 (선택적)
    classification: Optional[Dict] = None
    # {
    #     'code': str,              # CLASS_PRE_SALES 등
    #     'category': str,          # 분류 카테고리명
    #     'confidence': float       # 신뢰도 (0-100)
    #     'reason': str            # 분류 사유
    # }
    
    # 처리 단계 메타데이터
    processing_steps: ProcessingStatusMetadata
    
    # 성능 정보
    processing_time_seconds: float
    file_size_mb: float
```

### Phase 2: API 엔드포인트 수정

#### 2.1 POST /transcribe (단건 처리)

**요청 파라미터:**
```
file_path: str
language: str = "ko"
is_stream: bool = false
privacy_removal: bool = false              # NEW
classification: bool = false               # NEW
ai_agent: bool = false                     # NEW
privacy_prompt_type: str = "..."           
classification_prompt_type: str = "..."    
```

**응답:**
```json
{
  "success": true,
  "text": "...",
  "language": "ko",
  "duration": 10.5,
  "backend": "faster-whisper",
  "privacy_removal": {
    "privacy_exist": "Y",
    "exist_reason": "전화번호 포함",
    "text": "..."
  },
  "classification": {
    "code": "CLASS_PRE_SALES",
    "category": "사전판매",
    "confidence": 85.5,
    "reason": "..."
  },
  "processing_steps": {
    "stt": true,
    "privacy_removal": true,
    "classification": true,
    "ai_agent": false
  },
  "processing_time_seconds": 15.3
}
```

#### 2.2 POST /transcribe_batch (배치 처리) - NEW

**요청:**
```
files: List[str]                           # 파일 경로 리스트
language: str = "ko"
privacy_removal: bool = false
classification: bool = false
ai_agent: bool = false
```

### Phase 3: Classification Service (NEW)

- **목표**: STT 결과 텍스트 → 통화 카테고리 분류
- **구현**: vLLM 기반 분류
- **코드값**: ClassificationCode enum 사용

### Phase 4: Batch Service 개선

- processing_steps 옵션 저장
- 각 파일별 processing_steps 결과 저장
- 배치 작업 중 진행 상황 조회

## 파일 변경 계획

### 신규 파일
- `api_server/services/classification_service.py` - Classification 로직
- `api_server/constants.py` - 상수 정의
- `api_server/models.py` - Pydantic 모델

### 수정 파일
- `api_server/app.py` - /transcribe, /transcribe_batch 엔드포인트
- `web_ui/services/batch_service.py` - processing_steps 옵션 추가

## 배포 계획

1. 로컬 개발 환경에서 구현 및 테스트
2. Docker 환경에서 통합 테스트
3. Web UI와 API 서버 간 호환성 검증
4. 배포
