from pydantic_settings import BaseSettings
from pydantic import SecretStr, Field

class Settings(BaseSettings):
    skill_id: SecretStr
    fer_url: SecretStr
    fer_timeout: int = Field(default=10)
    fer_login: SecretStr
    fer_password: SecretStr
    
    web_server_host: str = Field(default="127.0.0.1")
    web_server_port: int = Field(default=8000)
    webhook_path: str = Field(default="/alice")
    debug: bool = Field(default=True)

    # Новые настройки для Celery и Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/0")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


config = Settings()
