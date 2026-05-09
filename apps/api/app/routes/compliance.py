from fastapi import APIRouter
from pydantic import BaseModel, Field, constr
from app.services.compliance_service import scan_email

router = APIRouter()

class ScanEmailRequest(BaseModel):
    email_id: constr(max_length=100) = Field(..., description="Email ID (max 100 characters)")

@router.post("/scan-email")
def scan(request: ScanEmailRequest):
    return scan_email(request.email_id)