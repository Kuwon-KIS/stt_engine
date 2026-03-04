#!/bin/bash
# 백엔드 성능 문제 진단 및 개선 가이드

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_UI_ROOT="${SCRIPT_DIR}/../../web_ui"

echo "========================================================================"
echo "🔍 백엔드 성능 문제 진단 가이드"
echo "========================================================================"

echo ""
echo "📌 Docker 컨테이너에서 실행:"
echo "  docker exec stt-web-ui python /app/diagnose_backend_issues.py"
echo ""

echo "📌 로컬에서 실행:"
echo "  cd ${SCRIPT_DIR}"
echo "  python diagnose_backend_issues.py"
echo ""

echo "========================================================================"
echo "📊 진단 항목"
echo "========================================================================"

echo ""
echo "1️⃣  N+1 쿼리 문제"
echo "   문제: get_analysis_history()에서 각 직원마다 별도 COUNT 쿼리 실행"
echo "   영향: 직원 100명 → 101개 쿼리 (1 + 100)"
echo "   해결: GROUP BY를 사용해 단일 쿼리로 변경"
echo ""

echo "2️⃣  메모리 오버헤드"
echo "   문제: AnalysisResult.all()로 모든 결과를 메모리에 로드"
echo "   영향: 1000개 파일 = 1000개 객체 메모리 점유"
echo "   해결: LIMIT/OFFSET으로 페이지네이션 구현"
echo ""

echo "3️⃣  불필요한 데이터 전송"
echo "   문제: 클라이언트가 필요하지 않은 필드도 모두 반환"
echo "   영향: JSON 크기 증가, 네트워크 느림"
echo "   해결: 응답에서 필수 필드만 선택"
echo ""

echo "4️⃣  JSON 직렬화 오버헤드"
echo "   문제: model_dump() + JSON 인코딩 비용"
echo "   영향: 대량 데이터 직렬화 시 느림"
echo "   해결: 필드 선택으로 크기 최소화"
echo ""

echo "========================================================================"
echo "💡 권장 개선 순서"
echo "========================================================================"

echo ""
echo "🔴 즉시 개선 (가장 효과 큼):"
echo "   1. get_analysis_history() GROUP BY 최적화 → 99% 쿼리 감소"
echo "   2. API 응답에 pagination 추가 → 메모리/네트워크 개선"
echo "   3. 응답 필드 최적화 → JSON 크기 50% 감소"
echo ""

echo "🟡 단계 2:"
echo "   4. 데이터베이스 인덱싱 확인"
echo "   5. 캐싱 전략 수립 (프론트엔드)"
echo ""

echo "🟢 장기 과제:"
echo "   6. 가상 스크롤 구현 (프론트엔드)"
echo "   7. 비동기 로딩 최적화"
echo ""
