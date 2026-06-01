from fastapi import APIRouter, Depends
from src.utils.issue import getSubIssueAtomicMap
from src.utils.auth import get_token

router = APIRouter()

@router.post("")
def sub_atomic_map(userModel = Depends(get_token)):
    return getSubIssueAtomicMap(userModel)