#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Set Datadog OTLP endpoint and headers
export OTEL_EXPORTER_OTLP_ENDPOINT="https://trace.agent.${DD_SITE}/api/v2/traces"
export OTEL_EXPORTER_OTLP_HEADERS="DD-API-KEY=${DD_API_KEY}"

# Set additional OpenTelemetry configuration
export OTEL_SERVICE_NAME="sample-booking-app"
export OTEL_RESOURCE_ATTRIBUTES="deployment.environment=${DD_ENV}"

echo "Configured to send traces directly to Datadog at ${OTEL_EXPORTER_OTLP_ENDPOINT}"
echo "Using API key: ${DD_API_KEY:0:5}..."

# Run the sample application
python sample-app-with-otel.py
