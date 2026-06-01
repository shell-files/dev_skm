from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import date
from typing import Optional

from src.utils.db import findAll, findOne, getConn
from src.utils.settings import settings


SUPPORTED_CYCLE_TYPE = "PRE_DMA_G0"
SUPPORTED_TARGET_ROLE = "EMPLOYEE"
INVITE_EXPIRE_DAYS = 7
ASSIGNMENT_STATUS_ASSIGNED = "assigned"
ASSIGNMENT_STATUS_INVITED = "invited"
ASSIGNMENT_STATUS_UNASSIGNED = "unassigned"
ASSIGNABLE_ROLE_CODES = {"EMPLOYEE", "ESG", "ADMIN"}


def normalizeEmail(email: str) -> str:
    return str(email or "").strip().lower()


def hashText(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def maskEmail(email: Optional[str]) -> Optional[str]:
    if not email or "@" not in email:
        return email
    name, domain = email.split("@", 1)
    if not name:
        return f"***@{domain}"
    return f"{name[0]}***@{domain}"


def listG0MetricMaster() -> list[dict]:
    return findAll(
        """
        SELECT DISTINCT metric_id, metric_name_kr
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE delete_yn = 0
          AND active_yn = 1
          AND metric_id LIKE 'G0-%'
        ORDER BY metric_id
        """
    ) or []


def validateG0MetricIds(metricIds: list[str]) -> list[str]:
    cleaned = []
    for metricId in metricIds or []:
        value = str(metricId or "").strip()
        if not value:
            continue
        if "__" in value:
            raise ValueError(f"atomic_metric_id is not allowed: {value}")
        if value not in cleaned:
            cleaned.append(value)
    if not cleaned:
        raise ValueError("metricIds is required")
    allowed = {row["metric_id"] for row in listG0MetricMaster()}
    invalid = [metricId for metricId in cleaned if metricId not in allowed]
    if invalid:
        raise ValueError(f"Unsupported metricId: {', '.join(invalid)}")
    return cleaned


def resolveExistingUser(companyId: int, normalizedEmail: str) -> Optional[int]:
    rows = findAll(
        f"""
        SELECT
            u.id AS user_id,
            aes_d(r.role, '{settings.maria_db_key}') AS role_code
        FROM `with`.`USER` u
        JOIN `with`.`USER_ROLE` ur
          ON ur.user_id = u.id
         AND ur.company_id = ?
         AND ur.delete_yn = 0
        JOIN `with`.`ROLE` r
          ON r.id = ur.role_id
         AND r.delete_yn = 0
        WHERE u.email = aes_e(?, '{settings.maria_db_key}')
          AND u.delete_yn = 0
        ORDER BY u.id
        """,
        (companyId, normalizedEmail),
    ) or []
    for row in rows:
        roleCode = str(row.get("role_code") or "").strip().upper()
        if roleCode in ASSIGNABLE_ROLE_CODES and row.get("user_id") is not None:
            return int(row["user_id"])
    return None


def getCompanyName(companyId: int) -> str:
    companyName = getCompanyNameFromCompanyTable(companyId)
    if companyName:
        return companyName
    row = findOne(
        f"""
        SELECT COALESCE(company_code, CAST(company_id AS CHAR)) AS company_name
        FROM ESG_COMPANY_PROFILE
        WHERE company_id = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (companyId,),
    ) or {}
    return row.get("company_name") or str(companyId)


def getCompanyNameFromCompanyTable(companyId: int) -> Optional[str]:
    for schemaName in [None, "skm", "with"]:
        tableInfo = getCompanyTableInfo(schemaName)
        if not tableInfo:
            continue
        qualifiedTable = tableInfo["qualifiedTable"]
        idColumn = tableInfo["idColumn"]
        nameColumn = tableInfo["nameColumn"]
        deleteFilter = "AND delete_yn = 0" if tableInfo.get("hasDeleteYn") else ""
        try:
            row = findOne(
                f"""
                SELECT aes_d({nameColumn}, '{settings.maria_db_key}') AS company_name
                FROM {qualifiedTable}
                WHERE {idColumn} = ?
                  {deleteFilter}
                ORDER BY {idColumn} DESC
                LIMIT 1
                """,
                (companyId,),
            ) or {}
        except Exception:
            continue
        companyName = str(row.get("company_name") or "").strip()
        if companyName:
            return companyName
    return None


def getCompanyTableInfo(schemaName: Optional[str]) -> Optional[dict]:
    schemaFilter = "DATABASE()" if schemaName is None else "?"
    params = [] if schemaName is None else [schemaName]
    rows = findAll(
        f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = {schemaFilter}
          AND table_name = 'COMPANY'
        """,
        tuple(params),
    ) or []
    columns = {str(row.get("column_name") or "").lower() for row in rows}
    if not columns:
        return None
    idColumn = "company_id" if "company_id" in columns else "id" if "id" in columns else None
    nameColumn = "company_name" if "company_name" in columns else "name" if "name" in columns else None
    if not idColumn or not nameColumn:
        return None
    qualifiedTable = "COMPANY" if schemaName is None else f"`{schemaName}`.`COMPANY`"
    return {
        "qualifiedTable": qualifiedTable,
        "idColumn": idColumn,
        "nameColumn": nameColumn,
        "hasDeleteYn": "delete_yn" in columns,
    }


def bulkAssignMetrics(
    *,
    companyId: int,
    reportingYear: int,
    cycle: dict,
    metricIds: list[str],
    assigneeEmail: str,
    dueDate: Optional[date],
    sendInviteYn: bool,
    actorUserId: Optional[int],
) -> dict:
    normalizedEmail = normalizeEmail(assigneeEmail)
    if not normalizedEmail or "@" not in normalizedEmail:
        raise ValueError("assigneeEmail is invalid")

    assigneeUserId = resolveExistingUser(companyId, normalizedEmail)
    cycleId = int(cycle["id"])
    rawToken = None
    mailEvent = None
    inviteId = None
    inviteCreatedYn = False
    inviteReusedYn = False
    assignmentStatus = ASSIGNMENT_STATUS_ASSIGNED if assigneeUserId else ASSIGNMENT_STATUS_INVITED
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")

    try:
        with conn.cursor(dictionary=True) as cur:
            oldInviteIds = listAssignmentInviteIdsTx(cur, cycleId, companyId, metricIds)
            if assigneeUserId is None:
                invite = getReusableInviteTx(cur, companyId, cycleId, normalizedEmail)
                if invite:
                    inviteId = int(invite["id"])
                    inviteReusedYn = True
                    if sendInviteYn:
                        rawToken = secrets.token_urlsafe(32)
                        rotateInviteTokenTx(cur, inviteId, rawToken)
                else:
                    rawToken = secrets.token_urlsafe(32)
                    inviteId = insertInviteTx(
                        cur,
                        companyId=companyId,
                        cycleId=cycleId,
                        normalizedEmail=normalizedEmail,
                        rawToken=rawToken,
                        actorUserId=actorUserId,
                        sentYn=sendInviteYn,
                    )
                    inviteCreatedYn = True
                if sendInviteYn and rawToken:
                    mailEvent = buildInviteMailEvent(
                        companyName=getCompanyName(companyId),
                        email=normalizedEmail,
                        rawToken=rawToken,
                        metricCount=len(metricIds),
                        dueDate=dueDate,
                    )

            for metricId in metricIds:
                upsertAssignmentTx(
                    cur,
                    cycleId=cycleId,
                    companyId=companyId,
                    metricId=metricId,
                    assigneeUserId=assigneeUserId,
                    inviteId=inviteId,
                    assignmentStatus=assignmentStatus,
                    dueDate=dueDate,
                    actorUserId=actorUserId,
                )
            for oldInviteId in oldInviteIds:
                if oldInviteId != inviteId:
                    revokeOrphanInviteTx(cur, oldInviteId)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "companyId": companyId,
        "reportingYear": reportingYear,
        "cycleId": cycleId,
        "metricIds": metricIds,
        "assignmentCount": len(metricIds),
        "assignmentStatus": assignmentStatus,
        "assigneeResolvedYn": assigneeUserId is not None,
        "inviteCreatedYn": inviteCreatedYn,
        "inviteReusedYn": inviteReusedYn,
        "inviteId": inviteId,
        "mailEvent": mailEvent,
    }


def getReusableInviteTx(cur, companyId: int, cycleId: int, normalizedEmail: str) -> dict:
    cur.execute(
        """
        SELECT *
        FROM ESG_ONBOARDING_INVITE
        WHERE company_id = ?
          AND esg_onboarding_cycle_id = ?
          AND invite_email_hash = ?
          AND invite_status = 'pending'
          AND expires_at > CURRENT_TIMESTAMP
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
        FOR UPDATE
        """,
        (companyId, cycleId, hashText(normalizedEmail)),
    )
    return cur.fetchone() or {}


def insertInviteTx(
    cur,
    *,
    companyId: int,
    cycleId: int,
    normalizedEmail: str,
    rawToken: str,
    actorUserId: Optional[int],
    sentYn: bool,
) -> int:
    cur.execute(
        f"""
        INSERT INTO ESG_ONBOARDING_INVITE (
            invite_public_id,
            company_id,
            esg_onboarding_cycle_id,
            invite_email_enc,
            invite_email_hash,
            target_role_code,
            invite_status,
            invite_token_hash,
            expires_at,
            invited_by_user_id,
            last_sent_at,
            resend_count,
            delete_yn
        ) VALUES (?, ?, ?, aes_e(?, '{settings.maria_db_key}'), ?, ?, 'pending', ?, DATE_ADD(CURRENT_TIMESTAMP, INTERVAL ? DAY), ?, CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END, CASE WHEN ? THEN 1 ELSE 0 END, 0)
        """,
        (
            uuid.uuid4().hex,
            companyId,
            cycleId,
            normalizedEmail,
            hashText(normalizedEmail),
            SUPPORTED_TARGET_ROLE,
            hashText(rawToken),
            INVITE_EXPIRE_DAYS,
            actorUserId,
            1 if sentYn else 0,
            1 if sentYn else 0,
        ),
    )
    return int(cur.lastrowid)


def rotateInviteTokenTx(cur, inviteId: int, rawToken: str) -> None:
    cur.execute(
        """
        UPDATE ESG_ONBOARDING_INVITE
        SET invite_token_hash = ?,
            expires_at = DATE_ADD(CURRENT_TIMESTAMP, INTERVAL ? DAY),
            last_sent_at = CURRENT_TIMESTAMP,
            resend_count = resend_count + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND invite_status = 'pending'
          AND delete_yn = 0
        """,
        (hashText(rawToken), INVITE_EXPIRE_DAYS, inviteId),
    )


def upsertAssignmentTx(
    cur,
    *,
    cycleId: int,
    companyId: int,
    metricId: str,
    assigneeUserId: Optional[int],
    inviteId: Optional[int],
    assignmentStatus: str,
    dueDate: Optional[date],
    actorUserId: Optional[int],
) -> None:
    cur.execute(
        """
        INSERT INTO ESG_METRIC_ASSIGNMENT (
            esg_onboarding_cycle_id,
            company_id,
            metric_id,
            invite_id,
            assignee_user_id,
            assignee_email,
            assignment_status,
            assignment_source_type,
            due_date,
            created_by_user_id,
            delete_yn
        ) VALUES (?, ?, ?, ?, ?, NULL, ?, 'manual', ?, ?, 0)
        ON DUPLICATE KEY UPDATE
            invite_id = VALUES(invite_id),
            assignee_user_id = VALUES(assignee_user_id),
            assignee_email = NULL,
            assignment_status = VALUES(assignment_status),
            assignment_source_type = 'manual',
            due_date = VALUES(due_date),
            created_by_user_id = VALUES(created_by_user_id),
            delete_yn = 0,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            cycleId,
            companyId,
            metricId,
            inviteId,
            assigneeUserId,
            assignmentStatus,
            dueDate.isoformat() if hasattr(dueDate, "isoformat") else dueDate,
            actorUserId,
        ),
    )


def buildInviteMailEvent(
    *,
    companyName: str,
    email: str,
    rawToken: str,
    metricCount: int,
    dueDate: Optional[date],
) -> dict:
    return {
        "type": 5,
        "email": email,
        "companyName": companyName,
        "inviteLink": f"http://main.{settings.host_ip}/onboarding-invite/{rawToken}",
        "metricCount": metricCount,
        "dueDate": dueDate.isoformat() if hasattr(dueDate, "isoformat") else dueDate,
    }


def listAssignments(companyId: int, reportingYear: int, cycle: dict) -> list[dict]:
    metricRows = listG0MetricMaster()
    cycleId = int(cycle["id"]) if cycle else None
    assignmentRows = []
    if cycleId is not None:
        assignmentRows = findAll(
            f"""
            SELECT
                a.metric_id,
                a.assignment_status,
                a.assignee_user_id,
                a.assignee_email,
                a.due_date,
                a.invite_id,
                i.invite_status,
                aes_d(i.invite_email_enc, '{settings.maria_db_key}') AS invite_email,
                aes_d(u.email, '{settings.maria_db_key}') AS user_email
            FROM ESG_METRIC_ASSIGNMENT a
            LEFT JOIN ESG_ONBOARDING_INVITE i
              ON i.id = a.invite_id
             AND i.delete_yn = 0
            LEFT JOIN `with`.`USER` u
              ON u.id = a.assignee_user_id
             AND u.delete_yn = 0
            WHERE a.esg_onboarding_cycle_id = ?
              AND a.company_id = ?
              AND a.delete_yn = 0
            ORDER BY a.metric_id
            """,
            (cycleId, companyId),
        ) or []
    assignmentByMetric = {row["metric_id"]: row for row in assignmentRows}
    items = []
    for metric in metricRows:
        metricId = metric["metric_id"]
        assignment = assignmentByMetric.get(metricId) or {}
        email = None
        if assignment.get("assignment_status") != ASSIGNMENT_STATUS_UNASSIGNED:
            email = assignment.get("invite_email") or assignment.get("user_email") or assignment.get("assignee_email")
        items.append(
            {
                "metricId": metricId,
                "metricName": metric.get("metric_name_kr"),
                "assignmentStatus": assignment.get("assignment_status") or ASSIGNMENT_STATUS_UNASSIGNED,
                "assigneeUserId": assignment.get("assignee_user_id"),
                "assigneeEmailMasked": maskEmail(email),
                "dueDate": str(assignment.get("due_date")) if assignment.get("due_date") is not None else None,
                "inviteId": assignment.get("invite_id"),
                "inviteStatus": assignment.get("invite_status"),
            }
        )
    return items


def listAssignmentInviteIdsTx(cur, cycleId: int, companyId: int, metricIds: list[str]) -> list[int]:
    if not metricIds:
        return []
    placeholders = ", ".join(["?"] * len(metricIds))
    cur.execute(
        f"""
        SELECT DISTINCT invite_id
        FROM ESG_METRIC_ASSIGNMENT
        WHERE esg_onboarding_cycle_id = ?
          AND company_id = ?
          AND metric_id IN ({placeholders})
          AND invite_id IS NOT NULL
          AND delete_yn = 0
        """,
        (cycleId, companyId, *metricIds),
    )
    return [int(row["invite_id"]) for row in cur.fetchall() or []]


def bulkUnassignMetrics(companyId: int, reportingYear: int, cycle: dict, metricIds: list[str]) -> dict:
    cycleId = int(cycle["id"])
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    revokedInviteIds = []
    try:
        with conn.cursor(dictionary=True) as cur:
            placeholders = ", ".join(["?"] * len(metricIds))
            cur.execute(
                f"""
                SELECT DISTINCT invite_id
                FROM ESG_METRIC_ASSIGNMENT
                WHERE esg_onboarding_cycle_id = ?
                  AND company_id = ?
                  AND metric_id IN ({placeholders})
                  AND invite_id IS NOT NULL
                  AND delete_yn = 0
                """,
                (cycleId, companyId, *metricIds),
            )
            affectedInviteIds = [int(row["invite_id"]) for row in cur.fetchall() or []]
            cur.execute(
                f"""
                UPDATE ESG_METRIC_ASSIGNMENT
                SET assignee_user_id = NULL,
                    assignee_email = NULL,
                    invite_id = NULL,
                    assignment_status = ?,
                    due_date = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE esg_onboarding_cycle_id = ?
                  AND company_id = ?
                  AND metric_id IN ({placeholders})
                  AND delete_yn = 0
                """,
                (ASSIGNMENT_STATUS_UNASSIGNED, cycleId, companyId, *metricIds),
            )
            unassignedCount = cur.rowcount
            for inviteId in affectedInviteIds:
                if revokeOrphanInviteTx(cur, inviteId):
                    revokedInviteIds.append(inviteId)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {
        "companyId": companyId,
        "reportingYear": reportingYear,
        "cycleId": cycleId,
        "metricIds": metricIds,
        "unassignedCount": unassignedCount,
        "revokedInviteIds": revokedInviteIds,
    }


def revokeOrphanInviteTx(cur, inviteId: int) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS active_count
        FROM ESG_METRIC_ASSIGNMENT
        WHERE invite_id = ?
          AND assignment_status <> ?
          AND delete_yn = 0
        """,
        (inviteId, ASSIGNMENT_STATUS_UNASSIGNED),
    )
    row = cur.fetchone() or {}
    if int(row.get("active_count") or 0) > 0:
        return False
    cur.execute(
        """
        UPDATE ESG_ONBOARDING_INVITE
        SET invite_status = 'revoked',
            revoked_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND invite_status = 'pending'
          AND delete_yn = 0
        """,
        (inviteId,),
    )
    return cur.rowcount > 0


__all__ = [
    "SUPPORTED_CYCLE_TYPE",
    "SUPPORTED_TARGET_ROLE",
    "INVITE_EXPIRE_DAYS",
    "ASSIGNMENT_STATUS_ASSIGNED",
    "ASSIGNMENT_STATUS_INVITED",
    "ASSIGNMENT_STATUS_UNASSIGNED",
    "ASSIGNABLE_ROLE_CODES",
    "normalizeEmail",
    "hashText",
    "maskEmail",
    "listG0MetricMaster",
    "validateG0MetricIds",
    "resolveExistingUser",
    "getCompanyName",
    "bulkAssignMetrics",
    "listAssignments",
    "bulkUnassignMetrics",
]
