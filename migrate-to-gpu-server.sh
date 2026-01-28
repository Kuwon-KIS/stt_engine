#!/bin/bash
# 🚀 STT Engine을 GPU 서버로 빠르게 이관하는 스크립트

echo "📋 STT Engine GPU 서버 이관 스크립트"
echo "=================================================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 단계 1: 환경 확인
echo -e "${YELLOW}📊 Step 1: 로컬 환경 확인 중...${NC}"
MODEL_PATH="./models/openai_whisper-large-v3-turbo/model.safetensors"

if [ -f "$MODEL_PATH" ]; then
    SIZE=$(du -h "$MODEL_PATH" | cut -f1)
    echo -e "${GREEN}✅ 모델 파일 발견: $SIZE${NC}"
else
    echo -e "${RED}❌ 모델 파일을 찾을 수 없습니다.${NC}"
    echo "   다음 명령어로 모델을 다운로드하세요:"
    echo "   python download_model.py"
    exit 1
fi

# 단계 2: 서버 정보 입력
echo ""
echo -e "${YELLOW}🖥️  Step 2: 대상 서버 정보 입력${NC}"

read -p "서버 주소 (예: user@192.168.1.100): " SERVER_ADDR
read -p "서버 경로 (기본값: /opt/stt_engine): " SERVER_PATH
SERVER_PATH=${SERVER_PATH:-/opt/stt_engine}

# 단계 3: 연결 확인
echo ""
echo -e "${YELLOW}🔗 Step 3: 서버 연결 확인 중...${NC}"

if ssh -o ConnectTimeout=5 "$SERVER_ADDR" "ls $SERVER_PATH" &>/dev/null; then
    echo -e "${GREEN}✅ 서버 연결 성공${NC}"
else
    echo -e "${YELLOW}⚠️  경로가 없거나 권한이 없습니다.${NC}"
    echo "   서버에서 다음 명령어로 디렉토리 생성:"
    echo "   mkdir -p $SERVER_PATH/models"
    echo "   mkdir -p $SERVER_PATH/audio"
fi

# 단계 4: 모델 폴더 복사
echo ""
echo -e "${YELLOW}📤 Step 4: 모델 폴더 복사 중...${NC}"
echo "이 과정은 수 분이 걸릴 수 있습니다..."
echo ""

scp -r ./models/openai_whisper-large-v3-turbo "$SERVER_ADDR:$SERVER_PATH/models/"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 모델 전송 완료${NC}"
else
    echo -e "${RED}❌ 모델 전송 실패${NC}"
    exit 1
fi

# 단계 5: 프로젝트 코드 확인
echo ""
echo -e "${YELLOW}📝 Step 5: 서버에 프로젝트 코드 배포${NC}"
echo "다음 옵션 중 선택하세요:"
echo "1) Git에서 클론 (권장)"
echo "2) 현재 폴더의 코드 전송"
read -p "선택 (1 또는 2): " CHOICE

if [ "$CHOICE" = "1" ]; then
    echo ""
    echo -e "${YELLOW}Git 클론 중...${NC}"
    ssh "$SERVER_ADDR" "cd $SERVER_PATH && git clone https://github.com/Kuwon-KIS/stt_engine.git . || git pull"
    echo -e "${GREEN}✅ Git 클론 완료${NC}"
else
    echo ""
    echo -e "${YELLOW}코드 전송 중...${NC}"
    # .git와 models 폴더 제외하고 전송
    rsync -av --exclude='.git' --exclude='models' --exclude='audio' --exclude='logs' \
        ./ "$SERVER_ADDR:$SERVER_PATH/"
    echo -e "${GREEN}✅ 코드 전송 완료${NC}"
fi

# 단계 6: docker-compose.yml 설정
echo ""
echo -e "${YELLOW}⚙️  Step 6: Docker Compose 설정 확인${NC}"
echo ""
echo "서버에서 다음 설정을 확인하세요:"
echo "  1. docker-compose.yml에서 WHISPER_DEVICE=cuda로 설정"
echo "  2. GPU 설정을 활성화하려면 deploy 섹션의 주석 해제"
echo ""
read -p "서버에서 설정을 완료했나요? (y/n): " READY

if [ "$READY" != "y" ]; then
    echo "설정을 먼저 완료한 후 다시 실행하세요."
    exit 1
fi

# 단계 7: Docker Compose 시작
echo ""
echo -e "${YELLOW}🐳 Step 7: Docker Compose 시작 중...${NC}"
ssh "$SERVER_ADDR" "cd $SERVER_PATH && docker-compose down && docker-compose up -d"

# 단계 8: 상태 확인
echo ""
echo -e "${YELLOW}✔️  Step 8: 서버 상태 확인${NC}"
sleep 5
echo ""

echo "STT 엔진 헬스 체크:"
curl -s http://$SERVER_ADDR:8001/health || echo "아직 시작 중입니다..."

echo ""
echo ""
echo -e "${GREEN}=================================================="
echo "🎉 이관 완료!"
echo "=================================================="
echo ""
echo "다음 API 주소를 사용하세요:"
echo "  STT 엔진: http://$SERVER_ADDR:8001"
echo "  vLLM 서버: http://$SERVER_ADDR:8000"
echo ""
echo "테스트:"
echo "  curl http://$SERVER_ADDR:8001/health"
echo "  curl -X POST -F \"file=@audio.wav\" http://$SERVER_ADDR:8001/transcribe"
echo ""
echo "로그 확인:"
echo "  ssh $SERVER_ADDR"
echo "  cd $SERVER_PATH"
echo "  docker-compose logs -f"
echo ""
