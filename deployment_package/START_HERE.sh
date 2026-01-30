#!/bin/bash

###############################################################################
# STT Engine 오프라인 배포 패키지 - 최종 설정 가이드
#
# 이 파일을 읽고 나열된 단계를 따르세요.
###############################################################################

cat << 'EOF'

╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║         🚀 STT Engine 오프라인 배포 패키지 - 설치 가이드                    ║
║                                                                            ║
║  대상: Linux 서버 (Python 3.11.5, NVIDIA Driver 575.57.08, CUDA 12.9)    ║
║  작성: 2026-01-30                                                          ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝


📋 현재 디렉토리 구조
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

deployment_package/
├── 🎯 핵심 스크립트
│   ├── ⬇️  download_wheels_macos.sh      (로컬: Wheel 다운로드)
│   ├── 🚀 deploy.sh                     (서버: 배포 실행)
│   ├── 📦 setup_offline.sh              (서버: 수동 설치)
│   └── ▶️  run_all.sh                    (서버: 서비스 실행)
│
├── 📖 설명서 (반드시 읽기!)
│   ├── 👉 QUICKSTART.md                 ← 시작하기 (필독!)
│   ├── 📚 DEPLOYMENT_GUIDE.md           (상세 가이드)
│   ├── 📄 README.md                     (패키지 개요)
│   └── ✅ COMPLETION_SUMMARY.md         (완성 체크리스트)
│
├── 📋 설정 파일
│   ├── requirements.txt                 (의존성 목록)
│   └── requirements-cuda-12.9.txt       (CUDA 최적화)
│
└── 📦 wheels/                           (다운로드 대기 중)
    └── (여기에 .whl 파일들이 생성됩니다)


🎯 3단계 배포 프로세스
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣  로컬 환경 (인터넷 있음)
    📍 위치: macOS/Linux 로컬 머신
    ⏱️  시간: 15-30분
    
    실행:
    $ cd deployment_package
    $ chmod +x download_wheels_macos.sh
    $ ./download_wheels_macos.sh
    
    결과:
    ✅ wheels/ 디렉토리에 2-3GB 파일 생성

2️⃣  데이터 전송 (네트워크)
    📍 전송 방법:
    • USB 드라이브
    • SCP/SFTP
    • 네트워크 드라이브
    
    명령어:
    $ scp -r deployment_package user@server:/home/user/

3️⃣  Linux 서버 배포 (인터넷 없음)
    📍 위치: Linux 서버 (외부 통신 불가)
    ⏱️  시간: 5-10분
    
    실행:
    $ cd /home/user/deployment_package
    $ chmod +x deploy.sh
    $ ./deploy.sh /opt/stt_engine_venv
    
    결과:
    ✅ 가상환경 생성 및 모든 패키지 설치


📦 각 파일의 역할
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📥 download_wheels_macos.sh (단계 1 - 로컬)
   • 목적: Linux 플랫폼용 wheel 파일 다운로드
   • 환경: macOS/Linux with 인터넷
   • 시간: 15-30분
   • 결과: wheels/ 디렉토리 (2-3GB)

🚀 deploy.sh (단계 3 - 서버)
   • 목적: 완전 자동화 배포
   • 환경: Linux 서버 (인터넷 불필요)
   • 시간: 5-10분
   • 기능: venv 생성 → pip 업그레이드 → wheel 설치 → 검증

📦 setup_offline.sh (대체 방법)
   • 목적: 수동 설치 (deploy.sh 실패 시)
   • 사용법: ./setup_offline.sh /path/to/venv

▶️  run_all.sh (배포 후)
   • 목적: STT Engine과 vLLM 함께 실행
   • 사용법: ./run_all.sh /opt/stt_engine_venv


🔧 시스템 요구사항 확인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Linux 서버에서 다음을 확인하세요:

✅ Python 버전
   $ python3 --version
   → Python 3.11.5 필요

✅ NVIDIA 드라이버
   $ nvidia-smi
   → Driver 575.57.08 이상

✅ CUDA 버전
   $ nvidia-smi | grep CUDA
   → CUDA 12.1 또는 12.9

✅ GPU 메모리
   $ nvidia-smi | grep memory.total
   → 6GB 이상

✅ 디스크 공간
   $ df -h /
   → 10GB 이상 여유


📖 추천 읽기 순서
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 👉 QUICKSTART.md (지금 읽기!)
   • 3단계 프로세스
   • 예상 시간
   • 빠른 확인

2. 📚 DEPLOYMENT_GUIDE.md (상세 정보)
   • 전체 과정 설명
   • 모든 옵션
   • 트러블슈팅

3. 📄 README.md (참고)
   • 패키지 개요
   • 포함 패키지
   • 사용 예제

4. ✅ COMPLETION_SUMMARY.md (체크리스트)
   • 생성된 파일 확인
   • 검증 방법
   • 완료 기준


🚀 빠른 시작 명령어
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 로컬 (인터넷 있음)
cd deployment_package && ./download_wheels_macos.sh

# 서버로 전송
scp -r deployment_package user@server:/home/user/

# 서버에서 배포
cd deployment_package && ./deploy.sh /opt/stt_engine_venv

# 배포 확인
source /opt/stt_engine_venv/bin/activate
python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"


📊 예상 시간 및 크기
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 단계            | 크기   | 시간      | 위치           |
|-----------------|--------|-----------|----------------|
| Wheel 다운로드  | 2-3GB  | 15-30분   | 로컬 (인터넷)  |
| 데이터 전송     | 2-3GB  | 가변      | 네트워크       |
| 서버 배포       | -      | 5-10분    | 서버 (오프라인)|
| 모델 다운로드*  | 5GB    | 20-30분   | 서버 (선택)    |
| ─────────────── | ────── | ───────── | ─────────────  |
| 합계            | 9-11GB | 40-70분   | -              |

* 모델 다운로드는 선택사항 (사전 다운로드 후 전송 가능)


⚡ 문제 해결
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

문제 발생 시:

1. QUICKSTART.md의 "🆘 문제 해결" 섹션 확인
2. DEPLOYMENT_GUIDE.md의 "트러블슈팅" 섹션 확인
3. 에러 메시지와 함께 로그 확인:
   $ python3 api_server.py 2>&1 | tail -50


✨ 다음 단계
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 👉 QUICKSTART.md 열기 (필독!)
   $ cat QUICKSTART.md

2. 서버 요구사항 확인
   $ python3 --version && nvidia-smi

3. Wheel 다운로드 시작
   $ ./download_wheels_macos.sh

4. 배포 패키지 전송
   $ scp -r deployment_package user@server:/home/user/

5. 서버에서 배포
   $ ssh user@server
   $ cd deployment_package && ./deploy.sh


💡 팁
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• 모든 스크립트는 이미 실행 권한을 가지고 있습니다
• 각 문서는 독립적으로 읽을 수 있습니다
• deploy.sh는 완전히 자동화되어 있습니다
• wheels 디렉토리는 여러 서버에 재사용 가능합니다


════════════════════════════════════════════════════════════════════════════

📖 다음 페이지: QUICKSTART.md를 읽으세요!

════════════════════════════════════════════════════════════════════════════

EOF
