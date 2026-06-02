from fastapi import APIRouter
from src.utils.db import findAll
from src.models.model import ResponseModel

router = APIRouter()

@router.post("/sub-atomic-map")
def get_sub_atomic_map():
    sql = """
        SELECT
            sub_issue_code,
            metric_id,
            atomic_metric_id,
            map_scope,
            required_yn
        FROM ESG_SUB_ISSUE_ATOMIC_MAP
        WHERE delete_yn = 0
        ORDER BY sub_issue_code, metric_id, sort_order
    """

    rows = findAll(sql)

    return ResponseModel(
        True,
        "sub issue atomic map 조회 성공",
        rows
    )