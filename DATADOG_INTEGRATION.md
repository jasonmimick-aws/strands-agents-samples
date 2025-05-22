# Datadog Integration for Strands Agents

This guide explains how to integrate Datadog telemetry with your Strands Agents projects while maintaining existing integrations like Langfuse.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Integration Steps](#integration-steps)
- [Usage Examples](#usage-examples)
- [Key Features](#key-features)
- [Configuration Options](#configuration-options)
- [Using with Langfuse](#using-with-langfuse)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

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

## Integration Steps

### Step 1: Create Utility Files

Create the following directory structure and files:

```
/utils/
  ├── __init__.py
  ├── datadog_integration.py
  └── datadog_agent_wrapper.py
```

#### datadog_integration.py

This file contains core functions for Datadog integration:

```python
"""
Datadog integration for Strands Agents
This module provides utilities to integrate Datadog telemetry with Strands Agents.
"""

import os
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, cast

# Import Datadog libraries
from ddtrace import tracer, config
from ddtrace.context import Context
from datadog import initialize, statsd

# Type variable for function return type
T = TypeVar('T')

# Initialize Datadog configuration
def init_datadog(
    service_name: str = "strands-agent",
    env: str = "development",
    dd_api_key: Optional[str] = None,
    dd_app_key: Optional[str] = None,
    dd_site: str = "datadoghq.com",
    dd_trace_enabled: bool = True,
    dd_profiling_enabled: bool = False,
) -> None:
    """
    Initialize Datadog configuration for tracing and metrics.
    """
    # Use environment variables if keys not provided
    dd_api_key = dd_api_key or os.environ.get("DD_API_KEY")
    dd_app_key = dd_app_key or os.environ.get("DD_APP_KEY")
    
    # Configure Datadog tracer
    config.service = service_name
    config.env = env
    
    # Initialize Datadog metrics
    initialize(
        api_key=dd_api_key,
        app_key=dd_app_key,
        site=dd_site,
    )
    
    if dd_profiling_enabled:
        from ddtrace.profiling import Profiler
        profiler = Profiler(service=service_name, env=env)
        profiler.start()
    
    print(f"Datadog initialized for service: {service_name}, env: {env}")


def trace_agent_call(
    operation_name: str = "agent_call",
    resource: Optional[str] = None,
    service: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Callable:
    """
    Decorator to trace Strands Agent calls with Datadog.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Extract user input if available
            user_input = kwargs.get("user_input", "")
            if not user_input and args and isinstance(args[0], str):
                user_input = args[0]
            
            # Create span tags
            span_tags = {
                "agent.input_length": len(user_input) if user_input else 0,
            }
            
            # Add custom tags if provided
            if tags:
                span_tags.update(tags)
            
            # Start the span
            with tracer.trace(
                operation_name,
                service=service,
                resource=resource or func.__name__,
                tags=span_tags,
            ) as span:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    
                    # Add response metadata to span
                    if hasattr(result, "metadata"):
                        metadata = result.metadata
                        if metadata:
                            span.set_tag("agent.model", metadata.get("model", "unknown"))
                            span.set_tag("agent.tokens", metadata.get("usage", {}).get("total_tokens", 0))
                    
                    # Mark as successful
                    span.set_tag("agent.status", "success")
                    return result
                except Exception as e:
                    # Record error details
                    span.set_tag("agent.status", "error")
                    span.set_tag("error.type", type(e).__name__)
                    span.set_tag("error.message", str(e))
                    raise
                finally:
                    # Record duration
                    duration = time.time() - start_time
                    span.set_tag("agent.duration_seconds", duration)
                    # Send metrics
                    statsd.timing("agent.response_time", duration * 1000)  # Convert to ms
        
        return cast(Callable[..., T], wrapper)
    
    return decorator


def trace_tool_call(
    operation_name: str = "tool_call",
    resource: Optional[str] = None,
    service: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Callable:
    """
    Decorator to trace Strands Agent tool calls with Datadog.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Extract tool information if available
            tool_info = None
            for arg in args:
                if isinstance(arg, dict) and "toolUseId" in arg:
                    tool_info = arg
                    break
            
            # Create span tags
            span_tags = {}
            if tool_info:
                span_tags["tool.id"] = tool_info.get("toolUseId", "")
                span_tags["tool.name"] = tool_info.get("name", "")
            
            # Add custom tags if provided
            if tags:
                span_tags.update(tags)
            
            # Start the span
            with tracer.trace(
                operation_name,
                service=service,
                resource=resource or func.__name__,
                tags=span_tags,
            ) as span:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    
                    # Add result status to span
                    if isinstance(result, dict) and "status" in result:
                        span.set_tag("tool.status", result["status"])
                    
                    return result
                except Exception as e:
                    # Record error details
                    span.set_tag("tool.status", "error")
                    span.set_tag("error.type", type(e).__name__)
                    span.set_tag("error.message", str(e))
                    raise
                finally:
                    # Record duration
                    duration = time.time() - start_time
                    span.set_tag("tool.duration_seconds", duration)
                    # Send metrics
                    statsd.timing("tool.response_time", duration * 1000)  # Convert to ms
                    statsd.increment("tool.calls", tags=[f"tool:{func.__name__}"])
        
        return cast(Callable[..., T], wrapper)
    
    return decorator
```

#### datadog_agent_wrapper.py

This file contains the wrapper for Strands Agent:

```python
"""
Datadog-instrumented Strands Agent wrapper
This module provides a wrapper for Strands Agent with Datadog telemetry.
"""

from typing import Any, Callable, Dict, List, Optional, Union
from strands import Agent
from .datadog_integration import init_datadog, trace_agent_call, trace_tool_call

class DatadogAgent:
    """
    A wrapper for Strands Agent that adds Datadog telemetry.
    """
    
    def __init__(
        self,
        agent: Agent,
        service_name: str = "strands-agent",
        env: str = "development",
        dd_api_key: Optional[str] = None,
        dd_app_key: Optional[str] = None,
        dd_site: str = "datadoghq.com",
    ):
        """
        Initialize a Datadog-instrumented Strands Agent.
        """
        self.agent = agent
        self.service_name = service_name
        
        # Initialize Datadog
        init_datadog(
            service_name=service_name,
            env=env,
            dd_api_key=dd_api_key,
            dd_app_key=dd_app_key,
            dd_site=dd_site,
        )
        
        # Wrap the agent's __call__ method with tracing
        self._original_call = agent.__call__
        agent.__call__ = self._traced_call
        
        # Wrap any tool functions with tracing
        if hasattr(agent, "tool"):
            self._wrap_tools()
    
    @trace_agent_call(operation_name="agent_call")
    def _traced_call(self, *args: Any, **kwargs: Any) -> Any:
        """
        Traced version of the agent's __call__ method.
        """
        return self._original_call(*args, **kwargs)
    
    def _wrap_tools(self) -> None:
        """
        Wrap all tool functions with Datadog tracing.
        """
        tool_obj = self.agent.tool
        
        # Find all callable attributes that might be tools
        for attr_name in dir(tool_obj):
            if attr_name.startswith('_'):
                continue
                
            attr = getattr(tool_obj, attr_name)
            if callable(attr):
                # Wrap the tool function with tracing
                wrapped_tool = trace_tool_call(
                    operation_name=f"tool.{attr_name}",
                    resource=attr_name,
                    service=self.service_name,
                )(attr)
                
                # Replace the original function with the wrapped one
                setattr(tool_obj, attr_name, wrapped_tool)
    
    def __getattr__(self, name: str) -> Any:
        """
        Delegate attribute access to the wrapped agent.
        """
        return getattr(self.agent, name)
```

#### __init__.py

This file exports the key functions and classes:

```python
"""
Utility modules for Strands Agents
"""

from .datadog_integration import init_datadog, trace_agent_call, trace_tool_call
from .datadog_agent_wrapper import DatadogAgent

__all__ = [
    'init_datadog',
    'trace_agent_call',
    'trace_tool_call',
    'DatadogAgent',
]
```

### Step 2: Configure Datadog Environment Variables

Set the following environment variables:

```bash
export DD_ENV=development  # or staging, production
export DD_SERVICE=strands-agent
export DD_API_KEY=your_datadog_api_key
```

### Step 3: Use the DatadogAgent Wrapper

```python
import os
from strands import Agent
from utils import DatadogAgent

# Create your Strands agent as usual
base_agent = Agent(
    system_prompt="You are a helpful assistant.",
    tools=[your_tools],
    # Langfuse is configured via environment variables
)

# Wrap with Datadog telemetry
agent = DatadogAgent(
    agent=base_agent,
    service_name="your-agent-name",
    env="development",
)

# Use the agent as normal - both Datadog and Langfuse will work
response = agent("Your prompt here")
```

### Step 4: Trace Individual Tools (Optional)

For more granular control, you can trace individual tools:

```python
from utils import trace_tool_call

@trace_tool_call(operation_name="tool.your_tool_name")
def your_tool_function(tool, **kwargs):
    # Your tool implementation
    return {"status": "success", "content": [{"text": "Result"}]}
```

## Usage Examples

### Basic Agent with Datadog

```python
import os
from strands import Agent
from utils import DatadogAgent

# Set Datadog environment variables
os.environ["DD_ENV"] = "development"
os.environ["DD_SERVICE"] = "strands-demo-agent"
os.environ["DD_API_KEY"] = "<your-datadog-api-key>"

# Create your Strands agent
base_agent = Agent(
    system_prompt="You are a helpful assistant.",
    tools=[my_tool1, my_tool2],
)

# Wrap with Datadog telemetry
agent = DatadogAgent(
    agent=base_agent,
    service_name="strands-demo-agent",
    env="development",
)

# Use the agent as normal
response = agent("Tell me about Strands Agents")
```

### Tracing a Tool Function

```python
from utils import trace_tool_call
from strands.types.tools import ToolResult, ToolUse

@trace_tool_call(operation_name="tool.create_booking")
def create_booking(tool: ToolUse, **kwargs) -> ToolResult:
    # Tool implementation
    tool_use_id = tool["toolUseId"]
    
    try:
        # Your business logic here
        return {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [{"text": "Booking created successfully"}]
        }
    except Exception as e:
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": str(e)}]
        }
```

## Key Features

1. **Automatic Tracing**: All agent calls and tool executions are automatically traced
2. **Performance Metrics**: Response times and execution durations are tracked
3. **Error Tracking**: Errors are captured with detailed context
4. **Custom Tags**: Add context-specific tags to your traces
5. **Works with Langfuse**: Designed to work alongside your existing Langfuse integration

## Configuration Options

The `DatadogAgent` wrapper accepts the following parameters:

- `agent`: The Strands Agent instance to wrap
- `service_name`: Name of the service in Datadog
- `env`: Environment (development, staging, production)
- `dd_api_key`: Datadog API key (defaults to DD_API_KEY env var)
- `dd_app_key`: Datadog application key (defaults to DD_APP_KEY env var)
- `dd_site`: Datadog site (defaults to datadoghq.com)

The `init_datadog` function accepts additional parameters:

- `dd_trace_enabled`: Enable tracing (default: True)
- `dd_profiling_enabled`: Enable profiling (default: False)

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

## Best Practices

1. **Use meaningful service names**: Choose descriptive service names that reflect the purpose of your agent
2. **Set appropriate environments**: Use different environments (dev, staging, prod) to separate metrics
3. **Add custom tags**: Add relevant tags to traces for better filtering and analysis
4. **Monitor critical paths**: Focus on tracing the most important or performance-sensitive parts of your agent
5. **Set up alerts**: Configure Datadog alerts for response times, error rates, or other key metrics
6. **Use consistent naming**: Maintain consistent naming conventions for services, operations, and resources
7. **Limit trace volume**: In high-traffic applications, consider sampling traces to reduce overhead

## Troubleshooting

- **Missing traces**: Ensure your Datadog API key is correctly set
- **Incomplete data**: Check that the agent wrapper is properly initialized
- **Performance issues**: Consider reducing the verbosity of tracing in high-volume scenarios
- **Duplicate traces**: Make sure you're not wrapping already-wrapped functions
- **Environment issues**: Verify that environment variables are correctly set

## Next Steps

1. Set up Datadog dashboards for your agent metrics
2. Configure alerts for critical performance thresholds
3. Add custom metrics for your specific use cases
4. Implement log correlation between traces and logs
5. Create custom views for monitoring agent performance

---

This integration is designed to be non-intrusive and work alongside your existing Langfuse setup, so you can maintain both telemetry systems simultaneously.
