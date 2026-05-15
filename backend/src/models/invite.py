from src.models.model import responseModel
from src.utils.db import findOne, findAll, save, exists
from src.utils.validatetok import validateToken
from src.utils.tokenset import decryptFromJwe, generateConsultantInviteToken
from src.utils.rediscl import getTokenRedis, setInviteRedis, getInviteRedis
from fastapi.responses import HTMLResponse
from src.models.model import responseModel, inviteSignUpUserInfo, inviteConsultantModel
from src.utils.db import save, addKey
from src.utils.kafkasv import sendToKafka

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
  inviteUserSql = f"INSERT INTO `USER` (`email`, `password`, `name`) values (?, ?, ?)"
  inviteUserSqlParam = (email, password, name)
  result = addKey(inviteUserSql, inviteUserSqlParam)

  if not result[0]:  # DB 저장 실패 시
      return responseModel(False, "회원가입에 실패했습니다.")

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
      
  return responseModel(True, "회원가입이 완료되었습니다.")

def inviteConsultantProcess(inviteConsultantModel: inviteConsultantModel):
    try:
            # 1. 세션 검증 및 자동 갱신 모듈 호출
            # 이 한 줄로 Redis 조회, Access 만료 체크, Refresh 재발급, DB/Redis 업데이트가 완료됩니다.
            authResponse = validateToken(inviteConsultantModel.uuid)
            
            # 인증 실패 시 (세션 만료, 리프레시 만료 등) 그대로 반환
            if not authResponse["status"]:
                return authResponse

            # 2. 검증 통과 후 최신 UUID 획득
            # 재발급되었다면 신규 UUID가, 유효하다면 기존 UUID가 들어있습니다.
            activeUuid = authResponse["data"]["uuid"]

            # 3. 최신 UUID를 통해 유저 ID(sub) 추출
            # Redis에서 토큰을 가져와 복호화하여 sub(userId)를 얻습니다.
            tokenRes = getTokenRedis(activeUuid)
            payload = decryptFromJwe(tokenRes["accessToken"])
            userId = payload.get("sub")
            selectSql = f"SELECT company_name, id FROM `COMPANY` WHERE user_id = ?"
            selectParams = (userId,)
            company = findOne(selectSql, selectParams)

            for email in inviteConsultantModel.email:
                # DB에 초대 정보 저장
                inviteSql = f"INSERT INTO `INVITE` (company_id, user_id, role_id, project_id, email) values (?, ?, ?, ?, ?)"
                inviteParams = (company["id"], userId, inviteConsultantModel.role, inviteConsultantModel.projectId, email)
                result = addKey(inviteSql, inviteParams)

                if not result[0]:  # DB 저장 실패 시
                    return responseModel(False, "초대 정보 저장에 실패했습니다.")

                inviteId = result[1]

                # 받는 사람 이메일, 권한 정보 토큰화
                token, uuid =generateConsultantInviteToken(company["company_name"], email, inviteConsultantModel.role, inviteConsultantModel.projectId, inviteId, company["id"])

                # Redis에 초대 토큰 저장
                setInviteRedis(uuid, token)

                # 기존 가입자인지 신규 가입자인지 확인
                checkSql = "SELECT * FROM `USER` WHERE email = ?;"
                checkParams = (email,)
                user = exists(checkSql, checkParams)
                if user:
                    # 기존 가입자 메일 발송
                    mailData = {"type": 3, "uuid": uuid}
                else:
                    # 신규 가입자 메일 발송
                    mailData = {"type": 2, "uuid": uuid}
                sendToKafka(mailData)
                return responseModel(True, "초대장이 성공적으로 발송되었습니다.")
    except Exception as e:
        return responseModel(False, f"인증 오류 발생 : {e}")