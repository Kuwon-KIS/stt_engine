# Docker 다중 컨테이너 환경에서 모니터링 설치

## 🔍 운영 서버 환경

운영 서버에 두 개의 Docker 컨테이너가 실행 중인 경우:

```bash
$ docker ps
CONTAINER ID   NAMES           STATUS
a1b2c3d4e5f6   stt-web-ui      Up 2 hours
x9y8z7w6v5u4   stt-api         Up 2 hours
```

---

## 🎯 어느 컨테이너에 설치할 것인가?

### stt-web-ui (웹 UI 서버) - **권장**

**역할:**
- FastAPI 웹 애플리케이션
- 파일 업로드, 분석 결과 조회
- 데이터베이스 쿼리

**성능 모니터링이 필요:** ✅ **YES**

**설치 명령:**
```bash
bash setup_monitoring_minimal.sh
```

또는 명시적으로:
```bash
CONTAINER=stt-web-ui bash setup_monitoring_minimal.sh
```

---

### stt-api (API 서버) - 선택사항

**역할:**
- 외부 API 제공
- 분석 요청 처리

**성능 모니터링이 필요:**
- API 성능 분석이 필요하면 ✅ **YES**
- 웹 UI만 모니터링 필요하면 ❌ **NO**

**설치 명령:**
```bash
CONTAINER=stt-api bash setup_monitoring_minimal.sh
```

---

## 📋 설치 절차

### 1️⃣ 첫 번째: stt-web-ui 설치 (필수)

```bash
# 파일 복사 후 자동으로 stt-web-ui를 선택
bash setup_monitoring_minimal.sh
```

**확인:**
```bash
docker exec stt-web-ui python /app/quick_diagnostic.py
```

### 2️⃣ 두 번째: stt-api 설치 (선택)

```bash
# stt-api에도 설치하려면
CONTAINER=stt-api bash setup_monitoring_minimal.sh
```

**확인:**
```bash
docker exec stt-api python /app/quick_diagnostic.py
```

---

## 💡 각 컨테이너별 모니터링 항목

### stt-web-ui 모니터링

```
✅ 데이터베이스 쿼리 성능
✅ FastAPI 엔드포인트 응답 시간
✅ 파일 업로드 처리 성능
✅ 분석 결과 조회 성능
```

**명령어:**
```bash
# 진단
docker exec stt-web-ui python /app/quick_diagnostic.py

# 상세 테스트
docker exec stt-web-ui python /app/run_performance_test.py

# 로그 확인
docker exec stt-web-ui tail -50 /app/logs/performance.log
```

---

### stt-api 모니터링 (선택)

```
✅ API 엔드포인트 성능
✅ 외부 요청 처리 시간
✅ 응답 직렬화 성능
```

**명령어:**
```bash
# 진단
docker exec stt-api python /app/quick_diagnostic.py

# 로그 확인
docker exec stt-api tail -50 /app/logs/performance.log
```

---

## 🚀 설치 스크립트 동작

### 자동 선택 (권장)

```bash
bash setup_monitoring_minimal.sh
```

스크립트가 자동으로:
1. stt-web-ui 컨테이너 검색
2. 찾으면 설치
3. 없으면 사용 가능한 컨테이너 목록 표시

### 명시적 선택

```bash
CONTAINER=stt-web-ui bash setup_monitoring_minimal.sh
CONTAINER=stt-api bash setup_monitoring_minimal.sh
CONTAINER=custom-name bash setup_monitoring_minimal.sh
```

---

## ✅ 확인 체크리스트

```bash
# 1. stt-web-ui 모니터링 활성화 확인
docker exec stt-web-ui python /app/quick_diagnostic.py
# 결과: ✅ GOOD, ⚠️ FAIR, ❌ SLOW

# 2. 로그 파일 생성 확인
docker exec stt-web-ui ls -la /app/logs/
# 결과: performance.log 파일 존재 여부

# 3. 성능 로그 내용 확인
docker exec stt-web-ui tail -20 /app/logs/performance.log
# 결과: SQL Query, API Response 로그 출력

# 4. (선택) stt-api에도 설치했다면
docker exec stt-api python /app/quick_diagnostic.py
```

---

## 📝 주의사항

### stt-web-ui에만 설치하면 충분한 경우

```
✅ 웹 UI 성능만 분석하고 싶을 때
✅ API는 별도로 모니터링하고 있을 때
✅ 대부분의 병목이 웹 UI에 있을 때
```

### 둘 다 설치해야 하는 경우

```
✅ API 성능도 함께 분석해야 할 때
✅ 전체 시스템 성능 대시보드를 만들 때
✅ 마이크로서비스 아키텍처로 분석할 때
```

---

## 🔧 문제 해결

### 컨테이너를 찾을 수 없을 때

```bash
# 실행 중인 모든 컨테이너 확인
docker ps

# 컨테이너 이름 확인 후
CONTAINER=<정확한_이름> bash setup_monitoring_minimal.sh
```

### 특정 컨테이너만 모니터링하고 싶을 때

```bash
# 명시적으로 지정
CONTAINER=stt-web-ui bash setup_monitoring_minimal.sh

# 또는
CONTAINER=stt-api bash setup_monitoring_minimal.sh
```

### 두 컨테이너 모두 설치

```bash
# 첫 번째
bash setup_monitoring_minimal.sh

# 두 번째
CONTAINER=stt-api bash setup_monitoring_minimal.sh
```

---

## 📊 권장 설치 순서

1. **stt-web-ui** ← 항상 필요
2. **stt-api** ← 필요하면 추가

```bash
# 스크립트 1회 실행
bash setup_monitoring_minimal.sh

# 필요시 2회 실행
CONTAINER=stt-api bash setup_monitoring_minimal.sh
```

---

**준비 완료! 이제 각 컨테이너의 성능을 독립적으로 모니터링할 수 있습니다.** ✅
