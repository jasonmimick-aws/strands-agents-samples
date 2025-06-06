#!/bin/bash
set -e

# Check if Datadog API key is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <datadog-api-key> [datadog-site]"
  echo "Example: $0 your_datadog_api_key datadoghq.com"
  exit 1
fi

DATADOG_API_KEY=$1
DATADOG_SITE=${2:-datadoghq.com}

# Create a temporary directory
TMP_DIR=$(mktemp -d)
echo "Created temporary directory: $TMP_DIR"

# Copy the OTEL collector config to the temporary directory
cp ./otel-collector-config.yaml $TMP_DIR/
echo "Copied OTEL collector config to temporary directory"

# Deploy the CloudFormation stack
echo "Deploying ADOT Collector with Datadog exporter..."
aws cloudformation deploy \
  --template-file adot-collector-deployment.yaml \
  --stack-name adot-collector \
  --parameter-overrides \
    DatadogApiKey=$DATADOG_API_KEY \
    DatadogSite=$DATADOG_SITE \
  --capabilities CAPABILITY_IAM

# Wait for the EFS to be available
echo "Waiting for EFS to be available..."
sleep 30

# Get the EFS ID
EFS_ID=$(aws cloudformation describe-stack-resources \
  --stack-name adot-collector \
  --query "StackResources[?ResourceType=='AWS::EFS::FileSystem'].PhysicalResourceId" \
  --output text)

echo "EFS ID: $EFS_ID"

# Get the VPC ID
VPC_ID=$(aws cloudformation describe-stack-resources \
  --stack-name adot-collector \
  --query "StackResources[?ResourceType=='AWS::EC2::VPC'].PhysicalResourceId" \
  --output text)

echo "VPC ID: $VPC_ID"

# Get the subnet ID
SUBNET_ID=$(aws cloudformation describe-stack-resources \
  --stack-name adot-collector \
  --query "StackResources[?ResourceType=='AWS::EC2::Subnet'].PhysicalResourceId" \
  --output text)

echo "Subnet ID: $SUBNET_ID"

# Create a temporary CloudFormation template to create an EC2 instance to update the EFS
cat > $TMP_DIR/update-efs-config.yaml << EOF
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Temporary EC2 instance to update EFS configuration'

Parameters:
  EfsFileSystemId:
    Type: String
    Description: The ID of the EFS file system
  
  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: The VPC ID where the EFS mount target is located

  SubnetId:
    Type: AWS::EC2::Subnet::Id
    Description: The subnet ID where the EFS mount target is located
    
  DatadogApiKey:
    Type: String
    Description: Datadog API key
    
  DatadogSite:
    Type: String
    Description: Datadog site

Resources:
  InstanceSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for temporary EC2 instance
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 22
          ToPort: 22
          CidrIp: 0.0.0.0/0
          Description: SSH
        - IpProtocol: tcp
          FromPort: 2049
          ToPort: 2049
          CidrIp: 10.0.0.0/16
          Description: NFS for EFS mount

  InstanceRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
        - arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess

  InstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      Roles:
        - !Ref InstanceRole

  EC2Instance:
    Type: AWS::EC2::Instance
    Properties:
      InstanceType: t3.micro
      ImageId: ami-0c7217cdde317cfec  # Amazon Linux 2023
      SubnetId: !Ref SubnetId
      SecurityGroupIds:
        - !Ref InstanceSecurityGroup
      IamInstanceProfile: !Ref InstanceProfile
      UserData:
        Fn::Base64: !Sub |
          #!/bin/bash -xe
          yum update -y
          yum install -y amazon-efs-utils
          
          # Create mount directory
          mkdir -p /mnt/efs
          
          # Mount EFS
          mount -t efs \${EfsFileSystemId}:/ /mnt/efs
          
          # Create the configuration file
          cat > /mnt/efs/otel-collector-config.yaml << 'EOT'
$(cat ./otel-collector-config.yaml)
EOT
          
          # Set proper permissions
          chmod 644 /mnt/efs/otel-collector-config.yaml
          
          # Signal completion
          /opt/aws/bin/cfn-signal -e \$? --stack \${AWS::StackName} --resource EC2Instance --region \${AWS::Region}
      
      Tags:
        - Key: Name
          Value: EFS-Config-Updater

Outputs:
  InstanceId:
    Description: The ID of the EC2 instance
    Value: !Ref EC2Instance
EOF

# Deploy the temporary EC2 instance to update the EFS
echo "Deploying temporary EC2 instance to update EFS configuration..."
aws cloudformation deploy \
  --template-file $TMP_DIR/update-efs-config.yaml \
  --stack-name update-efs-config \
  --parameter-overrides \
    EfsFileSystemId=$EFS_ID \
    VpcId=$VPC_ID \
    SubnetId=$SUBNET_ID \
    DatadogApiKey=$DATADOG_API_KEY \
    DatadogSite=$DATADOG_SITE \
  --capabilities CAPABILITY_IAM

# Wait for the EC2 instance to complete
echo "Waiting for EC2 instance to update EFS configuration..."
aws cloudformation wait stack-create-complete --stack-name update-efs-config

# Delete the temporary EC2 instance
echo "Deleting temporary EC2 instance..."
aws cloudformation delete-stack --stack-name update-efs-config

# Wait for the stack to be deleted
echo "Waiting for temporary EC2 instance to be deleted..."
aws cloudformation wait stack-delete-complete --stack-name update-efs-config

# Restart the ADOT collector task
echo "Restarting ADOT collector task..."
CLUSTER_NAME="adot-collector-cluster"
SERVICE_NAME="adot-collector-service"
aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment

# Clean up temporary directory
echo "Cleaning up temporary directory..."
rm -rf $TMP_DIR

# Get the ADOT Collector endpoint
echo "Getting ADOT Collector endpoint..."
./get-adot-collector-endpoint.sh

echo "ADOT Collector deployed successfully with updated configuration!"
echo "You can now configure your application to send traces to this endpoint."
echo "Example configuration for Python OpenTelemetry:"
echo "export OTEL_EXPORTER_OTLP_ENDPOINT=http://<public-ip>:4318/v1/traces"
echo "export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf"
