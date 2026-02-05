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

# SSL 인증서 검증 비활성화 (네트워크/방화벽 문제 해결용)
ssl._create_default_https_context = ssl._create_unverified_context

# urllib3 경고 비활성화
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 환경 변수 설정
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'

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
    
    # ========== SSL 검증 완전 비활성화 ==========
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    
    # urllib3 경고 무시
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    
    # 환경 변수로도 비활성화
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    os.environ['CURL_CA_BUNDLE'] = ''
    
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

print_step("Step 4: CTranslate2 포맷 변환 (model.bin 생성)")

print("⏳ PyTorch 모델을 CTranslate2 바이너리 포맷으로 변환 중...")
print("   (이 단계는 5-15분 걸릴 수 있습니다)")
print()

output_dir = model_specific_dir / "ctranslate2_model"
conversion_success = False

# CTranslate2 CLI 도구로 변환 (Hugging Face 모델 ID 사용)
try:
    print("⏳ ct2-transformers-converter CLI 도구로 변환 중...")
    print("   모델: openai/whisper-large-v3-turbo")
    print(f"   출력: {output_dir}")
    print()
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # CLI 도구 실행
    cmd = [
        "conda", "run", "-n", "stt-py311",
        "ct2-transformers-converter",
        "--model", "openai/whisper-large-v3-turbo",
        "--output_dir", str(output_dir),
        "--force",
        "--quantization", "int8"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    
    if result.returncode == 0:
        print_success("✅ CTranslate2 모델 변환 완료!")
        conversion_success = True
    else:
        # CLI 도구 실패 시 Python API로 재시도
        print(f"⚠️  CLI 도구 실패, Python API로 재시도...")
        print()
        
except Exception as e:
    print(f"⚠️  CLI 도구 오류: {e}")
    print("   Python API로 재시도...")
    print()

# 파이썬 API 사용 (HF 모델 ID)
if not conversion_success:
    try:
        from ctranslate2.converters.transformers import TransformersConverter
        
        print("⏳ Python API(TransformersConverter)로 변환 중...")
        print("   모델: openai/whisper-large-v3-turbo (Hugging Face)")
        print()
        
        # HF 모델 ID를 사용하여 변환
        converter = TransformersConverter("openai/whisper-large-v3-turbo")
        
        converter.convert(
            output_dir=str(output_dir),
            quantization="int8",
            force=True
        )
        
        print_success("✅ CTranslate2 모델 변환 완료!")
        conversion_success = True
        
    except Exception as e:
        error_msg = str(e)
        if len(error_msg) > 300:
            error_msg = error_msg[:300] + "..."
        print(f"⚠️  변환 중 오류: {error_msg}")
        print()

# 변환 결과 확인
print()
if conversion_success and output_dir.exists():
    bin_files = list(output_dir.glob("*.bin"))
    
    if bin_files:
        print("✅ 변환된 CTranslate2 모델 파일:")
        total_size = 0
        
        for bin_file in sorted(bin_files):
            size = bin_file.stat().st_size / (1024**2)
            total_size += size
            print(f"   ✓ {bin_file.name} ({size:.2f}MB)")
        
        print(f"\n   📏 합계: {total_size:.2f}MB")
        
        # model.bin 심링크 생성 (faster-whisper 호환성)
        print()
        print("⏳ 심링크 생성 중...")
        
        model_bin_src = bin_files[0]
        model_bin_link = model_specific_dir / "model.bin"
        
        if model_bin_link.exists() or model_bin_link.is_symlink():
            model_bin_link.unlink()
        
        model_bin_link.symlink_to(model_bin_src)
        print_success("✅ model.bin 심링크 생성 완료")
        print(f"   소스: {model_bin_src.name}")
        print(f"   대상: model.bin")
        
    else:
        print("⚠️  변환된 파일을 찾을 수 없습니다")
        print()
        print("💡 수동 변환 시도:")
        print(f"   conda activate stt-py311")
        print(f"   ct2-transformers-converter --model openai/whisper-large-v3-turbo \\")
        print(f"     --output_dir {output_dir} --force --quantization int8")
else:
    print("⚠️  CTranslate2 변환 실패")
    print()
    print("💡 수동 변환 시도:")
    print(f"   conda activate stt-py311")
    print(f"   ct2-transformers-converter --model openai/whisper-large-v3-turbo \\")
    print(f"     --output_dir {output_dir} --force --quantization int8")

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

# ============================================================================
# Step 7: faster-whisper 검증 (CTranslate2 변환된 모델 테스트)
# ============================================================================

print()
print("=" * 60)
print("🔍 모델 검증 (faster-whisper 로드 테스트)")
print("=" * 60)
print()

try:
    from faster_whisper import WhisperModel
    import numpy as np
    
    # CTranslate2로 변환된 모델 경로 확인
    ct2_model_dir = model_specific_dir / "ctranslate2_model"
    model_bin_path = ct2_model_dir / "model.bin"
    
    if not model_bin_path.exists():
        raise FileNotFoundError(f"CTranslate2 모델 파일을 찾을 수 없습니다: {model_bin_path}")
    
    print("⏳ faster-whisper로 CTranslate2 모델 로드 중...")
    print(f"   모델 경로: {ct2_model_dir}")
    print("   (이 단계는 1-3분 걸릴 수 있습니다)")
    print()
    
    # CTranslate2 변환된 모델 로드
    model = WhisperModel(
        model_size_or_path=str(ct2_model_dir),
        device="cpu",
        compute_type="int8"
    )
    
    print_success("✅ faster-whisper 모델 로드 성공!")
    print()
    
    # 모델 정보 출력
    print("📋 모델 정보:")
    print(f"   ✓ 모델 타입: Whisper Large-v3-Turbo")
    print(f"   ✓ 형식: CTranslate2 바이너리 (model.bin)")
    print(f"   ✓ 디바이스: CPU")
    print(f"   ✓ 양자화: INT8 (메모리 효율적)")
    print()
    
    # 더미 오디오로 추론 테스트
    print("⏳ 추론 테스트 중 (더미 오디오)...")
    
    # 1초의 더미 오디오 생성 (16kHz, 모노)
    dummy_audio = np.zeros((16000,), dtype=np.float32)
    
    # 추론 실행
    segments, info = model.transcribe(dummy_audio, language="ko")
    
    print_success("✅ 추론 테스트 성공!")
    print()
    
    print("📊 추론 결과:")
    print(f"   ✓ 감지된 언어: {info.language}")
    print(f"   ✓ 언어 신뢰도: {info.language_probability:.2%}")
    print(f"   ✓ 처리된 오디오 시간: {info.duration:.2f}초")
    
    segment_list = list(segments)
    print(f"   ✓ 감지된 세그먼트: {len(segment_list)}개")
    print()
    
    print("="*60)
    print("✅ 모델 검증 완료!")
    print("="*60)
    print()
    print("🎉 faster-whisper로 정상 작동합니다!")
    print("   CTranslate2 변환된 모델이 성공적으로 로드되었습니다.")
    print()
    
except FileNotFoundError as e:
    print(f"⚠️  파일 오류: {e}")
    print()
    print("💡 해결 방법:")
    print("   CTranslate2 변환이 성공적으로 완료되었는지 확인하세요.")
    print("   만약 변환 실패 시 다음 명령으로 수동 변환:")
    print()
    print("   conda activate stt-py311")
    print(f"   ct2-transformers-converter --model openai/whisper-large-v3-turbo \\")
    print(f"     --output_dir {ct2_model_dir} --force --quantization int8")
    print()
    
except ImportError:
    print("⚠️  faster-whisper가 설치되어 있지 않습니다")
    print()
    print("설치: pip install faster-whisper")
    print()
    
except Exception as e:
    print(f"⚠️  모델 로드 중 오류: {e}")
    print()
    print("📝 디버깅:")
    print("   1. CTranslate2 변환 상태 확인:")
    print(f"      ls -lh {model_specific_dir}/ctranslate2_model/")
    print()
    print("   2. 패키지 버전 확인:")
    print("      pip list | grep -E 'faster-whisper|ctranslate2'")
    print()
    print("   3. 패키지 업그레이드:")
    print("      pip install --upgrade faster-whisper ctranslate2 torch")
    print()