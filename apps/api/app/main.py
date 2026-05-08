from fastapi import FastAPI
from app.routes import health, ingestion, alerts, policies, qa, compliance, agents, reports
from app.routes.sec_ingestion import router as sec_router
from app.core.logging import setup_logging, get_logger
from app.dependencies.postgres import initialize_schema

setup_logging()
logger = get_logger(__name__)

app = FastAPI()
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
