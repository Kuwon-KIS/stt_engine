#!/usr/bin/env python3
"""
모델 압축/해제 및 로드 유틸리티
- TAR 압축 생성
- 자동 압축 해제
- 원격 저장소에서 로드 (S3, Hugging Face)
"""

import tarfile
import os
from pathlib import Path
from typing import Optional
import argparse
import sys

# 선택적 의존성: boto3는 S3 기능이 필요할 때만 import
try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


class ModelManager:
    """모델 관리 클래스"""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.model_folder = self.models_dir / "openai_whisper-large-v3-turbo"
        self.tar_file = self.models_dir / "whisper-model.tar.gz"
    
    def compress_model(self, verbose: bool = True) -> bool:
        """
        모델 폴더를 TAR로 압축
        
        Args:
            verbose: 상세 출력 여부
        
        Returns:
            성공 여부
        """
        if not self.model_folder.exists():
            print(f"❌ 모델 폴더를 찾을 수 없습니다: {self.model_folder}")
            return False
        
        if self.tar_file.exists():
            print(f"⚠️  압축 파일이 이미 존재합니다: {self.tar_file}")
            response = input("덮어쓰시겠습니까? (y/n): ")
            if response.lower() != 'y':
                return False
        
        try:
            if verbose:
                print(f"📦 모델 압축 중...")
                print(f"   원본: {self.model_folder}")
                print(f"   대상: {self.tar_file}")
            
            with tarfile.open(self.tar_file, "w:gz") as tar:
                tar.add(
                    self.model_folder,
                    arcname=self.model_folder.name
                )
            
            # 크기 비교
            original_size = self._get_folder_size(self.model_folder)
            compressed_size = self.tar_file.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100
            
            if verbose:
                print(f"✅ 압축 완료!")
                print(f"   원본 크기: {original_size / 1e9:.2f}GB")
                print(f"   압축 크기: {compressed_size / 1e9:.2f}GB")
                print(f"   압축률: {ratio:.1f}%")
            
            return True
        
        except Exception as e:
            print(f"❌ 압축 실패: {e}")
            return False
    
    def extract_model(self, verbose: bool = True) -> bool:
        """
        TAR 파일 압축 해제
        
        Args:
            verbose: 상세 출력 여부
        
        Returns:
            성공 여부
        """
        if not self.tar_file.exists():
            print(f"❌ 압축 파일을 찾을 수 없습니다: {self.tar_file}")
            return False
        
        if self.model_folder.exists():
            print(f"⚠️  모델 폴더가 이미 존재합니다: {self.model_folder}")
            response = input("덮어쓰시겠습니까? (y/n): ")
            if response.lower() != 'y':
                return False
            import shutil
            shutil.rmtree(self.model_folder)
        
        try:
            if verbose:
                print(f"📦 모델 압축 해제 중...")
                print(f"   압축 파일: {self.tar_file}")
            
            with tarfile.open(self.tar_file, "r:gz") as tar:
                tar.extractall(path=self.models_dir)
            
            if verbose:
                print(f"✅ 압축 해제 완료!")
                print(f"   위치: {self.model_folder}")
            
            return True
        
        except Exception as e:
            print(f"❌ 압축 해제 실패: {e}")
            return False
    
    def auto_extract_if_needed(self) -> Path:
        """
        필요시 자동 압축 해제
        
        Returns:
            모델 폴더 경로
        """
        # 이미 해제되어 있으면 반환
        if self.model_folder.exists():
            return self.model_folder
        
        # 압축 파일이 있으면 해제
        if self.tar_file.exists():
            print("📦 모델을 자동으로 압축 해제합니다...")
            if self.extract_model(verbose=True):
                return self.model_folder
            else:
                raise RuntimeError("모델 압축 해제 실패")
        
        # 둘 다 없으면 에러
        raise FileNotFoundError(
            f"모델을 찾을 수 없습니다:\n"
            f"  해제됨: {self.model_folder}\n"
            f"  압축됨: {self.tar_file}"
        )
    
    def cleanup_original_after_compress(self, verbose: bool = True) -> bool:
        """
        압축 후 원본 폴더 삭제
        
        Args:
            verbose: 상세 출력 여부
        
        Returns:
            성공 여부
        """
        if not self.tar_file.exists():
            print("❌ 압축 파일이 없습니다")
            return False
        
        if not self.model_folder.exists():
            print("⚠️  원본 폴더가 이미 없습니다")
            return True
        
        try:
            import shutil
            if verbose:
                print(f"🗑️  원본 폴더 삭제 중: {self.model_folder}")
            
            shutil.rmtree(self.model_folder)
            
            if verbose:
                print(f"✅ 삭제 완료!")
            
            return True
        
        except Exception as e:
            print(f"❌ 삭제 실패: {e}")
            return False
    
    def download_from_s3(
        self,
        bucket: str,
        key: str,
        region: str = "us-east-1",
        verbose: bool = True
    ) -> bool:
        """
        AWS S3에서 모델 다운로드
        
        Args:
            bucket: S3 버킷 이름
            key: S3 객체 키
            region: AWS 리전
            verbose: 상세 출력 여부
        
        Returns:
            성공 여부
        
        Raises:
            ImportError: boto3가 설치되지 않음
            Exception: S3 다운로드 실패
        """
        if not HAS_BOTO3:
            print("❌ boto3가 설치되지 않았습니다")
            print("   설치: pip install boto3")
            return False
        
        try:
            s3 = boto3.client('s3', region_name=region)
            
            if verbose:
                print(f"📥 S3에서 다운로드 중...")
                print(f"   버킷: {bucket}")
                print(f"   키: {key}")
            
            s3.download_file(bucket, key, str(self.tar_file))
            
            if verbose:
                print(f"✅ 다운로드 완료")
                print(f"   파일: {self.tar_file}")
            
            return True
        
        except Exception as e:
            print(f"❌ S3 다운로드 실패: {e}")
            return False
    
    @staticmethod
    def _get_folder_size(path: Path) -> int:
        """폴더 크기 계산"""
        total = 0
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
        return total


def main():
    """CLI 인터페이스"""
    parser = argparse.ArgumentParser(
        description="Whisper 모델 압축/해제 유틸리티",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 모델 압축
  python model_manager.py compress

  # 압축 해제
  python model_manager.py extract

  # S3에서 다운로드 후 해제
  python model_manager.py download-s3 --bucket my-bucket --key whisper-model.tar.gz

  # 압축 후 원본 삭제
  python model_manager.py compress --cleanup

  # 자동 로드 테스트
  python model_manager.py test
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='명령어')
    
    # compress 명령어
    compress_parser = subparsers.add_parser('compress', help='모델 압축')
    compress_parser.add_argument(
        '--cleanup',
        action='store_true',
        help='압축 후 원본 폴더 삭제'
    )
    
    # extract 명령어
    subparsers.add_parser('extract', help='모델 압축 해제')
    
    # download-s3 명령어
    s3_parser = subparsers.add_parser('download-s3', help='S3에서 다운로드')
    s3_parser.add_argument('--bucket', required=True, help='S3 버킷 이름')
    s3_parser.add_argument('--key', required=True, help='S3 객체 키')
    s3_parser.add_argument('--region', default='us-east-1', help='AWS 리전')
    
    # test 명령어
    subparsers.add_parser('test', help='자동 압축 해제 테스트')
    
    # info 명령어
    subparsers.add_parser('info', help='모델 상태 정보')
    
    args = parser.parse_args()
    
    manager = ModelManager()
    
    if args.command == 'compress':
        success = manager.compress_model()
        if success and args.cleanup:
            manager.cleanup_original_after_compress()
        return 0 if success else 1
    
    elif args.command == 'extract':
        return 0 if manager.extract_model() else 1
    
    elif args.command == 'download-s3':
        if manager.download_from_s3(args.bucket, args.key, args.region):
            return 0 if manager.extract_model() else 1
        return 1
    
    elif args.command == 'test':
        try:
            path = manager.auto_extract_if_needed()
            print(f"✅ 자동 로드 성공: {path}")
            return 0
        except Exception as e:
            print(f"❌ 자동 로드 실패: {e}")
            return 1
    
    elif args.command == 'info':
        print("📊 모델 상태 정보")
        print("─" * 50)
        
        if manager.model_folder.exists():
            size = manager._get_folder_size(manager.model_folder)
            print(f"✅ 해제됨: {manager.model_folder}")
            print(f"   크기: {size / 1e9:.2f}GB")
        else:
            print(f"❌ 해제됨: {manager.model_folder} (없음)")
        
        if manager.tar_file.exists():
            size = manager.tar_file.stat().st_size
            print(f"✅ 압축됨: {manager.tar_file}")
            print(f"   크기: {size / 1e9:.2f}GB")
        else:
            print(f"❌ 압축됨: {manager.tar_file} (없음)")
        
        return 0
    
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
