from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, constr
from app.services.compliance_service import scan_email
from app.core.audit import log_compliance_scan

router = APIRouter()

class ScanEmailRequest(BaseModel):
    email_id: constr(max_length=100) = Field(..., description="Email ID (max 100 characters)")

@router.post("/scan-email")
def scan(request: ScanEmailRequest, http_request: Request):
    try:
        result = scan_email(request.email_id)
        session_id = http_request.headers.get("X-Request-ID")
        log_compliance_scan(request.email_id, session_id, outcome="success")
        return result
    except Exception as e:
        session_id = http_request.headers.get("X-Request-ID")
        log_compliance_scan(request.email_id, session_id, outcome="failure")
        raise