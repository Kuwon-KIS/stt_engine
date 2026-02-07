# 🔧 Docker 모델 로드 오류 해결 가이드

**문제**: Docker 컨테이너에서 `Unable to open file 'model.bin'` 오류 발생  
**원인**: CTranslate2 변환이 완전하지 않거나 `config.json`이 손상됨  
**해결책**: EC2에서 모델 재다운로드 및 변환

---

## 📋 문제 분석

### 증상 1: config.json이 너무 작음 (2.2KB)
```
⚠️  config.json이 너무 작음: 2.2KB (손상 가능성)
```
- **원인**: CTranslate2 변환 중 config.json이 제대로 생성되지 않음
- **결과**: model.bin을 로드할 수 없음

### 증상 2: model.bin 파일을 열 수 없음
```
❌ faster-whisper 로드 실패: RuntimeError
   메시지: Unable to open file 'model.bin' in model '/app/models/openai_whisper-large-v3-turbo'
```
- **원인**: config.json 손상으로 인해 model.bin을 인식하지 못함
- **또는**: model.bin이 손상되었거나 불완전한 상태

---

## 🚀 EC2에서 해결하기

### Step 1: SSH로 EC2 접속
```bash
ssh -i your-key.pem ec2-user@your-ec2-ip

# 또는 EC2 인스턴스에서 직접
cd /home/ec2-user/stt_engine
```

### Step 2: 기존 모델 백업 및 삭제
```bash
# 백업 (선택사항)
tar czf models_backup_$(date +%Y%m%d).tar.gz models/ 2>/dev/null || true

# 모델 완전 삭제
rm -rf models/openai_whisper-large-v3-turbo
rm -rf build/output/*

# 확인
ls -la models/
```

### Step 3: 모델 재다운로드 (새로 시작)
```bash
# Python 3 사용 확인
python3 --version

# 모델 다운로드 + CTranslate2 변환 + 검증
python3 download_model_hf.py 2>&1 | tee model_rebuild.log
```

**예상 소요 시간**: 30~45분

### Step 4: 모델 파일 검증
```bash
echo "=== 모델 파일 검증 ==="

# 1. ctranslate2_model 폴더 확인
ls -lh models/openai_whisper-large-v3-turbo/ctranslate2_model/

# 2. 파일 크기 확인 (정상 범위)
du -sh models/openai_whisper-large-v3-turbo/ctranslate2_model/model.bin
# 예상: 1.5GB 정도

# 3. config.json 크기 확인 (정상: 2KB 이상)
ls -lh models/openai_whisper-large-v3-turbo/ctranslate2_model/config.json
# 예상: 2.2KB 이상

# 4. MD5 검증 (생성된 tar.gz의 무결성)
cat build/output/*.md5
# 압축 파일과 md5 비교
```

**정상 상태**:
```
ctranslate2_model/:
  -rw-r--r--  1 ec2-user  ec2-user 1.5G  model.bin        ✅
  -rw-r--r--  1 ec2-user  ec2-user 2.2K  config.json      ✅
  -rw-r--r--  1 ec2-user  ec2-user 1.0M  vocabulary.json  ✅
```

### Step 5: Docker 이미지 재빌드
```bash
# 이전 이미지 제거 (선택사항)
docker rmi stt-engine:cuda129-rhel89-v1.4

# 새 이미지 빌드 (최신 모델 포함)
bash scripts/build-server-image.sh

# 이미지 확인
docker images | grep stt-engine
```

**소요 시간**: 30분

### Step 6: 컨테이너 재실행
```bash
# 이전 컨테이너 제거
docker stop stt-engine 2>/dev/null || true
docker rm stt-engine 2>/dev/null || true

# 새 컨테이너 실행
docker run -d \
  --name stt-engine \
  -p 8003:8003 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/logs:/app/logs \
  -e CUDA_VISIBLE_DEVICES=0 \
  stt-engine:cuda129-rhel89-v1.4

# 실행 확인
docker ps | grep stt-engine
```

### Step 7: 로그 확인
```bash
# 실시간 로그 보기
docker logs -f stt-engine

# 특정 라인 수만 보기
docker logs --tail 50 stt-engine

# 모든 로그 저장
docker logs stt-engine > stt_engine.log 2>&1
cat stt_engine.log | grep -E "✅|❌|⚠️|로드" | head -20
```

**정상 로그**:
```
✅ STT 모델 로드 완료 (Device: cpu, Backend: faster-whisper)
```

**오류 로그**:
```
❌ 모델 로드 실패: RuntimeError
❌ 모델 로드 실패: 모델 로드 실패: 두 백엔드 모두 실패
```

### Step 8: 헬스 체크
```bash
# API 헬스 체크
curl -s http://localhost:8003/health | python3 -m json.tool

# 예상 응답
{
  "status": "ok",
  "version": "1.0.0",
  "backend": "faster-whisper"
}
```

---

## 🔍 고급 진단

### 컨테이너 내부에서 모델 확인
```bash
# 컨테이너 내부 접속
docker exec -it stt-engine bash

# 내부에서 실행
ls -lh /app/models/openai_whisper-large-v3-turbo/ctranslate2_model/
file /app/models/openai_whisper-large-v3-turbo/ctranslate2_model/config.json

# Python에서 직접 테스트
python3 << 'EOF'
from faster_whisper import WhisperModel

model = WhisperModel(
    "/app/models/openai_whisper-large-v3-turbo/ctranslate2_model",
    device="cpu",
    compute_type="float32"
)
print("✅ 모델 로드 성공!")
EOF

# 컨테이너 종료
exit
```

### 마운트 경로 확인
```bash
# 컨테이너의 마운트 확인
docker inspect stt-engine | grep -A 10 "Mounts"

# 또는
docker exec stt-engine df -h | grep models
```

### 권한 문제 확인
```bash
# EC2의 모델 권한
ls -la models/openai_whisper-large-v3-turbo/ctranslate2_model/

# 컨테이너 내부의 권한
docker exec stt-engine ls -la /app/models/openai_whisper-large-v3-turbo/ctranslate2_model/

# 사용자 확인
docker exec stt-engine id
# 예상: uid=2000(stt-user) gid=2000(stt-user)
```

---

## ⚠️ 일반적인 문제들

### 문제 1: 모델 다운로드 시 OOM (Out of Memory)
```bash
# 원인: EC2 인스턴스 메모리 부족
# 해결책: 이미지에서 자동으로 로드 테스트 스킵

# 확인
tail -100 model_rebuild.log | grep -E "⚠️|OOM|메모리"
```

### 문제 2: 모델 변환 실패
```bash
# 원인: CTranslate2 변환 중 오류
# 로그 확인
tail -100 model_rebuild.log | grep -E "❌|변환|CTranslate2"

# 수동 변환 시도
python3 << 'EOF'
from ctranslate2.converters import TransformersConverter

converter = TransformersConverter("openai/whisper-large-v3-turbo")
converter.convert("models/openai_whisper-large-v3-turbo/ctranslate2_model", force=True)
EOF
```

### 문제 3: 디스크 부족
```bash
# 여유 공간 확인
df -h

# 임시 파일 정리
rm -rf ~/.cache/huggingface/hub/*
rm -rf /tmp/*
```

---

## 💾 배포 전 체크리스트

- [ ] 모델 파일 존재: `models/openai_whisper-large-v3-turbo/ctranslate2_model/`
- [ ] config.json 크기: 2.2KB 이상
- [ ] model.bin 크기: 1.5GB 정도
- [ ] vocabulary.json 존재
- [ ] Docker 이미지 빌드 성공
- [ ] 컨테이너 실행 성공
- [ ] 헬스 체크 통과
- [ ] 로그에서 "✅ STT 모델 로드 완료" 확인

---

## 📝 결과 저장

재빌드 완료 후:

```bash
# 결과 기록
echo "=== 모델 재빌드 완료 ===" >> rebuild_summary.txt
date >> rebuild_summary.txt
ls -lh models/openai_whisper-large-v3-turbo/ctranslate2_model/ >> rebuild_summary.txt
docker images | grep stt-engine >> rebuild_summary.txt

# 로그 저장
docker logs stt-engine > stt_engine_final.log
```

---

**작성일**: 2026년 2월 7일  
**상태**: 최신 버전 기준  
**다음**: 모델 재빌드 후 헬스 체크 및 API 테스트
