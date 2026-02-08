#!/usr/bin/env python3
"""
EC2 모델 문제 진단 및 자동 수정 도구

오류: RuntimeError: Unable to open file 'model.bin' in model '/app/models/openai_whisper-large-v3-turbo'

이 스크립트는:
1. 모델 디렉토리 구조 확인
2. model.bin 파일 위치 파악
3. 필요하면 자동으로 심링크/복사 생성
4. faster-whisper 로드 테스트
"""

import sys
from pathlib import Path
import shutil

def diagnose_model(model_dir):
    """모델 디렉토리 진단"""
    
    print("=" * 70)
    print("🔍 모델 디렉토리 진단")
    print("=" * 70)
    print()
    
    model_path = Path(model_dir)
    
    if not model_path.exists():
        print(f"❌ 모델 디렉토리를 찾을 수 없습니다: {model_dir}")
        return False
    
    print(f"📁 모델 디렉토리: {model_path}")
    print()
    
    # 1. 최상위 파일 확인
    print("📂 최상위 파일:")
    top_files = list(model_path.glob("*"))
    if not top_files:
        print("   (파일 없음)")
    else:
        for f in sorted(top_files):
            if f.is_file():
                size_mb = f.stat().st_size / (1024**2)
                if f.name == "model.bin" or f.is_symlink():
                    target = f.resolve() if f.is_symlink() else "파일"
                    print(f"   {'🔗' if f.is_symlink() else '📄'} {f.name} ({size_mb:.2f}MB)")
                    if f.is_symlink():
                        print(f"      → {target.name}")
                else:
                    print(f"   📄 {f.name} ({size_mb:.2f}MB)")
            elif f.is_dir():
                item_count = len(list(f.iterdir()))
                print(f"   📁 {f.name}/ ({item_count} items)")
    
    # 2. model.bin 위치 파악
    print()
    print("🔎 model.bin 파일 검색:")
    
    model_bins = list(model_path.rglob("model.bin"))
    if model_bins:
        print(f"   ✅ {len(model_bins)}개 발견:")
        for bin_file in model_bins:
            rel_path = bin_file.relative_to(model_path)
            size_mb = bin_file.stat().st_size / (1024**2)
            print(f"      - {rel_path} ({size_mb:.2f}MB)")
    else:
        print("   ❌ model.bin 파일을 찾을 수 없습니다")
        
        # 다른 .bin 파일 확인
        other_bins = list(model_path.rglob("*.bin"))
        if other_bins:
            print()
            print(f"   다른 .bin 파일 발견 ({len(other_bins)}개):")
            for bin_file in other_bins:
                rel_path = bin_file.relative_to(model_path)
                size_mb = bin_file.stat().st_size / (1024**2)
                print(f"      - {rel_path} ({size_mb:.2f}MB)")
            
            return False  # 수정 필요
    
    # 3. ctranslate2_model 디렉토리 확인
    print()
    print("🔎 ctranslate2_model 디렉토리:")
    
    ct2_dir = model_path / "ctranslate2_model"
    if ct2_dir.exists():
        ct2_files = list(ct2_dir.glob("*"))
        print(f"   ✅ 발견 ({len(ct2_files)} items):")
        for f in sorted(ct2_files)[:10]:  # 처음 10개만 표시
            if f.is_file():
                size_mb = f.stat().st_size / (1024**2)
                print(f"      - {f.name} ({size_mb:.2f}MB)")
            else:
                print(f"      📁 {f.name}/")
        if len(ct2_files) > 10:
            print(f"      ... and {len(ct2_files) - 10} more")
    else:
        print("   ❌ ctranslate2_model 디렉토리가 없습니다")
        print("   변환이 필요합니다. 위의 스크립트를 실행하세요.")
    
    print()
    return True

def fix_model(model_dir):
    """model.bin 자동 수정 (상대 경로 심링크 사용)"""
    
    print("=" * 70)
    print("🔧 model.bin 파일 자동 수정")
    print("=" * 70)
    print()
    
    model_path = Path(model_dir)
    
    # 1. 기존 model.bin 제거
    existing_bin = model_path / "model.bin"
    if existing_bin.exists() or existing_bin.is_symlink():
        try:
            existing_bin.unlink()
            print(f"✅ 기존 model.bin 제거됨")
        except Exception as e:
            print(f"⚠️  기존 파일 삭제 실패: {e}")
    
    # 2. ctranslate2_model에서 .bin 파일 찾기
    ct2_dir = model_path / "ctranslate2_model"
    bin_files = list(ct2_dir.glob("*.bin")) if ct2_dir.exists() else []
    
    if not bin_files:
        print("❌ ctranslate2_model 디렉토리에서 .bin 파일을 찾을 수 없습니다")
        return False
    
    # 3. 첫 번째 .bin 파일을 model.bin으로 생성 (상대 경로 사용)
    src_bin = sorted(bin_files)[0]
    
    try:
        # 상대 경로 심링크 생성 (Docker/운영 서버 호환)
        relative_path = src_bin.relative_to(model_path)
        existing_bin.symlink_to(relative_path)
        print(f"✅ 상대 경로 심링크 생성 성공")
        print(f"   상대 경로: {relative_path}")
        print(f"   대상: model.bin")
        print(f"   (Docker: /app/models → 운영: /data/models에서도 작동)")
    except Exception as e:
        # 심링크 실패 시 파일 복사
        print(f"⚠️  심링크 실패: {e}")
        print(f"   파일 복사로 대체합니다...")
        
        try:
            shutil.copy2(src_bin, existing_bin)
            print(f"✅ 파일 복사 완료")
            size_mb = existing_bin.stat().st_size / (1024**2)
            print(f"   크기: {size_mb:.2f}MB")
        except Exception as copy_e:
            print(f"❌ 파일 복사 실패: {copy_e}")
            return False
    
    print()
    return True

def test_model_load(model_dir):
    """model.bin 파일로 faster-whisper 로드 테스트"""
    
    print("=" * 70)
    print("✅ faster-whisper 모델 로드 테스트")
    print("=" * 70)
    print()
    
    try:
        from faster_whisper import WhisperModel
        
        model_path = Path(model_dir) / "ctranslate2_model"
        
        print(f"⏳ 모델 로드 중... (이 단계는 1-2분 걸릴 수 있습니다)")
        print()
        
        model = WhisperModel(
            model_size_or_path=str(model_path),
            device="cpu",
            compute_type="float32"
        )
        
        print("✅ 모델 로드 성공!")
        print()
        print("📋 모델 정보:")
        print(f"   타입: Whisper Large-v3-Turbo (CTranslate2)")
        print(f"   디바이스: CPU")
        print(f"   Compute Type: FP32")
        print()
        
        # 샘플 오디오 테스트
        sample_dir = Path(model_dir).parent / "audio" / "samples"
        if sample_dir.exists():
            sample_file = sample_dir / "short_0.5s.wav"
            if sample_file.exists():
                print(f"⏳ 샘플 오디오 추론 테스트... ({sample_file.name})")
                segments, info = model.transcribe(str(sample_file), language="ko")
                list(segments)  # consume generator
                print(f"✅ 추론 성공")
                print()
        
        return True
        
    except ImportError:
        print("❌ faster-whisper를 설치하지 않았습니다")
        print("   설치: pip install faster-whisper")
        return False
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        return False

def main():
    """메인 함수"""
    
    if len(sys.argv) > 1:
        model_dir = sys.argv[1]
    else:
        # 기본 경로
        model_dir = Path(__file__).parent / "models" / "openai_whisper-large-v3-turbo"
    
    print()
    print("🔍 EC2 STT Engine 모델 진단 및 자동 수정")
    print()
    
    # 1. 진단
    if not diagnose_model(model_dir):
        print()
        print("⚠️  진단 완료 - 모델 구조 문제 발견")
        print()
        
        # 2. 자동 수정 시도
        if fix_model(model_dir):
            print()
            print("✅ model.bin 파일이 수정되었습니다")
        else:
            print()
            print("❌ 자동 수정 실패")
            print()
            print("💡 수동 해결 방법:")
            print("   1. 모델 재다운로드:")
            print("      python download_model_hf.py")
            print()
            print("   2. 또는 CTranslate2 수동 변환:")
            print("      ct2-transformers-converter --model openai/whisper-large-v3-turbo \\")
            print("        --output_dir models/openai_whisper-large-v3-turbo/ctranslate2_model --force")
            print()
            return 1
    
    print()
    
    # 3. 모델 로드 테스트
    if test_model_load(model_dir):
        print()
        print("=" * 70)
        print("✨ 모든 테스트 완료! 모델 준비 완료!")
        print("=" * 70)
        print()
        return 0
    else:
        print()
        print("=" * 70)
        print("❌ 모델 로드 테스트 실패")
        print("=" * 70)
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
