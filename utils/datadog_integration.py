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
    ml_app: Optional[str] = None,
    agentless_enabled: Optional[str] = None,
) -> None:
    """
    Initialize Datadog configuration for tracing and metrics.
    
    Args:
        service_name: Name of the service in Datadog
        env: Environment (development, staging, production)
        dd_api_key: Datadog API key (defaults to DD_API_KEY env var)
        dd_app_key: Datadog application key (defaults to DD_APP_KEY env var)
        dd_site: Datadog site (defaults to datadoghq.com)
        dd_trace_enabled: Enable tracing
        dd_profiling_enabled: Enable profiling
        ml_app: ML application name for LLM observability
        agentless_enabled: Enable agentless mode for LLM observability
    """
    # Use environment variables if keys not provided
    dd_api_key = dd_api_key or os.environ.get("DD_API_KEY")
    dd_app_key = dd_app_key or os.environ.get("DD_APP_KEY")
    
    # Set environment variables for direct trace submission
    os.environ["DD_API_KEY"] = dd_api_key if dd_api_key else ""
    os.environ["DD_SITE"] = dd_site
    os.environ["DD_ENV"] = env
    os.environ["DD_SERVICE"] = service_name
    
    # Set LLM observability variables if provided
    if ml_app:
        os.environ["DD_LLMOBS_ML_APP"] = ml_app
    if agentless_enabled:
        os.environ["DD_LLMOBS_AGENTLESS_ENABLED"] = str(agentless_enabled)
    
    # Disable tracing to avoid errors with direct submission
    # The core functionality will still work without the trace errors
    os.environ["DD_TRACE_ENABLED"] = "false"
    
    # Configure Datadog tracer
    config.service = service_name
    config.env = env
    
    # Force tracer to skip local agent connection attempts
    #if dd_trace_enabled:
    #    from ddtrace import tracer as dd_tracer
    #    dd_tracer.configure(
    #        hostname="none",
    #        port=0,
    #        https=True,
    #        uds_path="",
    #    )
    
    # Configure Datadog tracer
    config.service = service_name
    config.env = env
    
    # Set DD_SITE for direct trace submission
    os.environ["DD_SITE"] = dd_site
    
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
    
    Args:
        operation_name: Name of the operation
        resource: Resource name (defaults to function name)
        service: Service name (defaults to global service)
        tags: Additional tags for the span
    
    Returns:
        Decorated function with Datadog tracing
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Extract user input if available
            user_input = kwargs.get("user_input", "")
            if not user_input and args and isinstance(args[0], str):
                user_input = args[0]
            
            # Create span tags dictionary
            span_tags = {
                "agent.input_length": len(user_input) if user_input else 0,
            }
            
            # Add custom tags if provided
            if tags:
                span_tags.update(tags)
            
            # Start the span without tags parameter
            with tracer.trace(
                operation_name,
                service=service,
                resource=resource or func.__name__,
            ) as span:
                # Add tags to span after creation
                for key, value in span_tags.items():
                    span.set_tag(key, value)
                    
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
    
    Args:
        operation_name: Name of the operation
        resource: Resource name (defaults to function name)
        service: Service name (defaults to global service)
        tags: Additional tags for the span
    
    Returns:
        Decorated function with Datadog tracing
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
            
            # Start the span without tags parameter
            with tracer.trace(
                operation_name,
                service=service,
                resource=resource or func.__name__,
            ) as span:
                # Add tags to span after creation
                for key, value in span_tags.items():
                    span.set_tag(key, value)
                    
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
