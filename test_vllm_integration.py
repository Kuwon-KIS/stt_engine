#!/usr/bin/env python3
"""
vLLM 연동 테스트 스크립트
STT + vLLM 파이프라인 검증
"""

import os
import sys
import requests
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class VLLMTester:
    """vLLM 연동 테스트 클래스"""
    
    def __init__(self, stt_url: str = "http://localhost:8001", 
                 vllm_url: str = None):
        """
        테스터 초기화
        
        Args:
            stt_url: STT Engine URL
            vllm_url: vLLM 서버 URL (기본값: 환경변수에서 읽음)
        """
        self.stt_url = stt_url
        self.vllm_url = vllm_url or os.getenv(
            "VLLM_API_URL", 
            "http://localhost:8000"
        )
        
        print(f"🔗 설정")
        print(f"   STT Engine: {self.stt_url}")
        print(f"   vLLM Server: {self.vllm_url}")
    
    def check_stt_health(self) -> bool:
        """STT Engine 상태 확인"""
        try:
            print("\n📡 STT Engine 헬스 체크 중...")
            response = requests.get(f"{self.stt_url}/health", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ STT Engine 정상")
                print(f"   - 디바이스: {data.get('device', 'unknown')}")
                print(f"   - 모델 로드: {data.get('models_loaded', False)}")
                return True
            else:
                print(f"❌ STT Engine 오류: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ STT Engine 연결 실패: {e}")
            return False
    
    def check_vllm_health(self) -> bool:
        """vLLM 서버 상태 확인"""
        try:
            print("\n📡 vLLM 서버 헬스 체크 중...")
            response = requests.get(f"{self.vllm_url}/health", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ vLLM 서버 정상")
                print(f"   - 모델: {data.get('model_name', 'unknown')}")
                return True
            else:
                print(f"❌ vLLM 서버 오류: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ vLLM 서버 연결 실패: {e}")
            print(f"   💡 vLLM이 {self.vllm_url}에서 실행 중인지 확인하세요")
            return False
    
    def test_stt_only(self, audio_path: str, language: str = "ko") -> Optional[dict]:
        """STT만 테스트"""
        try:
            print(f"\n🎙️  STT 테스트 ({audio_path})")
            
            with open(audio_path, "rb") as f:
                files = {"file": f}
                data = {"language": language}
                
                response = requests.post(
                    f"{self.stt_url}/transcribe",
                    files=files,
                    data=data,
                    timeout=60
                )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ STT 성공")
                print(f"   - 인식 결과: {result.get('text', '')[:100]}...")
                print(f"   - 언어: {result.get('language', 'unknown')}")
                return result
            else:
                print(f"❌ STT 실패: {response.status_code}")
                print(f"   - {response.text}")
                return None
        
        except FileNotFoundError:
            print(f"❌ 파일을 찾을 수 없습니다: {audio_path}")
            return None
        except Exception as e:
            print(f"❌ 오류: {e}")
            return None
    
    def test_stt_with_vllm(
        self, 
        audio_path: str, 
        instruction: str = "다음 텍스트를 한 문장으로 요약해주세요:",
        language: str = "ko"
    ) -> Optional[dict]:
        """STT + vLLM 파이프라인 테스트"""
        try:
            print(f"\n🎙️  STT + vLLM 테스트 ({audio_path})")
            
            with open(audio_path, "rb") as f:
                files = {"file": f}
                data = {
                    "language": language,
                    "instruction": instruction
                }
                
                response = requests.post(
                    f"{self.stt_url}/transcribe-and-process",
                    files=files,
                    data=data,
                    timeout=120
                )
            
            if response.status_code == 200:
                result = response.json()
                
                # STT 결과
                stt_text = result.get("stt_result", {}).get("text", "")
                print(f"✅ STT 성공")
                print(f"   📝 인식: {stt_text[:80]}...")
                
                # vLLM 결과
                vllm_result = result.get("vllm_result", {})
                print(f"✅ vLLM 처리 성공")
                print(f"   🤖 결과: {str(vllm_result)[:80]}...")
                
                return result
            else:
                print(f"❌ 실패: {response.status_code}")
                print(f"   - {response.text}")
                return None
        
        except FileNotFoundError:
            print(f"❌ 파일을 찾을 수 없습니다: {audio_path}")
            return None
        except Exception as e:
            print(f"❌ 오류: {e}")
            return None
    
    def test_batch_processing(self, audio_dir: str) -> None:
        """배치 처리 테스트"""
        audio_dir = Path(audio_dir)
        
        if not audio_dir.exists():
            print(f"❌ 디렉토리를 찾을 수 없습니다: {audio_dir}")
            return
        
        audio_files = list(audio_dir.glob("*.mp3")) + \
                     list(audio_dir.glob("*.wav")) + \
                     list(audio_dir.glob("*.flac"))
        
        if not audio_files:
            print(f"❌ 오디오 파일이 없습니다: {audio_dir}")
            return
        
        print(f"\n📂 배치 처리 ({len(audio_files)}개 파일)")
        
        results = []
        for i, audio_file in enumerate(audio_files, 1):
            print(f"\n  [{i}/{len(audio_files)}] {audio_file.name}")
            
            result = self.test_stt_only(str(audio_file))
            if result:
                results.append({
                    "file": audio_file.name,
                    "text": result.get("text", ""),
                    "language": result.get("language", "")
                })
        
        # 결과 저장
        output_file = audio_dir / "batch_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 배치 처리 완료")
        print(f"   - 성공: {len(results)}개")
        print(f"   - 결과 저장: {output_file}")


def main():
    """메인 테스트 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="vLLM 연동 테스트"
    )
    parser.add_argument(
        "--stt-url",
        default="http://localhost:8001",
        help="STT Engine URL (기본값: http://localhost:8001)"
    )
    parser.add_argument(
        "--vllm-url",
        help="vLLM 서버 URL (기본값: 환경변수 또는 http://localhost:8000)"
    )
    parser.add_argument(
        "--check-health",
        action="store_true",
        help="헬스 체크만 수행"
    )
    parser.add_argument(
        "--test-stt",
        metavar="AUDIO_FILE",
        help="STT 테스트 (음성 파일 경로)"
    )
    parser.add_argument(
        "--test-vllm",
        metavar="AUDIO_FILE",
        help="STT + vLLM 테스트 (음성 파일 경로)"
    )
    parser.add_argument(
        "--instruction",
        default="다음 텍스트를 한 문장으로 요약해주세요:",
        help="vLLM 처리 지시사항 (기본값: 요약)"
    )
    parser.add_argument(
        "--language",
        default="ko",
        help="음성 언어 코드 (기본값: ko)"
    )
    parser.add_argument(
        "--batch",
        metavar="AUDIO_DIR",
        help="배치 처리 (디렉토리 경로)"
    )
    
    args = parser.parse_args()
    
    # 테스터 초기화
    tester = VLLMTester(args.stt_url, args.vllm_url)
    
    # 헬스 체크
    stt_ok = tester.check_stt_health()
    vllm_ok = tester.check_vllm_health()
    
    if not (stt_ok and vllm_ok):
        print(f"\n⚠️  일부 서비스가 실행 중이 아닙니다")
        if not stt_ok:
            print(f"   - STT Engine: python api_server.py")
        if not vllm_ok:
            print(f"   - vLLM Server: 위 VLLM_SETUP.md 참고")
        if args.check_health:
            return
    
    # 테스트 수행
    if args.test_stt:
        tester.test_stt_only(args.test_stt, args.language)
    
    elif args.test_vllm:
        tester.test_stt_with_vllm(
            args.test_vllm, 
            args.instruction,
            args.language
        )
    
    elif args.batch:
        tester.test_batch_processing(args.batch)
    
    elif not args.check_health:
        print(f"\n💡 사용 예시:")
        print(f"   # 헬스 체크")
        print(f"   python test_vllm_integration.py --check-health")
        print(f"")
        print(f"   # STT만 테스트")
        print(f"   python test_vllm_integration.py --test-stt audio.mp3")
        print(f"")
        print(f"   # STT + vLLM 테스트")
        print(f"   python test_vllm_integration.py --test-vllm audio.mp3")
        print(f"")
        print(f"   # 배치 처리")
        print(f"   python test_vllm_integration.py --batch audio_samples/")


if __name__ == "__main__":
    main()
