from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # [환경 설정]
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    gemini_api_key: str
    gemini_model: str

    pg_db_user: str
    pg_db_password: str
    pg_db_host: str
    pg_db_port: int = 5432
    pg_db_database: str = "ESG"

    hf_token: str
    @property
    def pg_database_url(self) -> str:
        """PostgreSQL 접속용 URL을 자동으로 생성"""
        return f"postgresql://{self.pg_db_user}:{self.pg_db_password}@{self.pg_db_host}:{self.pg_db_port}/{self.pg_db_database}"

# 설정 객체 생성
settings = Settings()