#!/bin/bash

# PyTorch/CUDA 라이브러리 위치 확인 스크립트

echo "============================================"
echo "PyTorch CUDA 라이브러리 위치 확인"
echo "============================================"
echo ""

IMAGE_NAME="stt-engine:cuda129-rhel89-v1.2"

echo "🔍 Step 1: PyTorch 설치 경로 확인"
docker run --rm "$IMAGE_NAME" python3.11 -c "
import torch
import os
torch_path = os.path.dirname(torch.__file__)
print(f'PyTorch path: {torch_path}')
print(f'PyTorch lib exists: {os.path.exists(os.path.join(torch_path, \"lib\"))}')
print(f'PyTorch lib path: {os.path.join(torch_path, \"lib\")}')
" 2>&1 || true

echo ""
echo "🔍 Step 2: torch/lib 디렉토리 내용"
docker run --rm "$IMAGE_NAME" ls -la /opt/app-root/lib/python3.11/site-packages/torch/lib/ 2>&1 | head -30

echo ""
echo "🔍 Step 3: libcusparseLt 라이브러리 검색"
docker run --rm "$IMAGE_NAME" find /opt/app-root -name "*cusparseLt*" 2>/dev/null

echo ""
echo "🔍 Step 4: cuDNN 라이브러리 검색"
docker run --rm "$IMAGE_NAME" find /opt/app-root -path "*/cudnn/lib/lib*" 2>/dev/null | head -20

echo ""
echo "🔍 Step 5: nvidia 패키지 lib 검색"
docker run --rm "$IMAGE_NAME" find /opt/app-root/lib/python3.11/site-packages/nvidia -name "*.so*" 2>/dev/null

echo ""
echo "🔍 Step 6: LD_LIBRARY_PATH 확인"
docker run --rm "$IMAGE_NAME" python3.11 -c "
import os
ld_path = os.environ.get('LD_LIBRARY_PATH', 'NOT SET')
print(f'LD_LIBRARY_PATH: {ld_path}')
print('')
print('각 경로별 존재 여부:')
for path in ld_path.split(':'):
    if path:
        exists = os.path.exists(path)
        print(f'  {path}: {\"✓\" if exists else \"✗\"}')" 2>&1

echo ""
echo "🔍 Step 7: PyTorch import 직접 테스트"
docker run --rm "$IMAGE_NAME" python3.11 -c "
import sys
try:
    import torch
    print(f'✅ PyTorch 로드 성공: {torch.__version__}')
    print(f'✅ CUDA 사용 가능: {torch.cuda.is_available()}')
except Exception as e:
    print(f'❌ PyTorch 로드 실패:')
    print(f'   {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
" 2>&1

echo ""
echo "============================================"
echo "End of diagnostics"
echo "============================================"
