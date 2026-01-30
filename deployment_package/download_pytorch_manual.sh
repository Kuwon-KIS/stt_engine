#!/bin/bash

# STT Engine - PyTorch wheels 다운로드 매뉴얼
# PyTorch 공식 index에서 직접 다운로드해야 합니다

WHEELS_DIR="./wheels"

echo "🔧 PyTorch CUDA 12.1 wheels 수동 설치 가이드"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "현재 상황:"
echo "  ✅ 기타 패키지: $(ls -1 $WHEELS_DIR/*.whl 2>/dev/null | wc -l)개 다운로드 완료"
echo "  ⏳ PyTorch: 별도 다운로드 필요"
echo ""

echo "📥 PyTorch CUDA 12.1 다운로드 방법:"
echo ""
echo "옵션 1: 웹 브라우저에서 직접 다운로드"
echo "  1. https://download.pytorch.org/whl/cu121/ 방문"
echo "  2. 다음 파일 다운로드:"
echo "     - torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
echo "     - torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
echo "  3. $WHEELS_DIR에 저장"
echo ""

echo "옵션 2: wget/curl로 다운로드"
echo "  wget -P $WHEELS_DIR https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
echo "  wget -P $WHEELS_DIR https://download.pytorch.org/whl/cu121/torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
echo ""

echo "옵션 3: 최신 버전 자동 선택"
echo "  이 스크립트 계속 실행..."
echo ""

# PyTorch 최신 버전 자동 선택 시도
echo "🔍 PyTorch 최신 버전 확인 중..."
/opt/homebrew/bin/python3.11 << 'PYTHON'
import urllib.request
import re

url = 'https://download.pytorch.org/whl/cu121/'
try:
    response = urllib.request.urlopen(url, timeout=5)
    html = response.read().decode('utf-8')
    
    # torch 파일 찾기
    matches = re.findall(r'(torch-[\d.]+(?:-cp\d+)?[^"<>]*\.whl)', html)
    if matches:
        # 유니크한 버전만
        versions = {}
        for m in matches:
            ver = m.split('-')[1]
            if ver not in versions:
                versions[ver] = m
        
        if versions:
            latest = sorted(versions.keys(), reverse=True)[0]
            print(f"✅ 최신 버전: torch=={latest}")
            print(f"   다운로드: {versions[latest]}")
except Exception as e:
    print(f"⚠️  수동 다운로드 필요: {e}")
PYTHON

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "다운로드 완료 후 다음을 실행:"
echo "  ls -lh $WHEELS_DIR/ | grep -E '(torch|audio)'"
