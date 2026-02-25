#!/bin/bash

# Phase 1 텍스트 입력 기반 처리 테스트 스크립트

API_URL="http://localhost:8003"
OUTPUT_DIR="/tmp/stt_test_results"

# 결과 디렉토리 생성
mkdir -p "$OUTPUT_DIR"

echo "======================================================================"
echo "Phase 1: 텍스트 입력 기반 처리 테스트"
echo "======================================================================"
echo ""

# ============================================================================
# Test 1: 텍스트 입력만 (STT 스킵, 후처리 없음)
# ============================================================================
echo "Test 1: 텍스트 입력 (STT 스킵, 후처리 없음)"
echo "─────────────────────────────────────────────────"

TEST1_TEXT="고객님, 저희 상품 정말 좋습니다. 지금 가입하면 할인이 있습니다."

curl -X POST "$API_URL/transcribe" \
  -F "stt_text=$TEST1_TEXT" \
  -H "Content-Type: multipart/form-data" \
  -s -o "$OUTPUT_DIR/test1_response.json"

echo "응답:"
cat "$OUTPUT_DIR/test1_response.json" | python3 -m json.tool
echo ""
echo ""

# ============================================================================
# Test 2: 텍스트 입력 + Privacy Removal
# ============================================================================
echo "Test 2: 텍스트 입력 + Privacy Removal (개인정보 제거)"
echo "─────────────────────────────────────────────────"

TEST2_TEXT="김철수님 (010-1234-5678, 서울시 강남구 거주) 저희 상품 가입하세요."

curl -X POST "$API_URL/transcribe" \
  -F "stt_text=$TEST2_TEXT" \
  -F "privacy_removal=true" \
  -H "Content-Type: multipart/form-data" \
  -s -o "$OUTPUT_DIR/test2_response.json"

echo "응답:"
cat "$OUTPUT_DIR/test2_response.json" | python3 -m json.tool
echo ""
echo ""

# ============================================================================
# Test 3: 텍스트 입력 + Privacy Removal + Classification
# ============================================================================
echo "Test 3: 텍스트 입력 + Privacy Removal + Classification"
echo "─────────────────────────────────────────────────"

TEST3_TEXT="저희 상품은 부당한 방법으로 판매되고 있습니다."

curl -X POST "$API_URL/transcribe" \
  -F "stt_text=$TEST3_TEXT" \
  -F "privacy_removal=true" \
  -F "classification=true" \
  -H "Content-Type: multipart/form-data" \
  -s -o "$OUTPUT_DIR/test3_response.json"

echo "응답:"
cat "$OUTPUT_DIR/test3_response.json" | python3 -m json.tool
echo ""
echo ""

# ============================================================================
# Test 4: 텍스트 입력 + 모든 처리 (Privacy + Classification + AI Agent)
# ============================================================================
echo "Test 4: 텍스트 입력 + Privacy Removal + Classification + AI Agent"
echo "─────────────────────────────────────────────────"

TEST4_TEXT="제품 가격을 말씀하지 않고 판매를 강요했습니다."

curl -X POST "$API_URL/transcribe" \
  -F "stt_text=$TEST4_TEXT" \
  -F "privacy_removal=true" \
  -F "classification=true" \
  -F "ai_agent=true" \
  -F "ai_agent_type=external" \
  -H "Content-Type: multipart/form-data" \
  -s -o "$OUTPUT_DIR/test4_response.json"

echo "응답:"
cat "$OUTPUT_DIR/test4_response.json" | python3 -m json.tool
echo ""
echo ""

# ============================================================================
# Test 5: 기존 방식 호환성 테스트 (음성 파일 - 있으면)
# ============================================================================
echo "Test 5: 기존 방식 호환성 테스트 (음성 파일 기반)"
echo "─────────────────────────────────────────────────"

# 테스트 오디오 파일 경로
TEST_AUDIO_FILE="/app/audio/samples/test.wav"

if [ -f "$TEST_AUDIO_FILE" ]; then
  echo "오디오 파일 발견: $TEST_AUDIO_FILE"
  
  curl -X POST "$API_URL/transcribe" \
    -F "file_path=$TEST_AUDIO_FILE" \
    -F "privacy_removal=false" \
    -H "Content-Type: multipart/form-data" \
    -s -o "$OUTPUT_DIR/test5_response.json"
  
  echo "응답:"
  cat "$OUTPUT_DIR/test5_response.json" | python3 -m json.tool
else
  echo "⚠️  오디오 파일을 찾을 수 없습니다: $TEST_AUDIO_FILE"
  echo "   (이 테스트는 선택사항입니다)"
fi
echo ""
echo ""

# ============================================================================
# Test 6: 에러 테스트 - 입력 없음
# ============================================================================
echo "Test 6: 에러 테스트 - 입력 없음 (예상: 400 에러)"
echo "─────────────────────────────────────────────────"

curl -X POST "$API_URL/transcribe" \
  -H "Content-Type: multipart/form-data" \
  -s -o "$OUTPUT_DIR/test6_response.json"

echo "응답:"
cat "$OUTPUT_DIR/test6_response.json" | python3 -m json.tool
echo ""
echo ""

# ============================================================================
# Test 7: 에러 테스트 - 입력 둘 다
# ============================================================================
echo "Test 7: 에러 테스트 - 입력 둘 다 제공 (예상: 400 에러)"
echo "─────────────────────────────────────────────────"

curl -X POST "$API_URL/transcribe" \
  -F "file_path=/app/audio/samples/test.wav" \
  -F "stt_text=test text" \
  -H "Content-Type: multipart/form-data" \
  -s -o "$OUTPUT_DIR/test7_response.json"

echo "응답:"
cat "$OUTPUT_DIR/test7_response.json" | python3 -m json.tool
echo ""
echo ""

# ============================================================================
# 결과 요약
# ============================================================================
echo "======================================================================"
echo "테스트 완료!"
echo "======================================================================"
echo "결과 파일 위치: $OUTPUT_DIR"
echo ""
echo "결과 파일 목록:"
ls -lh "$OUTPUT_DIR"
echo ""
echo "주의: 실제 결과는 LLM 호출 상태에 따라 다를 수 있습니다."
echo "═════════════════════════════════════════════════════════════════════"
