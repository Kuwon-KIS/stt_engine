#!/bin/bash

###############################################################################
# STT Engine 서버 구동 스크립트
#
# STT Engine과 vLLM을 함께 시작하는 편의 스크립트
#
# 사용법:
#   chmod +x run_all.sh
#   ./run_all.sh [venv_path] [vllm_model]
#
# 예제:
#   ./run_all.sh /opt/stt_engine_venv meta-llama/Llama-2-7b-hf
#   ./run_all.sh                        # 기본값 사용
###############################################################################

set -e

VENV_PATH="${1:-${HOME}/.venv/stt_engine}"
VLLM_MODEL="${2:-meta-llama/Llama-2-7b-hf}"
STT_PORT="${3:-8001}"
VLLM_PORT="${4:-8000}"

echo "🚀 STT Engine 서비스 시작"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "설정:"
echo "  • STT Engine 포트: $STT_PORT"
echo "  • vLLM 포트: $VLLM_PORT"
echo "  • vLLM 모델: $VLLM_MODEL"
echo "  • 가상환경: $VENV_PATH"
echo ""

# 가상환경 확인
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ 가상환경을 찾을 수 없습니다: $VENV_PATH"
    exit 1
fi

# STT Engine 실행
echo "📡 STT Engine 시작 중..."
source "${VENV_PATH}/bin/activate"

# 백그라운드에서 STT Engine 시작
python3 api_server.py --port $STT_PORT &
STT_PID=$!

echo "✅ STT Engine 시작됨 (PID: $STT_PID)"
echo "   http://localhost:$STT_PORT"
echo ""

# vLLM 실행 (Docker 필요)
echo "📡 vLLM 서버 시작 권장..."
echo ""
echo "다른 터미널에서 다음을 실행하세요:"
echo ""
echo "  docker run --gpus all \\"
echo "    -p ${VLLM_PORT}:8000 \\"
echo "    --ipc=host \\"
echo "    vllm/vllm-openai:latest \\"
echo "    --model ${VLLM_MODEL} \\"
echo "    --dtype float16"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 테스트:"
echo "  curl http://localhost:$STT_PORT/health"
echo ""
echo "  python3 api_client.py --health"
echo "  python3 api_client.py --transcribe audio.wav"
echo ""

# CTRL+C 처리
trap "kill $STT_PID 2>/dev/null || true" EXIT

echo "✨ 서비스가 실행 중입니다. CTRL+C로 중지할 수 있습니다."
echo ""

# STT Engine이 실행 중일 때까지 대기
wait $STT_PID
