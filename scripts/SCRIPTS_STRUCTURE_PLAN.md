# /scripts 폴더 구조 정리 및 조직화 가이드

## 현재 상태

```
scripts/
├── performance/                          ← 새로 생성됨
│   ├── run_performance_test.py
│   ├── deploy_performance_monitoring.sh
│   └── README.md
├── [기존] build-ec2-engine-image.sh
├── [기존] test_*.py (13+ 파일)
├── [기존] *.sh (여러 개)
└── [기존] build-analysis-image.sh
```

## 제안하는 구조

```
scripts/
├── performance/                          ← 성능 측정 및 모니터링
│   ├── run_performance_test.py
│   ├── deploy_performance_monitoring.sh
│   └── README.md
│
├── testing/                              ← 기능 테스트
│   ├── test_privacy_removal.py          (기존: 루트의 test_privacy_removal.py)
│   ├── test_*.py                         (기존 테스트 파일들)
│   └── README.md
│
├── diagnostics/                          ← 진단 및 디버깅
│   ├── diagnose_model.py                (기존: 루트의 diagnose_model.py)
│   ├── ec2_model_diagnostics.py         (기존: 루트의 ec2_model_diagnostics.py)
│   ├── test_models.sh
│   └── README.md
│
├── deployment/                           ← 배포 관련
│   ├── build-ec2-engine-image.sh
│   ├── build-analysis-image.sh
│   ├── docker-build.sh
│   └── README.md
│
├── utilities/                            ← 유틸리티 및 도구
│   ├── generate_sample_audio.py         (기존: 루트의 generate_sample_audio.py)
│   ├── download_model_hf.py             (기존: 루트의 download_model_hf.py)
│   ├── api_client.py                    (기존: 루트의 api_client.py)
│   └── README.md
│
└── archive/                              ← 참고/보관용
    └── SCRIPTS_MIGRATION.md              (마이그레이션 기록)
```

## 마이그레이션 계획

### Phase 1: 성능 측정 (✅ 완료)

- [x] `scripts/performance/` 생성
- [x] `run_performance_test.py` 작성
- [x] `deploy_performance_monitoring.sh` 작성
- [x] `README.md` (성능 측정 가이드) 작성

### Phase 2: 폴더 생성 (다음 단계)

필요한 디렉토리들을 생성합니다:

```bash
mkdir -p scripts/{testing,diagnostics,deployment,utilities,archive}
```

### Phase 3: 파일 이동

기존 파일들을 새로운 폴더 구조로 정리합니다:

#### 테스팅 폴더로 이동
```bash
# 현재 위치: /Users/a113211/workspace/stt_engine/
# 이동할 파일들:
# - test_privacy_removal.py → scripts/testing/
# - [기타 test_*.py 파일들] → scripts/testing/
```

#### 진단 폴더로 이동
```bash
# - diagnose_model.py → scripts/diagnostics/
# - ec2_model_diagnostics.py → scripts/diagnostics/
```

#### 배포 폴더로 이동
```bash
# - scripts/build-ec2-engine-image.sh → scripts/deployment/
# - scripts/build-analysis-image.sh → scripts/deployment/
```

#### 유틸리티 폴더로 이동
```bash
# - generate_sample_audio.py → scripts/utilities/
# - download_model_hf.py → scripts/utilities/
# - api_client.py → scripts/utilities/
```

### Phase 4: 문서화

각 폴더에 README.md 작성:
- scripts/testing/README.md
- scripts/diagnostics/README.md
- scripts/deployment/README.md
- scripts/utilities/README.md

### Phase 5: 마이그레이션 기록

마이그레이션 완료 후 변경 사항을 문서화합니다.

---

## 각 폴더의 목적

### 1. performance/ (성능 측정)

**목적**: API 및 데이터베이스 성능 측정

**포함 파일**:
- `run_performance_test.py` - 성능 테스트 실행
- `deploy_performance_monitoring.sh` - 배포 자동화
- `README.md` - 성능 측정 가이드

**사용 시기**:
- 운영 서버에서 정기적인 성능 모니터링
- 성능 개선 전/후 비교
- 병목 지점 식별

**예시 명령어**:
```bash
cd scripts/performance
python run_performance_test.py --verbose
bash deploy_performance_monitoring.sh /opt/stt_engine
```

---

### 2. testing/ (기능 테스트)

**목적**: 단위 테스트 및 기능 검증

**포함 파일**:
- `test_privacy_removal.py` - 개인정보 제거 기능 테스트
- 기타 단위 테스트 파일들

**사용 시기**:
- CI/CD 파이프라인에서 자동 실행
- 코드 변경 후 회귀 테스트
- 신규 기능 검증

**예시 명령어**:
```bash
cd scripts/testing
python test_privacy_removal.py
python -m pytest test_*.py -v
```

---

### 3. diagnostics/ (진단 및 디버깅)

**목적**: 모델 및 시스템 진단

**포함 파일**:
- `diagnose_model.py` - 모델 진단 도구
- `ec2_model_diagnostics.py` - EC2 모델 진단
- 기타 진단 스크립트

**사용 시기**:
- 배포 후 초기 검증
- 성능 문제 진단
- 모델 호환성 확인

**예시 명령어**:
```bash
cd scripts/diagnostics
python diagnose_model.py
python ec2_model_diagnostics.py --model base
```

---

### 4. deployment/ (배포 자동화)

**목적**: 도커 이미지 및 환경 구성

**포함 파일**:
- `build-ec2-engine-image.sh` - EC2 이미지 빌드
- `build-analysis-image.sh` - 분석 이미지 빌드
- 기타 배포 스크립트

**사용 시기**:
- 새로운 릴리스 배포
- 환경별 이미지 빌드
- 인프라 업데이트

**예시 명령어**:
```bash
cd scripts/deployment
bash build-ec2-engine-image.sh
bash build-analysis-image.sh v1.0
```

---

### 5. utilities/ (유틸리티 도구)

**목적**: 보조 도구 및 유틸리티

**포함 파일**:
- `generate_sample_audio.py` - 샘플 오디오 생성
- `download_model_hf.py` - 모델 다운로드
- `api_client.py` - API 클라이언트

**사용 시기**:
- 개발 중 테스트 데이터 생성
- 모델 초기화
- API 통합 테스트

**예시 명령어**:
```bash
cd scripts/utilities
python generate_sample_audio.py --duration 30
python download_model_hf.py --model base
python api_client.py --endpoint http://localhost:8000
```

---

## 구현 로드맵

### 즉시 필요 (High Priority)

- [x] `scripts/performance/` 완성 (이미 완료)
- [ ] 다른 폴더 생성
- [ ] 파일 이동 (scripts 하위 파일들)
- [ ] 루트 레벨 파일들 이동

### 중기 필요 (Medium Priority)

- [ ] 각 폴더에 README.md 작성
- [ ] __init__.py 파일 추가 (Python 패키지 구조)
- [ ] import 경로 업데이트

### 선택사항 (Low Priority)

- [ ] 마이그레이션 스크립트 자동화
- [ ] CI/CD에서 자동 재구성
- [ ] 레거시 폴더로 이전 버전 보관

---

## 주의사항

### 1. Import 경로 업데이트

파일을 이동할 때 import 경로가 변경됩니다:

```python
# 이전
from test_privacy_removal import test_function

# 이후
from scripts.testing.test_privacy_removal import test_function
```

### 2. 스크립트 경로 업데이트

bash 스크립트의 경로도 업데이트 필요:

```bash
# 이전
python test_privacy_removal.py

# 이후
python scripts/testing/test_privacy_removal.py
```

### 3. CI/CD 설정 업데이트

CI/CD 파이프라인에서 스크립트 경로 변경:

```yaml
# GitHub Actions 예시
- name: Run tests
  run: python -m pytest scripts/testing/test_*.py -v
```

---

## 마이그레이션 체크리스트

- [ ] 폴더 구조 검증
- [ ] 파일 이동 완료
- [ ] import 경로 검증
- [ ] 각 스크립트 실행 테스트
- [ ] CI/CD 파이프라인 테스트
- [ ] 마이그레이션 문서화
- [ ] 팀원에게 안내

---

## 참고 자료

### 현재 관련 문서

- [성능 측정 가이드](./performance/README.md)
- [배포 가이드](../docs/SERVER_DEPLOYMENT_GUIDE.md)
- [프로젝트 구조](../docs/PROJECT_STRUCTURE_AND_ORGANIZATION.md)

### 외부 자료

- [Python 패키지 구조 Best Practices](https://python-poetry.org/docs/libraries/)
- [Bash 스크립트 권장사항](https://mywiki.wooledge.org/BashGuide)

---

## 완료 후 이점

✅ **명확한 구조**: 스크립트의 용도가 한눈에 파악됨
✅ **유지보수 용이**: 관련 스크립트가 한 곳에 모여있음
✅ **확장성**: 새로운 스크립트 추가가 용이함
✅ **문서화**: 각 폴더의 목적이 명확함
✅ **재사용성**: 스크립트 재사용이 수월함

---

**마지막 업데이트**: 2024-01-15
**상태**: 계획 단계 (Phase 1 완료)
