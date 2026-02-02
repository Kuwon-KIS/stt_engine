#!/bin/bash

# STT Engine - 배포 후 자동 설정 스크립트
# Linux 서버에서 실행: bash post_deploy_setup.sh

set -e

echo "════════════════════════════════════════════════════════════"
echo "🚀 STT Engine - 배포 후 자동 설정"
echo "════════════════════════════════════════════════════════════"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Phase 1: Python 환경 확인
echo -e "${YELLOW}[Phase 1]${NC} Python 환경 확인 중..."
if ! command -v python3.11 &> /dev/null; then
    echo -e "${RED}❌ python3.11을 찾을 수 없습니다${NC}"
    echo "설치: sudo yum install -y python3.11 python3.11-devel"
    exit 1
fi
PYTHON_VERSION=$(/opt/rh/rh-python311/root/usr/bin/python3.11 --version 2>&1 || python3.11 --version)
echo -e "${GREEN}✅ Python 버전: $PYTHON_VERSION${NC}"
echo ""

# Phase 2: venv 생성
echo -e "${YELLOW}[Phase 2]${NC} 가상환경 설정 중..."
if [ ! -d "venv" ]; then
    python3.11 -m venv venv
    echo -e "${GREEN}✅ venv 생성 완료${NC}"
else
    echo -e "${GREEN}✅ venv가 이미 존재합니다${NC}"
fi

source venv/bin/activate
pip install --upgrade pip setuptools wheel
echo ""

# Phase 3: wheels 설치 (PyTorch 포함)
echo -e "${YELLOW}[Phase 3]${NC} wheels 설치 중..."
cd deployment_package

if [ ! -d "wheels" ]; then
    echo -e "${RED}❌ wheels 디렉토리를 찾을 수 없습니다${NC}"
    exit 1
fi

WHEEL_COUNT=$(ls -1 wheels/*.whl 2>/dev/null | wc -l)
TORCH_COUNT=$(ls -1 wheels/torch-*.whl 2>/dev/null | wc -l)

echo "📦 설치할 wheels:"
echo "  • 전체: $WHEEL_COUNT 개"
if [ "$TORCH_COUNT" -gt 0 ]; then
    echo "  • PyTorch: ✅ 포함됨"
else
    echo "  • PyTorch: ⚠️  미포함 (온라인 설치 필요)"
fi
echo ""

# wheels 설치
pip install wheels/*.whl --quiet

# PyTorch가 없으면 온라인 설치
if [ "$TORCH_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⏳ PyTorch를 온라인에서 설치 중...${NC}"
    pip install torch==2.2.0 torchaudio==2.2.0 \
        --index-url https://download.pytorch.org/whl/cu121 --quiet || {
        echo -e "${RED}❌ PyTorch 설치 실패${NC}"
        echo "수동 설치: pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121"
    }
fi

echo -e "${GREEN}✅ wheels 설치 완료${NC}"
echo ""

# Phase 4: CUDA 확인
echo -e "${YELLOW}[Phase 4]${NC} CUDA 호환성 확인 중..."
python3 -c "
import torch
print(f'PyTorch 버전: {torch.__version__}')
print(f'CUDA 사용 가능: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'GPU 메모리: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
"
echo -e "${GREEN}✅ CUDA 확인 완료${NC}"
echo ""

# Phase 5: 모델 다운로드
cd ..
echo -e "${YELLOW}[Phase 5]${NC} 모델 다운로드 시작..."
echo "⏳ 이 과정은 약 10-20분 소요됩니다 (네트워크 속도에 따라 다름)"
python3 download_model.py
echo -e "${GREEN}✅ 모델 다운로드 완료${NC}"
echo ""

# Phase 6: STT Engine 설치
echo -e "${YELLOW}[Phase 6]${NC} STT Engine 패키지 설치 중..."
pip install -e . --quiet
echo -e "${GREEN}✅ STT Engine 설치 완료${NC}"
echo ""

# Phase 7: 검증
echo -e "${YELLOW}[Phase 7]${NC} 최종 검증 중..."
echo ""

echo "🔍 import 테스트:"
python3 -c "import stt_engine; print('  ✅ stt_engine')"
python3 -c "import transformers; print('  ✅ transformers')"
python3 -c "import librosa; print('  ✅ librosa')"
python3 -c "import fastapi; print('  ✅ fastapi')"
echo ""

echo "📊 설치된 패키지 확인:"
pip list | grep -E "(torch|transformers|librosa|fastapi)" || true
echo ""

# Phase 8: 실행 준비
echo -e "${YELLOW}[Phase 8]${NC} API 서버 실행 준비 중..."
echo ""
echo "🚀 다음 명령으로 API 서버를 실행할 수 있습니다:"
echo ""
echo -e "${GREEN}옵션 1: 포그라운드 실행${NC}"
echo "  source venv/bin/activate"
echo "  python3 api_server.py"
echo ""
echo -e "${GREEN}옵션 2: 백그라운드 실행${NC}"
echo "  source venv/bin/activate"
echo "  nohup python3 api_server.py > api.log 2>&1 &"
echo ""
echo -e "${GREEN}옵션 3: Systemd로 등록 (프로덕션)${NC}"
echo "  sudo cp scripts/stt-engine.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable stt-engine"
echo "  sudo systemctl start stt-engine"
echo ""

echo "════════════════════════════════════════════════════════════"
echo -e "${GREEN}✨ 배포 후 자동 설정 완료!${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📝 다음 단계:"
echo "  1. API 서버 실행: python3 api_server.py"
echo "  2. 헬스체크: curl http://localhost:8001/health"
echo "  3. 로그 확인: tail -f logs/api.log"
echo ""
