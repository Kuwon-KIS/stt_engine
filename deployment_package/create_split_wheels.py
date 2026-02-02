#!/usr/bin/env python3
"""
wheel 파일들을 1GB 이하로 분할 압축하는 스크립트
"""
import os
import tarfile
import shutil
from pathlib import Path

def create_split_archives():
    wheels_dir = Path(__file__).parent / "wheels"
    os.chdir(wheels_dir)
    
    print("📦 wheel 파일들을 분할 압축 중...\n")
    
    # 분할 1: PyTorch 메인 (2.2GB) - 그대로 압축
    print("분할 1: PyTorch 메인 파일")
    with tarfile.open("torch-2.5.1-wheels.tar.gz", "w:gz") as tar:
        tar.add("torch-2.5.1-cp311-cp311-linux_aarch64.whl", 
                arcname="torch-2.5.1-cp311-cp311-linux_aarch64.whl")
    size1 = os.path.getsize("torch-2.5.1-wheels.tar.gz") / (1024**3)
    print(f"  ✅ torch-2.5.1-wheels.tar.gz: {size1:.2f} GB\n")
    
    # 분할 2: torchaudio + 의존성 (math/numeric libs)
    print("분할 2: torchaudio + 수학 라이브러리")
    files2 = [
        "torchaudio-2.5.1-cp311-cp311-linux_aarch64.whl",
        "sympy-1.13.1-py3-none-any.whl",
        "networkx-3.6.1-py3-none-any.whl",
        "mpmath-1.3.0-py3-none-any.whl",
    ]
    with tarfile.open("torchaudio-math-libs.tar.gz", "w:gz") as tar:
        for f in files2:
            if os.path.exists(f):
                tar.add(f, arcname=f)
    size2 = os.path.getsize("torchaudio-math-libs.tar.gz") / (1024**3)
    print(f"  ✅ torchaudio-math-libs.tar.gz: {size2:.2f} GB\n")
    
    # 분할 3: 유틸리티 라이브러리
    print("분할 3: 유틸리티 라이브러리")
    files3 = [
        "jinja2-3.1.6-py3-none-any.whl",
        "fsspec-2025.12.0-py3-none-any.whl",
        "filelock-3.20.0-py3-none-any.whl",
        "MarkupSafe-2.1.5-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl",
        "typing_extensions-4.15.0-py3-none-any.whl",
    ]
    with tarfile.open("utility-libs.tar.gz", "w:gz") as tar:
        for f in files3:
            if os.path.exists(f):
                tar.add(f, arcname=f)
    size3 = os.path.getsize("utility-libs.tar.gz") / (1024**3)
    print(f"  ✅ utility-libs.tar.gz: {size3:.3f} GB\n")
    
    print("━" * 60)
    print("✅ 분할 압축 완료!")
    print("━" * 60)
    print(f"\n파일 크기:")
    print(f"  • torch-2.5.1-wheels.tar.gz:   {size1:.2f} GB")
    print(f"  • torchaudio-math-libs.tar.gz: {size2:.2f} GB")
    print(f"  • utility-libs.tar.gz:         {size3:.3f} GB")
    print(f"  • 합계:                         {size1+size2+size3:.2f} GB")
    
    print(f"\n✨ 모두 1GB 이하입니다!")
    print(f"\n🔓 Linux 서버에서 압축 해제:")
    print(f"  tar -xzf torch-2.5.1-wheels.tar.gz")
    print(f"  tar -xzf torchaudio-math-libs.tar.gz")
    print(f"  tar -xzf utility-libs.tar.gz")

if __name__ == "__main__":
    create_split_archives()
