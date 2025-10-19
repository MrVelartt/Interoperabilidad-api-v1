from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "dev"

    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None

    # 🔹 Claves Alma (Usuarios)
    ALMA_API_URL: str | None = None
    ALMA_API_KEY: str | None = None

    # 🔹 Claves Primo (Publicaciones)
    PRIMO_API_URL: str | None = None
    PRIMO_API_KEY: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
