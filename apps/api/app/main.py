from fastapi import FastAPI
from app.routes import health, ingestion, alerts, policies, qa, compliance
from app.routes.sec_ingestion import router as sec_router
import logging
import sys

# Configure logging to show detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

# Set specific loggers
logging.getLogger("app.services.ollama_client").setLevel(logging.DEBUG)
logging.getLogger("app.services.policy_indexer").setLevel(logging.DEBUG)
logging.getLogger("app.services.ingest_docs").setLevel(logging.DEBUG)
logging.getLogger("app.services.sec_ingestion_service").setLevel(logging.DEBUG)

app = FastAPI()
app.include_router(health.router)
app.include_router(ingestion.router)
app.include_router(alerts.router)
app.include_router(sec_router)
app.include_router(policies.router)
app.include_router(qa.router)
app.include_router(compliance.router)

@app.get("/")
def root():
    return {"status": "ok", "service": "compliance-agent-api"}