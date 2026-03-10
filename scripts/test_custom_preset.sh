#!/bin/bash

# Custom Preset 비교 테스트 스크립트
# 각 preset별로 성능, 메모리, hallucination을 비교합니다

set -e

API_URL="${API_URL:-http://localhost:8003}"
TEST_AUDIO="${1:-/app/audio/samples/test_ko_1min.wav}"  # 30초 오디오
LONG_AUDIO="${2:-/app/audio/samples/long_20min.wav}"    # 20분 오디오 (선택사항)

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Custom Preset 성능 비교 테스트                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 테스트할 preset 목록
declare -A PRESETS=(
    ["accuracy"]="Transformer + float32 (높은 정확도)"
    ["balanced"]="FasterWhisper + float16 (균형)"
    ["speed"]="FasterWhisper + int8 (빠른 속도)"
    ["custom"]="사용자 정의 (기본값)"
)

# ============================================================================
# Phase 1: 각 Preset 테스트 (30초 오디오)
# ============================================================================

echo -e "${YELLOW}📊 Phase 1: 기본 테스트 (30초 오디오)${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 결과 저장 배열
declare -A results_time
declare -A results_text_length

for preset in accuracy balanced speed custom; do
    echo -e "${BLUE}🔄 Preset: ${preset} - ${PRESETS[$preset]}${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 1. Backend 재로드
    echo "  [1/3] Backend 로드 중..."
    RELOAD_RESPONSE=$(curl -s -X POST "$API_URL/backend/reload" \
        -H "Content-Type: application/json" \
        -d "{\"preset\": \"$preset\"}")
    
    if echo "$RELOAD_RESPONSE" | grep -q "error"; then
        echo -e "    ${RED}❌ Backend 로드 실패${NC}"
        echo "    응답: $RELOAD_RESPONSE"
        continue
    fi
    
    CURRENT_BACKEND=$(echo "$RELOAD_RESPONSE" | grep -o '"current_backend":"[^"]*"' | cut -d'"' -f4)
    echo "    ✅ Backend 로드 완료: $CURRENT_BACKEND"
    
    # 2. 1초 대기 (Backend 안정화)
    sleep 1
    
    # 3. STT 처리
    echo "  [2/3] STT 처리 중..."
    START_TIME=$(date +%s%N)
    
    TRANSCRIBE_RESPONSE=$(curl -s -X POST "$API_URL/transcribe" \
        -F "file_path=$TEST_AUDIO" \
        -F "language=ko")
    
    END_TIME=$(date +%s%N)
    ELAPSED_TIME=$(echo "scale=2; ($END_TIME - $START_TIME) / 1000000000" | bc)
    
    # 응답 파싱
    if echo "$TRANSCRIBE_RESPONSE" | grep -q '"success":true'; then
        echo -e "    ${GREEN}✅ STT 처리 성공${NC}"
        
        # 결과 추출
        TEXT_LENGTH=$(echo "$TRANSCRIBE_RESPONSE" | grep -o '"text":"[^"]*"' | wc -c)
        PROCESSING_TIME=$(echo "$TRANSCRIBE_RESPONSE" | grep -o '"processing_time_seconds":[0-9.]*' | cut -d':' -f2)
        BACKEND=$(echo "$TRANSCRIBE_RESPONSE" | grep -o '"backend":"[^"]*"' | cut -d'"' -f4)
        MEMORY_USED=$(echo "$TRANSCRIBE_RESPONSE" | grep -o '"used_percent":[0-9.]*' | cut -d':' -f2 | head -1)
        
        results_time["$preset"]=$ELAPSED_TIME
        results_text_length["$preset"]=$TEXT_LENGTH
        
        echo "    📊 결과:"
        echo "      - 전체 시간(API): ${ELAPSED_TIME}초"
        echo "      - 처리 시간(STT): ${PROCESSING_TIME}초"
        echo "      - 실제 백엔드: $BACKEND"
        echo "      - 메모리 사용률: ${MEMORY_USED}%"
        echo "      - 출력 길이: ${TEXT_LENGTH} 바이트"
    else
        echo -e "    ${RED}❌ STT 처리 실패${NC}"
        ERROR=$(echo "$TRANSCRIBE_RESPONSE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
        echo "    오류: $ERROR"
    fi
    
    echo ""
done

echo ""
echo -e "${YELLOW}📈 Phase 1 결과 요약${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 정렬된 결과 출력
echo "처리 시간 비교 (낮을수록 좋음):"
for preset in $(for p in "${!results_time[@]}"; do echo "$p ${results_time[$p]}"; done | sort -k2 -n | cut -d' ' -f1); do
    if [ ! -z "${results_time[$preset]}" ]; then
        printf "  %-10s: %8.2f초\n" "$preset" "${results_time[$preset]}"
    fi
done

echo ""

# ============================================================================
# Phase 2: 장시간 오디오 테스트 (선택사항)
# ============================================================================

if [ -f "$LONG_AUDIO" ]; then
    echo -e "${YELLOW}📊 Phase 2: 장시간 오디오 테스트 (20분+)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "파일: $LONG_AUDIO"
    echo ""
    
    # Hallucination 테스트: custom_hallu_free 사용
    echo -e "${BLUE}🔍 Custom Hallu-Free 테스트 (Hallucination 검사)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  [1/2] Backend 로드 중..."
    
    RELOAD_RESPONSE=$(curl -s -X POST "$API_URL/backend/reload" \
        -H "Content-Type: application/json" \
        -d '{
            "preset": "custom",
            "backend": "transformers",
            "compute_type": "float32",
            "chunk_duration": 10,
            "overlap_duration": 1
        }')
    
    echo "    ✅ Backend 로드 완료"
    sleep 1
    
    echo "  [2/2] STT 처리 중 (시간 소요 예상: 3-5분)..."
    echo "    ⏳ 진행 중..."
    
    START_TIME=$(date +%s%N)
    LONG_RESPONSE=$(curl -s -X POST "$API_URL/transcribe" \
        -F "file_path=$LONG_AUDIO" \
        -F "language=ko")
    END_TIME=$(date +%s%N)
    
    if echo "$LONG_RESPONSE" | grep -q '"success":true'; then
        ELAPSED_TIME=$(echo "scale=2; ($END_TIME - $START_TIME) / 1000000000" | bc)
        TEXT=$(echo "$LONG_RESPONSE" | grep -o '"text":"[^"]*"' | cut -d'"' -f4)
        DURATION=$(echo "$LONG_RESPONSE" | grep -o '"duration":[0-9.]*' | cut -d':' -f2)
        
        echo ""
        echo -e "    ${GREEN}✅ 처리 완료${NC}"
        echo "    📊 결과:"
        echo "      - 전체 시간: ${ELAPSED_TIME}초"
        echo "      - 오디오 길이: ${DURATION}초"
        
        # Hallucination 검사 (반복 음절 탐지)
        REPEAT_COUNT=$(echo "$TEXT" | grep -o "예 예" | wc -l)
        if [ $REPEAT_COUNT -gt 5 ]; then
            echo -e "      - Hallucination 감지: ${RED}⚠️  높음 ($REPEAT_COUNT회)${NC}"
        elif [ $REPEAT_COUNT -gt 0 ]; then
            echo -e "      - Hallucination 감지: ${YELLOW}⚠️  낮음 ($REPEAT_COUNT회)${NC}"
        else
            echo -e "      - Hallucination 감지: ${GREEN}없음${NC}"
        fi
        
        # 마지막 500자 출력 (hallucination 시작 구간 확인)
        echo ""
        echo "    📝 텍스트 마지막 500자 (Hallucination 확인 구간):"
        echo "$TEXT" | tail -c 500 | sed 's/^/      /'
    else
        echo -e "    ${RED}❌ 처리 실패${NC}"
        ERROR=$(echo "$LONG_RESPONSE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
        echo "    오류: $ERROR"
    fi
else
    echo -e "${YELLOW}⏭️  Phase 2 건너뜀${NC}"
    echo "    (20분 오디오 파일을 제공하지 않았습니다)"
    echo "    사용법: $0 <30초오디오> <20분오디오>"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================================================
# 권장사항 출력
# ============================================================================

echo -e "${BLUE}💡 권장사항${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "상황별 최적 설정:"
echo ""
echo "1️⃣  Hallucination 완전 제거 필요 (정확도 중심)"
echo "   → custom preset 사용:"
echo "      backend: transformers"
echo "      compute_type: float32"
echo "      chunk_duration: 10"
echo "      overlap_duration: 1"
echo ""
echo "2️⃣  속도와 정확도 균형 (일반 콜센터)"
echo "   → custom preset 사용:"
echo "      backend: faster-whisper"
echo "      compute_type: float16"
echo "      chunk_duration: 20"
echo "      overlap_duration: 2"
echo ""
echo "3️⃣  매우 긴 음성 (20분+, hallucination 없어야 함)"
echo "   → custom preset 사용:"
echo "      backend: transformers"
echo "      compute_type: float32"
echo "      chunk_duration: 8"
echo "      overlap_duration: 1"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✅ 테스트 완료${NC}"
