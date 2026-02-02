# torch "invalid wheel location" 오류 해결

## 🔍 문제 진단

### 1. wheels 파일 확인
```bash
# PyTorch wheels 파일 확인
ls -lh deployment_package/wheels/ | grep -E "(torch|audio)"

# 예상 출력:
# torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl  (약 800MB)
# torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl  (약 100MB)
```

### 2. 파일 크기 확인
```bash
# 파일이 너무 작으면 손상된 것
du -h deployment_package/wheels/torch-*.whl

# 크기가 0B, 1KB, 1MB 등이면 다운로드 실패
# 정상: 700MB-900MB
```

### 3. 파일 유효성 확인
```bash
# wheel 파일이 zip인지 확인
file deployment_package/wheels/torch-*.whl

# 정상 출력: ZIP archive data
# 비정상: empty, ASCII text 등

# 또는:
unzip -t deployment_package/wheels/torch-*.whl 2>&1 | head -5
```

---

## ✅ 해결 방법

### 방법 1️⃣: 다운로드 다시 시도 (권장)

**Step 1: 손상된 파일 삭제**
```bash
cd deployment_package/wheels

# torch 파일 삭제
rm -f torch-*.whl torchaudio-*.whl

# 확인
ls -lh | grep -E "(torch|audio)"
# 아무것도 출력되지 않아야 함
```

**Step 2: 다시 다운로드**

**옵션 A: wget (macOS/Linux)**
```bash
cd deployment_package/wheels

# torch 다운로드
wget https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

# torchaudio 다운로드
wget https://download.pytorch.org/whl/cu121/torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

# 다운로드 진행 상황 보기 (위 명령에 -v 추가)
wget -v https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

**옵션 B: curl (macOS/Linux)**
```bash
cd deployment_package/wheels

curl -O https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
curl -O https://download.pytorch.org/whl/cu121/torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

# 진행 상황 보기
curl -# -O https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

**Step 3: 다운로드 확인**
```bash
# 파일 크기 확인
ls -lh torch-*.whl torchaudio-*.whl

# 파일 유효성 확인
file torch-*.whl
# 출력: ZIP archive data 이어야 함

# zip 내용 확인
unzip -t torch-*.whl 2>&1 | tail -3
# 마지막 줄: "All files OK"
```

---

### 방법 2️⃣: 온라인으로 직접 설치 (서버에 인터넷 있을 경우)

**Linux 서버에서:**
```bash
source venv/bin/activate

# 기타 패키지 먼저 설치
pip install deployment_package/wheels/*.whl --no-deps 2>/dev/null || true

# PyTorch 온라인 설치
pip install torch==2.2.0 torchaudio==2.2.0 \
    --index-url https://download.pytorch.org/whl/cu121
```

**장점:**
- 파일 손상 없음
- 자동으로 최신 버전 설치

**단점:**
- 인터넷 필요
- 시간 소요 (10-20분)

---

### 방법 3️⃣: pip로 직접 다운로드 및 설치

**macOS에서:**
```bash
cd deployment_package/wheels

# Python 3.11로 다운로드
/opt/homebrew/bin/python3.11 -m pip download torch==2.2.0 torchaudio==2.2.0 \
    --only-binary=:all: \
    --platform manylinux_2_17_x86_64 \
    --python-version 311 \
    --index-url https://download.pytorch.org/whl/cu121 \
    --no-deps -v

# -v로 상세 로그 확인 가능
```

---

## 🆘 진단 스크립트

아래 스크립트를 실행하면 문제를 자동 진단합니다:

```bash
#!/bin/bash

echo "🔍 PyTorch wheels 진단"
echo "================================"
echo ""

TORCH_FILE="deployment_package/wheels/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"

# 1. 파일 존재 확인
if [ ! -f "$TORCH_FILE" ]; then
    echo "❌ torch wheel 파일 없음"
    echo "   경로: $TORCH_FILE"
    exit 1
fi

echo "✅ 파일 존재"
echo ""

# 2. 파일 크기 확인
SIZE=$(ls -lh "$TORCH_FILE" | awk '{print $5}')
SIZE_BYTES=$(ls -l "$TORCH_FILE" | awk '{print $5}')
echo "📊 파일 크기: $SIZE"

if [ "$SIZE_BYTES" -lt 100000000 ]; then
    echo "⚠️  파일이 너무 작습니다 (100MB 미만)"
    echo "   다시 다운로드해야 합니다"
    exit 1
fi

echo "✅ 파일 크기 정상"
echo ""

# 3. 파일 타입 확인
TYPE=$(file "$TORCH_FILE" | cut -d: -f2)
echo "📋 파일 타입: $TYPE"

if [[ "$TYPE" != *"ZIP"* ]]; then
    echo "❌ ZIP 파일이 아닙니다"
    echo "   파일이 손상되었습니다"
    exit 1
fi

echo "✅ 파일 타입 정상"
echo ""

# 4. zip 내용 확인
echo "🔎 ZIP 내용 검증 중..."
if unzip -t "$TORCH_FILE" > /dev/null 2>&1; then
    echo "✅ ZIP 파일 유효함"
else
    echo "❌ ZIP 파일 손상됨"
    exit 1
fi

echo ""
echo "================================"
echo "✨ 모든 진단 통과!"
echo ""
echo "설치 준비:"
echo "  pip install $TORCH_FILE"
```

이 스크립트를 파일로 저장:
```bash
cat > check_torch.sh << 'EOF'
# 위 내용 붙여넣기
EOF

chmod +x check_torch.sh
./check_torch.sh
```

---

## 📋 일반적인 원인과 해결책

| 원인 | 증상 | 해결책 |
|------|------|--------|
| 불완전한 다운로드 | 파일 크기가 작음 (< 100MB) | 파일 삭제 후 다시 다운로드 |
| 네트워크 오류 | 다운로드 중단됨 | `wget -c`로 재개 다운로드 |
| 잘못된 경로 | "No such file" | 경로 확인: `pwd`, `ls` |
| 손상된 파일 | `unzip -t` 실패 | 파일 삭제 후 다시 다운로드 |
| 디스크 부족 | 다운로드 실패 | 디스크 공간 확인: `df -h` |

---

## 🎯 권장 조치

**1순위: 파일 재다운로드**
```bash
rm -f deployment_package/wheels/torch-*.whl
cd deployment_package/wheels
wget https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
wget https://download.pytorch.org/whl/cu121/torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

**2순위: 파일 검증**
```bash
ls -lh torch-*.whl
file torch-*.whl
unzip -t torch-*.whl | tail -1
```

**3순위: 설치**
```bash
pip install deployment_package/wheels/*.whl
```

---

**현재 상황에서 가장 빠른 해결:**

```bash
# 1. 손상된 파일 삭제
rm -f deployment_package/wheels/torch-*.whl deployment_package/wheels/torchaudio-*.whl

# 2. 다시 다운로드
cd deployment_package/wheels
wget https://download.pytorch.org/whl/cu121/torch-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
wget https://download.pytorch.org/whl/cu121/torchaudio-2.2.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

# 3. 검증
file torch-*.whl

# 4. 설치
pip install torch-*.whl torchaudio-*.whl
```
