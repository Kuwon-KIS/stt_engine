# ✅ EC2 빌드 체크리스트

**작성일**: 2026년 2월 7일  
**대상**: EC2 RHEL 8.9 인스턴스

## 📋 사전 준비

- [ ] EC2 인스턴스 생성 (t3.xlarge 이상, RHEL 8.9)
- [ ] 스토리지 확보 (100GB 이상)
- [ ] SSH 접속 확인
- [ ] Docker 설치 확인 (`docker --version`)
- [ ] Git 설치 확인 (`git --version`)
- [ ] 인터넷 연결 확인 (`ping 8.8.8.8`)

## 🚀 EC2 빌드 순서

### 1단계: Repository 준비
- [ ] `cd /home/ec2-user` (또는 작업 디렉토리)
- [ ] `git clone https://github.com/Kuwon-KIS/stt_engine.git`
- [ ] `cd stt_engine`
- [ ] 파일 확인: `ls scripts/build-*.sh`

### 2단계: 모델 다운로드 (약 30분)
```bash
python3 download_model_hf.py
```
- [ ] 모델 다운로드 완료
- [ ] CTranslate2 변환 완료
- [ ] 압축 파일 생성 완료
- [ ] 결과 확인:
  ```bash
  ls -lh models/openai_whisper-large-v3-turbo/
  ls -lh build/output/*.tar.gz
  ls -lh build/output/*.md5
  ```

**체크항목**:
- [ ] `models/openai_whisper-large-v3-turbo/ctranslate2_model/model.bin` 존재
- [ ] `build/output/whisper-large-v3-turbo_models_*.tar.gz` 존재 (2.8GB)
- [ ] `build/output/whisper-large-v3-turbo_models_*.tar.gz.md5` 존재

### 3단계: Docker 이미지 빌드 (약 30분)
```bash
bash scripts/build-server-image.sh
```
- [ ] Docker 빌드 시작
- [ ] 패키지 설치 진행
- [ ] PyTorch/CUDA 설치 진행
- [ ] 이미지 저장 시작
- [ ] 최종 완료

**체크항목**:
- [ ] `docker images | grep stt-engine` 에서 이미지 확인
- [ ] 이미지 크기: 약 7.3GB
- [ ] `build/output/stt-engine-cuda129-rhel89-v*.tar` 파일 생성

### 4단계: 컨테이너 실행 테스트
```bash
docker run -d \
  --name stt-engine-test \
  -p 8003:8003 \
  -v $(pwd)/models:/app/models \
  stt-engine:cuda129-rhel89-v1.4
```
- [ ] 컨테이너 시작
- [ ] 포트 바인딩 확인

### 5단계: 헬스 체크
```bash
curl http://localhost:8003/health
```
- [ ] HTTP 200 응답
- [ ] JSON 응답 확인 (예: `{"status":"healthy"}`)

### 6단계: 로그 확인
```bash
docker logs stt-engine-test
```
- [ ] 에러 메시지 없음
- [ ] API 시작 메시지 확인

### 7단계: 정리
```bash
docker stop stt-engine-test
docker rm stt-engine-test
```
- [ ] 컨테이너 정지
- [ ] 컨테이너 삭제

## 🔍 필수 파일 위치 확인

```bash
# 모델 파일
ls -lh models/openai_whisper-large-v3-turbo/ctranslate2_model/model.bin

# Docker 파일
ls -l docker/Dockerfile.engine.rhel89

# 빌드 스크립트
ls -l scripts/build-server-image.sh
ls -l scripts/build-server-models.sh

# Python 스크립트
ls -l download_model_hf.py
ls -l main.py
ls -l api_server.py
ls -l stt_engine.py
```

## ⚠️ 문제 발생 시

### 모델 다운로드 실패
```bash
# 네트워크 확인
ping 8.8.8.8

# 디스크 공간 확인
df -h

# 로그 확인
tail -100 /tmp/model_prep.log
```

### Docker 빌드 실패
```bash
# Docker 상태 확인
systemctl status docker

# 디스크 공간 확인 (7GB 필요)
df -h

# 빌드 로그 확인
cat /tmp/build-image-*.log | tail -100
```

### 컨테이너 실행 실패
```bash
# 포트 충돌 확인
netstat -tlnp | grep 8003

# Docker 이미지 확인
docker images | grep stt-engine

# 모델 경로 확인
ls -lh models/
```

## 📊 리소스 사용량 확인

```bash
# 디스크 사용량
du -sh .
du -sh models/
du -sh build/

# 메모리 사용량
free -h

# Docker 이미지 크기
docker images stt-engine --format "table {{.Size}}"
```

## 📚 참고 문서

- [docs/deployment/EC2_BUILD_GUIDE.md](EC2_BUILD_GUIDE.md) - 상세 가이드
- [docs/deployment/AWS_BUILD_GUIDE.md](AWS_BUILD_GUIDE.md) - AWS 가이드
- [QUICKSTART.md](../../QUICKSTART.md) - 빠른 시작

## ✨ 성공 기준

- ✅ 모델 다운로드 완료 (CTranslate2 변환)
- ✅ Docker 이미지 빌드 완료
- ✅ 컨테이너 실행 성공
- ✅ /health 엔드포인트 응답 200 OK
- ✅ 로그에 에러 없음

## 📝 작업 완료 시

```bash
# 최종 확인
docker images | grep stt-engine
ls -lh build/output/

# Git 상태 확인 (선택사항)
git status
git log --oneline -5
```

---

**작성일**: 2026년 2월 7일  
**상태**: 최신 버전 기준 ✅  
**다음 단계**: 운영 배포 준비
