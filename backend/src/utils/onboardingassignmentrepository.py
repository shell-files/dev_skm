from __future__ import annotations

from datetime import date
from typing import Optional

from src.utils.db import findAll, findOne, getConn
from src.utils.rediscl import setInviteRedis
from src.utils.settings import settings
from src.utils.tokenset import generateInviteTokenWithUuid


SUPPORTED_TARGET_ROLE = "EMPLOYEE"
ASSIGNMENT_STATUS_ASSIGNED = "assigned"
ASSIGNMENT_STATUS_INVITED = "invited"
ASSIGNMENT_STATUS_UNASSIGNED = "unassigned"
ASSIGNABLE_ROLE_CODES = {"EMPLOYEE", "ESG", "ADMIN"}
INVITE_STATE_PENDING = "승인대기"
INVITE_STATE_COMPLETED = "승인완료"
INVITE_STATE_REVOKED = "승인취소"


def normalizeEmail(email: str) -> str:
    return str(email or "").strip().lower()


def maskEmail(email: Optional[str]) -> Optional[str]:
    if not email or "@" not in email:
        return email
    name, domain = email.split("@", 1)
    if not name:
        return f"***@{domain}"
    return f"{name[0]}***@{domain}"


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
                roleId = resolveRoleIdTx(cur, SUPPORTED_TARGET_ROLE)
                companyName = getCompanyName(companyId)
                inviteId = insertCommonInviteTx(
                    cur,
                    companyId=companyId,
                    actorUserId=actorUserId,
                    roleId=roleId,
                    normalizedEmail=normalizedEmail,
                )
                inviteCreatedYn = True
                token, inviteUuid = generateInviteTokenWithUuid(
                    [],
                    companyName,
                    normalizedEmail,
                    roleId,
                    0,
                    inviteId,
                    companyId,
                )
                setInviteRedis(inviteUuid, token, inviteExpireSeconds())
                if sendInviteYn:
                    mailEvent = buildCommonInviteMailEvent(normalizedEmail, inviteUuid, companyName)

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


def insertCommonInviteTx(
    cur,
    *,
    companyId: int,
    actorUserId: Optional[int],
    roleId: int,
    normalizedEmail: str,
) -> int:
    if actorUserId is None:
        raise ValueError("actorUserId is required for invite creation")
    cur.execute(
        """
        INSERT INTO INVITE (
            company_id,
            user_id,
            role_id,
            email,
            state,
            delete_yn
        ) VALUES (?, ?, ?, ?, ?, 0)
        """,
        (companyId, actorUserId, roleId, normalizedEmail, INVITE_STATE_PENDING),
    )
    return int(cur.lastrowid)


def buildCommonInviteMailEvent(email: str, inviteUuid: str, companyName: str) -> dict:
    return {
        "type": 1,
        "email": email,
        "uuid": inviteUuid,
        "companyName": companyName,
    }


def inviteExpireSeconds() -> int:
    return max(1, int(settings.invite_token_expire_days)) * 24 * 60 * 60


def resolveRoleIdTx(cur, roleCode: str) -> int:
    cur.execute(
        f"""
        SELECT id
        FROM `with`.`ROLE`
        WHERE aes_d(role, '{settings.maria_db_key}') = ?
          AND delete_yn = 0
        ORDER BY id
        LIMIT 1
        """,
        (roleCode,),
    )
    row = cur.fetchone() or {}
    if row.get("id") is None:
        raise ValueError(f"Role was not found: {roleCode}")
    return int(row["id"])


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


def listAssignments(companyId: int, reportingYear: int, cycle: dict) -> list[dict]:
    cycleId = int(cycle["id"]) if cycle else None
    metricRows = listCycleMetricScope(cycleId, companyId) if cycleId is not None else []
    assignmentRows = listAssignmentRows(cycleId, companyId) if cycleId is not None else []
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


def listAssignmentRows(cycleId: int, companyId: int) -> list[dict]:
    return findAll(
        f"""
        SELECT
            a.id AS assignment_id,
            a.metric_id,
            a.assignment_status,
            a.assignee_user_id,
            a.assignee_email,
            a.due_date,
            a.invite_id,
            i.state AS invite_status,
            i.email AS invite_email,
            aes_d(u.email, '{settings.maria_db_key}') AS user_email
        FROM ESG_METRIC_ASSIGNMENT a
        LEFT JOIN INVITE i
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
        UPDATE INVITE
        SET state = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND delete_yn = 0
        """,
        (INVITE_STATE_REVOKED, inviteId),
    )
    return cur.rowcount > 0


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


def listCycleMetricScope(cycleId: int, companyId: int) -> list[dict]:
    return findAll(
        """
        SELECT s.metric_id, m.metric_name_kr
        FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE s
        LEFT JOIN (
            SELECT metric_id, MIN(metric_name_kr) AS metric_name_kr
            FROM ESG_ATOMIC_METRIC_MASTER
            WHERE delete_yn = 0
              AND active_yn = 1
            GROUP BY metric_id
        ) m
          ON m.metric_id = s.metric_id
        WHERE s.esg_onboarding_cycle_id = ?
          AND s.company_id = ?
          AND s.active_yn = 1
          AND s.delete_yn = 0
        ORDER BY s.display_order, s.metric_id
        """,
        (cycleId, companyId),
    ) or []


def getCompanyName(companyId: int) -> str:
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
    row = findOne(
        """
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
