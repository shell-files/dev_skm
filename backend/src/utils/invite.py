"""
invite.py
레이어: Utils
역할: 초대 링크 검증 및 회원가입 처리 — 토큰 기반 초대 수락 흐름.
"""
from fastapi import Depends
from fastapi.responses import HTMLResponse

from src.models.model import (
    ResponseModel,
    inviteConsultantModel,
    inviteMemberModel,
    inviteSignUpUserInfo,
)
from src.utils.auth import get_token
from src.utils.db import addKey, exists, findOne, getConn, save
from src.utils.kafkasv import sendToKafka
from src.utils.rediscl import delInviteRedis, getInviteRedis, setInviteRedis
from src.utils.settings import settings
from src.utils.tokenset import decryptFromJwe, generateConsultantInviteToken, generateInviteTokenWithUuid


INVITE_STATE_PENDING = "승인대기"
INVITE_STATE_COMPLETED = "승인완료"
INVITE_STATE_REVOKED = "승인취소"
INVITE_STATE_EXPIRED = "토큰만료"


def inviteProcess(inviteId: str):
    html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>W.I.T.H - 회원가입</title>
        <link rel="icon" type="image/svg+xml" href="https://avatars.githubusercontent.com/u/276547385?s=200&v=4" />
        <link rel="stylesheet" href="https://shell-files.github.io/project_ui/styles/style.css">
        <link rel="stylesheet" href="/static/invite.css">
        <script src="https://unpkg.com/react@18/umd/react.development.js" crossorigin></script>
        <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js" crossorigin></script>
        <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
        <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/sweetalert2/11.23.0/sweetalert2.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11.26.24/dist/sweetalert2.all.min.js"></script>
        <script src="/static/App.jsx" type="text/babel"></script>
    </head>
    <body>
      <div id="signup_page" class="signup-container"></div>
      <script src="/static/Main.jsx" type="text/babel"></script>
    </body>
    </html>
    """
    return HTMLResponse(html)


def inviteSignUp(inviteId: str, inviteSignUpUserInfo: inviteSignUpUserInfo):
    email = str(inviteSignUpUserInfo.email or "").strip().lower()
    password = inviteSignUpUserInfo.password
    name = inviteSignUpUserInfo.name

    inviteData = getInviteRedis(inviteId)
    if not inviteData or inviteData.get("status") is not True or not inviteData.get("token"):
        return ResponseModel(False, "초대 토큰을 찾을 수 없습니다.")

    try:
        payload = decryptFromJwe(inviteData["token"])
    except Exception:
        return ResponseModel(False, "초대 토큰이 유효하지 않습니다.")
    if not payload:
        return ResponseModel(False, "초대 토큰이 유효하지 않습니다.")

    tokenEmail = str(payload.get("email") or "").strip().lower()
    companyId = payload.get("companyId")
    roleId = payload.get("roleId")
    commonInviteId = payload.get("inviteId")
    if not commonInviteId or not companyId or not roleId or tokenEmail != email:
        return ResponseModel(False, "초대 정보가 일치하지 않습니다.")

    conn = getConn()
    if not conn:
        return ResponseModel(False, "DB connection failed")

    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                f"""
                SELECT id, company_id, role_id, state, delete_yn,
                       aes_d(email, '{settings.maria_db_key}') AS email
                FROM INVITE
                WHERE id = ?
                  AND delete_yn = 0
                FOR UPDATE
                """,
                (commonInviteId,),
            )
            inviteRow = cur.fetchone() or {}
            if not inviteRow:
                conn.rollback()
                return ResponseModel(False, "초대 정보를 찾을 수 없습니다.")
            if int(inviteRow.get("company_id") or 0) != int(companyId):
                conn.rollback()
                return ResponseModel(False, "초대 회사 정보가 일치하지 않습니다.")
            if int(inviteRow.get("role_id") or 0) != int(roleId):
                conn.rollback()
                return ResponseModel(False, "초대 권한 정보가 일치하지 않습니다.")
            if str(inviteRow.get("email") or "").strip().lower() != email:
                conn.rollback()
                return ResponseModel(False, "초대 이메일 정보가 일치하지 않습니다.")
            inviteState = str(inviteRow.get("state") or "").strip()
            if inviteState != INVITE_STATE_PENDING:
                conn.rollback()
                return ResponseModel(False, f"사용할 수 없는 초대입니다: {inviteState}")

            cur.execute(
                f"""
                INSERT INTO `with`.`USER` (`email`, `password`, `name`)
                VALUES (
                    aes_e(?, '{settings.maria_db_key}'),
                    aes_e(?, '{settings.maria_db_key}'),
                    aes_e(?, '{settings.maria_db_key}')
                )
                """,
                (email, password, name),
            )
            userId = cur.lastrowid
            cur.execute(
                "INSERT INTO `with`.`USER_ROLE` (`user_id`, `company_id`, `role_id`) VALUES (?, ?, ?)",
                (userId, companyId, roleId),
            )
            cur.execute(
                """
                UPDATE ESG_METRIC_ASSIGNMENT
                SET assignee_user_id = ?,
                    assignment_status = 'assigned',
                    updated_at = CURRENT_TIMESTAMP
                WHERE invite_id = ?
                  AND assignment_status = 'invited'
                  AND delete_yn = 0
                """,
                (userId, commonInviteId),
            )
            if int(roleId) == 4:
                for issueId in payload.get("issueGroup", []):
                    cur.execute(
                        "INSERT INTO `ISSUE_DETAIL` (invite_id, user_id, issue_id) VALUES (?, ?, ?)",
                        (commonInviteId, userId, issueId),
                    )
            cur.execute(
                """
                UPDATE INVITE
                SET state = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                  AND delete_yn = 0
                """,
                (INVITE_STATE_COMPLETED, commonInviteId),
            )
        conn.commit()
        delResult = delInviteRedis(inviteId)
        if not delResult.get("status"):
            print(f"[WARN] delInviteRedis failed for uuid={inviteId}")
    except Exception as e:
        conn.rollback()
        return ResponseModel(False, f"회원가입 처리 오류: {e}")
    finally:
        conn.close()

    return ResponseModel(True, "회원가입이 완료되었습니다.")


def inviteConsultantProcess(inviteConsultantModel, userModel):
    try:
        userId = userModel.id
        companySql = f"""
            SELECT aes_d(company_name, '{settings.maria_db_key}') AS company_name, id
            FROM `COMPANY`
            WHERE user_id = ?
        """
        company = findOne(companySql, (userId,))
        if not company:
            return ResponseModel(False, "회사 정보를 찾을 수 없습니다.")

        for email in inviteConsultantModel.email:
            inviteSql = f"""
                INSERT INTO `INVITE`
                (company_id, user_id, role_id, email)
                VALUES (?, ?, ?, aes_e(?, '{settings.maria_db_key}'))
            """
            result = addKey(inviteSql, (company["id"], userId, inviteConsultantModel.role, email))
            if not result[0]:
                return ResponseModel(False, "초대 정보 저장 실패")

            inviteId = result[1]
            token, inviteUuid = generateConsultantInviteToken(
                company["company_name"],
                email,
                inviteConsultantModel.role,
                inviteId,
                company["id"],
            )
            redisResult = setInviteRedis(inviteUuid, token, inviteExpireSeconds())
            if not redisResult.get("status"):
                save(
                    "UPDATE INVITE SET state = ? WHERE id = ? AND delete_yn = 0",
                    (INVITE_STATE_REVOKED, inviteId),
                )
                return ResponseModel(False, "초대 토큰 Redis 저장에 실패했습니다.")
            userExists = exists(f"SELECT 1 FROM `with`.`USER` WHERE email = aes_e(?, '{settings.maria_db_key}')", (email,))
            sendToKafka(
                {
                    "type": 3 if userExists else 2,
                    "email": email,
                    "uuid": inviteUuid,
                    "companyName": company["company_name"],
                }
            )

        return ResponseModel(True, "초대 메일이 성공적으로 발송되었습니다.")
    except Exception as e:
        return ResponseModel(False, f"오류 발생: {str(e)}")


def inviteMember(inviteMemberModel: inviteMemberModel, userModel=Depends(get_token)):
    try:
        userId = userModel.id
        selectSql = f"""
            SELECT aes_d(company_name, '{settings.maria_db_key}') AS company_name, id
            FROM `COMPANY`
            WHERE user_id = ?
        """
        company = findOne(selectSql, (userId,))
        if not company:
            return ResponseModel(False, "회사 정보를 찾을 수 없습니다.")

        projectId = int(getattr(inviteMemberModel, "projectId", 0) or 0)
        for inviteEmail in inviteMemberModel.email:
            inviteSql = f"""
                INSERT INTO `INVITE`
                (company_id, user_id, role_id, email)
                VALUES (?, ?, ?, aes_e(?, '{settings.maria_db_key}'))
            """
            result = addKey(
                inviteSql,
                (
                    company["id"],
                    userId,
                    inviteMemberModel.role,
                    inviteEmail,
                ),
            )
            if not result[0]:
                return ResponseModel(False, "초대 정보 저장에 실패했습니다.")

            commonInviteId = result[1]
            token, inviteUuid = generateInviteTokenWithUuid(
                inviteMemberModel.issue,
                company["company_name"],
                inviteEmail,
                inviteMemberModel.role,
                projectId,
                commonInviteId,
                company["id"],
            )
            redisResult = setInviteRedis(inviteUuid, token, inviteExpireSeconds())
            if not redisResult.get("status"):
                save(
                    "UPDATE INVITE SET state = ? WHERE id = ? AND delete_yn = 0",
                    (INVITE_STATE_REVOKED, commonInviteId),
                )
                return ResponseModel(False, "초대 토큰 Redis 저장에 실패했습니다.")
            sendToKafka(
                {
                    "type": 1,
                    "uuid": inviteUuid,
                    "email": inviteEmail,
                    "companyName": company["company_name"],
                }
            )

        return ResponseModel(True, "초대 메일이 성공적으로 발송되었습니다.")
    except Exception as e:
        return ResponseModel(False, f"인증 오류 발생 : {e}")


def inviteExpireSeconds() -> int:
    return max(1, int(settings.invite_token_expire_days)) * 24 * 60 * 60
