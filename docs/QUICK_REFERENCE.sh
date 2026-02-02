#!/bin/bash
# ============================================================================
# 📋 STT Engine 배포 빠른 참고 (Quick Reference)
# 
# 현재 상황:
# - ✅ Wheels 준비됨 (59개, 413MB)
# - ✅ 배포 스크립트 완성
# - ✅ Docker 이미지 빌드 스크립트 최적화
# ============================================================================

# ===========================================================================
# 방법 1: Linux 서버로 직접 배포 (권장, 가장 빠름)
# ===========================================================================

echo "👉 방법 1: 오프라인 배포"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 로컬 머신 (macOS)에서:"
echo "  1. 배포 패키지 전송:"
scp -r deployment_package/ user@linux-server:/home/user/stt_engine/
echo ""
echo "📍 Linux 서버에서:"
echo "  2. 배포 실행:"
ssh user@linux-server
cd /home/user/stt_engine/deployment_package
chmod +x deploy.sh
./deploy.sh
echo ""
echo "  3. API 서버 시작:"
python3.11 api_server.py
echo ""
echo "  4. 헬스 체크 (다른 터미널):"
curl http://localhost:8003/health
echo ""

# ===========================================================================
# 방법 2: Docker 이미지 빌드 및 배포
# ===========================================================================

echo ""
echo "👉 방법 2: Docker 이미지로 배포"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 로컬 머신 (macOS)에서:"
echo "  1. Docker 이미지 빌드:"
bash build-engine-image.sh
echo ""
echo "  2. 이미지 확인:"
docker images | grep stt-engine
echo ""
echo "  3. 이미지를 tar로 저장 (자동):"
echo "     → stt-engine-linux-x86_64.tar (생성됨)"
echo ""
echo "📍 Linux 서버로 전송:"
echo "  4. tar 파일 전송:"
scp stt-engine-linux-x86_64.tar user@linux-server:/tmp/
echo ""
echo "📍 Linux 서버에서 로드 및 실행:"
echo "  5. 이미지 로드:"
docker load -i /tmp/stt-engine-linux-x86_64.tar
echo ""
echo "  6. 컨테이너 실행:"
docker run -p 8003:8003 stt-engine:linux-x86_64
echo ""
echo "  7. 헬스 체크 (로컬 머신에서):"
curl http://linux-server:8003/health
echo ""

# ===========================================================================
# 📊 비교 정보
# ===========================================================================

echo ""
echo "📊 방법 비교"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "방법 1 (직접 배포):"
echo "  • 장점: 빠름 (5-10분), 간단함, 의존성 최소"
echo "  • 단점: 서버마다 설치 필요"
echo "  • 추천: ⭐⭐⭐⭐⭐ (가장 권장)"
echo ""
echo "방법 2 (Docker 이미지):"
echo "  • 장점: 서버 간 일관성, 포팅 용이"
echo "  • 단점: 시간 소요 (15-30분), 이미지 크기 큼"
echo "  • 추천: ⭐⭐⭐ (운영 환경에 권장)"
echo ""

# ===========================================================================
# 📂 주요 파일 위치
# ===========================================================================

echo ""
echo "📂 주요 파일"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "로컬 머신:"
echo "  • build-engine-image.sh          (Docker 이미지 빌드)"
echo "  • Dockerfile.engine              (Engine 빌드 참고용)"
echo ""
echo "deployment_package/:"
echo "  • wheels/                        (59개 wheel 파일, 413MB)"
echo "  • deploy.sh                      (배포 실행)"
echo "  • setup_offline.sh               (수동 설치)"
echo "  • run_all.sh                     (서비스 실행)"
echo "  • START_HERE.sh                  (상세 가이드)"
echo "  • DEPLOYMENT_GUIDE.md            (배포 문서)"
echo ""

# ===========================================================================
# ✅ 체크리스트
# ===========================================================================

echo ""
echo "✅ 배포 전 확인사항"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "로컬 머신:"
echo "  [ ] Docker Desktop 설치 (방법 2 선택 시)"
echo "  [ ] SSH 키 설정"
echo ""
echo "Linux 서버:"
echo "  [ ] Python 3.11.5 설치"
echo "  [ ] NVIDIA Driver 설치 (GPU 사용 시)"
echo "  [ ] CUDA 12.1/12.9 설치 (GPU 사용 시)"
echo "  [ ] Docker 설치 (방법 2 선택 시)"
echo "  [ ] 디스크 여유 (최소 2GB)"
echo ""

# ===========================================================================
# 🚀 빠른 시작 (한 줄 명령)
# ===========================================================================

echo ""
echo "🚀 한 줄 시작"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "로컬에서: scp -r deployment_package/ user@server:/home/user/ && ssh user@server 'cd /home/user/deployment_package && ./deploy.sh'"
echo ""

# ===========================================================================
# 📞 문제 해결
# ===========================================================================

echo ""
echo "🆘 문제 해결"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Q: Wheels가 없다는 메시지가 나옴"
echo "A: 자동으로 온라인 설치 모드로 변환됨. 인터넷이 있으면 정상 작동"
echo ""
echo "Q: Docker 이미지 빌드가 느림"
echo "A: 정상. 첫 빌드는 15-30분 소요. 네트워크 상태 확인"
echo ""
echo "Q: 배포 후 API가 작동 안 함"
echo "A: 'python3.11 api_server.py' 실행하고 'curl http://localhost:8003/health' 확인"
echo ""
echo "Q: GPU를 사용하고 싶음"
echo "A: requirements-cuda-12.9.txt 사용. CUDA 드라이버 설치 필수"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
