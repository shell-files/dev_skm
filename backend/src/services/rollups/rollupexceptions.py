from typing import Optional


class RollupError(Exception):
    def __init__(self, statusCode: int, code: str, message: str, data: Optional[dict] = None):
        super().__init__(message)
        self.statusCode = statusCode
        self.code = code
        self.message = message
        self.data = data or {}
