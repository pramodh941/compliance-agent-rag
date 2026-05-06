from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

resource = Resource.create({
    "service.name": "compliance-mcp"
})

provider = TracerProvider(resource=resource)

span_processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(span_processor)

trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)