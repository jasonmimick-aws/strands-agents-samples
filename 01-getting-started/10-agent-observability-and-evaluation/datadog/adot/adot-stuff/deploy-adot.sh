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

# Deploy the CloudFormation stack
echo "Deploying ADOT Collector with Datadog exporter..."
aws cloudformation deploy \
  --template-file adot-collector-deployment.yaml \
  --stack-name adot-collector \
  --parameter-overrides \
    DatadogApiKey=$DATADOG_API_KEY \
    DatadogSite=$DATADOG_SITE \
  --capabilities CAPABILITY_IAM

# Get the ADOT Collector endpoint
ADOT_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name adot-collector \
  --query "Stacks[0].Outputs[?OutputKey=='ADOTCollectorEndpoint'].OutputValue" \
  --output text)

echo "ADOT Collector deployed successfully!"
echo "OTLP HTTP Endpoint: $ADOT_ENDPOINT"
echo ""
echo "You can now configure your application to send traces to this endpoint."
echo "Example configuration for Python OpenTelemetry:"
echo "export OTEL_EXPORTER_OTLP_ENDPOINT=$ADOT_ENDPOINT"
echo "export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf"
