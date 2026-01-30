#!/bin/bash

###############################################################################
# STT Engine - Linux 서버 배포 스크립트
#
# 사용법:
#   chmod +x deploy.sh
#   ./deploy.sh [venv_path]
#
# 예제:
#   ./deploy.sh /opt/stt_engine_venv
#   ./deploy.sh                          # 기본값: ~/.venv/stt_engine
#
# 전제 조건:
#   - Python 3.11.5 설치
#   - NVIDIA Driver 설치 (CUDA 가능 GPU 필요)
#   - CUDA 12.1/12.9 호환
###############################################################################

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WHEELS_DIR="${SCRIPT_DIR}/wheels"
VENV_PATH="${1:-${HOME}/.venv/stt_engine}"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 1. 환경 검사
print_header "1️⃣  시스템 환경 검사"

# Python 버전 확인
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 버전: $PYTHON_VERSION"

if [[ ! $PYTHON_VERSION =~ ^3\.11 ]]; then
    print_error "Python 3.11.x 필요 (현재: $PYTHON_VERSION)"
    exit 1
fi
print_success "Python 3.11.x 확인됨"

# wheels 디렉토리 확인
if [ ! -d "$WHEELS_DIR" ]; then
    print_error "wheels 디렉토리 없음: $WHEELS_DIR"
    exit 1
fi

WHEEL_COUNT=$(find "$WHEELS_DIR" -name "*.whl" | wc -l)
if [ $WHEEL_COUNT -eq 0 ]; then
    print_error "wheels 디렉토리에 .whl 파일이 없습니다"
    exit 1
fi
print_success "$WHEEL_COUNT개의 .whl 파일 발견"

# GPU 확인
print_info "GPU 장치 확인..."
if command -v nvidia-smi &> /dev/null; then
    NVIDIA_OUTPUT=$(nvidia-smi --query-gpu=name --format=csv,noheader)
    print_success "NVIDIA GPU 감지됨: $NVIDIA_OUTPUT"
else
    print_warning "nvidia-smi를 찾을 수 없습니다"
    print_warning "CUDA 드라이버 설치를 확인하세요"
fi

echo ""

# 2. 가상환경 생성
print_header "2️⃣  Python 가상환경 생성"

if [ -d "$VENV_PATH" ]; then
    print_warning "가상환경이 이미 존재합니다: $VENV_PATH"
    read -p "기존 환경을 삭제하고 재생성하시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "기존 환경 삭제 중..."
        rm -rf "$VENV_PATH"
    else
        print_info "기존 환경 유지"
    fi
fi

if [ ! -d "$VENV_PATH" ]; then
    print_info "새 가상환경 생성 중: $VENV_PATH"
    python3 -m venv "$VENV_PATH"
    print_success "가상환경 생성 완료"
fi

# 가상환경 활성화
source "${VENV_PATH}/bin/activate"
print_success "가상환경 활성화됨"

echo ""

# 3. pip 업그레이드
print_header "3️⃣  pip 업그레이드"

pip install --upgrade pip setuptools wheel -q
print_success "pip 업그레이드 완료"

echo ""

# 4. 오프라인 wheel 설치
print_header "4️⃣  Python 패키지 설치 (오프라인)"

print_info "설치 중인 패키지:"
echo ""

INSTALLED=0
FAILED=0

for wheel in "$WHEELS_DIR"/*.whl; do
    if [ -f "$wheel" ]; then
        WHEEL_NAME=$(basename "$wheel")
        echo -n "   • $WHEEL_NAME ... "
        
        if pip install "$wheel" -q 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
            ((INSTALLED++))
        else
            echo -e "${RED}✗${NC}"
            ((FAILED++))
        fi
    fi
done

echo ""
echo "설치 결과: $INSTALLED개 성공, $FAILED개 실패"

if [ $FAILED -gt 0 ]; then
    print_warning "일부 패키지 설치에 실패했습니다"
    print_info "다음 명령으로 상세 정보를 확인하세요:"
    echo "  pip install --no-index --find-links=$WHEELS_DIR -r requirements.txt"
fi

print_success "패키지 설치 완료"

echo ""

# 5. 설치 검증
print_header "5️⃣  설치 검증"

print_info "설치된 패키지 확인:"
echo ""

python3 << 'EOF'
import sys

packages = [
    'torch',
    'torchaudio',
    'transformers',
    'librosa',
    'fastapi',
    'pydantic',
]

failed = []
for pkg in packages:
    try:
        mod = __import__(pkg)
        version = getattr(mod, '__version__', 'unknown')
        print(f'   ✓ {pkg}: {version}')
    except ImportError:
        print(f'   ✗ {pkg}: 설치 실패')
        failed.append(pkg)

if failed:
    print(f'\n설치 실패한 패키지: {", ".join(failed)}')
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    print_error "패키지 설치 검증 실패"
    exit 1
fi

print_success "모든 패키지 설치 검증 완료"

echo ""

# 6. 완료 메시지
print_header "✨ 배포 완료!"

echo "가상환경 경로: $VENV_PATH"
echo ""
echo "다음 단계:"
echo ""
echo "  1. STT 엔진 소스코드를 /opt/stt_engine 등으로 복사:"
echo "     cp -r stt_engine /opt/"
echo ""
echo "  2. 가상환경 활성화:"
echo "     source $VENV_PATH/bin/activate"
echo ""
echo "  3. 모델 다운로드 (인터넷 접속 가능한 경우):"
echo "     cd /opt/stt_engine"
echo "     python3 download_model.py"
echo ""
echo "  4. STT 엔진 실행:"
echo "     python3 api_server.py"
echo ""
echo "  5. 다른 터미널에서 vLLM 실행:"
echo "     docker run --gpus all -p 8000:8000 vllm/vllm-openai:latest \\"
echo "       --model meta-llama/Llama-2-7b-hf --dtype float16"
echo ""

deactivate 2>/dev/null || true

echo ""
print_success "배포 준비 완료!"
