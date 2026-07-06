#!/bin/bash
# ==============================================================================
# [역할: 로컬 머신]
# ==============================================================================
ENGINE_VERSION=${1:-latest}
WEB_VERSION=${2:-latest}
BUCKET_NAME="stt-engine-build-artifacts-037129617559-ap-northeast-2-an"

echo "🚀 [로컬] 최신 Amazon Linux 2023 AMI 조회 중..."
# 하드코딩된 AMI_ID 대신 동적으로 최신 ID를 가져옵니다.
AMI_ID=$(aws ssm get-parameters \
    --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
    --query 'Parameters[0].Value' \
    --output text)
echo "💡 사용될 AMI: $AMI_ID"

# 1. 인스턴스 내부에서 실행할 스크립트 (AL2023 전용으로 완전 최적화)
cat <<EOF > user_data.sh
#!/bin/bash
# ==============================================================================
# [역할: EC2 인스턴스 내부 - 부팅 시 자동 실행]
# ==============================================================================
exec > /var/log/user-data.log 2>&1
export HOME=/root

echo "--- 1. 필수 패키지 설치 (AL2023) ---"
dnf update -y
# AL2023은 docker가 기본 저장소에 있어 바로 설치됩니다.
dnf install -y docker git pigz tar curl

echo "--- 2. Docker 서비스 시작 ---"
systemctl enable --now docker
usermod -aG docker ec2-user

echo "--- 3. 빌드 작업 실행 (ec2-user 권한) ---"
su - ec2-user -c '
    echo "--- 소스 코드 가져오기 ---"
    # 🚨 여기에 실제 Git 주소를 입력하세요! (기존 폴더가 없으므로 clone 필수)
    git clone https://github.com/여기에/주소를_넣어주세요.git /home/ec2-user/stt_engine || exit 1
    
    cd /home/ec2-user/stt_engine || exit 1
    
    echo "--- 엔진 및 웹 빌드 시작 ---"
    # 완전히 깨끗한 새 환경이므로, 빌드 스크립트 내부의 read 프롬프트(기존 이미지 삭제 여부 확인)가 
    # 아예 트리거되지 않고 무사히 통과됩니다.
    bash scripts/build-ec2-engine-image.sh $ENGINE_VERSION || exit 1
    bash scripts/build-ec2-web-ui-image.sh $WEB_VERSION || exit 1

    echo "--- S3 업로드 ---"
    aws s3 cp build/output/stt-engine-cuda129-rhel89-$ENGINE_VERSION.tar.gz s3://$BUCKET_NAME/ || exit 1
    aws s3 cp build/output/stt-web-ui-cuda129-rhel89-$WEB_VERSION.tar.gz s3://$BUCKET_NAME/ || exit 1
'

echo "[인스턴스] 모든 작업 완료 (수동 종료 대기 중)"
EOF

# 2. EC2 인스턴스 생성
echo "🚀 [로컬] EC2 인스턴스 생성 중..."
# --block-device-mappings 옵션을 추가하여 빌드 공간 부족을 막기 위해 120GB gp3 볼륨을 강제 할당합니다.
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type t3.xlarge \
    --iam-instance-profile Name="Build_S3_Role" \
    --instance-market-options '{"MarketType": "spot", "SpotOptions": {"MaxPrice": "0.1"}}' \
    --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":120,"VolumeType":"gp3"}}]' \
    --user-data file://user_data.sh \
    --query 'Instances[0].InstanceId' --output text)

echo "✅ [로컬] 인스턴스 생성 완료: $INSTANCE_ID"

# 3. 대기 안내
echo "⌛ [로컬] 인스턴스 부팅 대기 중..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID
echo "💡 인스턴스가 실행되었습니다."
echo "   SSH로 접속하여 'tail -f /var/log/user-data.log' 명령어로 실시간 로그를 확인하세요."
echo "   빌드가 성공적으로 끝나고 S3에 파일이 올라가면 수동으로 인스턴스를 종료(Terminate)하시면 됩니다."