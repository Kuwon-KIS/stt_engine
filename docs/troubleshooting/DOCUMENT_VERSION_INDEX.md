# 📚 [2026-02-03 v1.0] 문서 버전 인덱스 및 순서 가이드

**최종 업데이트**: 2026-02-03  
**목적**: 모든 배포/문제해결 문서의 버전, 상태, 읽는 순서 한눈에 보기

---

## 🎯 빠른 시작: 지금 읽어야 할 순서

### 1단계: 이것부터 읽기 (필수)
| 문서 | 버전 | 날짜 | 상태 | 이유 |
|------|------|------|------|------|
| 📌 [00_READ_ME_FIRST.md](00_READ_ME_FIRST.md) | v2.0 | 2026-02-03 | ✅ 현재 | **먼저 읽으세요** - 전체 흐름 이해 |

### 2단계: 배포 방법 선택
| 문서 | 버전 | 날짜 | 상태 | 대상 |
|------|------|------|------|------|
| 🎯 [CORRECT_FINAL_DEPLOYMENT.md](CORRECT_FINAL_DEPLOYMENT.md) | v2.0 | 2026-02-03 | ✅ 권장 | **온라인 서버** - pip install로 설치 |
| 📊 [PYTORCH_INSTALL_METHODS_ANALYSIS.md](PYTORCH_INSTALL_METHODS_ANALYSIS.md) | v2.0 | 2026-02-03 | ✅ 참고 | 과거 실패한 방법 분석 + 최종 스크립트 |
| ✅ [DEPLOYMENT_FINAL_CORRECTION.md](DEPLOYMENT_FINAL_CORRECTION.md) | v2.0 | 2026-02-03 | ✅ 참고 | 왜 이 방법만 작동하는지 설명 |
| 🔍 [SERVER_CUDA_STATUS.md](SERVER_CUDA_STATUS.md) | v1.0 | 2026-02-03 | ✅ 참고 | 서버 환경 검증 (이미 확인함) |

### 🔧 빌드 스크립트
| 파일 | 용도 | 상태 |
|------|------|------|
| 📜 `build-stt-engine-cuda.sh` | **CUDA 12.9 Docker 이미지 자동 빌드** | ✅ 추천 |
| ℹ️ `build-engine-image.sh` (루트) | 구형 빌드 스크립트 (CPU 버전) | ❌ 미사용 |

### 3단계: 더 알아보기 (선택사항)
| 문서 | 버전 | 날짜 | 상태 | 이유 |
|------|------|------|------|------|
| 📊 [PYTORCH_FINAL_SOLUTION.md](../deployment/PYTORCH_FINAL_SOLUTION.md) | v2.0 | 2026-02-02 | ✅ 참고 | PyTorch CUDA 선택 상세 가이드 |
| ⚙️ [BUILD_SYSTEM_CONFIG.md](BUILD_SYSTEM_CONFIG.md) | v1.0 | 2026-02-03 | ✅ 참고 | 빌드 설정, 버전, 검증 체크리스트 |

---

## ❌ 이미 작동하지 않음 (더 이상 사용 금지)

### v1.0-DEPRECATED: Mac에서 휠 다운로드하려던 방식
| 문서 | 버전 | 날짜 | 상태 | 왜 안 되는가 |
|------|------|------|------|------------|
| ❌ [EXACT_CUDA_12.4_COMMANDS.md](EXACT_CUDA_12.4_COMMANDS.md) | v1.0-DEPRECATED | 2026-02-03 | 🚫 작동 안 함 | Mac에서 Linux 휠을 다운로드할 수 없음 (아키텍처 차이) |
| ❌ [QUICK_CUDA_12.4_DEPLOY.md](QUICK_CUDA_12.4_DEPLOY.md) | v1.0-DEPRECATED | 2026-02-03 | 🚫 작동 안 함 | Docker 이미지 재빌드 방식 불가능 |
| ❌ [PYTORCH_CUDA_NONE_FIX.md](PYTORCH_CUDA_NONE_FIX.md) | v1.0-DEPRECATED | 2026-02-03 | 🚫 작동 안 함 | 컨테이너 수정 후 cp는 작동하지 않음 |
| ❌ [CUDA_12.4_BUILD_GUIDE.md](CUDA_12.4_BUILD_GUIDE.md) | v1.0-DEPRECATED | 2026-02-02 | 🚫 작동 안 함 | Mac/Linux 아키텍처 불일치 |
| ℹ️ [CUDA_12.9_COMPATIBILITY.md](CUDA_12.9_COMPATIBILITY.md) | v1.0 | 2026-02-01 | ⚠️ 부분 유효 | 초기 분석 (결론은 outdated) |

---

## 📊 문서 상태 범례

| 상태 | 의미 | 액션 |
|------|------|------|
| ✅ 현재 | 지금 사용하는 문서 | **지금 읽고 따르기** |
| ✅ 유효 | 참고용으로 유용함 | 필요하면 읽기 |
| ⚠️ 부분 유효 | 일부만 참고 가능 | 선택적 읽기 |
| 🚫 작동 안 함 | 이미 증명된 실패 | **절대 따르지 마기** |
| v1.0-DEPRECATED | 이전 방식 (실패) | 참고만 하고 따르지 말기 |

---

## 🔄 버전 관리 정책

### 현재 시스템
- **v2.0** (2026-02-03): 최종 정정된 올바른 방법 ✅
- **v1.0** (2026-02-01 ~ 2026-02-02): 초기 실패한 시도들 ❌
- **v1.0-DEPRECATED**: 명확히 실패가 증명된 방식들

### 버전 업그레이드 기준
- 새로운 PyTorch 버전 출시 → v2.1
- 새로운 CUDA Toolkit 버전 → 새 문서 생성 (CUDA_XXX.X_SOLUTION.md)
- 서버 배포 경험 추가 → v2.X

---

## 🎯 현재 상황 요약

### ✅ 작동 중인 방법
1. **온라인 서버**: `pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu129`
   - 파일: [CORRECT_FINAL_DEPLOYMENT.md](CORRECT_FINAL_DEPLOYMENT.md)
   - 검증됨: ✅ 서버 환경 확인 완료 (CUDA 12.9 + 드라이버 575.57.08)

### ❌ 실패한 방법들
1. **Mac에서 Linux 휠 다운로드**: 아키텍처 불일치 (darwin vs x86_64-linux-gnu)
2. **Docker 이미지 재빌드**: 스토리지 문제, 휠 의존성 해결 불가
3. **컨테이너 수정 후 복사**: 작동하지 않음

### 🔑 핵심 교훈
```
❌ Mac에서 하려고 한 일들:
   - 휠 다운로드 (다른 아키텍처)
   - Docker 빌드 (재빌드 실패)
   - 복잡한 배포 (불필요)

✅ 서버에서 해야 할 일:
   - pip install torch (온라인 서버만 가능)
   - 간단한 재설치 (다운타임 최소)
   - 기존 설정 유지 (나머지는 그대로)
```

---

## 📁 파일 위치 안내

### 주요 배포/문제해결 문서들
- 📌 **시작**: `docs/troubleshooting/00_READ_ME_FIRST.md`
- 🎯 **배포**: `docs/troubleshooting/CORRECT_FINAL_DEPLOYMENT.md`
- 📊 **분석**: `docs/troubleshooting/DEPLOYMENT_FINAL_CORRECTION.md`
- ℹ️ **서버 환경**: `docs/troubleshooting/SERVER_CUDA_STATUS.md`

### 추가 참고 문서
- `docs/deployment/PYTORCH_FINAL_SOLUTION.md` - PyTorch 상세 설명
- `deployment_package/DEPLOYMENT_STATUS.md` - 휠 다운로드 상태
- `deployment_package/START_HERE.sh` - 배포 스크립트

---

## 💡 자주 묻는 질문

**Q: 어떤 문서부터 읽어야 하나요?**  
A: [00_READ_ME_FIRST.md](00_READ_ME_FIRST.md) 부터 시작하세요 - 전체 흐름이 정리되어 있습니다.

**Q: 실제 배포는 어떻게 하나요?**  
A: [CORRECT_FINAL_DEPLOYMENT.md](CORRECT_FINAL_DEPLOYMENT.md)의 **3단계: 서버에서 PyTorch 설치** 섹션을 따르세요.

**Q: 왜 Mac에서 못하나요?**  
A: [DEPLOYMENT_FINAL_CORRECTION.md](DEPLOYMENT_FINAL_CORRECTION.md)의 **아키텍처 불일치** 섹션을 읽어보세요.

**Q: 이전 가이드들은 왜 작동 안 하나요?**  
A: 위 "이미 작동하지 않음" 섹션의 각 문서별 설명을 참고하세요.

---

**마지막 업데이트**: 2026-02-03  
**다음 계획**: 배포 실행 후 성공 케이스 추가 (v2.1)
