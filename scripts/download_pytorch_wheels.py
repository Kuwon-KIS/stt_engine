#!/usr/bin/env python3
"""
PyTorch wheel 다운로드 스크립트 (오프라인 배포용)
Linux RHEL 8.9 + CUDA 12.9 환경에 맞춰서 다운로드
"""

import subprocess
import os
import sys
from pathlib import Path

# 설정
WHEELS_DIR = Path("/Users/a113211/workspace/stt_engine/deployment_package/wheels")
PIP_EXECUTABLE = "/opt/homebrew/Caskroom/miniforge/base/bin/pip"

# PyTorch 패키지 정보
PACKAGES = {
    "torch": "2.0.1",
    "torchaudio": "2.0.2",
}

# 다운로드 옵션
DOWNLOAD_OPTIONS = [
    "--only-binary=:all:",
    "--platform", "manylinux_2_17_x86_64",
    "--python-version", "311",
    "-d", str(WHEELS_DIR),
    "--no-deps",
    "--no-build-isolation",
]

def main():
    print("📦 PyTorch wheel 다운로드 (오프라인 배포용)")
    print("=" * 60)
    print(f"📍 저장 경로: {WHEELS_DIR}")
    print(f"🐍 Python: {PIP_EXECUTABLE}")
    print("")
    
    # wheels 디렉토리 확인/생성
    WHEELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✅ wheels 디렉토리 준비 완료")
    print("")
    
    # PyPI 인덱스 시도 순서
    indexes = [
        ("PyTorch Official (cu124)", "https://download.pytorch.org/whl/cu124"),
        ("PyTorch Official (cu121)", "https://download.pytorch.org/whl/cu121"),
        ("PyPI (온라인 설치용)", "https://pypi.org/simple"),
    ]
    
    for idx_name, idx_url in indexes:
        print(f"⬇️  시도 {idx_name}: {idx_url}")
        print("-" * 60)
        
        for pkg_name, pkg_version in PACKAGES.items():
            pkg_spec = f"{pkg_name}=={pkg_version}"
            print(f"  📦 {pkg_spec} 다운로드 중...", end=" ")
            sys.stdout.flush()
            
            cmd = [
                PIP_EXECUTABLE, "download",
                pkg_spec,
                *DOWNLOAD_OPTIONS,
                "--index-url", idx_url,
                "--trusted-host", idx_url.split("//")[1],
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5분 타임아웃
                )
                
                if result.returncode == 0:
                    # 파일 확인
                    whl_files = list(WHEELS_DIR.glob(f"{pkg_name}-{pkg_version}-*.whl"))
                    if whl_files:
                        file_size = whl_files[0].stat().st_size / (1024*1024)  # MB
                        print(f"✅ ({file_size:.1f} MB)")
                        continue
                    else:
                        print(f"⚠️  파일 없음")
                else:
                    if "Could not find a version" in result.stderr or "No matching distribution" in result.stderr:
                        print(f"❌ 버전 없음")
                    else:
                        print(f"❌ 에러: {result.stderr[:50]}")
            
            except subprocess.TimeoutExpired:
                print(f"⏱️  타임아웃")
            except Exception as e:
                print(f"❌ 예외: {str(e)[:50]}")
        
        # 모든 패키지가 다운로드되었는지 확인
        all_downloaded = all(
            list(WHEELS_DIR.glob(f"{pkg_name}-{pkg_version}-*.whl"))
            for pkg_name, pkg_version in PACKAGES.items()
        )
        
        if all_downloaded:
            print(f"")
            print(f"✅ {idx_name}에서 모든 패키지 다운로드 성공!")
            break
        else:
            print(f"")
            missing = [
                pkg_name for pkg_name, pkg_version in PACKAGES.items()
                if not list(WHEELS_DIR.glob(f"{pkg_name}-{pkg_version}-*.whl"))
            ]
            print(f"⚠️  누락: {', '.join(missing)}")
            print(f"")
    
    # 최종 검증
    print("")
    print("=" * 60)
    print("📋 최종 검증")
    print("=" * 60)
    print("")
    
    total_size = 0
    for whl_file in sorted(WHEELS_DIR.glob("*.whl")):
        if "torch" in whl_file.name and "audio" not in whl_file.name:
            size_mb = whl_file.stat().st_size / (1024*1024)
            total_size += size_mb
            print(f"  {whl_file.name}: {size_mb:.1f} MB")
    
    for whl_file in sorted(WHEELS_DIR.glob("torchaudio*.whl")):
        size_mb = whl_file.stat().st_size / (1024*1024)
        total_size += size_mb
        print(f"  {whl_file.name}: {size_mb:.1f} MB")
    
    if total_size > 0:
        print(f"")
        print(f"✅ 총 크기: {total_size:.1f} MB")
        print(f"✅ PyTorch wheel 다운로드 완료!")
        return 0
    else:
        print(f"❌ 다운로드 실패")
        return 1

if __name__ == "__main__":
    sys.exit(main())
