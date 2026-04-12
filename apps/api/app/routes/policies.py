from fastapi import APIRouter
from app.services.policy_indexer import index_policies

router = APIRouter()

@router.post("/index-policies")
def run_indexing():
    return index_policies()