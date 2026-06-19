"""
onboardingassignmentrepository.py
레이어: Repository
역할: 온보딩 지표 배정 요청·이력 DB 조회 및 저장.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from src.utils.db import findAll, findOne, getConn
from src.utils.typeutils import maskEmail
from src.utils.invite import inviteExpireSeconds
from src.repositories.companyutils import getCompanyName, getCompanyTableInfo
from src.utils.rediscl import setInviteRedis
from src.utils.settings import settings
from src.utils.tokenset import generateInviteTokenWithUuid
from src.repositories import onboardingscoperepository as scopeRepo


SUPPORTED_TARGET_ROLE = "EMPLOYEE"
ASSIGNMENT_STATUS_ASSIGNED = "assigned"
ASSIGNMENT_STATUS_INVITED = "invited"
ASSIGNMENT_STATUS_UNASSIGNED = "unassigned"
ASSIGNABLE_ROLE_CODES = {"EMPLOYEE", "ESG", "ADMIN"}
INVITE_STATE_PENDING = "승인대기"
INVITE_STATE_COMPLETED = "승인완료"
INVITE_STATE_REVOKED = "승인취소"


# 이메일 소문자·공백 정규화
def normalizeEmail(email: str) -> str:
    return str(email or "").strip().lower()


# 이메일 기준 기존 사용자 ID 조회 — 배정 가능 역할(EMPLOYEE/ESG/ADMIN) 필터
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


# 지표 목록 일괄 배정 — 기존 사용자면 직접 배정, 없으면 초대 생성
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
            requireWritableAssignmentCycleTx(cur, cycle, companyId)
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
                redisResult = setInviteRedis(inviteUuid, token, inviteExpireSeconds())
                if not redisResult.get("status"):
                    raise RuntimeError("Invite token Redis save failed")
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


# 공통 초대 레코드 INSERT — actorUserId 필수 (트랜잭션 커서용)
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


# 초대 메일 이벤트 dict 구성
def buildCommonInviteMailEvent(email: str, inviteUuid: str, companyName: str) -> dict:
    return {
        "type": 1,
        "email": email,
        "uuid": inviteUuid,
        "companyName": companyName,
    }


# 역할 코드 기준 role_id 조회 — 없으면 ValueError (트랜잭션 커서용)
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


# 지표 배정 upsert (트랜잭션 커서용)
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


# 사이클 기준 지표 배정 목록 조회 — 마스킹된 이메일 포함
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


# 사이클·기업 기준 배정 행 목록 조회 — 초대·사용자 이메일 포함
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


# 사이클·지표 기준 기존 초대 ID 목록 조회 (트랜잭션 커서용)
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


# 지표 목록 일괄 배정 해제 — 고아 초대 자동 취소
def bulkUnassignMetrics(companyId: int, reportingYear: int, cycle: dict, metricIds: list[str]) -> dict:
    cycleId = int(cycle["id"])
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    revokedInviteIds = []
    try:
        with conn.cursor(dictionary=True) as cur:
            requireWritableAssignmentCycleTx(cur, cycle, companyId)
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


# 배정 쓰기 가능 사이클 여부 검증 (트랜잭션 커서용)
def requireWritableAssignmentCycleTx(cur, cycle: dict, companyId: int) -> None:
    scopeRepo.requireWritableCycleTx(
        cur,
        cycle,
        companyId,
        batchId=cycle.get("parent_rollup_batch_id"),
    )


# 활성 배정 없는 고아 초대 취소 — 취소 성공 여부 반환 (트랜잭션 커서용)
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


# 초대 ID 기준 배정된 지표 ID 목록 조회
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


# 사이클·기업 기준 지표 범위 목록 조회 — 표시 순서 정렬
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


