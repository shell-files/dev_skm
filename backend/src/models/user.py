from src.utils.db import executeTransaction, findAll, save
from src.models.model import logoutModel, ResponseModel
from src.utils.validatetok import validateToken
from src.utils.tokenset import decryptFromJwe
from src.utils.rediscl import delTokenRedis, getTokenRedis
from src.utils.settings import settings


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
def updateUserProcess(request, userUpdateModel):
    # 1. 쿠키에서 UUID 가져오기
    current_uuid = request.cookies.get("yakgwa")
    
    # 2. 쿠키가 없는 경우 처리
    if not current_uuid:
         return ResponseModel(False, "로그인 정보가 만료되었습니다.")

    try:
        # 1. 통합 인증 모듈 호출 (UUID 검증 및 만료 시 자동 갱신)
        # 이 한 줄로 Redis 확인, 토큰 만료 체크, 필요 시 UUID/액세스토큰 재발급이 수행됩니다.
        authResponse = validateToken(current_uuid)
        
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
            updateFields.append(f"name = aes_e(?, '{settings.maria_db_key}')")
            updateParams.append(userUpdateModel.name)

        if userUpdateModel.newPassword:
            # [수정] AES_ENCRYPT 함수를 사용하여 암호화 저장
            updateFields.append(f"password = aes_e(?, '{settings.maria_db_key}')")
            updateParams.append(userUpdateModel.newPassword) 

        if not updateFields:
            return ResponseModel(False, "변경할 내용이 없습니다.", {"uuid": activeUuid})

        # DB 업데이트 수행
        updateSql = f"""
            UPDATE `with`.`USER` 
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
def deleteUserProcess(request):
    """
    1. 쿠키(yakgwa)로 세션 검증
    2. 트랜잭션 기반 데이터 삭제 (Soft Delete)
    """
    # 1. 쿠키에서 UUID 추출
    current_uuid = request.cookies.get("yakgwa")
    if not current_uuid:
         return ResponseModel(False, "로그인 정보가 만료되었습니다.")

    try:
        # 2. 통합 인증 (세션이 살아있는지 확인)
        authResponse = validateToken(current_uuid)
        if not authResponse["status"]:
            return authResponse
        
        activeUuid = authResponse["data"]["uuid"]
        tokenResponse = getTokenRedis(activeUuid)
        payload = decryptFromJwe(tokenResponse["accessToken"])
        userId = payload.get("sub")

        # 3. 사용자 역할 및 데이터 조회
        roleCheckSql = """
            SELECT ur.role_id, ur.company_id, ur.user_id
            FROM `with`.`USER_ROLE` ur 
            JOIN `with`.`USER` u ON ur.user_id = u.id 
            WHERE user_id = ? AND ur.delete_yn = 0;
        """
        roles = findAll(roleCheckSql, (userId,))
        if not roles:
            return ResponseModel(False, "회원 정보가 존재하지 않습니다.")

        # 4. 삭제 쿼리 구성 (트랜잭션)
        queries = []
        targetUserId = roles[0]['user_id']
        
        # 공통 삭제
        queries.append(("UPDATE `with`.`USER` SET delete_yn = 1 WHERE id = ?", (targetUserId,)))
        queries.append(("UPDATE `with`.`USER_ROLE` SET delete_yn = 1 WHERE user_id = ?", (targetUserId,)))
        queries.append(("UPDATE `skm`.`INVITE` SET delete_yn = 1 WHERE user_id = ?", (targetUserId,)))
        
        deleteIssueDetailSql = """
        UPDATE skm.`ISSUE_DETAIL` 
        SET delete_yn = 1 
        WHERE invite_id IN (SELECT id FROM `INVITE` WHERE user_id = ?);
        """
        queries.append((deleteIssueDetailSql, (targetUserId,)))
        
        # --- [B] 역할 및 회사별 개별 삭제 로직 (반복문 내부로 이동 완료) ---
        for role in roles:
            rId = role.get('role_id')
            cId = role.get('company_id')

            # ESG 담당자(role_id=2)인 경우 해당 회사 관련 정보 삭제
            if rId == 2 and cId:
                ## 1. 해당 COMPANY 삭제
                queries.append(("UPDATE `skm`.`COMPANY` SET delete_yn = 1 WHERE id = ?", (cId,)))
                
                ## 2. 해당 COMPANY의 LICENSE_FILE 삭제
                deleteLicenseSql = """
                    UPDATE `skm`.`LICENSE_FILE` 
                    SET delete_yn = 1 
                    WHERE id = (SELECT license_file_id FROM `skm`.`COMPANY` WHERE id = ?);
                """
                queries.append((deleteLicenseSql, (cId,)))

                ## 3. 해당 COMPANY의 INDUSTRY_DETAIL 삭제
                queries.append(("UPDATE `skm`.`INDUSTRY_DETAIL` SET delete_yn = 1 WHERE company_id = ?", (cId,)))

        # 5. 트랜잭션 실행
        success = executeTransaction(queries)
        
        if success:
            # 세션 파기
            try:
                logoutSql = "UPDATE `with`.TOKEN SET `delete_yn` = 1 WHERE uuid = ?;"
                save(logoutSql, (activeUuid,))
                delTokenRedis(activeUuid)
            except Exception as redis_e:
                print(f"세션 파기 실패: {redis_e}")

            return ResponseModel(True, "회원 탈퇴가 성공적으로 완료되었습니다.", {"uuid": None}) 
        else:
            return ResponseModel(False, "데이터베이스 업데이트 중 오류가 발생했습니다.")

    except Exception as e:
        print(f"deleteUserProcess Error: {e}")
        return ResponseModel(False, "탈퇴 처리 중 시스템 오류 발생")