#!/usr/bin/env python3
"""
# 🧠 Personal Agent with Datadog Telemetry

A specialized Strands agent that personalizes the answers based on websearch and memory,
with added Datadog telemetry for monitoring and observability.

## What This Example Shows

This example demonstrates:
- Creating a specialized Strands agent with memory capabilities
- Storing information across conversations and sessions
- Retrieving relevant memories based on context
- Using memory to create more personalized and contextual AI interactions
- Integrating Datadog telemetry for monitoring agent performance and behavior

## Key Memory Operations

- **store**: Save important information for later retrieval
- **retrieve**: Access relevant memories based on queries
- **list**: View all stored memories

## Usage Examples

Storing memories: `Remember that I prefer tea over coffee`
Retrieving memories: `What do I prefer to drink?`
Listing all memories: `Show me everything you remember about me`
"""

import os
import sys
import time
from strands import Agent, tool
from strands_tools import mem0_memory, http_request
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException, RatelimitException

# Add the parent directory to the path to import utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from utils import DatadogAgent

# Set up environment variables for AWS credentials and OpenSearch
os.environ["OPENSEARCH_HOST"] = "<your-opensearch-hostname>.<your-region>.aoss.amazonaws.com" # Note: Please make sure to remove 'https://' from the AOSS endpoint.
os.environ["AWS_REGION"] = "<your-region>" # Replace with your region name e.g. 'us-west-2'
os.environ['AWS_ACCESS_KEY_ID'] = "<your-aws-access-key-id>"
os.environ['AWS_SECRET_ACCESS_KEY'] = "<your-aws-secret-access-key>"

# Datadog environment variables (can also be set in the environment)
os.environ["DD_ENV"] = "development"  # or staging, production
os.environ["DD_SERVICE"] = "strands-memory-agent"
# os.environ["DD_API_KEY"] = "<your-datadog-api-key>"  # Set your Datadog API key here or in environment

# User identifier
USER_ID = "new_user" # In the real app, this would be set based on user authentication.

# System prompt
SYSTEM_PROMPT = """You are a helpful personal assistant that provides personalized responses based on user history.

Capabilities:
- Store information with mem0_memory (action="store")
- Retrieve memories with mem0_memory (action="retrieve")
- Search the web with duckduckgo_search

Key Rules:
- Be conversational and natural
- Retrieve memories before responding
- Store new user information and preferences
- Share only relevant information
- Politely indicate when information is unavailable
"""

@tool
def websearch(keywords: str, region: str = "us-en", max_results: int = 5) -> str:
    """Search the web for updated information.
    
    Args:
        keywords (str): The search query keywords.
        region (str): The search region: wt-wt, us-en, uk-en, ru-ru, etc..
        max_results (int | None): The maximum number of results to return.
    Returns:
        List of dictionaries with search results.
    
    """
    try:
        results = DDGS().text(keywords, region=region, max_results=max_results)
        return results if results else "No results found."
    except RatelimitException:
        return "Rate limit reached. Please try again later."
    except DuckDuckGoSearchException as e:
        return f"Search error: {e}"

# Initialize base agent
base_agent = Agent(
    system_prompt=SYSTEM_PROMPT,
    tools=[mem0_memory, websearch, http_request],
)

# Wrap with Datadog telemetry
memory_agent = DatadogAgent(
    agent=base_agent,
    service_name="strands-memory-agent",
    env=os.environ.get("DD_ENV", "development"),
)

if __name__ == "__main__":
    """Run the personal agent interactive session with Datadog telemetry."""
    print("\n🧠 Personal Agent with Datadog Telemetry 🧠\n")
    print("This agent uses memory and websearch capabilities in Strands Agents.")
    print("You can ask me to remember things, retrieve memories, or search the web.")
    print("All interactions are monitored with Datadog telemetry.")

    # Initialize user memory
    memory_agent.agent.tool.mem0_memory(
        action="store", content=f"The user's name is {USER_ID}.", user_id=USER_ID
    )

    # Interactive loop
    while True:
        try:
            print("\nWrite your question below or 'exit' to quit, or 'memory' to list all memories:")
            user_input = input("\n> ").strip().lower()
            
            if user_input.lower() == "exit":
                print("\nGoodbye! 👋")
                break
            if user_input.lower() == "memory":
                all_memories = memory_agent.agent.tool.mem0_memory(
                    action="list",
                    user_id=USER_ID,
                )
                continue
            else:
                # Track request start time for custom metrics
                start_time = time.time()
                
                # Process the request through the agent
                response = memory_agent(user_input)
                
                # Calculate and log request duration
                duration = time.time() - start_time
                print(f"[Datadog] Request processed in {duration:.2f}s")
                
        except KeyboardInterrupt:
            print("\n\nExecution interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Please try a different request.")
