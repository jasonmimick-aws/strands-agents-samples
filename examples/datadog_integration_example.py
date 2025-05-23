#!/usr/bin/env python3
"""
# 📊 Strands Agent with Datadog Integration

This example demonstrates how to integrate Datadog with Strands Agents
for comprehensive observability.

## What This Example Shows

This example demonstrates:
- Setting up Datadog telemetry for Strands Agents
- Collecting metrics and traces for agent performance
- Monitoring tool usage and execution times

## Requirements

- Datadog account and API key
- Strands Agents SDK
- python-dotenv package (pip install python-dotenv)
"""

import os
import sys
import time
from typing import Dict, Any
from strands import Agent, tool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set AWS region if not already set - MUST be done before any AWS calls
if not os.environ.get("AWS_REGION") and not os.environ.get("AWS_DEFAULT_REGION"):
    os.environ["AWS_REGION"] = "us-east-1"  # Default to us-east-1 if no region is set

# Add the parent directory to the path to import utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.datadog_integration import init_datadog, trace_agent_call, trace_tool_call

# Get environment variables with defaults
dd_env = os.getenv("DD_ENV", "development")  # or staging, production
dd_service = os.getenv("DD_SERVICE", "strands-demo-agent")
dd_api_key = os.getenv("DD_API_KEY")
dd_app_key = os.getenv("DD_APP_KEY")
dd_site = os.getenv("DD_SITE", "datadoghq.com")
ml_app= os.getenv("LLMOBS_ML_APP", "strands-demo-agent")
agentless_enabled= os.getenv("DD_LLMOBS_AGENTLESS_ENABLED", 1)

# Get model configuration
model_name = os.getenv("MODEL_NAME", "amazon.titan-text-express-v1")

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

@trace_tool_call(operation_name="tool.calculate")
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

def main():
    """Run the agent interactive session with Datadog telemetry."""
    try:
        # Print AWS credentials info
        print("\nChecking AWS configuration...")
        aws_region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        print(f"AWS Region: {aws_region or 'Not set'}")
        print(f"AWS Access Key ID: {'Set' if os.environ.get('AWS_ACCESS_KEY_ID') else 'Not set'}")
        print(f"AWS Secret Access Key: {'Set' if os.environ.get('AWS_SECRET_ACCESS_KEY') else 'Not set'}")
        
        # Initialize Datadog
        print("\nInitializing Datadog...")
        init_datadog(
            service_name=dd_service,
            env=dd_env,
            dd_api_key=dd_api_key,
            dd_app_key=dd_app_key,
            dd_site=dd_site,
            ml_app=ml_app,
            agentless_enabled=agentless_enabled
        )

        # Initialize agent with configured model
        print(f"Initializing agent with model: {model_name}")
        agent = Agent(
            system_prompt=SYSTEM_PROMPT,
            tools=[calculate],
            model=model_name,
        )

        print("\n📊 Strands Agent with Datadog Integration 📊\n")
        print("This agent demonstrates integration with observability tools.")
        print("All interactions are monitored with Datadog telemetry.")
        print(f"Using model: {model_name}")
        print(f"AWS Region: {aws_region}")
        
        # Track session metrics
        session_start = time.time()
        interaction_count = 0
        
        # Create a traced version of the agent call
        @trace_agent_call(operation_name="agent_call")
        def traced_agent_call(agent, user_input):
            """Traced version of the agent call"""
            return agent(user_input)
        
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
                
                # Process the request through the agent with tracing
                start_time = time.time()
                response = traced_agent_call(agent, user_input)
                duration = time.time() - start_time
                
                # Display the response
                print(response)
                
                # Update metrics
                interaction_count += 1
                
                # Log request metrics
                print(f"\n[Metrics] Request #{interaction_count} processed in {duration:.2f}s")
                
            except KeyboardInterrupt:
                print("\n\nExecution interrupted. Exiting...")
                break
            except Exception as e:
                print(f"\nAn error occurred: {str(e)}")
                print("Please try a different request.")

    except Exception as e:
        print(f"Failed to initialize: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
