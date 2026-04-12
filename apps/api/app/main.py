from fastapi import FastAPI
from app.routes import health, ingestion, alerts, policies, qa

app = FastAPI()
app.include_router(health.router)
app.include_router(ingestion.router)
app.include_router(alerts.router)
app.include_router(policies.router)
app.include_router(qa.router)

@app.get("/")
def root():
    return {"status": "ok", "service": "compliance-agent-api"}