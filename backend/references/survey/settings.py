from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    환경변수 기반 설정 관리
    (Pydantic Settings v2 방식)
    """

    # Google Service Account 경로
    GOOGLE_APPLICATION_CREDENTIALS: str

    # Google Project ID (선택)
    GOOGLE_PROJECT_ID: str | None = None

    # APPS SCRIPT URL(배포시 env 설정 다시)
    APPS_SCRIPT_URL:str
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


# 전역 settings 객체
settings = Settings()