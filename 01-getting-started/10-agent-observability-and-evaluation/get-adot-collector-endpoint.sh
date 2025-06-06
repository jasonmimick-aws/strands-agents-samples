#!/bin/bash
# Script to get the public IP address of the ADOT collector running on Fargate
# This script retrieves the public endpoint information for the ADOT collector service

set -e

echo "Retrieving ADOT Collector endpoint information..."

# Get the cluster name and service name
CLUSTER_NAME="adot-collector-cluster"
SERVICE_NAME="adot-collector-service"

# Get the task ARN
echo "Finding task ARN for service $SERVICE_NAME in cluster $CLUSTER_NAME..."
TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --query 'taskArns[0]' --output text)

if [ "$TASK_ARN" == "None" ] || [ -z "$TASK_ARN" ]; then
  echo "Error: No running tasks found for the ADOT collector service."
  exit 1
fi

echo "Found task: $TASK_ARN"

# Get the ENI ID
echo "Retrieving network interface ID..."
ENI_ID=$(aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)

if [ -z "$ENI_ID" ]; then
  echo "Error: Could not retrieve network interface ID."
  exit 1
fi

echo "Network interface ID: $ENI_ID"

# Get the public IP
echo "Retrieving public IP address..."
PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

if [ -z "$PUBLIC_IP" ] || [ "$PUBLIC_IP" == "None" ]; then
  echo "Error: No public IP address found for the ADOT collector."
  exit 1
fi

echo ""
echo "===== ADOT Collector Endpoints ====="
echo "Public IP: $PUBLIC_IP"
echo "OTLP HTTP Endpoint: http://$PUBLIC_IP:4318/v1/traces"
echo "OTLP gRPC Endpoint: $PUBLIC_IP:4317"
echo "Prometheus Metrics: http://$PUBLIC_IP:8888/metrics"
echo "Health Check: http://$PUBLIC_IP:13133"
echo "=================================="
