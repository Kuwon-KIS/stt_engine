#!/usr/bin/env python3
"""
STT Engine 모델 압축 스크립트

목적:
  - 다운로드된 모델을 tar.gz로 압축
  - 오프라인 Linux 서버로 전송 가능하게 준비
  - 배포 시 신속한 설치

사용:
  python compress_model.py
"""

import os
import sys
import tarfile
import shutil
from pathlib import Path
from datetime import datetime

# 색상 정의
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
NC = '\033[0m'


def print_header(text):
    print(f"{BLUE}╔════════════════════════════════════════════════════════╗{NC}")
    print(f"{BLUE}║{NC} {text}")
    print(f"{BLUE}╚════════════════════════════════════════════════════════╝{NC}")


def print_step(text):
    print(f"{YELLOW}▶ {text}{NC}")


def print_success(text):
    print(f"{GREEN}✅ {text}{NC}")


def print_error(text):
    print(f"{RED}❌ {text}{NC}", file=sys.stderr)


def get_size_str(bytes_size):
    """바이트를 읽기 쉬운 문자열로 변환"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f}TB"


def calculate_compression_ratio(original_size, compressed_size):
    """압축률 계산"""
    ratio = (compressed_size / original_size) * 100
    return ratio


def main():
    print_header("📦 STT Engine 모델 압축 시작")
    
    # 경로 설정
    BASE_DIR = Path(__file__).parent.absolute()
    models_dir = BASE_DIR / "models"
    output_dir = BASE_DIR
    compress_name = "whisper-large-v3-turbo-models.tar.gz"
    compress_path = output_dir / compress_name
    
    # 1단계: 모델 디렉토리 확인
    print_step("1단계: 모델 디렉토리 확인")
    
    if not models_dir.exists():
        print_error(f"모델 디렉토리가 없습니다: {models_dir}")
        sys.exit(1)
    
    # 필수 파일 확인
    required_files = [
        "config.json",
        "model.safetensors",
        "generation_config.json",
        "preprocessor_config.json",
        "tokenizer.json",
    ]
    
    all_found = True
    for req_file in required_files:
        file_path = models_dir / req_file
        if file_path.exists():
            size = get_size_str(file_path.stat().st_size)
            print(f"  ✓ {req_file} ({size})")
        else:
            print(f"  ✗ {req_file} (MISSING)")
            all_found = False
    
    if not all_found:
        print_error("일부 필수 파일이 누락되었습니다")
        sys.exit(1)
    
    print_success("모델 디렉토리 검증 완료")
    
    # 2단계: 압축 전 크기 확인
    print_step("2단계: 압축 전 모델 크기 확인")
    
    total_size = sum(
        f.stat().st_size 
        for f in models_dir.rglob('*') 
        if f.is_file() and not f.name.startswith('.')
    )
    original_size_str = get_size_str(total_size)
    print(f"  원본 크기: {original_size_str}")
    
    # 3단계: 기존 압축 파일 확인
    print_step("3단계: 기존 압축 파일 확인")
    
    if compress_path.exists():
        existing_size = get_size_str(compress_path.stat().st_size)
        print(f"  기존 파일 발견: {compress_name} ({existing_size})")
        
        response = input("  기존 파일을 덮어쓸까요? (y/n) ")
        if response.lower() != 'y':
            print_error("작업 취소됨")
            sys.exit(1)
        
        compress_path.unlink()
        print_success("기존 파일 제거됨")
    else:
        print_success("신규 압축")
    
    # 4단계: 모델 압축
    print_step("4단계: 모델 압축 중 (이 과정은 2-5분 소요)...")
    print(f"  타겟: {compress_path}")
    print()
    
    try:
        with tarfile.open(compress_path, 'w:gz') as tar:
            # 모델 디렉토리의 모든 파일을 압축 (숨김파일 제외)
            for file_path in models_dir.rglob('*'):
                # 숨김파일, .DS_Store 제외
                if file_path.is_file() and not any(
                    part.startswith('.') for part in file_path.relative_to(models_dir).parts
                ):
                    arcname = file_path.relative_to(models_dir)
                    tar.add(file_path, arcname=arcname)
                    if int(tar.fileobj.tell() / (1024*1024)) % 100 == 0:
                        print(f"  진행 중... {get_size_str(tar.fileobj.tell())}")
        
        print_success("압축 완료")
        
    except Exception as e:
        print_error(f"압축 실패: {e}")
        sys.exit(1)
    
    # 5단계: 압축 파일 검증
    print_step("5단계: 압축 파일 검증")
    
    if not compress_path.exists():
        print_error("압축 파일을 생성하지 못했습니다")
        sys.exit(1)
    
    compressed_size = compress_path.stat().st_size
    compressed_size_str = get_size_str(compressed_size)
    ratio = calculate_compression_ratio(total_size, compressed_size)
    
    print(f"  파일명: {compress_name}")
    print(f"  크기: {compressed_size_str}")
    print(f"  압축률: {ratio:.1f}%")
    
    print_success("압축 파일 검증 완료")
    
    # 6단계: 압축 파일 내용 확인
    print_step("6단계: 압축 파일 내용 확인")
    
    try:
        with tarfile.open(compress_path, 'r:gz') as tar:
            members = tar.getmembers()
            file_count = sum(1 for m in members if m.isfile())
            print(f"  파일 수: {file_count}")
            print("\n  상위 10개 파일:")
            for member in members[:10]:
                if member.isfile():
                    size_str = get_size_str(member.size)
                    print(f"    - {member.name} ({size_str})")
            if file_count > 10:
                print(f"    ... 외 {file_count - 10}개 파일")
    except Exception as e:
        print_error(f"압축 파일 확인 실패: {e}")
    
    print_success("압축 파일 내용 확인 완료")
    
    # 7단계: 서버 전송 가이드
    print_step("7단계: 서버 전송 가이드")
    
    print()
    print("  📤 Mac에서 Linux 서버로 전송:")
    print(f"  $ scp {compress_path} ddpapp@dlddpgai1:/data/stt/models/")
    print()
    print("  📥 Linux 서버에서 압축 풀기:")
    print("  $ cd /app/models")
    print(f"  $ tar -xzf {compress_name}")
    print()
    print("  ✅ 압축 풀기 확인:")
    print("  $ ls -lh /app/models/")
    print("     (config.json, model.safetensors, ... 등이 보여야 함)")
    print()
    
    # 최종 결과
    print_header("✅ 모델 압축 완료!")
    
    print()
    print("📊 요약:")
    print(f"  원본 크기: {original_size_str}")
    print(f"  압축 파일: {compressed_size_str}")
    print(f"  압축률: {ratio:.1f}%")
    print(f"  위치: {compress_path}")
    print()
    print("📝 타임스탬프:")
    print(f"  생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("🚀 다음: 서버로 파일 전송")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 작업을 취소했습니다")
        sys.exit(130)
    except Exception as e:
        print_error(f"예기치 않은 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
