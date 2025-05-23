FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV DD_ENV=development
ENV DD_SERVICE=strands-demo-agent
ENV DD_SITE=datadoghq.com
ENV DD_LLMOBS_ML_APP=strands-demo-agent
ENV DD_LLMOBS_AGENTLESS_ENABLED=1
ENV AWS_REGION=us-east-1

# Run the application
CMD ["python", "examples/datadog_integration_example.py"]

