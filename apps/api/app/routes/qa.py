from fastapi import APIRouter
from app.services.rag_service import answer_question

router = APIRouter()

@router.post("/qa")
def qa(query: str):
    answer = answer_question(query)
    return {"answer": answer}