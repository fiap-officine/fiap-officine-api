from pydantic import computed_field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DB_USER: str = "dbadmin"
    DB_PASSWORD: str = "password"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "officine_db"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"
    REDIS_DB: str = "0"

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    JWT_SECRET_KEY: str = "default-secret-key-change-in-production-12345"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    WEBHOOK_SHARED_SECRET: str = "change-me"
    AUTH_LAMBDA_URL: str | None = None

    # Observabilidade & New Relic
    NEW_RELIC_LICENSE_KEY: str | None = None
    NEW_RELIC_APP_NAME: str = "fiap-officine-api"
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
