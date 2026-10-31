from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(extra="ignore")

    APP_NAME: str = "Brightloop Subscription Management API"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "local"

    DATABASE_URL: str

    SECRET_KEY: str

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    FRONTEND_ORIGIN: str = "http://localhost:5173"


settings = Settings()