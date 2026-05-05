from fastapi import FastAPI
from app.routes import health, ingestion, alerts, policies, qa, compliance
from app.routes.sec_ingestion import router as sec_router

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