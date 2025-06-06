# Setting up AWS Distro for OpenTelemetry (ADOT) with Datadog Exporter

This guide explains how to deploy AWS Distro for OpenTelemetry (ADOT) Collector with Datadog exporter and configure your application to send traces to it.

## Prerequisites

1. AWS CLI installed and configured with appropriate permissions
2. A Datadog account and API key
3. Python 3.6+ for the sample application

## Deployment Steps

### 1. Deploy ADOT Collector with Datadog Exporter

Run the deployment script with your Datadog API key:

```bash
./deploy-adot.sh YOUR_DATADOG_API_KEY [DATADOG_SITE]
```

Where:
- `YOUR_DATADOG_API_KEY` is your Datadog API key
- `DATADOG_SITE` (optional) is the Datadog site to send data to (default: datadoghq.com)

The script will:
1. Deploy a CloudFormation stack that creates:
   - An ECS Fargate cluster
   - ADOT Collector task definition with Datadog exporter
   - Necessary networking and security groups
2. Output the OTLP HTTP endpoint URL for your application to use

### 2. Configure Your Application

Once the ADOT Collector is deployed, you need to configure your application to send traces to it.

#### Using the provided helper module:

```python
from app_otel_config import configure_otel

# Configure OpenTelemetry with the ADOT endpoint
ADOT_ENDPOINT = "http://your-adot-endpoint:4318/v1/traces"  # Replace with your endpoint
tracer = configure_otel("your-service-name", ADOT_ENDPOINT)

# Use the tracer in your code
with tracer.start_as_current_span("operation-name") as span:
    span.set_attribute("attribute.name", "value")
    # Your code here
```

#### Using environment variables:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://your-adot-endpoint:4318/v1/traces
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_SERVICE_NAME=your-service-name
```

### 3. Run the Sample Application

A sample application is provided to demonstrate tracing:

```bash
# Set the ADOT endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT=http://your-adot-endpoint:4318/v1/traces

# Install dependencies
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http requests

# Run the sample application
python sample-app-with-otel.py
```

## Verification

1. After running the application, check your Datadog APM dashboard
2. You should see traces from your application with the service name you configured
3. The traces will include spans for various operations with attributes

## Cleanup

To delete the ADOT Collector deployment:

```bash
aws cloudformation delete-stack --stack-name adot-collector
```

## Troubleshooting

If you don't see traces in Datadog:

1. Check that your Datadog API key is correct
2. Verify the ADOT Collector is running:
   ```bash
   aws ecs list-tasks --cluster adot-collector-cluster
   ```
3. Check the ADOT Collector logs:
   ```bash
   aws logs get-log-events --log-group-name /ecs/adot-collector --log-stream-name adot-collector/adot-collector/[TASK_ID]
   ```
4. Ensure your application is correctly configured to send traces to the ADOT endpoint
