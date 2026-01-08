from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "dev"
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./docops.db"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
