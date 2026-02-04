#!/bin/bash
# STT Engine 프로젝트 초기 설정 스크립트

set -e

echo "🚀 STT Engine 초기 설정을 시작합니다..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 1. 모델 다운로드
echo "1️⃣  모델 다운로드"
echo "   명령어: python download_model_simple.py"
echo ""
echo "   또는 다음을 직접 실행하세요:"
echo "   cd $PROJECT_DIR"
echo "   python download_model_simple.py"
echo ""
read -p "   지금 모델을 다운로드하시겠습니까? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "$PROJECT_DIR"
    python download_model_simple.py
    echo ""
fi

# 2. 모델 검증
echo "2️⃣  모델 검증"
if [ -f "$PROJECT_DIR/validate_model.py" ]; then
    echo "   명령어: python validate_model.py"
    read -p "   모델을 검증하시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$PROJECT_DIR"
        python validate_model.py
        echo ""
    fi
fi

# 3. 가상 환경 생성 (선택)
echo "3️⃣  Python 가상 환경 설정"
if [ ! -d "$PROJECT_DIR/venv" ]; then
    read -p "   가상 환경을 생성하시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$PROJECT_DIR"
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip setuptools wheel
        pip install -r requirements.txt
        echo "   ✓ 가상 환경 생성 완료"
        echo ""
    fi
else
    echo "   ℹ️  가상 환경이 이미 존재합니다"
fi

# 4. 환경 변수 설정
echo "4️⃣  환경 변수 파일 설정"
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "   ✓ .env 파일이 생성되었습니다"
    echo "   💡 필요시 편집: nano $PROJECT_DIR/.env"
else
    echo "   ℹ️  .env 파일이 이미 존재합니다"
fi
echo ""

# 5. 다음 단계 안내
echo "✨ 초기 설정이 완료되었습니다!"
echo ""
echo "📖 다음 단계:"
echo ""
echo "  🐳 Docker 이미지 빌드 (권장):"
echo "    bash $SCRIPT_DIR/build-engine-image.sh"
echo ""
echo "  📦 모델 압축 및 배포 (오프라인 서버용):"
if [ -d "$PROJECT_DIR/models/models--openai--whisper-large-v3-turbo" ]; then
    echo "    python compress_model.py"
else
    echo "    (먼저 모델을 다운로드하세요)"
fi
echo ""
echo "  🧪 로컬 테스트:"
echo "    python $PROJECT_DIR/stt_engine.py"
echo ""
echo "  🌐 API 서버 실행:"
echo "    python $PROJECT_DIR/api_server.py"
echo ""
