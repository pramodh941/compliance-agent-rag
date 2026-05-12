from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uuid
import signal
import sys
import time
from app.routes import health, ingestion, alerts, policies, qa, compliance, agents, reports
from app.routes.sec_ingestion import router as sec_router
from app.core.logging import setup_logging, get_logger
from app.dependencies.postgres import initialize_schema

setup_logging()
logger = get_logger(__name__)

app = FastAPI()

# Graceful shutdown handling
def signal_handler(sig, frame):
    logger.info("Shutdown signal received, closing gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Request tracing middleware with correlation ID
@app.middleware("http")
async def request_tracing(request: Request, call_next):
    start_time = time.time()
    
    # Get or generate correlation ID
    correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    
    # Log request start
    logger.info(
        "Request started",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "client_host": request.client.host if request.client else None
        }
    )
    
    response = await call_next(request)
    
    # Log request completion with duration
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        "Request completed",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2)
        }
    )
    
    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id
    
    return response

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

# CORS middleware (configure allowed origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure specific origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(health.router)
app.include_router(ingestion.router)
app.include_router(alerts.router)
app.include_router(sec_router)
app.include_router(policies.router)
app.include_router(qa.router)
app.include_router(compliance.router)
app.include_router(agents.router)
app.include_router(reports.router)

@app.get("/")
def root():
    return {"status": "ok", "service": "compliance-agent-api"}


@app.on_event("startup")
def startup():
    try:
        initialize_schema()
        logger.info("Database schema initialized", extra={"status": "ok"})
    except Exception:
        logger.exception("Database schema initialization failed", extra={"status": "error"})
