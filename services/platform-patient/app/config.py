from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLATFORM_PATIENT_")

    api_prefix: str = "/api/platform-patient"
    database_url: str = "postgresql+psycopg://dev:dev@localhost:5432/hospital"
    # 患者敏感字段加密密钥：运行时由环境注入，生产必须覆盖，绝不写死/不进仓库。
    pii_key: str = "dev-only-pii-key-change-me"


settings = Settings()
