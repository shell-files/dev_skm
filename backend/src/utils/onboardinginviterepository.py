from __future__ import annotations

import secrets
from typing import Optional

from src.utils.db import findAll, findOne, getConn
from src.utils.onboardingassignmentrepository import (
    ASSIGNMENT_STATUS_UNASSIGNED,
    INVITE_EXPIRE_DAYS,
    buildInviteMailEvent,
    getCompanyName,
    hashText,
    maskEmail,
)
from src.utils.settings import settings


def getInvite(inviteId: int) -> dict:
    return findOne(
        f"""
        SELECT
            i.*,
            aes_d(i.invite_email_enc, '{settings.maria_db_key}') AS invite_email
        FROM ESG_ONBOARDING_INVITE i
        WHERE i.id = ?
          AND i.delete_yn = 0
        LIMIT 1
        """,
        (inviteId,),
    ) or {}


def listInvites(companyId: int, cycleId: Optional[int], status: Optional[str]) -> list[dict]:
    params = [companyId]
    cycleFilter = ""
    statusFilter = ""
    if cycleId is not None:
        cycleFilter = "AND i.esg_onboarding_cycle_id = ?"
        params.append(cycleId)
    if status:
        statusFilter = "AND i.invite_status = ?"
        params.append(status)
    rows = findAll(
        f"""
        SELECT
            i.id AS inviteId,
            i.invite_public_id AS invitePublicId,
            aes_d(i.invite_email_enc, '{settings.maria_db_key}') AS inviteEmail,
            i.target_role_code AS targetRoleCode,
            i.invite_status AS inviteStatus,
            i.expires_at AS expiresAt,
            i.last_sent_at AS lastSentAt,
            i.resend_count AS resendCount,
            GROUP_CONCAT(a.metric_id ORDER BY a.metric_id) AS assignedMetricIdsCsv
        FROM ESG_ONBOARDING_INVITE i
        LEFT JOIN ESG_METRIC_ASSIGNMENT a
          ON a.invite_id = i.id
         AND a.delete_yn = 0
         AND a.assignment_status <> ?
        WHERE i.company_id = ?
          {cycleFilter}
          {statusFilter}
          AND i.delete_yn = 0
        GROUP BY
            i.id,
            i.invite_public_id,
            i.invite_email_enc,
            i.target_role_code,
            i.invite_status,
            i.expires_at,
            i.last_sent_at,
            i.resend_count
        ORDER BY i.updated_at DESC, i.id DESC
        """,
        (ASSIGNMENT_STATUS_UNASSIGNED, *params),
    ) or []
    return [
        {
            "inviteId": int(row["inviteId"]),
            "invitePublicId": row.get("invitePublicId"),
            "inviteEmailMasked": maskEmail(row.get("inviteEmail")),
            "targetRoleCode": row.get("targetRoleCode"),
            "inviteStatus": row.get("inviteStatus"),
            "expiresAt": str(row.get("expiresAt")) if row.get("expiresAt") is not None else None,
            "lastSentAt": str(row.get("lastSentAt")) if row.get("lastSentAt") is not None else None,
            "resendCount": int(row.get("resendCount") or 0),
            "assignedMetricIds": [
                metricId
                for metricId in str(row.get("assignedMetricIdsCsv") or "").split(",")
                if metricId
            ],
        }
        for row in rows
    ]


def resendInvite(inviteId: int, companyId: int) -> dict:
    rawToken = secrets.token_urlsafe(32)
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    assignedMetricIds = []
    dueDate = None
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                f"""
                SELECT
                    *,
                    aes_d(invite_email_enc, '{settings.maria_db_key}') AS invite_email
                FROM ESG_ONBOARDING_INVITE
                WHERE id = ?
                  AND company_id = ?
                  AND invite_status = 'pending'
                  AND delete_yn = 0
                FOR UPDATE
                """,
                (inviteId, companyId),
            )
            invite = cur.fetchone()
            if not invite:
                raise ValueError("Pending invite was not found")
            cur.execute(
                """
                SELECT metric_id, due_date
                FROM ESG_METRIC_ASSIGNMENT
                WHERE invite_id = ?
                  AND assignment_status <> ?
                  AND delete_yn = 0
                ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date, metric_id
                """,
                (inviteId, ASSIGNMENT_STATUS_UNASSIGNED),
            )
            assignmentRows = cur.fetchall() or []
            if not assignmentRows:
                raise ValueError("Invite has no active metric assignments")
            assignedMetricIds = [row["metric_id"] for row in assignmentRows]
            dueDate = next((row.get("due_date") for row in assignmentRows if row.get("due_date") is not None), None)
            cur.execute(
                """
                UPDATE ESG_ONBOARDING_INVITE
                SET invite_token_hash = ?,
                    expires_at = DATE_ADD(CURRENT_TIMESTAMP, INTERVAL ? DAY),
                    last_sent_at = CURRENT_TIMESTAMP,
                    resend_count = resend_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (hashText(rawToken), INVITE_EXPIRE_DAYS, inviteId),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    mailEvent = buildInviteMailEvent(
        companyName=getCompanyName(companyId),
        email=invite["invite_email"],
        rawToken=rawToken,
        metricCount=len(assignedMetricIds),
        dueDate=dueDate,
    )
    return {
        "companyId": companyId,
        "inviteId": inviteId,
        "inviteStatus": "pending",
        "mailEvent": mailEvent,
    }


def revokeInvite(inviteId: int, companyId: int) -> dict:
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT *
                FROM ESG_ONBOARDING_INVITE
                WHERE id = ?
                  AND company_id = ?
                  AND invite_status = 'pending'
                  AND delete_yn = 0
                FOR UPDATE
                """,
                (inviteId, companyId),
            )
            invite = cur.fetchone()
            if not invite:
                raise ValueError("Pending invite was not found")
            cur.execute(
                """
                UPDATE ESG_ONBOARDING_INVITE
                SET invite_status = 'revoked',
                    revoked_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (inviteId,),
            )
            cur.execute(
                """
                UPDATE ESG_METRIC_ASSIGNMENT
                SET assignee_user_id = NULL,
                    assignee_email = NULL,
                    invite_id = NULL,
                    assignment_status = ?,
                    due_date = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE invite_id = ?
                  AND delete_yn = 0
                """,
                (ASSIGNMENT_STATUS_UNASSIGNED, inviteId),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"companyId": companyId, "inviteId": inviteId, "inviteStatus": "revoked"}


def listAssignedMetricIds(inviteId: int) -> list[str]:
    rows = findAll(
        """
        SELECT metric_id
        FROM ESG_METRIC_ASSIGNMENT
        WHERE invite_id = ?
          AND assignment_status <> ?
          AND delete_yn = 0
        ORDER BY metric_id
        """,
        (inviteId, ASSIGNMENT_STATUS_UNASSIGNED),
    ) or []
    return [row["metric_id"] for row in rows]


__all__ = [
    "getInvite",
    "listInvites",
    "resendInvite",
    "revokeInvite",
    "listAssignedMetricIds",
]
