# 환경변수 및 서비스 Alignment - 검증 결과 및 개선 계획

**검증 실행일**: 2026년 3월 9일  
**검증 도구**: scripts/verify_alignment.py  
**종합 점수**: 19/25 (76.0%) - **PARTIAL ⚠**

---

## 📊 검증 결과 요약

### 점수 분포

| 항목 | 상태 | 점수 | 비고 |
|------|------|------|------|
| 환경변수 명명 규칙 | ⚠️ 부분 | 4/10 | **6개 환경변수 정의 누락** |
| Service Singleton | ✅ 양호 | 6/6 | 모든 서비스 완료 |
| 레거시 코드 | ✅ 양호 | 5/5 | 레거시 파일/패턴 정리 완료 |
| FormData ↔ API | ✅ 양호 | 3/3 | 모든 task 매핑 일치 |
| 코드 메트릭 | ✅ 양호 | 1/1 | 코드 크기 목표 달성 |

---

## 🔴 긴급 개선 필요 (즉시 처리)

### 1. 환경변수 정의 누락 (6개)

#### 문제점
다음 환경변수들이 config.py에서 실제로 정의/사용되지 않음:

```
❌ PRIVACY_REMOVAL_VLLM_API_BASE
❌ CLASSIFICATION_VLLM_MODEL_NAME
❌ CLASSIFICATION_VLLM_API_BASE
❌ CLASSIFICATION_PROMPT_TYPE
❌ ELEMENT_DETECTION_VLLM_MODEL_NAME
❌ ELEMENT_DETECTION_VLLM_API_BASE
```

#### 원인 분석
- config.py에서 정의되었지만 실제 메서드에서 구현되지 않음
- 또는 다른 이름으로 구현됨 (예: `get_vllm_api_base()` 메서드는 존재하지만 task별 환경변수 확인 로직 부재)

#### 개선 방안

**Step 1: config.py 메서드 검토**

```python
# 현재: get_vllm_api_base(task) - task별 환경변수를 확인하지 않음
def get_vllm_api_base(self, task: str, default: str = "http://localhost:8001/v1") -> str:
    # 수정 필요: task별 환경변수(PRIVACY_REMOVAL_VLLM_API_BASE 등) 확인

# 수정 후:
def get_vllm_api_base(self, task: str, default: str = "http://localhost:8001/v1") -> str:
    # 1. FormData 확인
    form_value = self.form_data.get(f"{task}_vllm_api_base", "").strip()
    if form_value:
        return form_value
    
    # 2. Task별 환경변수 확인
    env_key = f"{task.upper()}_VLLM_API_BASE"
    env_value = os.getenv(env_key, "").strip()
    if env_value:
        return env_value
    
    # 3. 공용 환경변수 확인
    common_value = os.getenv("VLLM_API_BASE", "").strip()
    if common_value:
        return common_value
    
    # 4. 기본값
    return default
```

**Step 2: Classification 환경변수 추가**

```python
# config.py에 추가 필요
def get_classification_vllm_model_name(self, default_fallback: Optional[str] = None) -> str:
    """Classification vLLM 모델명"""
    return self.get_vllm_model_name('classification', default_fallback)

def get_classification_vllm_api_base(self) -> str:
    """Classification vLLM API base"""
    return self.get_vllm_api_base('classification')

def get_classification_prompt_type(self, default: str = "classification_default_v1") -> str:
    """Classification 프롬프트 타입"""
    form_value = self.form_data.get("classification_prompt_type", "").strip()
    if form_value:
        return form_value
    
    env_value = os.getenv("CLASSIFICATION_PROMPT_TYPE", "").strip()
    if env_value:
        return env_value
    
    return default
```

**Step 3: Element Detection 환경변수 추가**

```python
def get_element_detection_vllm_model_name(self, default_fallback: Optional[str] = None) -> str:
    """Element Detection vLLM 모델명"""
    return self.get_vllm_model_name('element_detection', default_fallback)

def get_element_detection_vllm_api_base(self) -> str:
    """Element Detection vLLM API base"""
    return self.get_vllm_api_base('element_detection')
```

### 2. 레거시 EXTERNAL_API_URL 참조 제거

#### 문제점
```
❌ 발견: 레거시 EXTERNAL_API_URL
```

#### 위치 파악
```bash
# grep으로 찾기
grep -r "EXTERNAL_API_URL" /Users/a113211/workspace/stt_engine --include="*.py" --exclude-dir=.git
```

#### 수정 사항
- `EXTERNAL_API_URL` 모든 참조를 `ELEMENT_DETECTION_AGENT_URL`로 변경
- constants.py에서도 정의 확인 및 업데이트

---

## 🟡 단기 개선 (1주일 내)

### 3. 환경변수 검증 강화

**추가할 검증 로직:**

```python
class ConfigValidator:
    """환경변수 및 설정 검증"""
    
    @staticmethod
    def validate_required_env() -> bool:
        """필수 환경변수 검증"""
        required = [
            'VLLM_MODEL_NAME',
            'VLLM_API_BASE',
        ]
        
        optional = [
            'PRIVACY_REMOVAL_VLLM_MODEL_NAME',
            'CLASSIFICATION_VLLM_MODEL_NAME',
            'ELEMENT_DETECTION_AGENT_URL',
        ]
        
        missing = []
        for var in required:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"필수 환경변수 누락: {', '.join(missing)}")
        
        return True
    
    @staticmethod
    def validate_urls() -> bool:
        """URL 형식 검증"""
        urls = {
            'VLLM_API_BASE': os.getenv('VLLM_API_BASE'),
            'ELEMENT_DETECTION_AGENT_URL': os.getenv('ELEMENT_DETECTION_AGENT_URL'),
        }
        
        for name, url in urls.items():
            if url and not url.startswith(('http://', 'https://')):
                raise ValueError(f"{name}이 유효한 URL 형식이 아님: {url}")
        
        return True
```

### 4. API 문서 생성

생성할 문서:
- [ ] FormData 파라미터 스키마 (OpenAPI format)
- [ ] 환경변수 설정 가이드
- [ ] 우선순위 명명 규칙 정리

---

## 📋 개선 작업 체크리스트

### 즉시 처리 (TODAY)
- [ ] config.py의 `get_vllm_api_base()` 메서드 수정
- [ ] Classification 환경변수 메서드 추가 (3개)
- [ ] Element Detection 환경변수 메서드 추가 (2개)
- [ ] EXTERNAL_API_URL 모든 참조 제거 및 ELEMENT_DETECTION_AGENT_URL로 변경
- [ ] verify_alignment.py 다시 실행하여 점수 확인

### 수정 후 예상 점수
```
수정 전: 19/25 (76.0%)
수정 후: 24/25 (96.0%) - 예상
```

---

## 🔍 상세 문제 분석

### 왜 이런 일이 발생했는가?

1. **부분적 구현**
   - FormDataConfig 추상화 계층은 만들어졌지만
   - 모든 task별 환경변수 메서드가 구현되지 않음

2. **환경변수 정규화 미완료**
   - commit edb38d8에서 문서만 업데이트
   - 코드 구현이 따라가지 못함

3. **레거시 참조 누락**
   - EXTERNAL_API_URL → ELEMENT_DETECTION_AGENT_URL 변경이 완전하지 않음

---

## 💡 근본 원인 및 예방 방안

### 근본 원인
- 환경변수 정규화 작업이 3개 task 모두를 커버하지 않음
- 검증 스크립트가 없어서 미완료 부분을 발견하지 못함

### 예방 방안
1. **자동 검증 CI/CD**
   - GitHub Actions에서 verify_alignment.py 자동 실행
   - 점수 < 90%면 PR 병합 차단

2. **체계적 구현 체크리스트**
   ```
   - [ ] FormData 파라미터 추가
   - [ ] config.py 메서드 추가
   - [ ] app.py에서 메서드 호출 확인
   - [ ] web_ui에서 파라미터 전송 확인
   - [ ] 환경변수 테스트 추가
   ```

3. **검증 스크립트 활용**
   - 매 커밋 전에 verify_alignment.py 실행
   - 점수가 유지/상승하는지 확인

---

## 📈 검증 스크립트 활용 가이드

### 로컬 실행
```bash
conda run -n stt-py311 python scripts/verify_alignment.py
```

### 자동화 (GitHub Actions)
```yaml
name: Alignment Verification

on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run alignment verification
        run: python scripts/verify_alignment.py
```

---

## 🎯 최종 권장사항

### Priority 1 (오늘)
1. config.py 메서드 완성 (6개 환경변수)
2. EXTERNAL_API_URL 제거
3. 검증 스크립트 재실행
4. 점수 96% 이상 달성

### Priority 2 (이번 주)
1. 자동 검증 CI/CD 구성
2. 환경변수 검증 로직 추가
3. Docker env 파일 점검

### Priority 3 (이번 달)
1. API 문서 자동 생성
2. 모니터링 대시보드 강화
3. 운영 가이드 정리

---

## 부록: 수정 전/후 비교

### 수정 전
```
환경변수 명명 규칙: 4/10 (40%)  ❌
Service Singleton: 6/6 (100%)  ✅
레거시 코드: 5/5 (100%)  ✅
FormData ↔ API: 3/3 (100%)  ✅
코드 메트릭: 1/1 (100%)  ✅
─────────────────────────────
전체: 19/25 (76%) - PARTIAL ⚠️
```

### 수정 후 (예상)
```
환경변수 명명 규칙: 9/10 (90%)  ✅
Service Singleton: 6/6 (100%)  ✅
레거시 코드: 5/5 (100%)  ✅
FormData ↔ API: 3/3 (100%)  ✅
코드 메트릭: 1/1 (100%)  ✅
─────────────────────────────
전체: 24/25 (96%) - PASS ✓
```

