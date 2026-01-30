#!/bin/bash
# STT Engine 프로젝트 초기 설정 스크립트

echo "🚀 STT Engine 초기 설정을 시작합니다..."
echo ""

# 1. 가상 환경 생성
echo "1️⃣  가상 환경 생성 중..."
python3 -m venv venv

# 2. 가상 환경 활성화
echo "2️⃣  가상 환경 활성화 중..."
source venv/bin/activate

# 3. pip 업그레이드
echo "3️⃣  pip 업그레이드 중..."
pip install --upgrade pip setuptools wheel

# 4. 의존성 설치
echo "4️⃣  의존성 설치 중..."
pip install -r requirements.txt

# 5. 환경 변수 설정
echo "5️⃣  환경 변수 파일 설정 중..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "   .env 파일이 생성되었습니다. 필요시 수정해주세요."
fi

# 6. 모델 다운로드 확인
echo ""
echo "6️⃣  모델 다운로드"
echo "   다음 명령어로 Whisper 모델을 다운로드하세요:"
echo "   python download_model.py"
echo ""

echo "✨ 초기 설정이 완료되었습니다!"
echo ""
echo "📖 다음 단계:"
echo "  1. 환경 변수 설정: nano .env"
echo "  2. 모델 다운로드: python download_model.py"
echo "  3. 음성 파일 준비: audio/ 디렉토리에 음성 파일 추가"
echo "  4. STT 테스트: python stt_engine.py"
echo "  5. API 서버 실행: python api_server.py"
echo ""
