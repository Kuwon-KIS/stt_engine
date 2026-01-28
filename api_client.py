#!/usr/bin/env python3
"""
STT API 클라이언트 - 테스트 및 통합용
"""

import requests
import argparse
from pathlib import Path
from typing import Optional, Dict
import json


class STTClient:
    """STT API 클라이언트"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        """
        클라이언트 초기화
        
        Args:
            base_url: API 서버 주소
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
    
    def health_check(self) -> bool:
        """
        서버 상태 확인
        
        Returns:
            서버 정상 여부
        """
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 서버 정상")
                print(f"   상태: {data.get('status')}")
                print(f"   디바이스: {data.get('device')}")
                print(f"   모델 로드: {data.get('models_loaded')}")
                return True
            else:
                print(f"❌ 서버 오류: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 서버 연결 실패: {e}")
            return False
    
    def transcribe(
        self,
        audio_file: str,
        language: Optional[str] = None
    ) -> Dict:
        """
        음성 파일을 텍스트로 변환
        
        Args:
            audio_file: 음성 파일 경로
            language: 음성 언어 코드
        
        Returns:
            변환 결과
        """
        try:
            audio_path = Path(audio_file)
            if not audio_path.exists():
                print(f"❌ 파일 없음: {audio_file}")
                return {"success": False, "error": "File not found"}
            
            print(f"📤 파일 업로드: {audio_path.name}")
            
            with open(audio_path, "rb") as f:
                files = {"file": f}
                params = {}
                if language:
                    params["language"] = language
                
                response = self.session.post(
                    f"{self.base_url}/transcribe",
                    files=files,
                    params=params,
                    timeout=120
                )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"✅ 변환 완료")
                    print(f"\n📝 결과:")
                    print(f"{result.get('text', '')}")
                    return result
                else:
                    print(f"❌ 변환 실패: {result.get('error')}")
                    return result
            else:
                print(f"❌ 서버 오류: {response.status_code}")
                print(f"   {response.text}")
                return {"success": False, "error": response.text}
        
        except Exception as e:
            print(f"❌ 오류: {e}")
            return {"success": False, "error": str(e)}
    
    def transcribe_and_process(
        self,
        audio_file: str,
        instruction: str = "다음 텍스트를 요약해주세요:",
        language: Optional[str] = None
    ) -> Dict:
        """
        음성 파일을 변환하고 vLLM으로 처리
        
        Args:
            audio_file: 음성 파일 경로
            instruction: vLLM 처리 지시사항
            language: 음성 언어 코드
        
        Returns:
            변환 및 처리 결과
        """
        try:
            audio_path = Path(audio_file)
            if not audio_path.exists():
                print(f"❌ 파일 없음: {audio_file}")
                return {"success": False, "error": "File not found"}
            
            print(f"📤 파일 업로드: {audio_path.name}")
            print(f"📝 지시사항: {instruction}")
            
            with open(audio_path, "rb") as f:
                files = {"file": f}
                params = {"instruction": instruction}
                if language:
                    params["language"] = language
                
                response = self.session.post(
                    f"{self.base_url}/transcribe-and-process",
                    files=files,
                    params=params,
                    timeout=300
                )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    stt_result = result.get("stt_result", {})
                    vllm_result = result.get("vllm_result", {})
                    
                    print(f"✅ 변환 및 처리 완료")
                    print(f"\n📝 STT 결과:")
                    print(f"{stt_result.get('text', '')}")
                    print(f"\n🤖 vLLM 처리 결과:")
                    print(f"{vllm_result.get('processed_text', '')}")
                    return result
                else:
                    print(f"❌ 처리 실패: {result.get('error')}")
                    return result
            else:
                print(f"❌ 서버 오류: {response.status_code}")
                print(f"   {response.text}")
                return {"success": False, "error": response.text}
        
        except Exception as e:
            print(f"❌ 오류: {e}")
            return {"success": False, "error": str(e)}
    
    def batch_transcribe(self, audio_dir: str) -> list:
        """
        디렉토리의 모든 음성 파일 변환
        
        Args:
            audio_dir: 음성 파일 디렉토리
        
        Returns:
            변환 결과 리스트
        """
        audio_path = Path(audio_dir)
        if not audio_path.exists():
            print(f"❌ 디렉토리 없음: {audio_dir}")
            return []
        
        # 지원하는 파일 형식
        supported_formats = ("*.wav", "*.mp3", "*.flac", "*.ogg")
        audio_files = []
        for fmt in supported_formats:
            audio_files.extend(audio_path.glob(fmt))
        
        if not audio_files:
            print(f"⚠️  음성 파일을 찾을 수 없습니다: {audio_dir}")
            return []
        
        results = []
        print(f"\n🔄 총 {len(audio_files)}개 파일 처리 중...\n")
        
        for idx, audio_file in enumerate(audio_files, 1):
            print(f"{'='*60}")
            print(f"[{idx}/{len(audio_files)}] {audio_file.name}")
            print(f"{'='*60}")
            
            result = self.transcribe(str(audio_file))
            results.append({
                "file": str(audio_file),
                "result": result
            })
            print()
        
        return results


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="STT API 클라이언트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 헬스 체크
  python api_client.py --health

  # 단일 파일 변환
  python api_client.py --transcribe audio.wav

  # 언어 지정하여 변환
  python api_client.py --transcribe audio.wav --language ko

  # 변환 및 vLLM 처리
  python api_client.py --process audio.wav --instruction "요약해주세요"

  # 배치 처리
  python api_client.py --batch audio/
        """
    )
    
    parser.add_argument(
        "--url",
        default="http://localhost:8001",
        help="API 서버 주소 (기본값: http://localhost:8001)"
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="서버 상태 확인"
    )
    parser.add_argument(
        "--transcribe",
        metavar="FILE",
        help="음성 파일 변환"
    )
    parser.add_argument(
        "--process",
        metavar="FILE",
        help="음성 파일 변환 및 vLLM 처리"
    )
    parser.add_argument(
        "--batch",
        metavar="DIR",
        help="디렉토리의 모든 음성 파일 변환"
    )
    parser.add_argument(
        "--language",
        metavar="LANG",
        help="음성 언어 코드 (예: ko, en)"
    )
    parser.add_argument(
        "--instruction",
        default="다음 텍스트를 요약해주세요:",
        help="vLLM 처리 지시사항 (기본값: 다음 텍스트를 요약해주세요:)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON 형식으로 결과 출력"
    )
    
    args = parser.parse_args()
    
    # 클라이언트 생성
    client = STTClient(args.url)
    
    # 헬스 체크
    if args.health:
        print(f"🔍 서버 주소: {args.url}\n")
        client.health_check()
        return
    
    # 단일 파일 변환
    if args.transcribe:
        print(f"🎯 모드: STT 변환")
        print(f"🔗 서버: {args.url}\n")
        result = client.transcribe(args.transcribe, language=args.language)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    # 변환 및 vLLM 처리
    if args.process:
        print(f"🎯 모드: STT + vLLM 처리")
        print(f"🔗 서버: {args.url}\n")
        result = client.transcribe_and_process(
            args.process,
            instruction=args.instruction,
            language=args.language
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    # 배치 처리
    if args.batch:
        print(f"🎯 모드: 배치 처리")
        print(f"🔗 서버: {args.url}\n")
        results = client.batch_transcribe(args.batch)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    
    # 도움말 출력
    parser.print_help()


if __name__ == "__main__":
    main()
