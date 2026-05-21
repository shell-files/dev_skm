from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
  host_ip: str
  domain: str
  # --------------------------
  # ocrai.py
  # --------------------------
  file_dir: str
  gemini_api_key: str
  gemini_model: str
  # --------------------------
  # kafka config
  # --------------------------
  kafka_server: str
  kafka_topic: str
  # --------------------------
  # email config
  # --------------------------
  mail_username: str
  mail_password: str
  mail_from: str
  mail_port: int = 587
  mail_server: str = "smtp.gmail.com"
  mail_from_name: str = "W.I.T.H"
  mail_starttls: bool = True
  mail_ssl_tls: bool = False
  use_credentials: bool = True
  validate_certs: bool = True
  # tokenset.py
  # --------------------------
  # secret_key: str
  private_key: str = "secrets/authpr.pem"
  public_key: str = "secrets/authpb.pem"
  access_token_expire_minutes: int
  refresh_token_expire_days: int
  invite_token_expire_days: int
  # --------------------------
  # rediscl.py
  # --------------------------
  redis_host: str
  redis_port: int
  redis_db1: int
  redis_db2: int
  redis_db3: int
  # --------------------------
  # file.py
  # --------------------------
  service_key: str
  # --------------------------
  # ocr.py
  # --------------------------
  ocr_key_path: str = "secrets/ocr_key.json"
  # --------------------------
  # db.py
  # --------------------------
  maria_db_user: str
  maria_db_password: str
  maria_db_host: str
  maria_db_database: str
  maria_db_port: int
  maria_db_key: str
  cookie_key: str
  

  model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
  )

settings = Settings()
