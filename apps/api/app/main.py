from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uuid
from app.routes import health, ingestion, alerts, policies, qa, compliance, agents, reports
from app.routes.sec_ingestion import router as sec_router
from app.core.logging import setup_logging, get_logger
from app.dependencies.postgres import initialize_schema

setup_logging()
logger = get_logger(__name__)

app = FastAPI()

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

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
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
