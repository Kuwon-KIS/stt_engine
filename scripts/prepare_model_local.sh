#!/bin/bash
#
# 로컬 개발 환경용 STT 모델 준비 스크립트
#
# 용도:
#   - HuggingFace에서 모델 다운로드
#   - CTranslate2 변환
#   - 로컬 Docker에 마운트할 모델 준비
#
# 특징 (EC2 스크립트와의 차이점):
#   - 압축 스킵 (로컬 테스트용이므로 압축 불필요)
#   - CPU 최적화
#   - 빠른 준비 (5-15분)
#
# 사용:
#   bash scripts/prepare_model_local.sh
#   bash scripts/prepare_model_local.sh --skip-ctranslate
#   bash scripts/prepare_model_local.sh --no-validate
#

set -e

echo "=========================================="
echo "🚀 로컬 개발용 STT 모델 준비"
echo "=========================================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# 1. 환경 설정
# ============================================================================

echo "1️⃣  환경 설정..."

# Python 확인
if command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
    PY_VERSION=$($PYTHON_BIN --version 2>&1)
    echo -e "${GREEN}✅${NC} Python 찾음: $PY_VERSION"
else
    echo -e "${RED}❌${NC} Python을 찾을 수 없습니다"
    exit 1
fi

# 작업 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(dirname "$SCRIPT_DIR")"
echo "   📁 프로젝트 경로: $WORKSPACE"

# 옵션 파싱
SKIP_CTRANSLATE=false
NO_VALIDATE=false

if [[ "$*" == *"--skip-ctranslate"* ]]; then
    SKIP_CTRANSLATE=true
    echo -e "${YELLOW}⚠️${NC}  CTranslate2 변환 스킵"
fi

if [[ "$*" == *"--no-validate"* ]]; then
    NO_VALIDATE=true
    echo -e "${YELLOW}⚠️${NC}  모델 검증 스킵"
fi

# ============================================================================
# 2. 필수 패키지 확인
# ============================================================================

echo ""
echo "2️⃣  필수 패키지 확인..."

# 필수 패키지 리스트
REQUIRED_PACKAGES=("huggingface-hub" "faster-whisper" "ctranslate2" "transformers")
MISSING_PACKAGES=()

for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if $PYTHON_BIN -c "import ${pkg//-/_}" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} $pkg"
    else
        echo -e "${YELLOW}⚠️${NC}  $pkg 미설치"
        MISSING_PACKAGES+=("$pkg")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}설치 권장:${NC}"
    echo "  pip install ${MISSING_PACKAGES[*]}"
    echo ""
    read -p "계속하시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ============================================================================
# 3. 모델 디렉토리 준비
# ============================================================================

echo ""
echo "3️⃣  모델 디렉토리 준비..."

# Docker에 바인드 마운트될 경로
MODELS_DIR="$WORKSPACE/models"
MODEL_NAME="openai_whisper-large-v3-turbo"
MODEL_PATH="$MODELS_DIR/$MODEL_NAME"

mkdir -p "$MODELS_DIR"
echo "   📁 모델 경로: $MODELS_DIR"

# 기존 모델 확인
if [ -d "$MODEL_PATH" ]; then
    echo -e "${BLUE}ℹ️${NC}  모델이 이미 존재합니다: $MODEL_PATH"
    echo ""
    read -p "기존 모델을 사용하시겠습니까? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}✅${NC} 기존 모델 사용"
        SKIP_CTRANSLATE=true
    else
        echo -e "${YELLOW}⚠️${NC}  기존 모델 삭제 후 새로 준비합니다..."
        rm -rf "$MODEL_PATH"
        mkdir -p "$MODEL_PATH"
    fi
else
    mkdir -p "$MODEL_PATH"
fi

# ============================================================================
# 4. HuggingFace 모델 다운로드
# ============================================================================

echo ""
echo "4️⃣  HuggingFace 모델 다운로드..."
echo "   모델: openai/whisper-large-v3-turbo"
echo "   크기: ~3GB (처음 한 번만, 이후 캐시 사용)"
echo ""

cd "$WORKSPACE"

# download_model_hf.py 실행
if [ -f "download_model_hf.py" ]; then
    echo "실행: $PYTHON_BIN download_model_hf.py --no-compress"
    echo ""
    
    if $PYTHON_BIN download_model_hf.py --no-compress; then
        echo ""
        echo -e "${GREEN}✅${NC} 모델 다운로드 완료"
    else
        echo ""
        echo -e "${RED}❌${NC} 모델 다운로드 실패"
        exit 1
    fi
else
    echo -e "${RED}❌${NC} download_model_hf.py를 찾을 수 없습니다"
    exit 1
fi

# ============================================================================
# 5. 모델 검증 (선택사항)
# ============================================================================

if [ "$NO_VALIDATE" = false ]; then
    echo ""
    echo "5️⃣  모델 검증..."
    
    # CTranslate2 모델 확인
    CT_MODEL_DIR="$MODEL_PATH/ctranslate2_model"
    if [ -d "$CT_MODEL_DIR" ]; then
        echo -e "${GREEN}✅${NC} CTranslate2 모델 발견"
        
        # 주요 파일 확인
        required_files=("model.bin" "config.json")
        for file in "${required_files[@]}"; do
            if [ -f "$CT_MODEL_DIR/$file" ]; then
                SIZE=$(du -h "$CT_MODEL_DIR/$file" | cut -f1)
                echo -e "  ${GREEN}✅${NC} $file ($SIZE)"
            else
                echo -e "  ${YELLOW}⚠️${NC}  $file 미발견"
            fi
        done
    else
        echo -e "${YELLOW}⚠️${NC}  CTranslate2 모델 미발견: $CT_MODEL_DIR"
    fi
else
    echo ""
    echo "5️⃣  모델 검증 스킵"
fi

# ============================================================================
# 6. 완료
# ============================================================================

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ 로컬 모델 준비 완료!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

echo "다음 단계:"
echo ""
echo "📝 1. 모델 위치 확인:"
echo "   ls -lh $MODEL_PATH/"
echo ""

echo "🐳 2. Docker Compose로 서비스 시작:"
echo "   docker-compose -f docker/docker-compose.dev.yml up -d"
echo ""

echo "🔍 3. 서비스 상태 확인:"
echo "   docker-compose -f docker/docker-compose.dev.yml ps"
echo ""

echo "📊 4. 헬스 체크:"
echo "   curl http://localhost:8003/health | jq"
echo "   curl http://localhost:8100/health | jq"
echo ""

echo "🎙️  5. STT 테스트:"
echo "   curl -X POST http://localhost:8003/transcribe \\"
echo "     -F 'file_path=/app/audio/samples/test_ko_1min.wav'"
echo ""

echo "💻 6. Web UI 접속:"
echo "   open http://localhost:8100"
echo ""

echo "📋 7. 로그 확인:"
echo "   docker-compose -f docker/docker-compose.dev.yml logs -f stt-api"
echo ""

echo "🛑 8. 서비스 중지:"
echo "   docker-compose -f docker/docker-compose.dev.yml down"
echo ""

# ============================================================================
# 진단 정보
# ============================================================================

echo -e "${BLUE}═══ 진단 정보 ═══${NC}"
echo "Python: $($PYTHON_BIN --version)"
echo "모델 위치: $MODEL_PATH"
echo "모델 크기: $(du -sh "$MODEL_PATH" 2>/dev/null | cut -f1 || echo '계산 중...')"
echo "사용 가능한 저장공간: $(df -h "$MODELS_DIR" | tail -1 | awk '{print $4}')"
echo ""
