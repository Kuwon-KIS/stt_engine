#!/bin/bash

cd /Users/a113211/workspace/stt_engine

echo "📁 프로젝트 구조 리팩토링 시작..."

# 모델 변환 스크립트 이동
echo "🔄 변환 스크립트 이동..."
mv -v convert_final.py scripts/models/convert/ 2>/dev/null
mv -v convert_model_ctranslate2.py scripts/models/convert/ 2>/dev/null
mv -v convert_model_direct.py scripts/models/convert/ 2>/dev/null
mv -v simple_model_convert.py scripts/models/convert/ 2>/dev/null
mv -v setup_and_convert.py scripts/models/convert/ 2>/dev/null

# 모델 검증 스크립트 이동
echo "✅ 검증 스크립트 이동..."
mv -v validate_model.py scripts/models/validate/ 2>/dev/null
mv -v validate_model_detailed.py scripts/models/validate/ 2>/dev/null
mv -v test_model.py scripts/models/validate/ 2>/dev/null
mv -v test_model_transformers.py scripts/models/validate/ 2>/dev/null
mv -v check_model_structure.py scripts/models/validate/ 2>/dev/null

# 분석 스크립트 이동
echo "🔍 분석 스크립트 이동..."
mv -v analyze_model_compatibility.py scripts/analysis/ 2>/dev/null
mv -v docker_model_fix_analysis.py scripts/analysis/ 2>/dev/null
mv -v compress_model.py scripts/analysis/ 2>/dev/null

# download_model_hf.py는 root에 유지

echo "✨ 리팩토링 완료!"
echo ""
echo "📊 최종 구조:"
echo "Root (서비스 파일만 유지):"
ls -1 *.py | grep -E "^(main|stt_engine|api_server|api_client|model_manager|download_model_hf)" || echo "  (파일 없음)"
echo ""
echo "scripts/models/convert/:"
ls -1 scripts/models/convert/*.py 2>/dev/null || echo "  (파일 없음)"
echo ""
echo "scripts/models/validate/:"
ls -1 scripts/models/validate/*.py 2>/dev/null || echo "  (파일 없음)"
echo ""
echo "scripts/analysis/:"
ls -1 scripts/analysis/*.py 2>/dev/null || echo "  (파일 없음)"
