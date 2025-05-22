# Datadog Integration for Strands Agents

This guide explains how to integrate Datadog telemetry with your Strands Agents projects for monitoring, tracing, and observability.

## Overview

The Datadog integration for Strands Agents provides:

- **Distributed Tracing**: Track agent calls and tool executions across your application
- **Metrics Collection**: Monitor agent performance, response times, and usage patterns
- **Error Tracking**: Identify and troubleshoot issues in your agent workflows
- **Custom Tagging**: Add context-specific tags to your traces and metrics

## Prerequisites

1. A Datadog account with an API key
2. Python 3.8+ environment
3. Strands Agents SDK installed

## Installation

1. Install the required Datadog packages:

```bash
pip install ddtrace datadog
```

2. Add these packages to your requirements.txt:

```
ddtrace>=2.0.0
datadog>=0.47.0
```

## Quick Start

### Basic Integration

```python
import os
from strands import Agent
from utils import DatadogAgent

# Set Datadog environment variables
os.environ["DD_ENV"] = "development"
os.environ["DD_SERVICE"] = "my-strands-agent"
os.environ["DD_API_KEY"] = "<your-datadog-api-key>"

# Create your Strands agent
base_agent = Agent(
    system_prompt="You are a helpful assistant.",
    tools=[my_tool1, my_tool2],
)

# Wrap with Datadog telemetry
agent = DatadogAgent(
    agent=base_agent,
    service_name="my-strands-agent",
    env="development",
)

# Use the agent as normal
response = agent("Tell me about Strands Agents")
```

### Tracing Individual Tools

You can also trace individual tools without wrapping the entire agent:

```python
from utils import trace_tool_call

@trace_tool_call(operation_name="tool.my_custom_tool")
def my_custom_tool(tool, **kwargs):
    # Tool implementation
    return {"status": "success", "content": [{"text": "Result"}]}
```

## Configuration Options

The `DatadogAgent` wrapper accepts the following parameters:

- `agent`: The Strands Agent instance to wrap
- `service_name`: Name of the service in Datadog
- `env`: Environment (development, staging, production)
- `dd_api_key`: Datadog API key (defaults to DD_API_KEY env var)
- `dd_app_key`: Datadog application key (defaults to DD_APP_KEY env var)
- `dd_site`: Datadog site (defaults to datadoghq.com)

## Using with Langfuse

This integration is designed to work alongside Langfuse. You can use both observability tools simultaneously:

1. Configure Langfuse as you normally would with environment variables:

```python
os.environ["LANGFUSE_PUBLIC_KEY"] = "<your-langfuse-public-key>"
os.environ["LANGFUSE_SECRET_KEY"] = "<your-langfuse-secret-key>"
os.environ["LANGFUSE_HOST"] = "https://cloud.langfuse.com"
```

2. Then wrap your agent with the Datadog wrapper:

```python
# Create your Strands agent with Langfuse configured
base_agent = Agent(
    system_prompt="You are a helpful assistant.",
    tools=[my_tool1, my_tool2],
    # Langfuse is configured via environment variables
)

# Add Datadog telemetry
agent = DatadogAgent(agent=base_agent)
```

## Examples

See the following examples for more detailed usage:

- `examples/datadog_integration_example.py`: Basic integration with Datadog
- `01-getting-started/14-memory-persistent-agents/personal_agent_with_memory_datadog.py`: Memory agent with Datadog
- `01-getting-started/10-agent-observability-and-evaluation/create_booking_with_datadog.py`: Tool tracing example

## Best Practices

1. **Use meaningful service names**: Choose descriptive service names that reflect the purpose of your agent
2. **Set appropriate environments**: Use different environments (dev, staging, prod) to separate metrics
3. **Add custom tags**: Add relevant tags to traces for better filtering and analysis
4. **Monitor critical paths**: Focus on tracing the most important or performance-sensitive parts of your agent
5. **Set up alerts**: Configure Datadog alerts for response times, error rates, or other key metrics

## Troubleshooting

- **Missing traces**: Ensure your Datadog API key is correctly set
- **Incomplete data**: Check that the agent wrapper is properly initialized
- **Performance issues**: Consider reducing the verbosity of tracing in high-volume scenarios
