from fastapi import FastAPI
from app.routes import health

app = FastAPI()
app.include_router(health.router)

@app.get("/")
def root():
    return {"status": "ok", "service": "compliance-agent-api"}