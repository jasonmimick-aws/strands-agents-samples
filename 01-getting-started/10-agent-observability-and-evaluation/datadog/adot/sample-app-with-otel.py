"""
Sample application that sends traces to ADOT Collector
"""

import os
import time
import random
import requests
from app_otel_config import configure_otel

# Configure OpenTelemetry
ADOT_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
tracer = configure_otel("sample-booking-app", ADOT_ENDPOINT)

def make_request(url):
    """Make an HTTP request and trace it"""
    with tracer.start_as_current_span("http_request") as span:
        span.set_attribute("http.url", url)
        span.set_attribute("http.method", "GET")
        
        try:
            response = requests.get(url, timeout=5)
            span.set_attribute("http.status_code", response.status_code)
            return response.text
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            return None

def process_booking(booking_id):
    """Process a booking with tracing"""
    with tracer.start_as_current_span("process_booking") as span:
        span.set_attribute("booking.id", booking_id)
        
        # Simulate some processing time
        processing_time = random.uniform(0.1, 0.5)
        time.sleep(processing_time)
        span.set_attribute("processing.time_ms", processing_time * 1000)
        
        # Simulate a database query
        with tracer.start_as_current_span("database_query") as db_span:
            db_span.set_attribute("db.system", "postgresql")
            db_span.set_attribute("db.statement", f"SELECT * FROM bookings WHERE id = {booking_id}")
            db_span.set_attribute("db.operation", "SELECT")
            
            # Simulate query time
            query_time = random.uniform(0.05, 0.2)
            time.sleep(query_time)
            db_span.set_attribute("db.query_time_ms", query_time * 1000)
        
        return {"booking_id": booking_id, "status": "processed"}

def create_booking(customer_id, service_type):
    """Create a booking with tracing"""
    with tracer.start_as_current_span("create_booking") as span:
        span.set_attribute("customer.id", customer_id)
        span.set_attribute("service.type", service_type)
        
        # Generate a booking ID
        booking_id = random.randint(10000, 99999)
        span.set_attribute("booking.id", booking_id)
        
        # Process the booking
        result = process_booking(booking_id)
        
        # Make an external API call
        with tracer.start_as_current_span("notification_service") as notify_span:
            notify_span.set_attribute("notification.type", "email")
            notify_span.set_attribute("notification.recipient", f"customer-{customer_id}@example.com")
            
            # Simulate API call time
            api_time = random.uniform(0.2, 0.8)
            time.sleep(api_time)
            notify_span.set_attribute("api.response_time_ms", api_time * 1000)
        
        return result

def main():
    """Main function to demonstrate tracing"""
    print(f"Sending traces to: {ADOT_ENDPOINT}")
    
    # Create some sample bookings
    for i in range(5):
        customer_id = random.randint(1000, 9999)
        service_types = ["hotel", "flight", "car", "package", "cruise"]
        service_type = random.choice(service_types)
        
        with tracer.start_as_current_span("booking_request") as span:
            span.set_attribute("request.id", f"req-{random.randint(100000, 999999)}")
            result = create_booking(customer_id, service_type)
            print(f"Created booking: {result}")
        
        # Add some delay between requests
        time.sleep(random.uniform(0.5, 2.0))
    
    # Make some external requests
    urls = [
        "https://www.example.com",
        "https://www.google.com",
        "https://www.amazon.com"
    ]
    
    for url in urls:
        make_request(url)
        time.sleep(random.uniform(0.5, 1.5))
    
    print("Completed sending sample traces")

if __name__ == "__main__":
    main()
