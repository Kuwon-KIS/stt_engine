#!/usr/bin/env python3
"""
STT Engine API Server - Entry Point

이 파일은 api_server 패키지의 진입점입니다.
실제 FastAPI 애플리케이션은 api_server.app 모듈에 있습니다.

사용 방법:
1. 직접 실행: python3 api_server.py
2. uvicorn 실행: uvicorn api_server.app:app --host 0.0.0.0 --port 8003
3. Dockerfile: CMD ["python3", "api_server.py"]

패키지 구조:
api_server/
├── __init__.py          (패키지 정의)
├── app.py               (FastAPI 애플리케이션 - 메인 로직)
├── services/            (서비스 모듈)
│   ├── privacy_removal_service.py
│   ├── privacy_removal/
│   │   ├── privacy_remover.py
│   │   ├── vllm_client.py
│   │   └── prompts/
│   └── ...
└── ... (기타 모듈)
"""

if __name__ == "__main__":
    import sys
    import uvicorn
    from api_server.app import app

    # 환경변수로 설정 가능
    import os
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8003"))

    print(f"🚀 Starting STT Engine API Server")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Docs: http://{host}:{port}/docs")
    print()

    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n⚠️  Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)
