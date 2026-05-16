from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
  host_ip: str = "192.168.219.104"
  
  model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
  )

settings = Settings()
