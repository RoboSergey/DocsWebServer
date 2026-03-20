from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_path: str = "./documents.db"
    secret_key: str = "change-me-in-production"
    token_expire_days: int = 30


settings = Settings()
