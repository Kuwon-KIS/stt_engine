#!/bin/bash
#
# EC2에서 STT Engine 모델을 준비하는 스크립트
# 
# 용도: 
#   - Python 3.11 환경 설정
#   - 모델 다운로드
#   - CTranslate2 변환
#   - 모델 검증
#
# 주의:
#   - model.bin은 상대 경로 심링크로 생성됨
#   - Docker (/app/models)와 운영 서버 (/data/models)에서 모두 작동
#
# 사용:
#   bash ec2_prepare_model.sh
#   bash ec2_prepare_model.sh --skip-test
#   bash ec2_prepare_model.sh --skip-compress
#

set -e

echo "=========================================="
echo "🚀 EC2 STT Engine 모델 준비"
echo "=========================================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Python 환경 확인
echo "1️⃣  Python 환경 확인..."
if command -v python3.11 &> /dev/null; then
    PYTHON_BIN="python3.11"
    echo -e "${GREEN}✅${NC} Python 3.11 found: $($PYTHON_BIN --version)"
elif command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
    PY_VERSION=$($PYTHON_BIN --version)
    if [[ ! "$PY_VERSION" =~ "3.11" ]]; then
        echo -e "${YELLOW}⚠️${NC}  Python 3.11이 아닙니다: $PY_VERSION"
        echo "   Python 3.11 설치를 권장합니다"
    else
        echo -e "${GREEN}✅${NC} $PY_VERSION"
    fi
else
    echo -e "${RED}❌${NC} Python을 찾을 수 없습니다"
    exit 1
fi

# 2. 필수 패키지 확인
echo ""
echo "2️⃣  필수 패키지 확인..."

for pkg in huggingface-hub faster-whisper ctranslate2 transformers; do
    if $PYTHON_BIN -c "import ${pkg//-/_}" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} $pkg"
    else
        echo -e "${YELLOW}⚠️${NC}  $pkg 설치 필요"
        echo "   설치: pip install $pkg"
    fi
done

# 3. 작업 디렉토리 확인
echo ""
echo "3️⃣  작업 디렉토리 확인..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "   📁 작업 경로: $SCRIPT_DIR"

# 4. 모델 다운로드 및 변환
echo ""
echo "4️⃣  모델 다운로드 및 변환..."
echo ""

# 옵션 파싱
PYTHON_OPTS=""
if [[ "$*" == *"--skip-test"* ]]; then
    PYTHON_OPTS="$PYTHON_OPTS --skip-test"
    echo "   ⏭️  테스트 스킵 옵션 활성화"
fi
if [[ "$*" == *"--skip-compress"* ]]; then
    PYTHON_OPTS="$PYTHON_OPTS --skip-compress"
    echo "   ⏭️  압축 스킵 옵션 활성화"
fi
if [[ "$*" == *"--no-convert"* ]]; then
    PYTHON_OPTS="$PYTHON_OPTS --no-convert"
    echo "   ⏭️  변환 스킵 옵션 활성화"
fi

echo ""
echo "실행: $PYTHON_BIN download_model_hf.py $PYTHON_OPTS"
echo ""

cd "$SCRIPT_DIR"
$PYTHON_BIN download_model_hf.py $PYTHON_OPTS

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "✅ 모델 준비 완료!"
    echo "==========================================${NC}"
    echo ""
    echo "다음 단계:"
    echo "  1. 모델 위치 확인:"
    echo "     ls -lh models/openai_whisper-large-v3-turbo/"
    echo ""
    echo "  2. Docker에서 실행:"
    echo "     docker build -t stt-engine:latest -f docker/Dockerfile ."
    echo "     docker run -p 8003:8003 -v \$(pwd)/models:/app/models stt-engine:latest"
    echo ""
    echo "  3. API 테스트:"
    echo "     curl -X POST http://localhost:8003/transcribe -F 'file=@audio/samples/short_0.5s.wav'"
    echo ""
else
    echo ""
    echo -e "${RED}=========================================="
    echo "❌ 모델 준비 실패!"
    echo "==========================================${NC}"
    echo ""
    echo "오류 진단:"
    echo "  1. 패키지 업그레이드:"
    echo "     pip install --upgrade huggingface-hub faster-whisper ctranslate2"
    echo ""
    echo "  2. model.bin 파일 확인:"
    echo "     find . -name 'model.bin' -type f"
    echo "     find . -name 'model.bin' -type l"
    echo ""
    echo "  3. ctranslate2 변환 수동 실행:"
    echo "     ct2-transformers-converter --model openai/whisper-large-v3-turbo \\"
    echo "       --output_dir models/openai_whisper-large-v3-turbo/ctranslate2_model --force"
    echo ""
    exit 1
fi
