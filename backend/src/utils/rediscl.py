"""
rediscl.py
레이어: Utils
역할: Redis 클라이언트 — 토큰·회사·로테이션 세션 저장·조회·삭제.
"""
from src.utils.settings import settings
import redis


client1 = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db1,
    decode_responses=True,
)
client2 = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db2,
    decode_responses=True,
)
client3 = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db3,
    decode_responses=True,
)


def setTokenRedis(uuid: str, token: str):
    try:
        client1.set(uuid, token)
        print(f"Success: Set Redis - uuid: {uuid}")
        return {"status": True}
    except Exception as e:
        print(f"Error setting Redis keys: {e}")
        return {"status": False}


def getTokenRedis(uuid: str):
    try:
        result = client1.get(uuid)
        if result:
            return {"status": True, "uuid": uuid, "accessToken": result}
        return {"status": False, "message": "Key not found"}
    except Exception as e:
        print(f"Error getting Redis value: {e}")
        return {"status": False}


def getInviteRedis(uuid: str):
    try:
        result = client3.get(uuid)
        if result:
            return {"status": True, "uuid": uuid, "token": result}
        return {"status": False, "message": "Key not found"}
    except Exception as e:
        print(f"Error getting Redis value: {e}")
        return {"status": False}


def delTokenRedis(uuid: str):
    try:
        client1.delete(uuid)
        return {"status": True}
    except Exception as e:
        print(f"Error deleting Redis key: {e}")
        return {"status": False}


def setRotatedTokenRedis(oldUuid: str, newUuid: str, seconds: int = 30):
    """토큰 갱신 시 구 UUID → 신 UUID 매핑을 저장한다 (동시 요청 Race Condition 방지용)."""
    try:
        client1.set(f"rotated:{oldUuid}", newUuid, ex=seconds)
        return {"status": True}
    except Exception as e:
        print(f"Error setting rotated key: {e}")
        return {"status": False}


def getRotatedTokenRedis(oldUuid: str):
    """구 UUID가 이미 갱신된 경우 신 UUID를 반환한다."""
    try:
        result = client1.get(f"rotated:{oldUuid}")
        if result:
            return {"status": True, "newUuid": result}
        return {"status": False}
    except Exception as e:
        print(f"Error getting rotated key: {e}")
        return {"status": False}


def setPasswordRedis(tempPwd: str, email: str):
    try:
        client2.set(tempPwd, email)
        print(f"Success: Set Redis - tempPwd: {tempPwd}")
        return {"status": True}
    except Exception as e:
        print(f"Error setting Redis keys: {e}")
        return {"status": False}


def getPasswordRedis(tempPwd: str):
    try:
        result = client2.get(tempPwd)
        if result:
            return {"status": True, "tempPwd": tempPwd, "email": result}
        return {"status": False, "message": "Key not found"}
    except Exception as e:
        print(f"Error getting Redis value: {e}")
        return {"status": False}


def delPasswordRedis(tempPwd: str):
    try:
        client2.delete(tempPwd)
        return {"status": True}
    except Exception as e:
        print(f"Error deleting Redis key: {e}")
        return {"status": False}


def setCompanyRedis(uuid: str, companyId: int):
    try:
        client3.set(uuid, companyId)
        return {"status": True}
    except Exception as e:
        print(f"Error setting Redis keys: {e}")
        return {"status": False}


def getCompanyRedis(uuid: str):
    try:
        result = client3.get(uuid)
        if result:
            return {"status": True, "uuid": uuid, "companyId": result}
        return {"status": False, "message": "Key not found"}
    except Exception as e:
        print(f"Error getting Redis value: {e}")
        return {"status": False}


def delCompanyRedis(uuid: str):
    try:
        client3.delete(uuid)
        return {"status": True}
    except Exception as e:
        print(f"Error deleting Redis key: {e}")
        return {"status": False}


def setInviteRedis(uuid: str, token: str, expireSeconds: int | None = None):
    try:
        if expireSeconds:
            client3.set(uuid, token, ex=expireSeconds)
        else:
            client3.set(uuid, token)
        print(f"Success: Set Redis - uuid: {uuid}")
        return {"status": True}
    except Exception as e:
        print(f"Error setting Redis keys: {e}")
        return {"status": False}


def delInviteRedis(uuid: str):
    try:
        client3.delete(uuid)
        return {"status": True}
    except Exception as e:
        print(f"Error deleting Redis key: {e}")
        return {"status": False}
