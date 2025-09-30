from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "dev"
    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
