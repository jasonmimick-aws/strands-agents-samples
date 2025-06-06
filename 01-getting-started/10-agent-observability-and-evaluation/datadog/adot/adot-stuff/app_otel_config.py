"""
Helper script to configure OpenTelemetry in your application to send traces to ADOT Collector
"""

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

def configure_otel(service_name, adot_endpoint=None):
    """
    Configure OpenTelemetry to send traces to ADOT Collector
    
    Args:
        service_name (str): Name of your service
        adot_endpoint (str, optional): ADOT Collector endpoint. If not provided, 
                                      will use OTEL_EXPORTER_OTLP_ENDPOINT env var
    """
    # Get the ADOT endpoint from environment variable if not provided
    if not adot_endpoint:
        adot_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
    
    # Create a resource with service name
    resource = Resource.create({SERVICE_NAME: service_name})
    
    # Create a tracer provider
    tracer_provider = TracerProvider(resource=resource)
    
    # Create an OTLP exporter
    otlp_exporter = OTLPSpanExporter(endpoint=adot_endpoint)
    
    # Add the exporter to the tracer provider
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    # Set the tracer provider
    trace.set_tracer_provider(tracer_provider)
    
    print(f"OpenTelemetry configured to send traces to {adot_endpoint}")
    
    # Return the tracer
    return trace.get_tracer(service_name)

# Example usage:
# tracer = configure_otel("my-service", "http://adot-collector-endpoint:4318/v1/traces")
# 
# with tracer.start_as_current_span("my-operation") as span:
#     span.set_attribute("attribute.name", "attribute-value")
#     # Your code here
