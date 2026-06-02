from src.models.model import ResponseModel
from src.utils.db import findOne, findAll, save, exists
from src.utils.validatetok import validateToken
from src.utils.tokenset import decryptFromJwe, generateConsultantInviteToken
from src.utils.rediscl import getTokenRedis, setInviteRedis, getInviteRedis
from fastapi.responses import HTMLResponse
from src.models.model import ResponseModel, inviteSignUpUserInfo, inviteConsultantModel
from src.utils.db import save, addKey
from src.utils.kafkasv import sendToKafka
from src.utils.auth import get_token
from src.utils.settings import settings
from src.utils.tokenset import generateInviteTokenWithUuid
from src.models.model import inviteMemberModel, ResponseModel
from fastapi import Depends


def inviteProcess(inviteId: str):
  html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>W.I.T.H -회원가입 폼</title>
        <link rel="icon" type="image/svg+xml" href="https://avatars.githubusercontent.com/u/276547385?s=200&v=4" />
        <link rel="stylesheet" href="https://shell-files.github.io/project_ui/styles/style.css">
        <link rel="stylesheet" href="/static/invite.css">

        <!-- React & ReactDOM CDN -->
        <script src="https://unpkg.com/react@18/umd/react.development.js" crossorigin></script>
        <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js" crossorigin></script>

        <!-- Babel CDN (JSX 변환용) -->
        <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>

        <!-- AXIOS CDN -->
        <script src="https://unpkg.com/axios/dist/axios.min.js"></script>

        <script src="https://cdnjs.cloudflare.com/ajax/libs/sweetalert2/11.23.0/sweetalert2.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11.26.24/dist/sweetalert2.all.min.js"></script>

        <!-- React 코드 (JSX 사용 가능, type="text/babel") -->
        <script src="/static/App.jsx" type="text/babel"></script>
    </head>
    <body>
      <!-- React가 렌더링될 DOM 요소 -->
      <div id="signup_page" class="signup-container"></div>
      <script src="/static/Main.jsx" type="text/babel"></script>
    </body>
    </html>
  """
  return HTMLResponse(html)

def inviteSignUp(inviteId: str, inviteSignUpUserInfo: inviteSignUpUserInfo):
  """
  초대 링크로 회원가입을 처리하는 API입니다.
  1. inviteSignUpUserInfo에서 이메일과 회사명을 추출합니다.
  2. 사용자 계정을 생성합니다.
  3. inviteId로 Redis에서 초대 토큰을 조회하여 payload를 복호화합니다.
  4. payload에서 companyId, roleId, inviteId를 추출합니다.
  """
  # 1. inviteSignUpUserInfo에서 이메일과 회사명을 추출합니다.
  email = inviteSignUpUserInfo.email
  password = inviteSignUpUserInfo.password
  name = inviteSignUpUserInfo.name

  # 2. 사용자 계정을 생성합니다.
  inviteUserSql = f"INSERT INTO `with`.`USER` (`email`, `password`, `name`) values (?, ?, ?)"
  inviteUserSqlParam = (email, password, name)
  result = addKey(inviteUserSql, inviteUserSqlParam)

  if not result[0]:  # DB 저장 실패 시
      return ResponseModel(False, "회원가입에 실패했습니다.")

  userId = result[1]
  inviteData = getInviteRedis(inviteId)
  payload = decryptFromJwe(inviteData["token"])
  companyId = payload.get("companyId")
  roleId = payload.get("roleId")
  inviteId = payload.get("inviteId")

  # 사용자 권한 설정
  userRoleSql = f"INSERT INTO `USER_ROLE` (`user_id`, `company_id`, `role_id`) values (?, ?, ?)"
  userRoleSqlParam = (userId, companyId, roleId)
  save(userRoleSql, userRoleSqlParam)

  # 부서담당자 회원가입인 경우, ISSUE_DETAIL 테이블에 이슈 그룹 정보 저장
  if roleId == 4:
    issueGroup = payload.get("issueGroup", [])
    # issueGroup 
    for issueId in issueGroup:
      issueDetailSql = f"INSERT INTO `ISSUE_DETAIL` (invite_id, user_id, issue_id) VALUES (?, ?, ?)"
      issueDetailSqlParam = (inviteId, userId, issueId)
      save(issueDetailSql, issueDetailSqlParam)
      
  return ResponseModel(True, "회원가입이 완료되었습니다.")

def inviteConsultantProcess(inviteConsultantModel, userModel):
    try:
        # 1. 인증된 사용자 정보 
        userId = userModel.id

        # 2. 회사 조회
        companySql = f"""
            SELECT aes_d(company_name, '{settings.maria_db_key}') AS company_name, id
            FROM `COMPANY`
            WHERE user_id = ?
        """
        company = findOne(companySql, (userId, ))

        if not company:
            return ResponseModel(False, "회사 정보를 찾을 수 없습니다.")

        # 3. 초대 처리
        for email in inviteConsultantModel.email:

            inviteSql = """
                INSERT INTO `INVITE`
                (company_id, user_id, role_id, email)
                VALUES (?, ?, ?, ?)
            """

            result = addKey(inviteSql, (
                company["id"],
                userId,
                inviteConsultantModel.role,
                email
            ))

            if not result[0]:
                return ResponseModel(False, "초대 정보 저장 실패")

            inviteId = result[1]
            token, inviteUuid = generateConsultantInviteToken(
                company["company_name"],
                email,
                inviteConsultantModel.role,
                inviteId,
                company["id"]
            )


            setInviteRedis(inviteUuid, token)


            userExists = exists(
                "SELECT 1 FROM `with`.`USER` WHERE email = ?",
                (email,)
            )
            sendToKafka({
                "type": 3 if userExists else 2,
                "email":email,
                "uuid": inviteUuid
            })

        return ResponseModel(True, "초대장이 성공적으로 발송되었습니다.")

    except Exception as e:
        return ResponseModel(False, f"오류 발생: {str(e)}")
    
def inviteMember(inviteMemberModel: inviteMemberModel, userModel = Depends(get_token)):
    try:
        # 인증 유저 정보 
        userId = userModel.id

        # 회사 조회
        selectSql = f"""
            SELECT aes_d(company_name, '{settings.maria_db_key}'), id 
            FROM `COMPANY` 
            WHERE user_id = ?
        """
        company = findOne(selectSql, (userId, ))
        
        if not company:
            return ResponseModel(False, "회사 정보를 찾을 수 없습니다.")

        for invite_email in inviteMemberModel.email:

            # DB 저장
            inviteSql = """
                INSERT INTO `INVITE` 
                (company_id, user_id, role_id,  email) 
                VALUES (?, ?, ?, ?)
            """

            result = addKey(
                inviteSql,
                (
                    company["id"],
                    userId,
                    inviteMemberModel.role,
                    inviteMemberModel.projectId,
                    invite_email
                )
            )

            if not result[0]:
                return ResponseModel(False, "초대 정보 저장에 실패했습니다.")

            inviteId = result[1]

            # 토큰 생성
            token, invite_uuid = generateInviteTokenWithUuid(
                inviteMemberModel.issue, 
                company["company_name"], 
                invite_email,
                inviteMemberModel.role, 
                inviteMemberModel.projectId, 
                inviteId, 
                company["id"]
            )

            # Redis 저장
            setInviteRedis(invite_uuid, token)

            # Kafka 발송
            sendToKafka({
                "type": 1,
                "uuid": invite_uuid,
                "email": invite_email
            })

        return ResponseModel(True, "초대장이 성공적으로 발송되었습니다.")

    except Exception as e:
        return ResponseModel(False, f"인증 오류 발생 : {e}")