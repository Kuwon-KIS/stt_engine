#!/usr/bin/env python3
"""
FastAPI Request + Form 혼합 테스트
"""
from fastapi import FastAPI, Form, Request, Query
from fastapi.testclient import TestClient
from typing import Optional

# 우리의 실제 함수와 동일한 방식
app = FastAPI()

@app.post("/transcribe_old")
async def transcribe_old(
    file_path: str = Form(...),
    language: str = Form("ko"),
):
    return {"file_path": file_path, "language": language}

@app.post("/transcribe_new")
async def transcribe_new(
    request: Request,
    export: Optional[str] = Query(None),
):
    """Request만 사용"""
    form_data = await request.form()
    return {
        "file_path": form_data.get('file_path'),
        "stt_text": form_data.get('stt_text'),
        "language": form_data.get('language', 'ko'),
    }

# 테스트
client = TestClient(app)

print("\n=== Old style (file_path required) ===")
try:
    r = client.post("/transcribe_old", data={"language": "ko"})
    print(f"Status: {r.status_code}, Response: {r.json()}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== New style (Request only) - No data ===")
r = client.post("/transcribe_new")
print(f"Status: {r.status_code}, Response: {r.json()}")

print("\n=== New style (Request only) - With stt_text ===")
r = client.post("/transcribe_new", data={"stt_text": "Hello world"})
print(f"Status: {r.status_code}, Response: {r.json()}")

print("\n=== New style (Request only) - With file_path ===")
r = client.post("/transcribe_new", data={"file_path": "/path/to/file.wav"})
print(f"Status: {r.status_code}, Response: {r.json()}")

print("\nAll tests completed!")
