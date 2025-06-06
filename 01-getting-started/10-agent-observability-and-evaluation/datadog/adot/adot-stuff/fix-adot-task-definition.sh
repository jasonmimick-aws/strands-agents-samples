#!/bin/bash
set -e

# Register a new task definition with updated configuration
echo "Creating new task definition with fixed configuration path..."

# Create a temporary JSON file for the new task definition
cat > /tmp/adot-task-definition.json << EOF
{
  "family": "adot-collector",
  "taskRoleArn": "arn:aws:iam::347830095179:role/adot-collector-ADOTCollectorRole-jsxjPYx1K2Fb",
  "executionRoleArn": "arn:aws:iam::347830095179:role/adot-collector-ADOTCollectorRole-jsxjPYx1K2Fb",
  "networkMode": "awsvpc",
  "containerDefinitions": [
    {
      "name": "adot-collector",
      "image": "amazon/aws-otel-collector:latest",
      "essential": true,
      "command": [
        "--config=/etc/otel-collector-config/config.yaml"
      ],
      "environment": [
        {
          "name": "DD_SITE",
          "value": "datadoghq.com"
        },
        {
          "name": "DD_API_KEY",
          "value": "74db26c4836f1702565ec78647512465"
        }
      ],
      "mountPoints": [
        {
          "sourceVolume": "otel-collector-config",
          "containerPath": "/etc/otel-collector-config",
          "readOnly": true
        }
      ],
      "portMappings": [
        {
          "containerPort": 13133,
          "hostPort": 13133,
          "protocol": "tcp"
        },
        {
          "containerPort": 4317,
          "hostPort": 4317,
          "protocol": "tcp"
        },
        {
          "containerPort": 8888,
          "hostPort": 8888,
          "protocol": "tcp"
        },
        {
          "containerPort": 4318,
          "hostPort": 4318,
          "protocol": "tcp"
        },
        {
          "containerPort": 55680,
          "hostPort": 55680,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/adot-collector",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "adot-collector"
        }
      }
    }
  ],
  "volumes": [
    {
      "name": "otel-collector-config",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-0cb3fa10321118526",
        "rootDirectory": "/",
        "transitEncryption": "ENABLED"
      }
    }
  ],
  "requiresCompatibilities": [
    "FARGATE"
  ],
  "cpu": "512",
  "memory": "1024"
}
EOF

# Register the new task definition
echo "Registering new task definition..."
NEW_TASK_DEF=$(aws ecs register-task-definition --cli-input-json file:///tmp/adot-task-definition.json)
NEW_REVISION=$(echo $NEW_TASK_DEF | jq -r '.taskDefinition.revision')
echo "Created new task definition revision: $NEW_REVISION"

# Update the EFS configuration
echo "Updating EFS configuration..."

# Create a temporary CloudFormation template for the EC2 instance
cat > /tmp/update-efs-config.yaml << EOF
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Temporary EC2 instance to update EFS configuration'

Parameters:
  EfsFileSystemId:
    Type: String
    Default: fs-0cb3fa10321118526
    Description: The ID of the EFS file system
  
  VpcId:
    Type: String
    Default: vpc-08699bf0189a11c6a
    Description: The VPC ID where the EFS mount target is located

  SubnetId:
    Type: String
    Default: subnet-0759aad269811f421
    Description: The subnet ID where the EFS mount target is located

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
          
          # Create directory for config file
          mkdir -p /mnt/efs/config
          
          # Create the configuration file
          cat > /mnt/efs/config/config.yaml << 'EOT'
$(cat ./otel-collector-config.yaml)
EOT
          
          # Set proper permissions
          chmod 644 /mnt/efs/config/config.yaml
          
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
  --template-file /tmp/update-efs-config.yaml \
  --stack-name update-efs-config \
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

# Update the service to use the new task definition
echo "Updating ADOT collector service to use the new task definition..."
aws ecs update-service \
  --cluster adot-collector-cluster \
  --service adot-collector-service \
  --task-definition adot-collector:$NEW_REVISION \
  --force-new-deployment

echo "ADOT collector service updated successfully!"
echo "The service is now being deployed with the fixed configuration."
echo "It may take a few minutes for the new task to start running."

# Clean up temporary files
rm -f /tmp/adot-task-definition.json /tmp/update-efs-config.yaml

echo "Waiting for the new task to start..."
sleep 30

# Run the get-adot-collector-endpoint.sh script to get the new endpoint
echo "Getting the new ADOT collector endpoint..."
./get-adot-collector-endpoint.sh
