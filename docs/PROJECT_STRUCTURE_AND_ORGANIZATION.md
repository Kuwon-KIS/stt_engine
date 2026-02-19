# Project Structure Guide

## 📁 Directory Layout

```
stt_engine/
├── 📄 api_server.py             ← API 서버 진입점 (진입점만, 실제 앱은 api_server/app.py)
├── 📄 api_client.py             ← API 클라이언트 (테스트용)
│
├── 📁 api_server/               ← 메인 API 서버 패키지
│   ├── __init__.py
│   ├── app.py                   ← FastAPI 애플리케이션 (메인 로직)
│   ├── services/                ← 서비스 모듈
│   │   ├── __init__.py
│   │   ├── privacy_removal_service.py    ← Privacy Removal 서비스
│   │   └── privacy_removal/              ← Privacy Removal 패키지
│   │       ├── __init__.py
│   │       ├── privacy_remover.py        ← LLM 처리 클래스
│   │       ├── vllm_client.py            ← vLLM 클라이언트
│   │       └── prompts/
│   │           └── privacy_remover_default_v6.prompt
│   └── ...
│
├── 📁 web_ui/                   ← 웹 인터페이스
│   ├── main.py
│   ├── templates/
│   └── static/
│
├── 📁 utils/                    ← 공용 유틸리티
│   ├── performance_monitor.py
│   └── ...
│
├── 📁 docs/                     ← 📚 문서 (중요!)
│   ├── PRIVACY_REMOVAL_GUIDE.md ← Privacy Removal 종합 가이드 ⭐
│   ├── API_USAGE_GUIDE.md
│   ├── QUICKSTART.md
│   ├── DEPLOYMENT_READY.md
│   └── ... (기타 문서)
│
├── 📁 models/                   ← STT 모델
│   └── openai_whisper-large-v3-turbo/
│
├── 📁 deployment_package/       ← 배포용 패키지
│
├── 📁 docker/                   ← Docker 설정
│
├── 📁 scripts/                  ← 실행 스크립트
│
├── 📁 scratch/                  ← 테스트용 코드 (참고용)
│
├── requirements.txt             ← Python 의존성
├── pyproject.toml
└── README.md
```

---

## 🎯 Core Files Explanation

### 1. api_server.py (루트)
**역할:** API 서버의 진입점

**내용:**
```python
# 간단한 래퍼: api_server.app에서 FastAPI app을 import해서 실행
from api_server.app import app
uvicorn.run(app, host="0.0.0.0", port=8003)
```

**왜 이렇게?**
- 진입점은 깔끔하게 유지
- 실제 구현은 패키지 내부에서 관리
- Docker/script에서 `python3 api_server.py`로 실행 가능

**실행 방법:**
```bash
python3 api_server.py                          # 직접 실행
uvicorn api_server.app:app --port 8003         # uvicorn으로 실행
```

---

### 2. api_server/ (디렉토리)
**역할:** FastAPI 애플리케이션의 메인 패키지

**구조:**
```
api_server/
├── __init__.py          ← app을 import (패키지 정의)
├── app.py               ← FastAPI 애플리케이션 (1400+ 줄)
├── services/            ← 비즈니스 로직
│   ├── privacy_removal_service.py
│   └── privacy_removal/
│       ├── privacy_remover.py
│       ├── vllm_client.py
│       └── prompts/
```

**핵심 파일: api_server/app.py**
- FastAPI 앱 정의
- 모든 라우트(@app.get, @app.post) 정의
- STT 엔드포인트: `/transcribe`, `/health` 등
- Privacy Removal 엔드포인트: `/api/privacy-removal/process` 등

---

### 3. api_client.py (루트)
**역할:** STT API 서버와 상호작용하는 클라이언트

**내용:**
- STTClient 클래스: API 호출 메서드 제공
- PrivacyRemovalClient 클래스: Privacy Removal 테스트용
- 커맨드라인 인터페이스: 직접 실행 가능

**사용 예시:**
```python
from api_client import STTClient

client = STTClient("http://localhost:8003")
result = client.transcribe("audio.wav")
```

**커맨드라인 실행:**
```bash
python3 api_client.py --file audio.wav
python3 api_client.py --health
```

---

## 📦 Package Structure Details

### api_server/__init__.py
```python
# app을 import하여 패키지 노출
from .app import app as fastapi_app
__all__ = ["fastapi_app"]
```

### api_server/services/__init__.py
```python
# 서비스들을 패키지 레벨에서 import
from .privacy_removal_service import PrivacyRemovalService, get_privacy_removal_service
__all__ = ["PrivacyRemovalService", "get_privacy_removal_service"]
```

### api_server/services/privacy_removal/__init__.py
```python
# Privacy Removal 컴포넌트들을 import
from .privacy_remover import LLMProcessorForPrivacy
from .vllm_client import VLLMClient
from .privacy_removal_service import PrivacyRemovalService

__all__ = [
    "LLMProcessorForPrivacy",
    "VLLMClient",
    "PrivacyRemovalService",
]
```

---

## 🔄 Import Paths

### API 서버 실행
```python
# api_server.py (루트)에서
from api_server.app import app
uvicorn.run(app)
```

### API 클라이언트 사용
```python
# 파이썬 코드에서
from api_client import STTClient

client = STTClient("http://localhost:8003")
```

### 서비스 직접 사용 (개발용)
```python
# Python 스크립트에서 서비스 직접 호출
from api_server.services.privacy_removal_service import PrivacyRemovalService

service = PrivacyRemovalService()
result = await service.remove_privacy_from_stt("텍스트")
```

---

## ✅ Why This Structure?

### 1. 명확한 진입점
```
✅ api_server.py (파일) = 진입점
✅ api_server/ (디렉토리) = 구현
```

### 2. 패키지 조직
```
✅ api_server.app = FastAPI 메인 앱
✅ api_server.services = 비즈니스 로직
✅ api_server.services.privacy_removal = Privacy Removal 기능
```

### 3. 모듈 재사용성
```
✅ api_server 패키지를 다른 프로젝트에서도 import 가능
✅ 서비스는 독립적으로 테스트 가능
```

### 4. Docker 호환성
```
✅ CMD ["python3", "api_server.py"]로 실행
✅ requirements.txt 관리 단순화
```

---

## 🚀 Running the Application

### Method 1: Direct Python
```bash
python3 api_server.py
# → Starts on http://localhost:8003
```

### Method 2: uvicorn
```bash
uvicorn api_server.app:app --host 0.0.0.0 --port 8003
```

### Method 3: Docker
```bash
docker run -p 8003:8003 stt-engine:latest
# → Runs api_server.py inside container
```

---

## 📚 Documentation Structure

**docs/ 폴더에 모든 문서가 있습니다:**
- [docs/PRIVACY_REMOVAL_GUIDE.md](PRIVACY_REMOVAL_GUIDE.md) ⭐ ← **Privacy Removal 종합 가이드**
- [docs/API_USAGE_GUIDE.md](API_USAGE_GUIDE.md) ← API 사용법
- [docs/QUICKSTART.md](QUICKSTART.md) ← 빠른 시작
- [docs/DEPLOYMENT_READY.md](DEPLOYMENT_READY.md) ← 배포 가이드

---

## 🔍 Quick Reference

| 파일/폴더 | 용도 |
|----------|------|
| `api_server.py` | ✅ 진입점 (실행) |
| `api_server/app.py` | FastAPI 메인 로직 |
| `api_server/services/` | 서비스 구현 |
| `api_client.py` | API 클라이언트 |
| `docs/` | 📚 모든 문서 |
| `requirements.txt` | Python 의존성 |
| `docker/` | Docker 설정 |

---

## ✨ Best Practices

### ✅ DO
```python
# ✅ 정확함
from api_server.app import app
from api_client import STTClient
from api_server.services.privacy_removal_service import PrivacyRemovalService
```

### ❌ DON'T
```python
# ❌ 피할 것
import api_server.py  # 파일 직접 import 안 함
from api_server import *  # 와일드카드 import 피함
```

---

## 📝 Notes

1. **api_server.py는 진입점만**: 실제 로직은 모두 api_server/ 패키지에 있음
2. **api_client.py는 독립적**: 서버 없이 독립적으로 실행/테스트 가능
3. **패키지 구조는 확장성을 고려**: 향후 다른 서비스 추가 용이
4. **문서는 docs/에 집중**: README.md는 상위 개요만

---

**Updated:** 2024
**Version:** 1.0
