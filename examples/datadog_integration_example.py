#!/usr/bin/env python3
"""
# 📊 Strands Agent with Datadog and Langfuse Integration

This example demonstrates how to integrate both Datadog and Langfuse with Strands Agents
for comprehensive observability and evaluation.

## What This Example Shows

This example demonstrates:
- Setting up Datadog telemetry for Strands Agents
- Maintaining existing Langfuse integration
- Collecting metrics and traces for agent performance
- Monitoring tool usage and execution times

## Requirements

- Datadog account and API key
- Langfuse account and API keys (if using Langfuse)
- Strands Agents SDK
"""

import os
import sys
import time
from typing import Dict, Any, List
from strands import Agent, tool

# Add the parent directory to the path to import utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import DatadogAgent, init_datadog

# Set Datadog environment variables
os.environ["DD_ENV"] = "development"  # or staging, production
os.environ["DD_SERVICE"] = "strands-demo-agent"
# os.environ["DD_API_KEY"] = "<your-datadog-api-key>"  # Set your Datadog API key here or in environment

# Set Langfuse environment variables (if using Langfuse)
# os.environ["LANGFUSE_PUBLIC_KEY"] = "<your-langfuse-public-key>"
# os.environ["LANGFUSE_SECRET_KEY"] = "<your-langfuse-secret-key>"
# os.environ["LANGFUSE_HOST"] = "https://cloud.langfuse.com"  # or your self-hosted URL

# System prompt
SYSTEM_PROMPT = """You are a helpful assistant that can answer questions and perform calculations.

Capabilities:
- Answer general knowledge questions
- Perform mathematical calculations
- Generate creative content
- Provide recommendations

Key Rules:
- Be concise and accurate
- Ask clarifying questions when needed
- Admit when you don't know something
"""

@tool
def calculate(expression: str) -> Dict[str, Any]:
    """
    Safely evaluate a mathematical expression.
    
    Args:
        expression (str): A mathematical expression to evaluate.
        
    Returns:
        Dict with result or error message.
    """
    try:
        # Use a safer eval approach for calculations
        import ast
        import operator
        
        # Define allowed operators
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.BitXor: operator.xor,
            ast.USub: operator.neg,
        }
        
        def eval_expr(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                return operators[type(node.op)](eval_expr(node.left), eval_expr(node.right))
            elif isinstance(node, ast.UnaryOp):
                return operators[type(node.op)](eval_expr(node.operand))
            else:
                raise TypeError(f"Unsupported operation: {node}")
        
        result = eval_expr(ast.parse(expression, mode='eval').body)
        return {"result": result, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "error"}

# Initialize base agent
base_agent = Agent(
    system_prompt=SYSTEM_PROMPT,
    tools=[calculate],
    model="anthropic.claude-3-sonnet-20240229-v1:0",  # Specify your preferred model
)

# Initialize Datadog separately for any standalone metrics
init_datadog(
    service_name="strands-demo-agent",
    env=os.environ.get("DD_ENV", "development"),
)

# Wrap with Datadog telemetry
agent = DatadogAgent(
    agent=base_agent,
    service_name="strands-demo-agent",
    env=os.environ.get("DD_ENV", "development"),
)

# If using Langfuse, you would configure it here
# This example assumes Langfuse is configured via environment variables
# and the Strands Agent is already set up to use it

if __name__ == "__main__":
    """Run the agent interactive session with Datadog telemetry."""
    print("\n📊 Strands Agent with Datadog and Langfuse Integration 📊\n")
    print("This agent demonstrates integration with observability tools.")
    print("All interactions are monitored with Datadog telemetry.")
    
    # Track session metrics
    session_start = time.time()
    interaction_count = 0
    
    # Interactive loop
    while True:
        try:
            print("\nWrite your question below or 'exit' to quit:")
            user_input = input("\n> ").strip()
            
            if user_input.lower() == "exit":
                # Log session metrics before exiting
                session_duration = time.time() - session_start
                print(f"\n[Metrics] Session duration: {session_duration:.2f}s")
                print(f"[Metrics] Total interactions: {interaction_count}")
                print("\nGoodbye! 👋")
                break
            
            # Process the request through the agent
            start_time = time.time()
            response = agent(user_input)
            duration = time.time() - start_time
            
            # Update metrics
            interaction_count += 1
            
            # Log request metrics
            print(f"\n[Metrics] Request #{interaction_count} processed in {duration:.2f}s")
            
            # If you have Langfuse integration, you might log additional metrics here
            
        except KeyboardInterrupt:
            print("\n\nExecution interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Please try a different request.")
