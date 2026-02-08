# 모델 다운로드 스크립트 업데이트

## 요약

`download_model_hf.py` 스크립트가 명령줄 옵션을 지원하도록 업데이트되었습니다.

**핵심 특징: 옵션이 없으면 자동으로 모든 단계(다운로드 → 변환 → 압축 → 테스트)를 수행합니다.**

## 사용법

```bash
conda activate stt-py311
python download_model_hf.py [옵션]
```

## 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--no-convert` | CTranslate2 변환 스킵 (PyTorch 모델만 다운로드) | 변환 수행 |
| `--skip-compress` | 모델 파일 압축 스킵 | 압축 수행 |
| `--skip-test` | 모델 로드 테스트 스킵 | 테스트 수행 |
| `--help` | 도움말 표시 | - |

## 사용 예시

### 1. 모든 단계 실행 (권장)
```bash
python download_model_hf.py
```
결과:
- ✅ HF 모델 다운로드
- ✅ CTranslate2 변환 (model.bin 생성)
- ✅ 모델 압축 (tar.gz)
- ✅ MD5 체크섬 생성
- ✅ 로드 테스트

### 2. 변환 스킵 (PyTorch 모델만 필요한 경우)
```bash
python download_model_hf.py --no-convert
```
결과:
- ✅ HF 모델 다운로드
- ⏭️ CTranslate2 변환 스킵
- ✅ 모델 압축
- ✅ MD5 체크섬 생성
- ⏭️ 테스트 스킵

**사용 시기:**
- transformers 백엔드만 사용하는 경우
- faster-whisper가 필요 없는 경우
- 변환 시간을 절약하고 싶은 경우

### 3. 압축 스킵 (모델만 필요한 경우)
```bash
python download_model_hf.py --skip-compress
```
결과:
- ✅ HF 모델 다운로드
- ✅ CTranslate2 변환
- ⏭️ 압축 스킵
- ⏭️ 테스트 실행

**사용 시기:**
- 로컬 개발 환경
- 모델 디렉토리 직접 사용
- 압축 시간 절약

### 4. 테스트 스킵
```bash
python download_model_hf.py --skip-test
```
결과:
- ✅ HF 모델 다운로드
- ✅ CTranslate2 변환
- ✅ 모델 압축
- ⏭️ 로드 테스트 스킵

**사용 시기:**
- 자동화 스크립트
- 메모리 부족 환경
- 빠른 실행 필요

### 5. 옵션 조합
```bash
# 변환과 압축만 수행, 테스트 스킵
python download_model_hf.py --skip-test

# 다운로드와 테스트만 수행 (변환/압축 스킵)
python download_model_hf.py --no-convert --skip-compress
```

## 동작 단계

### Step 1: 기존 모델 정리
- 이전 모델 파일 삭제
- 신규 디렉토리 생성

### Step 2: HF 모델 다운로드
- openai/whisper-large-v3-turbo 다운로드 (1.5GB)
- PyTorch/SafeTensors 형식

### Step 3: 파일 검증
- config.json ✓
- model.safetensors ✓
- generation_config.json ✓
- preprocessor_config.json ✓
- tokenizer.json ✓

### Step 4: CTranslate2 변환 (조건부)
- PyTorch → CTranslate2 바이너리 포맷
- 심링크 생성: model.bin

### Step 5: 압축 (조건부)
- tar.gz로 압축
- 크기 계산 및 압축률 표시

### Step 6: MD5 체크섬 (조건부)
- 무결성 검증용 체크섬 생성

### Step 7: 로드 테스트 (조건부)
- faster-whisper로 모델 로드
- 추론 테스트 실행

## 빠른 참조

| 목적 | 명령어 |
|------|--------|
| **전체 준비** | `python download_model_hf.py` |
| **PyTorch만** | `python download_model_hf.py --no-convert --skip-test` |
| **빠른 실행** | `python download_model_hf.py --skip-test` |
| **압축만** | `python download_model_hf.py --skip-test --no-convert` |
| **도움말** | `python download_model_hf.py --help` |

## 주요 개선사항

### Before (기존)
- 옵션 없음
- 항상 모든 단계 수행
- 변환 실패 시 전체 실패

### After (새 버전)
- ✅ 선택적 단계 실행
- ✅ 옵션 없으면 모든 단계 수행 (기본값)
- ✅ 개별 단계별 진행 상황 표시
- ✅ 에러 처리 개선
- ✅ 도움말 포함

## 주의사항

1. **옵션 없음 = 모든 단계 수행**
   - 변환, 압축, 테스트 모두 수행
   - 이것이 가장 안전한 기본값

2. **--no-convert 사용 시**
   - CTranslate2 모델이 생성되지 않음
   - faster-whisper 백엔드 사용 불가
   - transformers 백엔드로 폴백

3. **메모리 요구사항**
   - 로드 테스트: 16GB 이상 권장
   - 부족하면 --skip-test 사용

## 예상 실행 시간

| 단계 | 시간 | 옵션 |
|------|------|------|
| 다운로드 | 5-10분 | - |
| 변환 | 5-15분 | --no-convert |
| 압축 | 3-5분 | --skip-compress |
| 테스트 | 3-5분 | --skip-test |
| **전체** | **15-40분** | - |

## 다음 단계

```bash
# 1. 모든 단계 실행 (권장)
python download_model_hf.py

# 2. 결과 확인
ls -lh models/openai_whisper-large-v3-turbo/
ls -lh build/output/

# 3. EC2에 배포
scp build/output/*.tar.gz deploy-user@server:/tmp/
scp build/output/*.md5 deploy-user@server:/tmp/
```
