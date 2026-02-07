#!/usr/bin/env python3
"""
STT Engine Main Entry Point
Starts the FastAPI server
"""
import subprocess
import sys
from pathlib import Path


def main():
    """Main entry point - starts the STT API server"""
    app_dir = Path(__file__).parent
    
    # Start the API server
    print(f"🚀 Starting STT Engine API Server from {app_dir}")
    try:
        subprocess.run([
            sys.executable, 
            str(app_dir / "api_server.py")
        ], check=True)
    except KeyboardInterrupt:
        print("\n⚠️ API Server stopped by user")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"❌ API Server failed with error code {e.returncode}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
