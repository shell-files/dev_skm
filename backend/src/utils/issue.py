from fastapi import Depends
from src.utils.auth import get_token
from src.utils.db import findAll
from src.models.model import ResponseModel
from src.utils.settings import settings


def getSubIssueAtomicMap(userModel = Depends(get_token)):
    try:
        sql = """
            SELECT
                sub_issue_code,
                metric_id,
                atomic_metric_id,
                map_scope,
                required_yn
            FROM ESG_SUB_ISSUE_ATOMIC_MAP
            WHERE delete_yn = 0
            ORDER BY sub_issue_code, metric_id, atomic_metric_id
        """

        rows = findAll(sql)

        return ResponseModel(True, "조회 성공", rows)

    except Exception as e:
        return ResponseModel(False, f"조회 실패: {str(e)}")