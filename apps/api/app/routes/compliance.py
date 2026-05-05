from fastapi import APIRouter
from app.services.compliance_service import scan_email

router = APIRouter()

@router.post("/scan-email")
def scan(email_id: str):
    return scan_email(email_id)