import json
import uuid
from jwcrypto import jwk, jwe
from datetime import datetime, timedelta, timezone
from src.utils.settings import settings
from src.models.model import UserModel

# --------------------------
# 공통 복호화/암호화 로직: 데이터를 JWE로 암호화 (AES-GCM)
# --------------------------
def encryptToJwe(payload: dict):
    """ 공통 복호화/암호화 로직: 데이터를 JWE로 암호화 (AES-GCM)"""
    with open(settings.public_key, 'rb') as f:
        pemData = f.read()

    # from_pem은 라이브러리 제공 클래스 형식이라 카멜케이스 불가
    key = jwk.JWK.from_pem(pemData)
    payloadStr = json.dumps(payload)

    header = {"alg": "RSA-OAEP", "enc": "A256GCM"}
    # RSA-OAEP(RSA 키 암호화) + A256GCM(데이터 암호화) 조합, add_recipient는 반드시 스네이크 형식이어야 함(jwcrypto 라이브러리 제작자가 함수 이름을 add_recipient라고 지어놓았기 때문).
    jwetoken = jwe.JWE(payloadStr.encode('utf-8'), json.dumps(header))
    jwetoken.add_recipient(key)
    return jwetoken.serialize(compact=True)

# --------------------------
# 복호화 함수: JWE 토큰을 해독하여 파이썬 딕셔너리로 반환
# --------------------------
def decryptFromJwe(token: str):
    """ 복호화 함수: JWE 토큰 해독 및 만료시간 검증 """
    try:
        with open(settings.private_key, 'rb') as f:
            pemData = f.read()
        key = jwk.JWK.from_pem(pemData)
        
        jwetoken = jwe.JWE()
        jwetoken.deserialize(token)
        jwetoken.decrypt(key)
        
        # 1. 먼저 페이로드를 딕셔너리로 변환해야 합니다 (중요!)
        payload = json.loads(jwetoken.payload.decode('utf-8'))
        
        # 2. 이제 딕셔너리에서 exp를 꺼내올 수 있습니다.(만료시간 검증)
        exp = payload.get('exp')
        
        if exp:
            # 현재 시간 (UTC 기준 timestamp)
            currentTime = int(datetime.now(timezone.utc).timestamp())
            
            if currentTime > exp:
                print("Token has expired.")
                return None

        return payload
        
    except Exception as e:
        return None
    
# --------------------------
# 액세스 토큰 생성 함수 (공통 모듈)
# --------------------------
def generateAccessWithUuid(userClaims: UserModel):
    """ 액세스 토큰 생성 함수 (공통 모듈)"""

    now = datetime.now(timezone.utc)
    payload = {
        "iss": "withProject",
        "sub": userClaims.id,
        "user": userClaims.model_dump(),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp())
    }

    # JWE로 암호화하여 반환
    return encryptToJwe(payload)

# --------------------------
# 리프레시 액세스 토큰 생성 함수 (공통 모듈)
# --------------------------
def generateRefreshAccessWithUuid(userClaims: UserModel):
    """ 리프레시 액세스 토큰 생성 함수 (공통 모듈)"""
    
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "withProject",
        "sub": userClaims.id,
        "user": userClaims.model_dump(),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.refresh_token_expire_days)).timestamp())
    }

    # JWE로 암호화하여 반환
    return encryptToJwe(payload)


# --------------------------
# 토큰 재발급: 리프레시 토큰 검증 후 새로운 UUID와 액세스 토큰 생성
# --------------------------
def refreshAccessToken(refreshToken: str):
    """ 토큰 재발급: 리프레시 토큰 검증 후 새로운 UUID와 액세스 토큰 생성"""
    # 1. JWE 복호화 및 유효성 검사
    payload = decryptFromJwe(refreshToken)
    if not payload:
        return None # 해독 실패 또는 변조
        
    user = payload.get("user")
    newUuid = str(uuid.uuid4().hex)
    userClaims = UserModel(
        uuid=newUuid,
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        role_name=user["role_name"]
    )

    # 2. 새로운 액세스 토큰과 UUID 생성 
    newAccessToken = generateAccessWithUuid(userClaims)
    
    return newAccessToken, newUuid, userClaims.id
