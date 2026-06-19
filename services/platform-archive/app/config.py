from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLATFORM_ARCHIVE_")

    api_prefix: str = "/api/platform-archive"
    database_url: str = "postgresql+psycopg://dev:dev@localhost:5432/hospital"


settings = Settings()
