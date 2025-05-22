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
        
        Args:
            agent: The Strands Agent instance to wrap
            service_name: Name of the service in Datadog
            env: Environment (development, staging, production)
            dd_api_key: Datadog API key (defaults to DD_API_KEY env var)
            dd_app_key: Datadog application key (defaults to DD_APP_KEY env var)
            dd_site: Datadog site (defaults to datadoghq.com)
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
