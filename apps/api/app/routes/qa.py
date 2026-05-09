from fastapi import APIRouter
from pydantic import BaseModel, Field, constr
from app.services.rag_service import answer_question

router = APIRouter()

class QARequest(BaseModel):
    query: constr(max_length=2000) = Field(..., description="Query text (max 2000 characters)")

@router.post("/qa")
def qa(request: QARequest):
    answer = answer_question(request.query)
    return {"answer": answer}