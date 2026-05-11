from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, constr
from app.services.rag_service import answer_question
from app.core.audit import log_query_event

router = APIRouter()

class QARequest(BaseModel):
    query: constr(max_length=2000) = Field(..., description="Query text (max 2000 characters)")

@router.post("/qa")
def qa(request: QARequest, http_request: Request):
    try:
        answer = answer_question(request.query)
        session_id = http_request.headers.get("X-Request-ID")
        log_query_event(request.query, session_id, outcome="success")
        return {"answer": answer}
    except Exception as e:
        session_id = http_request.headers.get("X-Request-ID")
        log_query_event(request.query, session_id, outcome="failure")
        raise