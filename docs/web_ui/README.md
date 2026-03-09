# Web UI 문서

Web UI (사용자 인터페이스) 관련 아키텍처, API 흐름, 배포 가이드 문서입니다.

## 📚 주요 문서

### 1. [Web UI → API 호출 흐름 분석](./WEB_UI_API_FLOW.md) ⭐ 신규

**최우선 읽을 문서**

Web UI의 프론트엔드에서 STT API 백엔드로의 전체 데이터 흐름을 분석합니다.

- 로그인 → 업로드 → 분석 메인 루트 설명
- 각 단계별 API 호출 방식 (FormData, JSON)
- FormData 파라미터 상세 정의
- Docker 환경에서의 경로 변환
- 환경변수 우선순위 흐름
- 현재 상태 & 이슈 식별
- 리팩토링 계획

**대상**: 개발자, 아키텍처 검토자

**포함 내용**:
```
1️⃣ 로그인 (/api/auth/login)
2️⃣ 파일 업로드 (/api/files/upload)
3️⃣ 분석 시작 (/api/analysis/start)
4️⃣ 백그라운드 처리
5️⃣ STT API 호출 (핵심!)
6️⃣ 진행률 조회 (/api/analysis/progress/{job_id})
7️⃣ 결과 조회 (/api/analysis/results/{job_id})
```

---

## 🔗 관련 문서

### API 문서
- [docs/api/README.md](../api/README.md) - API 문서 중앙 허브
- [docs/api/ENVIRONMENT_VARIABLES.md](../api/ENVIRONMENT_VARIABLES.md) - 환경변수 완전 가이드
- [docs/api/API_REFACTORING_SUMMARY.md](../api/API_REFACTORING_SUMMARY.md) - API 구조

### 아키텍처 문서
- [docs/architecture/](../architecture/) - 시스템 아키텍처

### 배포 문서
- [docs/deployment/](../deployment/) - Docker, K8s 배포 가이드

---

## 📊 데이터 흐름 요약

### 간단 버전
```
로그인 → 파일 업로드 → 분석 시작 → [백그라운드] → STT API 호출 → 결과 저장
```

### 상세 버전
```
브라우저
  ├─ Login: POST /api/auth/login {"emp_id": "000123"}
  │
  ├─ Upload: POST /api/files/upload (파일 바이너리)
  │  └─ 저장위치: /app/web_ui/data/uploads/{emp_id}/{folder_date}/{file}
  │
  └─ Analysis: POST /api/analysis/start {folder_path, ...}
     └─ 응답: {job_id} (202 Accepted)
     
[백그라운드 처리]
  ├─ 파일 목록 조회
  ├─ for each file:
  │  └─ POST http://stt-api:8003/transcribe
  │     ├─ file_path: "/app/web_ui/data/uploads/..."
  │     ├─ privacy_removal: "true"
  │     ├─ classification: "true"
  │     └─ element_detection: "true"
  │        └─ STT 처리 + LLM 분석
  │
  └─ DB에 결과 저장
  
프론트엔드 - 진행상황 폴링
  ├─ GET /api/analysis/progress/{job_id}
  └─ GET /api/analysis/results/{job_id}
```

---

## 🔑 핵심 개념

### FormData vs JSON

| 단계 | 엔드포인트 | 형식 | 용도 |
|------|----------|------|------|
| 로그인 | `/api/auth/login` | JSON | 사번 인증 |
| **업로드** | `/api/files/upload` | **FormData** | 파일 바이너리 전송 |
| 분석시작 | `/api/analysis/start` | JSON | 분석 옵션 |
| **STT 호출** | `/transcribe` | **FormData** | 파일 경로 + 옵션 |

### 파일 경로 vs 파일 바이너리

- **Upload**: 브라우저 → Web UI 서버
  - 파일 바이너리를 전송
  - 서버에서 디스크에 저장
  
- **STT 호출**: Web UI 서버 → API 서버
  - 파일 바이너리 대신 **경로 String을 전달**
  - API 서버에서 디스크에서 파일 읽음
  - ✅ 네트워크 대역폭 절약

---

## ⚠️ 현재 이슈 & 개선 필요

### 식별된 문제들

1. **반복되는 환경변수 로직** (app.py 라인 415-444)
   - Privacy, Classification, Element Detection 각각에서 모델명 처리 반복
   - 우선순위: 요청 파라미터 > 작업별 환경변수 > 공통 환경변수 > 기본값
   
2. **FormData 문자열 변환 반복** (라인 461, 468, 475)
   - Boolean String ("true", "false") 변환 로직 중복
   - `.lower() in ['true', '1', 'yes', 'on']` 패턴 반복

3. **API URL 중복** (라인 483)
   - EXTERNAL_API_URL과 AGENT_URL (레거시) 우선순위 처리

### 리팩토링 계획

📄 [WEB_UI_API_FLOW.md](./WEB_UI_API_FLOW.md#-리팩토링-계획) 참고

---

## 🚀 빠른 시작

### 로컬 개발

```bash
# 1. Web UI 시작
cd web_ui
python main.py

# 2. STT API 시작 (별도 터미널)
python api_server/app.py

# 3. 브라우저에서 접근
open http://localhost:8100
```

### Docker 환경

```bash
# docker-compose.yml 참고
docker-compose up

# Web UI: http://localhost:8100
# API: http://localhost:8003
```

---

## 📝 문서 작성 시 참고사항

Web UI 관련 문서를 작성할 때:

1. **경로 명시**: 절대 경로 또는 상대 경로 명확히
   - Web UI 내부: `/app/web_ui/data/uploads/...`
   - API 서버: `/app/web_ui/data/uploads/...` (마운트된 같은 경로)

2. **FormData vs JSON 구분**: 각 API의 Content-Type 명확히

3. **환경변수 우선순위**: 항상 계층적 우선순위 표기

4. **Docker 경로 변환**: 컨테이너 간 경로 매핑 설명

---

**작성자**: GitHub Copilot  
**마지막 수정**: 2026년 3월 9일  
**상태**: ✅ 완료
