from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Gemini
    gemini_api_key: str
    gemini_model: str

    # PostgreSQL
    pg_db_user: str
    pg_db_password: str
    pg_db_host: str
    pg_db_port: int = 5432
    pg_db_database: str = "ESG"

    # MySQL
    mysql_host: str
    mysql_port: int = 3306
    mysql_user: str
    mysql_password: str
    mysql_database: str
    db_decryption_key: str
    # HuggingFace
    hf_token: str

    @property
    def pg_database_url(self) -> str:
        return f"postgresql://{self.pg_db_user}:{self.pg_db_password}@{self.pg_db_host}:{self.pg_db_port}/{self.pg_db_database}"

# 설정 객체 생성
settings = Settings()