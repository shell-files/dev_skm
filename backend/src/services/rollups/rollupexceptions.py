"""
rollupexceptions.py
레이어: Service (rollups)
역할: 롤업 서비스 커스텀 예외 클래스 정의.
"""
from typing import Optional


class RollupError(Exception):
    def __init__(self, statusCode: int, code: str, message: str, data: Optional[dict] = None):
        super().__init__(message)
        self.statusCode = statusCode
        self.code = code
        self.message = message
        self.data = data or {}
