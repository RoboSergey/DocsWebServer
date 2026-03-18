from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_path: str = "./documents.db"

    class Config:
        env_file = ".env"


settings = Settings()
