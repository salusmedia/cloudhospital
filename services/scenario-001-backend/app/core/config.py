from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCENARIO_001_")

    scenario_id: str = "001"
    api_prefix: str = "/api/scenario-001"
    # 数据库/密钥等通过环境注入，绝不写死（见根 CLAUDE.md 合规条款）。
    database_url: str = "postgresql://dev:dev@localhost:5432/hospital"


settings = Settings()
