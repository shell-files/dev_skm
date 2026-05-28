from src.utils.db import executeTransaction, findAll, save
from src.models.model import logoutModel, ResponseModel
from src.utils.validatetok import validateToken
from src.utils.tokenset import decryptFromJwe
from src.utils.rediscl import delTokenRedis, getTokenRedis


# models/user.py
# ────────────────────────────────────────────────────────────────────────────
# [역할]
#  1. Pydantic v2 Request/Response 모델 정의
#  2. 회원가입 비즈니스 로직 및 SQL 실행
#
# [ERD FK 흐름]
#  USER.id          ──→ COMPANY.user_id
#  USER.id          ──→ USER_ROLE.user_id
#  COMPANY.id       ──→ USER_ROLE.company_id
#  COMPANY.id       ──→ INDUSTRY_DETAIL.company_id
#  INDUSTRY_CODE.id ──→ INDUSTRY_DETAIL.industry_id
#  ROLE.id          ──→ USER_ROLE.role_id
# ────────────────────────────────────────────────────────────────────────────
# --------------------------
# 회원 정보 수정 로직 처리 함수
# --------------------------
def updateUserProcess(userUpdateModel):
    """ 
    1. 통합 세션 검증 및 자동 갱신 (UUID 활용)
    2. 유저 ID 추출
    3. 이름/비밀번호 변경 필드 구성
    4. DB 업데이트 및 최신 UUID 반환
    """
    try:
        # 1. 통합 인증 모듈 호출 (UUID 검증 및 만료 시 자동 갱신)
        # 이 한 줄로 Redis 확인, 토큰 만료 체크, 필요 시 UUID/액세스토큰 재발급이 수행됩니다.
        authResponse = validateToken(userUpdateModel.uuid)
        
        # 인증 실패 시 (세션 만료 등) 에러 응답 즉시 반환
        if not authResponse["status"]:
            return authResponse

        # 2. 최신 UUID를 통해 내부 user_id 추출
        activeUuid = authResponse["data"]["uuid"]
        tokenResponse = getTokenRedis(activeUuid)
        payload = decryptFromJwe(tokenResponse["accessToken"])
        userId = payload.get("sub")

        # 3. 업데이트 필드 구성
        updateFields = []
        updateParams = []

        if userUpdateModel.name:
            updateFields.append("name = ?")
            updateParams.append(userUpdateModel.name)

        if userUpdateModel.newPassword:
            updateFields.append("password = ?")
            updateParams.append(userUpdateModel.newPassword) 

        if not updateFields:
            # 변경사항은 없지만 세션은 유효하므로 현재 UUID를 담아 반환
            return ResponseModel(False, "변경할 내용이 없습니다.", {"uuid": activeUuid})

        # 4. DB 업데이트 수행
        updateSql = f"""
            UPDATE `USER` 
            SET {', '.join(updateFields)} 
            WHERE id = ? AND delete_yn = 0;
        """
        print(updateSql)
        updateParams.append(userId)
        save(updateSql, tuple(updateParams))

        # 5. 성공 응답: 최신 UUID를 함께 전달하여 프론트엔드 세션 유지
        return ResponseModel(True, "회원 정보가 수정되었습니다.", {"uuid": activeUuid})

    except Exception as e:
        print(f"updateUserProcess Error: {e}")
        return ResponseModel(False, f"수정 중 오류 발생: {str(e)}")
    
# --------------------------
# 회원 탈퇴 로직 처리 함수
# --------------------------
def deleteUserProcess(userDeleteModel):
    """ 
     1. 통합 인증 모듈 호출 (UUID 검증 및 만료 시 자동 갱신)
     2. 최신 UUID를 통해 내부 user_id 추출
     3. 회원이 ESG담당자인지 그 외 회원인지 확인
     4. roles 리스트의 모든 항목은 동일한 user_id를 가지므로 첫 번째 항목에서 추출
        [A] 사용자 공통 삭제 로직 (반복문 밖에서 1회만 추가)
        (USER,USER_ROLE,INVITE,ISSUE_DETAIL 삭제에 사용)
        [B] 역할 및 회사별 개별 삭제 로직 (반복문 순회)
        (COMPANY,LICENSE_FILE,INDUSTRY_DETAIL 삭제에 사용)
     5. 트랜잭션 실행
     6. 트랜잭션 성공 시 → 탈퇴 후 세션 파기 로직 수행
        - DB 토큰 delete_yn 1로 변경
        - Redis uuid 삭제
    """
    try:
          # 1. 통합 인증 모듈 호출 (UUID 검증 및 만료 시 자동 갱신)
          authResponse = validateToken(userDeleteModel.uuid)

          # 인증 실패 시 (세션 만료 등) 에러 응답 즉시 반환
          if not authResponse["status"]:
              return authResponse
          
          # 2. 최신 UUID를 통해 내부 user_id 추출
          activeUuid = authResponse["data"]["uuid"]
          tokenResponse = getTokenRedis(activeUuid)
          payload = decryptFromJwe(tokenResponse["accessToken"])
          userId = payload.get("sub")

          # 3. 회원이 ESG담당자인지 그 외 회원인지 확인
          roleCheckSql = """
              SELECT ur.role_id, ur.company_id, ur.user_id
              FROM `USER_ROLE` ur 
              JOIN `USER` u ON ur.user_id = u.id 
              WHERE user_id = ? AND ur.delete_yn = 0;
          """
          roles = findAll(roleCheckSql, (userId,))
          
          if not roles:
            return ResponseModel(False, "회원 정보가 존재하지 않습니다.")
          queries = []
          # 4. roles 리스트의 모든 항목은 동일한 user_id를 가지므로 첫 번째 항목에서 추출
          targetUserId = roles[0]['user_id']

          # --- [A] 사용자 공통 삭제 로직 (반복문 밖에서 1회만 추가) ---
          queries.append(("UPDATE `USER` SET delete_yn = 1 WHERE id = ?", (targetUserId,)))
          queries.append(("UPDATE `USER_ROLE` SET delete_yn = 1 WHERE user_id = ?", (targetUserId,)))
          queries.append(("UPDATE `INVITE` SET delete_yn = 1 WHERE user_id = ?", (targetUserId,)))
        
          # 사용자가 생성한 모든 초대(INVITE)와 연결된 ISSUE_DETAIL 일괄 삭제
          deleteIssueDetailSql = """
            UPDATE `ISSUE_DETAIL` 
            SET delete_yn = 1 
            WHERE invite_id IN (SELECT id FROM `INVITE` WHERE user_id = ?);
          """
          queries.append((deleteIssueDetailSql, (targetUserId,)))
         
          # --- [B] 역할 및 회사별 개별 삭제 로직 (반복문 순회) ---
          for role in roles:
            rId = role.get('role_id')
            cId = role.get('company_id')

          # ESG 담당자(role_id=2)인 경우 해당 회사 관련 정보 삭제
            if rId == 2 and cId:
                ## 1. 해당 COMPANY 삭제
                queries.append(("UPDATE `COMPANY` SET delete_yn = 1 WHERE id = ?", (cId,)))
                
                ## 2. 해당 COMPANY의 LICENSE_FILE 삭제
                deleteLicenseSql = """
                    UPDATE `LICENSE_FILE` 
                    SET delete_yn = 1 
                    WHERE id = (SELECT license_file_id FROM `COMPANY` WHERE id = ?);
                """
                queries.append((deleteLicenseSql, (cId,)))

                ## 3. 해당 COMPANY의 INDUSTRY_DETAIL 삭제
                queries.append(("UPDATE `INDUSTRY_DETAIL` SET delete_yn = 1 WHERE company_id = ?", (cId,)))

          # 5. 트랜잭션 실행
          success = executeTransaction(queries)    
          # 6. 트랜잭션 성공 시 → 탈퇴 후 세션 파기 로직 수행
          if success:
            try:
                ## 1. db에서 refresh token delete_yn 1으로 변경
                logoutSql="""
                UPDATE TOKEN
                    SET `delete_yn` = 1
                    WHERE uuid = ?;
                """
                logoutParams = (activeUuid,)
                save(logoutSql, logoutParams)

                ## 2. redis에서 uuid 삭제
                delTokenRedis(activeUuid)   

            except Exception as redis_e:
                print(f"탈퇴 후 세션 파기 실패: {redis_e}")
                # DB는 이미 지워졌으므로 사용자에게 실패를 알릴 필요는 없으나 로그는 남깁니다.

            return ResponseModel(True, "회원 탈퇴가 성공적으로 완료되었습니다.", {"uuid": None}) 
          else:
            return ResponseModel(False, "데이터베이스 업데이트 중 오류가 발생했습니다.")

    except Exception as e:
        print(f"deleteUserProcess Error: {e}")
        return ResponseModel(False, "탈퇴 처리 중 시스템 오류 발생")