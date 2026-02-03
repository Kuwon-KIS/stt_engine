# 🔧 Troubleshooting 가이드

**목적**: STT Engine 운영 중 발생하는 문제 해결  
**최종 업데이트**: 2026-02-03

---

## 📋 가이드 목록

### 1. [CONTAINER_FILE_UPDATES.md](./CONTAINER_FILE_UPDATES.md)
이미지 재빌드 없이 **Python 파일만 수정**하여 운영환경에서 테스트하기
- 빠른 핫픽스가 필요한 경우
- 새 이미지 빌드 전에 동작 검증하고 싶을 때
- 예: stt_engine.py 오류 수정

### 2. [IMAGE_RUN_ISSUES.md](./IMAGE_RUN_ISSUES.md)
Docker 이미지 실행 오류 원인 분석 및 해결책
- `docker run` 실패
- 컨테이너 즉시 종료
- 포트 충돌
- 메모리 부족

### 3. [PERFORMANCE_OPTIMIZATION.md](./PERFORMANCE_OPTIMIZATION.md)
음성 인식 성능 최적화 (향후 추가 예정)

---

## 🎯 문제별 빠른 진단

### 문제: `docker run` 명령이 실패한다
**진단**: [IMAGE_RUN_ISSUES.md](./IMAGE_RUN_ISSUES.md) → "Docker 실행 오류" 섹션 참고

### 문제: 컨테이너 시작 후 바로 종료된다
**진단**: 로그 확인
```bash
docker logs <container_id>
```
오류 메시지를 보고 [IMAGE_RUN_ISSUES.md](./IMAGE_RUN_ISSUES.md) 에서 검색

### 문제: Python 코드 오류를 빠르게 수정하고 싶다
**해결**: [CONTAINER_FILE_UPDATES.md](./CONTAINER_FILE_UPDATES.md) → "Method 1: docker cp 사용"

### 문제: 새 이미지 빌드 전에 변경사항을 테스트하고 싶다
**해결**: [CONTAINER_FILE_UPDATES.md](./CONTAINER_FILE_UPDATES.md) → "테스트 및 검증" 섹션

---

## 💡 선택 가이드

| 상황 | 추천 방법 | 소요시간 | 가이드 |
|------|---------|--------|------|
| Python 파일만 수정 후 테스트 | docker cp | ~5분 | [링크](./CONTAINER_FILE_UPDATES.md) |
| 이미지 실행 오류 발생 | 오류 로그 분석 | ~10분 | [링크](./IMAGE_RUN_ISSUES.md) |
| 최종 이미지 빌드 | 새 이미지 생성 | ~30분 | [SERVER_DEPLOYMENT_GUIDE.md](../SERVER_DEPLOYMENT_GUIDE.md) |

---

## 🚀 일반적인 워크플로우

```
1️⃣ 로컬에서 코드 수정
   ↓
2️⃣ 운영환경에서 빠르게 테스트 (docker cp 활용)
   ↓
3️⃣ 동작 검증 (curl, 헬스 체크)
   ↓
4️⃣ 문제 없으면 새 이미지 빌드
   ↓
5️⃣ 새 이미지로 배포
```

---

## 📝 다른 문제 보고

이 문서에 없는 문제가 발생하면:
1. 문제 설명 정리
2. 오류 메시지/로그 수집
3. 새 파일 생성 (예: `GPU_ISSUES.md`)
4. 이 INDEX.md에 추가

---

**각 가이드의 상세 내용은 해당 파일을 참고하세요.**
