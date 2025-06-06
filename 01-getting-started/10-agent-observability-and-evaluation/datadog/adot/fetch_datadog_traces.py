#!/usr/bin/env python3
import os
import requests
import json
from datetime import datetime, timedelta
import time
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Get Datadog credentials
DD_API_KEY = os.environ.get('DD_API_KEY')
DD_SITE = os.environ.get('DD_SITE', 'datadoghq.com')
DD_SERVICE = "sample-booking-app"  # From run-with-datadog.sh

print(f"Using API key: {DD_API_KEY[:5]}... and site: {DD_SITE}")

# Calculate time range (last 24 hours)
now = int(time.time())
start_time = now - 86400  # 24 hours ago

print(f"Fetching traces from {datetime.fromtimestamp(start_time)} to {datetime.fromtimestamp(now)}")

# Datadog API endpoint for APM traces search
url = f"https://api.{DD_SITE}/api/v2/apm/traces"

# Headers for authentication
headers = {
    'DD-API-KEY': DD_API_KEY,
    'Content-Type': 'application/json'
}

try:
    # Make the API request to get traces
    print(f"Making request to {url}")
    response = requests.get(url, headers=headers)
    
    # Check if the request was successful
    if response.status_code == 200:
        traces = response.json()
        print(f"Successfully fetched traces")
        print(json.dumps(traces, indent=2))
    else:
        print(f"Error fetching traces: {response.status_code}")
        print(response.text)
        
        # Try the APM search endpoint
        search_url = f"https://api.{DD_SITE}/api/v2/apm/search/traces"
        print(f"\nTrying APM search endpoint: {search_url}")
        
        # For search API, we need to use query parameters
        params = {
            'start': start_time,
            'end': now,
            'service': DD_SERVICE,
            'limit': 10
        }
        
        search_response = requests.get(search_url, params=params, headers=headers)
        
        if search_response.status_code == 200:
            search_traces = search_response.json()
            print(f"Successfully fetched traces from search API")
            print(json.dumps(search_traces, indent=2))
        else:
            print(f"Error fetching traces from search API: {search_response.status_code}")
            print(search_response.text)
            
            # Try the events endpoint
            events_url = f"https://api.{DD_SITE}/api/v1/events"
            print(f"\nTrying events endpoint: {events_url}")
            
            # For events API
            events_params = {
                'start': start_time,
                'end': now,
                'sources': 'trace',
                'tags': f"service:{DD_SERVICE}"
            }
            
            events_response = requests.get(events_url, params=events_params, headers=headers)
            
            if events_response.status_code == 200:
                events = events_response.json()
                print(f"Successfully fetched trace events")
                print(json.dumps(events, indent=2))
            else:
                print(f"Error fetching trace events: {events_response.status_code}")
                print(events_response.text)
                
except Exception as e:
    print(f"Exception occurred: {e}")
    
print("\nNote: If you're still getting errors, you may need to:")
print("1. Ensure your API key has APM access permissions")
print("2. Add an Application Key (DD_APP_KEY) to your environment")
print("3. Verify that there are traces being sent to Datadog")
print("4. Consider using the Datadog UI to view traces: https://app.datadoghq.com/apm/traces")
