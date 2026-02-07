#!/usr/bin/env python3
"""
EC2 STT 엔진 모델 진단 및 재구축 스크립트
EC2 RHEL 8.9 환경에서 모델 문제를 진단하고 해결합니다.

사용법:
  1. 진단만: python ec2_model_diagnostics.py
  2. 자동 수정: python ec2_model_diagnostics.py --fix
  3. 강제 재구축: python ec2_model_diagnostics.py --rebuild
"""

import sys
import os
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


class EC2Diagnostics:
    """EC2 STT 엔진 진단 클래스"""
    
    def __init__(self):
        self.stt_dir = Path("/home/ec2-user/stt_engine")
        self.models_dir = self.stt_dir / "models"
        self.model_dir = self.models_dir / "openai_whisper-large-v3-turbo"
        self.ct_model_dir = self.model_dir / "ctranslate2_model"
        self.issues = []
        self.warnings = []
        self.success_checks = []
    
    def print_header(self, msg):
        print("\n" + "="*70)
        print(msg)
        print("="*70)
    
    def print_step(self, msg):
        print(f"\n📌 {msg}")
        print("-"*70)
    
    def print_ok(self, msg):
        print(f"  ✅ {msg}")
        self.success_checks.append(msg)
    
    def print_warn(self, msg):
        print(f"  ⚠️  {msg}")
        self.warnings.append(msg)
    
    def print_error(self, msg):
        print(f"  ❌ {msg}")
        self.issues.append(msg)
    
    def diagnose_model_structure(self):
        """모델 파일 구조 진단"""
        self.print_step("모델 파일 구조 진단")
        
        if not self.model_dir.exists():
            self.print_error(f"모델 폴더 없음: {self.model_dir}")
            return False
        
        print(f"\n  📁 {self.model_dir.name}/ 파일:")
        model_files = sorted(self.model_dir.glob("*"))
        for f in model_files:
            if f.is_file():
                size_mb = f.stat().st_size / (1024**2)
                print(f"     - {f.name} ({size_mb:.2f}MB)")
            else:
                print(f"     - {f.name}/ (폴더)")
        
        # CTranslate2 모델 진단
        if self.ct_model_dir.exists():
            self.print_ok(f"ctranslate2_model 폴더 존재")
            
            print(f"\n  📁 ctranslate2_model/ 파일:")
            ct_files = sorted(self.ct_model_dir.glob("*"))
            
            model_bin_size = 0
            
            for f in ct_files:
                if f.is_file():
                    size_mb = f.stat().st_size / (1024**2)
                    if size_mb > 1:
                        print(f"     - {f.name} ({size_mb:.2f}MB)")
                    else:
                        print(f"     - {f.name} ({f.stat().st_size/1024:.1f}KB)")
                    
                    if f.name == "model.bin":
                        model_bin_size = size_mb
            
            # 필수 파일 확인
            has_model_bin = (self.ct_model_dir / "model.bin").exists()
            has_config = (self.ct_model_dir / "config.json").exists()
            
            if has_model_bin:
                if model_bin_size < 1000:
                    self.print_error(f"model.bin 너무 작음: {model_bin_size:.2f}MB (최소 1000MB 필요)")
                    return False
                else:
                    self.print_ok(f"model.bin 크기 정상: {model_bin_size:.2f}MB")
            else:
                self.print_error("model.bin 파일 없음")
                return False
            
            if has_config:
                self.print_ok("config.json 있음")
            else:
                self.print_error("config.json 파일 없음")
                return False
            
            return True
        else:
            self.print_error("ctranslate2_model 폴더 없음 - 모델 변환 필요")
            return False
    
    def run_full_diagnosis(self):
        """전체 진단 실행"""
        self.print_header("🔍 EC2 STT 엔진 모델 진단 (RHEL 8.9)")
        
        self.diagnose_model_structure()
        
        if self.issues:
            print("\n" + "="*70)
            print("❌ 문제점:")
            for issue in self.issues:
                print(f"   - {issue}")
            return False
        else:
            print("\n" + "="*70)
            print("✅ 모든 점검 통과!")
            return True
    
    def rebuild_model(self):
        """모델 재구축"""
        self.print_header("🔨 모델 재구축")
        
        print("\n⏳ 모델 재구축을 시작합니다...")
        print("   (이 과정은 10-20분 걸릴 수 있습니다)\n")
        
        download_script = self.stt_dir / "download_model_hf.py"
        
        if not download_script.exists():
            print(f"❌ 다운로드 스크립트 없음: {download_script}")
            return False
        
        try:
            # 기존 모델 백업
            if self.model_dir.exists():
                backup_dir = self.models_dir / f"openai_whisper-large-v3-turbo.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                print(f"📦 기존 모델 백업: {backup_dir}")
                shutil.move(str(self.model_dir), str(backup_dir))
            
            # 모델 재다운로드 실행
            print("\n🚀 download_model_hf.py 실행 중...\n")
            result = subprocess.run(
                [sys.executable, str(download_script)],
                cwd=str(self.stt_dir),
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                print("\n✅ 모델 재구축 완료!")
                return True
            else:
                print(f"\n❌ 모델 재구축 실패 (종료 코드: {result.returncode})")
                return False
        
        except Exception as e:
            print(f"\n❌ 모델 재구축 중 오류: {e}")
            return False


def main():
    """메인 진단 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="EC2 STT 엔진 모델 진단 및 재구축"
    )
    parser.add_argument('--fix', action='store_true', help='문제 자동 수정')
    parser.add_argument('--rebuild', action='store_true', help='강제 재구축')
    
    args = parser.parse_args()
    
    diag = EC2Diagnostics()
    
    # 진단 실행
    is_ok = diag.run_full_diagnosis()
    
    # 필요시 수정
    if args.rebuild or (args.fix and not is_ok):
        if diag.rebuild_model():
            print("\n✅ 모델 재구축 후 진단 다시 실행 중...\n")
            diag = EC2Diagnostics()
            is_ok = diag.run_full_diagnosis()
        else:
            print("\n❌ 모델 재구축 실패")
            sys.exit(1)
    
    sys.exit(0 if is_ok else 1)


if __name__ == "__main__":
    main()
