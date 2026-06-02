from fastapi import Response, Depends, HTTPException, status, Request
from fastapi.security import APIKeyCookie
from src.utils.settings import settings
from src.utils.validatetok import validateToken
from src.utils.tokenset import decryptFromJwe
from src.utils.rediscl import getTokenRedis, delTokenRedis
from src.models.model import UserModel
from src.utils.db import save

cookie_scheme = APIKeyCookie(name=settings.cookie_key)

def get_domain(request: Request):
    current_domain = request.url.hostname
    # 강의장용 DNS
    print(f"요청한 Domain : {current_domain}")
    allowed_domains = ["myapp.com", "main.myapp.com"]
    if current_domain.endswith(settings.domain):
        cookie_domain = f".{settings.domain}"
    elif current_domain.endswith(settings.skm_domain):
        cookie_domain = f".{settings.skm_domain}"
    elif current_domain in allowed_domains:
        cookie_domain = ".myapp.com"
    else:
        cookie_domain = None
    print(f"Cookie Domain : {cookie_domain}")
    return cookie_domain

def get_token(request: Request, response: Response, token: str = Depends(cookie_scheme)) -> UserModel:

    """
    쿠키에서 토큰을 추출하고 검증하며, 필요 시 쿠키를 유연하게 갱신합니다.
    """
    try:
        # 1. 토큰 존재 여부 확인
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰이 없습니다.")

        # 2. 통합 인증 모듈 호출 (구 UUID 유예 로직이 반영된 validateToken)
        authResponse = validateToken(token)

        # 인증 실패 처리
        if not authResponse.get("status"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=authResponse.get("message", "세션이 만료되었습니다.")
            )

        # 3. 쿠키 갱신 (UUID가 변경되었거나 갱신이 필요한 경우)
        authData = authResponse.get("data", {})
        activeUuid = authData.get("uuid")

        # [개선] 만약 토큰이 갱신되었거나(is_updated), 현재 쿠키값과 activeUuid가 다르면 쿠키 재발급
        if token != activeUuid or authData.get("is_updated"):
            max_age = (60 * 60 * 24 * settings.refresh_token_expire_days)
            
            # 동적 도메인 추출 함수 활용
            cookie_domain = get_domain(request)
            
            response.set_cookie(
                key=settings.cookie_key,
                value=activeUuid,
                domain=cookie_domain,  # settings.domain 대신 동적 도메인 적용

                httponly=True,
                samesite="lax",
                # secure=True, # 프로덕션 환경 권장
                max_age=max_age
            )

        # 4. Redis에서 사용자 정보 조회
        # (validateToken 단계에서 유예 시간을 주었기 때문에, 동시 요청의 activeUuid가 구_UUID여도 안전하게 통과됨)
        tokenResponse = getTokenRedis(activeUuid)
        if not tokenResponse or not tokenResponse.get("status"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자 세션을 찾을 수 없습니다.")

        payload = decryptFromJwe(tokenResponse["accessToken"])
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰 복호화에 실패했습니다.")
            
        user_data = payload.get("user")
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 유저 정보입니다.")

        return UserModel(**user_data)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="접근 권한이 없거나 오류가 발생했습니다.",
        )
        
def delete_cookie(response: Response, request: Request, uuid: str):
    try:
        # 1. db에서 refresh token delete_yn 1으로 변경
        logoutSql="""
            UPDATE `with`.TOKEN
                SET `delete_yn` = 1
                WHERE uuid = ?;
        """
        logoutParams = (uuid,)
        save(logoutSql, logoutParams)

        # 2. redis에서 uuid 삭제
        delTokenRedis(uuid)

        # 3. cookie 삭제
        response.delete_cookie(
            key=settings.cookie_key,
            domain=get_domain(request),
            # secure=True,
            httponly=True, samesite="lax"
        )
        return True
    except Exception as e:
        print(f"delete_cookie Error: {e}")
    return False

