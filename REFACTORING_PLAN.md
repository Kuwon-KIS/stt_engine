# deployment_package 스크립트 정리 가이드

## 현황
deployment_package에 여러 다운로드 스크립트가 있어서 혼란스러움.

## 필요한 스크립트
1. **deploy.sh** - 메인 배포 스크립트 (유지)
2. **setup_offline.sh** - 오프라인 설치 (유지)
3. **run_all.sh** - 서비스 실행 (유지)
4. **post_deploy_setup.sh** - 사후 설정 (유지)

## 불필요한 스크립트 (삭제 대상)
- download_wheels.sh - 로컬에서 사용 (루트의 scripts/로 이동)
- download-wheels.sh - 분할 압축 (로컬에서 사용)
- download_wheels_macos.sh - macOS 특화 (로컬에서 사용)
- download_wheels_3.11.sh - Python 3.11 특화 (로컬에서 사용)
- download_pytorch.sh - PyTorch 전용 (로컬에서 사용)
- download_pytorch_manual.sh - 수동 다운로드 (로컬에서 사용)
- download_all_wheels.sh - 모든 휠 다운로드 (로컬에서 사용)
- download-wheels-docker.sh - Docker 기반 (로컬에서 사용)
- download-wheels-docker-rhel89.sh - RHEL 특화 (로컬에서 사용)
- verify-wheels.sh - 검증용 (필요시 유지)

## 정리 전략
1. deployment_package에는 배포에 필수적인 스크립트만 유지
2. 로컬 다운로드 스크립트는 scripts/로 이동
3. 검증 스크립트는 별도 관리
