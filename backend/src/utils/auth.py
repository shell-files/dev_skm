from fastapi import Response, Depends, HTTPException, status
from fastapi.security import APIKeyCookie
from src.utils.settings import settings
from src.utils.validatetok import validateToken
from src.utils.token import decryptFromJwe
from src.utils.rediscl import getTokenRedis
from src.models.model import UserModel

cookie_scheme = APIKeyCookie(name=settings.cookie_key)

def get_token(response: Response, token: str = Depends(cookie_scheme)) -> UserModel:
    """
    쿠키에서 토큰을 추출하고 검증하며, 필요 시 쿠키를 갱신합니다.
    """
    try:
        # 1. 토큰 존재 여부 확인
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰이 없습니다.")

        # 2. 통합 인증 모듈 호출
        authResponse = validateToken(token)
        
        # 인증 실패 처리 (딕셔너리 반환 대신 예외 발생)
        if not authResponse.get("status"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail=authResponse.get("message", "세션이 만료되었습니다.")
            )
        
        # 3. 쿠키 갱신 (UUID가 변경되었거나 갱신이 필요한 경우)
        activeUuid = authResponse["data"]["uuid"]
        
        # 현재 쿠키값과 전달받은 activeUuid가 다를 때만 set_cookie를 호출하는 것이 효율적입니다.
        if token != activeUuid:                
            max_age = (60 * 60 * 24 * settings.refresh_token_expire_days)
            response.set_cookie(
                key=settings.cookie_key,
                value=activeUuid,
                domain=settings.domain,
                httponly=True,
                samesite="lax",
                # secure=True, # 프로덕션 환경 권장
                max_age=max_age
            )

        # 4. Redis에서 사용자 정보 조회
        tokenResponse = getTokenRedis(activeUuid)
        if not tokenResponse:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자 세션을 찾을 수 없습니다.")

        payload = decryptFromJwe(tokenResponse["accessToken"])
        user_data = payload.get("user")
        
        if not user_data:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 유저 정보입니다.")

        return UserModel(**user_data)

    except HTTPException as http_exc:
        # 명시적인 HTTP 에러는 그대로 다시 던집니다.
        raise http_exc
    except Exception as e:
        # 예상치 못한 에러 로깅
        print(f"Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="접근 권한이 없거나 오류가 발생했습니다.",
        )
    
