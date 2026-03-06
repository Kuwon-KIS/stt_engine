#!/bin/bash
# ============================================================================
# vLLM 엔드포인트 테스트 스크립트
# ============================================================================
# 
# 목적: privacy_remover와 element_detection이 vLLM을 제대로 호출하는지 확인
# 
# 사용법:
#   ./test_vllm_endpoints.sh [vllm_host] [vllm_port]
#
# 예시:
#   ./test_vllm_endpoints.sh localhost 8001
#   ./test_vllm_endpoints.sh 10.19.167.68 8001
#
# ============================================================================

# 기본값 설정
VLLM_HOST="${1:-localhost}"
VLLM_PORT="${2:-8001}"
VLLM_BASE_URL="http://${VLLM_HOST}:${VLLM_PORT}/v1"
MODEL_NAME="${3:-qwen30_thinking_2507}"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# 타이틀 출력
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          vLLM 엔드포인트 테스트 스크립트                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
log_info "vLLM 서버: ${VLLM_BASE_URL}"
log_info "모델: ${MODEL_NAME}"
echo ""

# ============================================================================
# 1. vLLM 서버 연결성 확인
# ============================================================================
echo "═ 1️⃣  vLLM 서버 연결성 확인"
echo "────────────────────────────────────────────────────────────────"

if timeout 5 curl -s "${VLLM_BASE_URL}/health" >/dev/null 2>&1; then
    log_success "vLLM 서버 연결 가능: ${VLLM_BASE_URL}"
else
    log_error "vLLM 서버 연결 실패: ${VLLM_BASE_URL}"
    log_warning "다음을 확인하세요:"
    log_warning "  1. vLLM 서버가 실행 중인가?"
    log_warning "  2. 올바른 호스트/포트를 지정했는가?"
    log_warning "  3. 네트워크 연결이 정상인가?"
    echo ""
    exit 1
fi

# ============================================================================
# 2. 모델 가용성 확인
# ============================================================================
echo ""
echo "═ 2️⃣  모델 가용성 확인: ${MODEL_NAME}"
echo "────────────────────────────────────────────────────────────────"

MODELS=$(curl -s "${VLLM_BASE_URL}/models" 2>/dev/null | jq -r '.data[].id' 2>/dev/null)

if echo "$MODELS" | grep -q "^${MODEL_NAME}$"; then
    log_success "모델 가용: ${MODEL_NAME}"
else
    log_warning "모델을 찾을 수 없음: ${MODEL_NAME}"
    log_info "사용 가능한 모델:"
    echo "$MODELS" | sed 's/^/  - /'
    echo ""
    exit 1
fi

# ============================================================================
# 3. vLLMClient 테스트 (/v1/chat/completions)
# ============================================================================
echo ""
echo "═ 3️⃣  vLLMClient 테스트 (Direct Chat Completions)"
echo "────────────────────────────────────────────────────────────────"
echo "엔드포인트: ${VLLM_BASE_URL}/chat/completions"
echo "클라이언트: vLLMClient (element_detection 사용)"
echo ""

VLLM_REQUEST='{
    "model": "'${MODEL_NAME}'",
    "messages": [
        {
            "role": "user",
            "content": "Say hello briefly"
        }
    ],
    "max_tokens": 100,
    "temperature": 0.3
}'

log_info "요청 전송..."
echo "───────────────────────────────────────"

VLLM_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$VLLM_REQUEST" \
    "${VLLM_BASE_URL}/chat/completions" 2>&1)

VLLM_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "$VLLM_REQUEST" \
    "${VLLM_BASE_URL}/chat/completions")

echo "HTTP 상태 코드: $VLLM_HTTP_CODE"
echo ""
echo "응답:"
echo "$VLLM_RESPONSE" | jq '.' 2>/dev/null || echo "$VLLM_RESPONSE"

if echo "$VLLM_RESPONSE" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
    log_success "vLLMClient 테스트 성공"
    RESPONSE_TEXT=$(echo "$VLLM_RESPONSE" | jq -r '.choices[0].message.content')
    echo "응답 내용: ${RESPONSE_TEXT:0:50}..."
else
    log_error "vLLMClient 테스트 실패"
    if echo "$VLLM_RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
        ERROR_MSG=$(echo "$VLLM_RESPONSE" | jq -r '.error.message')
        log_error "에러: $ERROR_MSG"
    fi
fi

# ============================================================================
# 4. QwenClient 테스트 (OpenAI SDK 호환 mode)
# ============================================================================
echo ""
echo "═ 4️⃣  QwenClient 테스트 (OpenAI SDK Compatibility)"
echo "────────────────────────────────────────────────────────────────"
echo "엔드포인트: ${VLLM_BASE_URL}/chat/completions"
echo "클라이언트: QwenClient (privacy_remover 사용)"
echo ""

QWEN_REQUEST='{
    "model": "'${MODEL_NAME}'",
    "messages": [
        {
            "role": "user",
            "content": "이 문장에서 개인정보를 찾으세요: 010-1234-5678에 전화하세요."
        }
    ],
    "max_tokens": 200,
    "temperature": 0.3
}'

log_info "요청 전송 (OpenAI SDK 스타일)..."
echo "───────────────────────────────────────"

QWEN_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$QWEN_REQUEST" \
    "${VLLM_BASE_URL}/chat/completions" 2>&1)

QWEN_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "$QWEN_REQUEST" \
    "${VLLM_BASE_URL}/chat/completions")

echo "HTTP 상태 코드: $QWEN_HTTP_CODE"
echo ""
echo "응답:"
echo "$QWEN_RESPONSE" | jq '.' 2>/dev/null || echo "$QWEN_RESPONSE"

if echo "$QWEN_RESPONSE" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
    log_success "QwenClient 테스트 성공"
    RESPONSE_TEXT=$(echo "$QWEN_RESPONSE" | jq -r '.choices[0].message.content')
    echo "응답 내용: ${RESPONSE_TEXT:0:50}..."
else
    log_error "QwenClient 테스트 실패"
    if echo "$QWEN_RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
        ERROR_MSG=$(echo "$QWEN_RESPONSE" | jq -r '.error.message')
        log_error "에러: $ERROR_MSG"
    fi
fi

# ============================================================================
# 5. Element Detection 시뮬레이션
# ============================================================================
echo ""
echo "═ 5️⃣  Element Detection 시뮬레이션"
echo "────────────────────────────────────────────────────────────────"
echo "목적: transcribe → element_detection → vLLM 호출 경로 테스트"
echo ""

ELEMENT_DETECTION_PROMPT="이 텍스트에서 감정을 분석하세요: 안녕하세요, 저는 행복합니다."

ELEMENT_REQUEST='{
    "model": "'${MODEL_NAME}'",
    "messages": [
        {
            "role": "user",
            "content": "'${ELEMENT_DETECTION_PROMPT}'"
        }
    ],
    "max_tokens": 150,
    "temperature": 0.3
}'

log_info "요청 전송..."
echo "───────────────────────────────────────"

ELEMENT_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$ELEMENT_REQUEST" \
    "${VLLM_BASE_URL}/chat/completions" 2>&1)

ELEMENT_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "$ELEMENT_REQUEST" \
    "${VLLM_BASE_URL}/chat/completions")

echo "HTTP 상태 코드: $ELEMENT_HTTP_CODE"
echo ""
echo "응답:"
echo "$ELEMENT_RESPONSE" | jq '.' 2>/dev/null || echo "$ELEMENT_RESPONSE"

if echo "$ELEMENT_RESPONSE" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
    log_success "Element Detection 테스트 성공"
else
    log_error "Element Detection 테스트 실패"
fi

# ============================================================================
# 6. Privacy Removal 시뮬레이션
# ============================================================================
echo ""
echo "═ 6️⃣  Privacy Removal 시뮬레이션"
echo "────────────────────────────────────────────────────────────────"
echo "목적: transcribe → privacy_remover → vLLM 호출 경로 테스트"
echo ""

PRIVACY_PROMPT='다음 텍스트를 분석하여 JSON으로 응답하세요:
{
  "text": "저의 전화번호는 010-1234-5678이고, 이메일은 user@example.com입니다."
}

응답 형식:
{
  "privacy_exist": "Y",
  "exist_reason": "전화번호, 이메일",
  "privacy_rm_usertxt": "저의 전화번호는 [전화번호]이고, 이메일은 [이메일]입니다."
}'

PRIVACY_REQUEST='{
    "model": "'${MODEL_NAME}'",
    "messages": [
        {
            "role": "user",
            "content": "'${PRIVACY_PROMPT}'"
        }
    ],
    "max_tokens": 300,
    "temperature": 0.3
}'

log_info "요청 전송..."
echo "───────────────────────────────────────"

PRIVACY_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$PRIVACY_REQUEST" \
    "${VLLM_BASE_URL}/chat/completions" 2>&1)

PRIVACY_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "$PRIVACY_REQUEST" \
    "${VLLM_BASE_URL}/chat/completions")

echo "HTTP 상태 코드: $PRIVACY_HTTP_CODE"
echo ""
echo "응답 (첫 300자):"
echo "$PRIVACY_RESPONSE" | jq '.' 2>/dev/null | head -20 || echo "$PRIVACY_RESPONSE" | head -c 300

if echo "$PRIVACY_RESPONSE" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
    log_success "Privacy Removal 테스트 성공"
else
    log_error "Privacy Removal 테스트 실패"
fi

# ============================================================================
# 7. 테스트 결과 요약
# ============================================================================
echo ""
echo "═ 📊 테스트 결과 요약"
echo "────────────────────────────────────────────────────────────────"
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

[ "$VLLM_HTTP_CODE" = "200" ] && ((SUCCESS_COUNT++)) || ((FAIL_COUNT++))
[ "$QWEN_HTTP_CODE" = "200" ] && ((SUCCESS_COUNT++)) || ((FAIL_COUNT++))
[ "$ELEMENT_HTTP_CODE" = "200" ] && ((SUCCESS_COUNT++)) || ((FAIL_COUNT++))
[ "$PRIVACY_HTTP_CODE" = "200" ] && ((SUCCESS_COUNT++)) || ((FAIL_COUNT++))

echo "성공: $SUCCESS_COUNT/4"
echo "실패: $FAIL_COUNT/4"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    log_success "모든 테스트 성공! vLLM 통합이 정상 작동합니다."
else
    log_warning "일부 테스트 실패. 위 로그를 확인하세요."
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
