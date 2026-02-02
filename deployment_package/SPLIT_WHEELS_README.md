# 분할 압축 Wheel 파일 설치 가이드

## 📦 파일 구성

deployment_package/wheels/ 디렉토리의 wheel 파일들이 900MB 이하로 분할 압축되었습니다.

| 파일명 | 크기 | 포함 내용 |
|--------|------|---------|
| **torch-900mb-part1.tar.gz** | 897 MB | PyTorch 2.5.1 (분할 1/3) |
| **torch-900mb-part2.tar.gz** | 899 MB | PyTorch 2.5.1 (분할 2/3) |
| **torch-900mb-part3.tar.gz** | 449 MB | PyTorch 2.5.1 (분할 3/3) |
| **torchaudio-math-libs.tar.gz** | 11 MB | torchaudio + sympy, networkx, mpmath |
| **utility-libs.tar.gz** | 409 KB | jinja2, fsspec, filelock, MarkupSafe, typing_extensions |
| **torch-2.5.1-cp311-cp311-linux_aarch64.whl** | 2.2 GB | ✅ 원본 파일 (유지) |
| | | |
| **합계** | **6.7 GB** | 모든 파일 포함 |

## 🚀 Linux 서버에서의 설치 방법

### 1단계: 모든 tar.gz 파일을 서버로 전송

```bash
scp deployment_package/wheels/*.tar.gz user@your-server:/tmp/wheels/
```

### 2단계: 서버에서 모든 파일 압축 해제

```bash
cd /tmp/wheels/

# 모든 tar.gz 파일 압축 해제
tar -xzf torch-900mb-part*.tar.gz
tar -xzf torchaudio-math-libs.tar.gz
tar -xzf utility-libs.tar.gz

# 또는 한 줄로:
tar -xzf *.tar.gz
```

### 3단계: PyTorch 파일 재결합

분할된 PyTorch 파일들을 다시 결합합니다:

```bash
# Linux/macOS
cat torch-2.5.1-cp311-cp311-linux_aarch64.partaa \
    torch-2.5.1-cp311-cp311-linux_aarch64.partab \
    torch-2.5.1-cp311-cp311-linux_aarch64.partac > \
    torch-2.5.1-cp311-cp311-linux_aarch64.whl

# Windows (PowerShell)
Get-Content torch-2.5.1-cp311-cp311-linux_aarch64.part* | \
  Set-Content torch-2.5.1-cp311-cp311-linux_aarch64.whl -Encoding Byte
```

### 4단계: 모든 wheel 파일 설치 (오프라인)

```bash
# 가상환경 활성화
source venv/bin/activate

# 모든 wheel 파일 설치
pip install *.whl --no-index --find-links .
```

### 5단계: 재결합된 분할 파일 정리 (선택사항)

```bash
# 분할 부분 파일 제거
rm torch-2.5.1-cp311-cp311-linux_aarch64.part*
```

## ⚙️ 파일 무결성 확인

재결합 후 파일 크기를 확인하여 올바르게 결합되었는지 확인합니다:

```bash
# 원본 파일 크기: 2,359,949,312 bytes (약 2.2GB)
ls -lh torch-2.5.1-cp311-cp311-linux_aarch64.whl

# 전체 분할 파일 크기의 합과 같아야 함
wc -c torch-2.5.1-cp311-cp311-linux_aarch64.part*
```

## 📝 분할 방식

- **전체 파일**: 2.2GB PyTorch
- **분할 방식**: 1GB + 1GB + 201MB (3개 파일)
- **분할 방법**: `split -b 1G` 명령 사용
- **재결합**: `cat` 명령으로 순서대로 연결

## ✅ 검증

모든 wheel 파일이 설치되었는지 확인:

```bash
python3 -c "import torch; print(torch.__version__)"
# 출력: 2.5.1+cu124

python3 -c "import torchaudio; print(torchaudio.__version__)"
# 출력: 2.5.1
```

---

**주의**: 분할 파일들을 설치하기 전에 반드시 재결합해야 합니다. 개별 분할 파일로는 설치할 수 없습니다.
