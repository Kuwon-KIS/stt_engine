## 📚 STT Engine 문서 색인

## 🚀 빠른 시작
- **[../README.md](../README.md)** - 프로젝트 개요
- **[../QUICKSTART.md](../QUICKSTART.md)** - 5분 안에 시작하기
- **[status/DEPLOYMENT_STATUS_CURRENT.md](status/DEPLOYMENT_STATUS_CURRENT.md)** - 현재 배포 상태
- **[status/MODEL_READY.md](status/MODEL_READY.md)** - 모델 준비 완료 현황

## 🔐 Privacy Removal 기능
- **[PRIVACY_REMOVAL_GUIDE.md](PRIVACY_REMOVAL_GUIDE.md)** - Privacy Removal 전체 가이드
- **[WEB_UI_PRIVACY_REMOVAL_INTEGRATION.md](WEB_UI_PRIVACY_REMOVAL_INTEGRATION.md)** - Web UI 통합 계획 및 구현 ✨

## 📦 배포 및 설치
- **[deployment/DEPLOYMENT.md](deployment/DEPLOYMENT.md)** - 상세 배포 가이드
- **[deployment/OFFLINE_DEPLOYMENT_GUIDE.md](deployment/OFFLINE_DEPLOYMENT_GUIDE.md)** - 오프라인 배포
- **[deployment/OFFLINE_ENVIRONMENT.md](deployment/OFFLINE_ENVIRONMENT.md)** - 오프라인 환경 설정
- **[deployment/PYTORCH_FINAL_SOLUTION.md](deployment/PYTORCH_FINAL_SOLUTION.md)** - PyTorch 최종 솔루션
- **[deployment/DEPLOYMENT_CHECKLIST.md](deployment/DEPLOYMENT_CHECKLIST.md)** - 배포 체크리스트

## 🔧 기술 문서
- **[API_USAGE_GUIDE.md](API_USAGE_GUIDE.md)** - API 사용 상세 가이드
- **[API_SERVER_RESTRUCTURING_GUIDE.md](API_SERVER_RESTRUCTURING_GUIDE.md)** - API 서버 재구조화
- **[architecture/MODEL_STRUCTURE.md](architecture/MODEL_STRUCTURE.md)** - 모델 구조 설명
- **[architecture/MODEL_COMPRESSION.md](architecture/MODEL_COMPRESSION.md)** - 모델 압축 기법
- **[architecture/MODEL_MIGRATION_SUMMARY.md](architecture/MODEL_MIGRATION_SUMMARY.md)** - 모델 마이그레이션

## 🌐 Web UI
- **[WEB_UI_ARCHITECTURE.md](WEB_UI_ARCHITECTURE.md)** - Web UI 아키텍처
- **[SETUP_WEB_UI.md](SETUP_WEB_UI.md)** - Web UI 설정
- **[WEB_UI_PRIVACY_REMOVAL_INTEGRATION.md](WEB_UI_PRIVACY_REMOVAL_INTEGRATION.md)** - Privacy Removal Web UI 통합 ✨

## 📋 트러블슈팅
- **[troubleshooting/](troubleshooting/)** - 문제 해결 가이드

## 📖 기타 가이드
- **[guides/](guides/)** - 각종 설정 및 마이그레이션 가이드
- **[../scripts/](../scripts/)** - 자동화 스크립트

---

## 📂 전체 문서 구조

```
stt_engine/
├── README.md                      ← 프로젝트 메인
├── QUICKSTART.md                  ← 시작 가이드
│
├── scripts/                       ← 자동화 스크립트
│   ├── build-stt-engine-cuda.sh
│   ├── build-background.sh
│   ├── run-docker-gpu.sh
│   └── ...
│
└── docs/
    ├── index.md                   ← 여기서 시작
    ├── PRIVACY_REMOVAL_GUIDE.md   ← Privacy Removal 기능 ✨
    ├── WEB_UI_PRIVACY_REMOVAL_INTEGRATION.md ← Web UI 통합 ✨
    ├── status/
    │   ├── DEPLOYMENT_STATUS_CURRENT.md
    │   ├── OFFLINE_DEPLOYMENT_READINESS.md
    │   ├── MODEL_READY.md
    │   ├── REFACTORING_COMPLETE.md
    │   ├── REFACTORING_PLAN.md
    │   └── REFACTORING_SUMMARY.md
    ├── deployment/
    │   ├── DEPLOYMENT.md
    │   ├── OFFLINE_DEPLOYMENT_GUIDE.md
    │   ├── OFFLINE_ENVIRONMENT.md
    │   ├── PYTORCH_FINAL_SOLUTION.md
    │   ├── DEPLOYMENT_CHECKLIST.md
    │   ├── DOCKER_REBUILD_GUIDE.md
    │   └── ...
    ├── architecture/
    │   ├── MODEL_STRUCTURE.md
    │   ├── MODEL_COMPRESSION.md
    │   ├── MODEL_MIGRATION_SUMMARY.md
    │   └── MODEL_COMPRESSION_QUICKSTART.md
    ├── troubleshooting/
    │   ├── 00_READ_ME_FIRST.md
    │   ├── CORRECT_FINAL_DEPLOYMENT.md
    │   ├── PYTORCH_INSTALL_METHODS_ANALYSIS.md
    │   └── ... (20+ troubleshooting guides)
    └── guides/
        └── ...
```

## 상황별 추천 문서

| 상황 | 추천 문서 |
|------|---------|
| 처음 시작 | [../README.md](../README.md) → [../QUICKSTART.md](../QUICKSTART.md) |
| 배포 상태 | [status/DEPLOYMENT_STATUS_CURRENT.md](status/DEPLOYMENT_STATUS_CURRENT.md) |
| 모델 준비 | [status/MODEL_READY.md](status/MODEL_READY.md) |
| Privacy Removal | [PRIVACY_REMOVAL_GUIDE.md](PRIVACY_REMOVAL_GUIDE.md) |
| Web UI Privacy 통합 | [WEB_UI_PRIVACY_REMOVAL_INTEGRATION.md](WEB_UI_PRIVACY_REMOVAL_INTEGRATION.md) ✨ |
| API 사용법 | [API_USAGE_GUIDE.md](API_USAGE_GUIDE.md) |
| Linux 배포 | [deployment/DEPLOYMENT.md](deployment/DEPLOYMENT.md) |
| 오프라인 배포 | [deployment/OFFLINE_DEPLOYMENT_GUIDE.md](deployment/OFFLINE_DEPLOYMENT_GUIDE.md) |
| 오프라인 환경 | [deployment/OFFLINE_ENVIRONMENT.md](deployment/OFFLINE_ENVIRONMENT.md) |
| PyTorch 설치 | [deployment/PYTORCH_FINAL_SOLUTION.md](deployment/PYTORCH_FINAL_SOLUTION.md) |
| 배포 체크리스트 | [deployment/DEPLOYMENT_CHECKLIST.md](deployment/DEPLOYMENT_CHECKLIST.md) |
| 기술 이해 | [architecture/](architecture/) |
| 문제 해결 | [troubleshooting/00_READ_ME_FIRST.md](troubleshooting/00_READ_ME_FIRST.md) |
| Docker 재구축 | [deployment/DOCKER_REBUILD_GUIDE.md](deployment/DOCKER_REBUILD_GUIDE.md) |
| 자동화 스크립트 | [../scripts/](../scripts/) |

---

**마지막 업데이트**: 2026년 2월 19일
