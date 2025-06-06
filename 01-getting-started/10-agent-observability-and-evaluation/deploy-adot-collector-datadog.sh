#!/bin/bash
set -e

# Check if Datadog API key is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <datadog-api-key> [datadog-site]"
  echo "Example: $0 your_datadog_api_key datadoghq.com"
  exit 1
fi

STACK_NAME="adot-collector
DATADOG_API_KEY=$1
DATADOG_SITE=${2:-datadoghq.com}

# Delete the existing stack if it exists
echo "Checking if existing stack needs to be deleted..."
if aws cloudformation describe-stacks --stack-name $STACK_NAME &> /dev/null; then
  echo "Deleting existing ADOT Collector stack..."
  aws cloudformation delete-stack --stack-name $STACK_NAME
  echo "Waiting for stack deletion to complete..."
  aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME
  echo "Stack deleted successfully."
else
  echo "No existing stack found, proceeding with deployment."
fi

# Deploy the CloudFormation stack with the environment variable configuration
echo "Deploying ADOT Collector with Datadog environment variable configuration..."
echo "Datadog API Key: $DATADOG_API_KEY Datadog Site: $DATADOG_SITE"
aws cloudformation deploy \
  --template-file adot-collector-datadog-deployment.yaml \
  --stack-name $STACK_NAME \
  --parameter-overrides \
    DatadogApiKey=$DATADOG_API_KEY \
    DatadogSite=$DATADOG_SITE \
  --capabilities CAPABILITY_IAM

echo "ADOT Collector deployment initiated!"
echo "Waiting for deployment to complete (this may take several minutes)..."

# Wait for the stack to be created
aws cloudformation wait stack-create-complete --stack-name $STACK_NAME

echo "ADOT Collector deployed successfully!"
echo "Waiting for the ECS service to stabilize..."
sleep 60

# Get the ADOT Collector endpoint
echo "Getting ADOT Collector endpoint..."
./get-adot-collector-endpoint.sh

echo ""
echo "You can now configure your application to send traces to this endpoint."
echo "Example configuration for Python OpenTelemetry:"
echo "export OTEL_EXPORTER_OTLP_ENDPOINT=http://<public-ip>:4318/v1/traces"
echo "export OTEL_EXPORTER_OTLP_HEADERS=\"DD-API-KEY=${DATADOG_API_KEY}\""
