#!/usr/bin/env python3
"""
STT Engine 모델 준비 스크립트 (Complete)

목적:
  1. 기존 모델 파일 정리
  2. Hugging Face에서 openai/whisper-large-v3-turbo 모델 다운로드
  3. CTranslate2 포맷 변환 (model.bin 생성)
  4. 모델 파일 압축 (tar.gz)
  5. 서버 전송 준비

사용:
  conda activate stt-py311
  python download_model_hf.py
"""

import os
import sys
import ssl
import shutil
import subprocess
import gzip
import tarfile
from pathlib import Path
from datetime import datetime

# SSL 인증서 검증 비활성화 (네트워크 문제 해결용)
ssl._create_default_https_context = ssl._create_unverified_context

def print_header(msg):
    print("\n" + "=" * 60)
    print(msg)
    print("=" * 60 + "\n")

def print_step(msg):
    print(f"\n📌 {msg}")

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")
    sys.exit(1)

print_header("🚀 STT Engine 모델 준비 (다운로드 + 변환 + 압축)")

# 모델 저장 경로 설정
BASE_DIR = Path(__file__).parent.absolute()
models_dir = BASE_DIR / "models"
model_specific_dir = models_dir / "openai_whisper-large-v3-turbo"

print(f"📁 기본 경로: {BASE_DIR}")
print(f"📁 모델 저장 경로: {models_dir}")
print(f"📁 모델 특정 경로: {model_specific_dir}")

# ============================================================================
# Step 1: 기존 모델 파일 정리
# ============================================================================

print_step("Step 1: 기존 모델 파일 정리")

if model_specific_dir.exists():
    print(f"기존 모델 디렉토리 발견: {model_specific_dir}")
    print("삭제 중...")
    shutil.rmtree(model_specific_dir)
    print_success("기존 모델 파일 삭제 완료")
else:
    print(f"기존 모델 디렉토리 없음 (신규 설치)")

# 모델 디렉토리 생성
models_dir.mkdir(parents=True, exist_ok=True)
model_specific_dir.mkdir(parents=True, exist_ok=True)

print(f"📁 신규 모델 디렉토리 생성: {model_specific_dir}")

# ============================================================================
# Step 2: Hugging Face에서 모델 다운로드
# ============================================================================

print_step("Step 2: Hugging Face에서 모델 다운로드")

try:
    from huggingface_hub import snapshot_download
    
    MODEL_REPO = "openai/whisper-large-v3-turbo"
    
    print(f"📦 모델: {MODEL_REPO}")
    print(f"⏳ Hugging Face Hub에서 다운로드 중 (약 1.5GB)...")
    print()
    
    # snapshot_download를 사용하여 실제 파일로 저장
    model_path = snapshot_download(
        repo_id=MODEL_REPO,
        cache_dir=None,
        local_dir=str(model_specific_dir),
        local_dir_use_symlinks=False,  # 🔑 심링크 사용 안 함
        resume_download=True,           # 중단된 다운로드 재개
        force_download=False            # 이미 있으면 스킵
    )
    
    print_success("모델 다운로드 완료")
    
except ImportError:
    print_error("huggingface-hub이 설치되어 있지 않습니다. 설치: pip install huggingface-hub")
    
except Exception as e:
    print_error(f"다운로드 중 오류: {e}")

# ============================================================================
# Step 3: 다운로드된 파일 검증
# ============================================================================

print_step("Step 3: 다운로드된 파일 검증")

print(f"\n📁 다운로드된 파일:")
if not any(model_specific_dir.iterdir()):
    print_error("모델 파일을 찾을 수 없습니다")

# 필수 파일 확인
REQUIRED_FILES = [
    "config.json",
    "model.safetensors",
    "generation_config.json",
    "preprocessor_config.json",
    "tokenizer.json",
]

all_found = True
total_size = 0

for req_file in REQUIRED_FILES:
    file_path = model_specific_dir / req_file
    if file_path.exists():
        size = file_path.stat().st_size / (1024**2)
        total_size += size
        print(f"  ✓ {req_file} ({size:.2f}MB)")
    else:
        print(f"  ✗ {req_file} (MISSING)")
        all_found = False

if not all_found:
    print_error("일부 필수 파일이 누락되었습니다")

print(f"\n📏 전체 크기: {total_size:.2f}MB")
print_success("파일 검증 완료")

# ============================================================================
# Step 4: CTranslate2 포맷 변환 (model.bin 생성)
# ============================================================================

print_step("Step 4: CTranslate2 포맷 변환")

print("⏳ PyTorch 모델을 CTranslate2 바이너리 포맷으로 변환 중...")
print("   (이 단계는 몇 분 걸릴 수 있습니다)")
print()

try:
    import torch
    import torch.nn as nn
    from ctranslate2.converters import TransformersConverter
    
    # PyTorch 모델 경로
    pytorch_model_path = model_specific_dir
    
    # CTranslate2 변환기 생성
    converter = TransformersConverter(
        model_name_or_path=str(pytorch_model_path),
        quantization=None,  # 정밀도 유지 (no quantization)
        trust_remote_code=True
    )
    
    # 변환 실행
    output_dir = model_specific_dir / "ctranslate2_model"
    converter.convert(str(output_dir), force=True)
    
    print_success("CTranslate2 모델 변환 완료")
    
    # 변환된 파일 확인
    print(f"\n📁 변환된 파일:")
    for f in output_dir.glob("*"):
        if f.is_file():
            size = f.stat().st_size / (1024**2)
            print(f"  ✓ {f.name} ({size:.2f}MB)")
    
    # model.bin 복사/링크 생성 (호환성)
    print(f"\n⏳ model.bin 복사 중...")
    model_bin_src = output_dir / "model.bin"
    model_bin_dst = model_specific_dir / "model.bin"
    
    if model_bin_src.exists():
        # 바이너리 파일 복사
        shutil.copy2(model_bin_src, model_bin_dst)
        print_success(f"model.bin 생성 완료: {model_bin_dst}")
    else:
        # 심링크 생성 (공간 절약)
        if model_bin_dst.exists() or model_bin_dst.is_symlink():
            model_bin_dst.unlink()
        model_bin_dst.symlink_to(model_bin_src)
        print_success(f"model.bin 심링크 생성: {model_bin_dst} -> {model_bin_src}")
    
except ImportError as e:
    print(f"❌ CTranslate2 변환 실패: {e}")
    print("   설치: pip install ctranslate2 torch")
    print("   ⚠️  CTranslate2 변환은 선택사항입니다. (openai-whisper로 폴백 가능)")
    print()
except Exception as e:
    print(f"❌ CTranslate2 변환 중 오류: {e}")
    print("   ⚠️  CTranslate2 변환은 선택사항입니다. (openai-whisper로 폴백 가능)")
    print()

# ============================================================================
# Step 5: 모델 파일 압축 (tar.gz)
# ============================================================================

print_step("Step 5: 모델 파일 압축")

print("⏳ 모델 파일을 tar.gz로 압축 중...")
print("   (이 단계는 몇 분 걸릴 수 있습니다)")
print()

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
compressed_filename = f"whisper-large-v3-turbo_models_{timestamp}.tar.gz"
compressed_path = BASE_DIR / "build" / "output" / compressed_filename

# 출력 디렉토리 생성
compressed_path.parent.mkdir(parents=True, exist_ok=True)

try:
    # tar.gz 생성
    with tarfile.open(compressed_path, "w:gz") as tar:
        tar.add(model_specific_dir, arcname="models/openai_whisper-large-v3-turbo")
    
    print_success("모델 압축 완료")
    
    # 압축 파일 크기
    comp_size = compressed_path.stat().st_size / (1024**3)
    print(f"📦 압축 파일: {compressed_path}")
    print(f"📏 크기: {comp_size:.2f}GB")
    
    # 압축률
    original_size = sum(f.stat().st_size for f in model_specific_dir.rglob("*") if f.is_file()) / (1024**3)
    compression_ratio = (1 - comp_size / original_size) * 100
    print(f"📊 압축률: {compression_ratio:.1f}%")
    
except Exception as e:
    print_error(f"압축 중 오류: {e}")

# ============================================================================
# Step 6: MD5 체크섬 생성
# ============================================================================

print_step("Step 6: 무결성 검증 파일 생성")

import hashlib

def calculate_md5(file_path):
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()

md5_value = calculate_md5(compressed_path)
md5_path = compressed_path.with_suffix('.tar.gz.md5')

with open(md5_path, 'w') as f:
    f.write(f"{md5_value}  {compressed_path.name}\n")

print_success(f"MD5 체크섬: {md5_value}")
print(f"파일: {md5_path}")

# ============================================================================
# Step 7: 최종 요약
# ============================================================================

print_header("✅ 모델 준비 완료!")

print("📦 생성된 파일:")
print(f"  1. 모델 디렉토리: {model_specific_dir}")
print(f"  2. 압축 파일: {compressed_path}")
print(f"  3. MD5 체크섬: {md5_path}")
print()

print("📋 다음 단계:")
print("  1. 압축 파일을 운영 서버로 전송:")
print(f"     scp {compressed_path} deploy-user@server:/tmp/")
print()
print("  2. 운영 서버에서 압축 해제:")
print(f"     cd /path/to/deployment")
print(f"     tar -xzf {compressed_filename}")
print()
print("  3. Docker 볼륨 마운트:")
print(f"     docker run -v /path/to/models:/app/models stt-engine:cuda129-v1.2")
print()

print("✨ 모든 준비가 완료되었습니다!")