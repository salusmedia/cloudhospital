from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLATFORM_FILE_")

    api_prefix: str = "/api/platform-file"
    database_url: str = "postgresql+psycopg://dev:dev@localhost:5432/hospital"
    # 对象存储桶（演示占位；原件实际走 MinIO/S3）。
    bucket: str = "hospital"


settings = Settings()
