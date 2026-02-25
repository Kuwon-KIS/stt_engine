#!/usr/bin/env python3
"""
직접 API 테스트용 스크립트
"""
import sys
import asyncio
from pathlib import Path

# 경로 설정
app_root = Path(__file__).parent
sys.path.insert(0, str(app_root))

from fastapi import FastAPI, Form, Request
from fastapi.testclient import TestClient
from typing import Optional

# 테스트용 간단한 앱
app_test = FastAPI()

@app_test.post("/test1")
async def test1(
    request: Request,
    export: Optional[str] = None
):
    """Request만 사용하는 엔드포인트"""
    form_data = await request.form()
    return {
        "method": "Request only",
        "data": dict(form_data),
        "file_path": form_data.get('file_path'),
        "stt_text": form_data.get('stt_text'),
    }

@app_test.post("/test2")
async def test2(
    file_path: str = Form(None),
    stt_text: str = Form(None),
):
    """Optional Form 사용"""
    return {
        "method": "Optional Form",
        "file_path": file_path,
        "stt_text": stt_text,
    }

@app_test.post("/test3")
async def test3(
    request: Request,
    language: str = Form("ko"),
):
    """Request + Form 혼합"""
    form_data = await request.form()
    return {
        "method": "Request + Form",
        "data": dict(form_data),
    }

# 테스트
if __name__ == "__main__":
    client = TestClient(app_test)
    
    print("\n=== Test 1: Request only ===")
    r = client.post("/test1", data={"stt_text": "Hello"})
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
    
    print("\n=== Test 2: Optional Form ===")
    r = client.post("/test2", data={"stt_text": "Hello"})
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
    
    print("\n=== Test 3: Request + Form ===")
    r = client.post("/test3", data={"stt_text": "Hello"})
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
