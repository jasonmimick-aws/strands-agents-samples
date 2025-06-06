# How to Deploy AWS Distro for OpenTelemetry (ADOT) with Datadog Exporter

This guide provides step-by-step instructions for deploying AWS Distro for OpenTelemetry (ADOT) Collector with Datadog exporter configuration. The deployment will create an ADOT instance that receives traces at the `/traces` endpoint and forwards them to Datadog.

You can then use this endpoint to send OTEL traces which will get forwarded to Datadog.

## Prerequisites

- AWS CLI installed and configured with appropriate permissions
- A Datadog account and API key
- Python 3.6+ for the sample application

## Deployment Steps

### 1. Prepare the Configuration Files

The repository contains all necessary files for deployment:

- `adot-collector-datadog-deployment.yaml`: CloudFormation template for deploying ADOT
-  Configuration for ADOT Collector with Datadog exporter as env variable in CFN template
- `deploy-adot-collector-datadog.sh`: Deployment script
- `app-otel-config.py`: Helper module for configuring OpenTelemetry in your application
- `sample-app-with-otel.py`: Sample application demonstrating tracing

### 2. Deploy ADOT Collector

Run the deployment script with your Datadog API key:

```bash
./deploy-adot-collector-datadog.sh YOUR_DATADOG_API_KEY [DATADOG_SITE]
```

Parameters:
- `YOUR_DATADOG_API_KEY`: Your Datadog API key (required)
- `DATADOG_SITE`: The Datadog site to send data to (optional, default: datadoghq.com)

The script will:
1. Deploy a CloudFormation stack with:
   - ECS Fargate cluster
   - ADOT Collector task definition
   - Necessary networking components
   - Security groups
2. Configure the ADOT Collector with Datadog exporter
3. Output the OTLP HTTP endpoint URL for your application

### 3. Fetch the ADOR collection HTTP endpoint

Replace the IP address in the output from the Cloudformation deployment using the output from this script. This comes from the Fargate ECS task running an instance of the collector.

```bash
./get-adot-collector-endpoint.sh
```

### 4. _Optional_ Test it - Update Application Dependencies

Install the required OpenTelemetry packages:

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http requests
```

Or use the provided updated requirements file:

```bash
pip install -r update-requirements.txt
```

### 4. Configure Your Application

#### Option 1: Using the helper module

```python
from app_otel_config import configure_otel

# Replace with your ADOT endpoint from the deployment output
ADOT_ENDPOINT = "http://your-adot-endpoint:4318/v1/traces"
tracer = configure_otel("your-service-name", ADOT_ENDPOINT)

# Use the tracer in your code
with tracer.start_as_current_span("operation-name") as span:
    span.set_attribute("attribute.name", "value")
    # Your code here
```

#### Option 2: Using environment variables

```bash
# Replace with your ADOT endpoint from the deployment output
export OTEL_EXPORTER_OTLP_ENDPOINT=http://your-adot-endpoint:4318/v1/traces
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_SERVICE_NAME=your-service-name
```

### 5. Run the Sample Application

A sample application is provided to demonstrate tracing:

```bash
# Set the ADOT endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT=http://your-adot-endpoint:4318/v1/traces

# Run the sample application
python sample-app-with-otel.py
```

## Verification

1. After running the application, check your Datadog APM dashboard
2. You should see traces from your application with the service name you configured
3. The traces will include spans for various operations with attributes

## Understanding the Architecture

```
┌─────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│                 │     │                   │     │                 │
│  Your           │     │  ADOT Collector   │     │  Datadog        │
│  Application    │────▶│  with Datadog     │────▶│  Platform       │
│                 │     │  Exporter         │     │                 │
└─────────────────┘     └───────────────────┘     └─────────────────┘
      OTLP/HTTP              Datadog Protocol
```

- Your application sends traces to ADOT Collector using OTLP/HTTP protocol
- ADOT Collector receives traces at the `/traces` endpoint
- ADOT processes and forwards the traces to Datadog using the Datadog exporter
- Traces appear in your Datadog APM dashboard

## CloudFormation Resources Created

The deployment creates the following AWS resources:

- ECS Fargate Cluster
- Task Definition for ADOT Collector
- VPC with public subnet
- Security Groups
- IAM Roles
- CloudWatch Log Group
- EFS File System for configuration

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
5. Verify network connectivity between your application and the ADOT endpoint

## Cleanup

To delete the ADOT Collector deployment:

```bash
aws cloudformation delete-stack --stack-name adot-collector
```

## Additional Resources

- [AWS Distro for OpenTelemetry Documentation](https://aws-otel.github.io/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Datadog OpenTelemetry Integration](https://docs.datadoghq.com/tracing/setup_overview/open_standards/)
