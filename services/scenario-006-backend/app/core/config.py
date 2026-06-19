from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCENARIO_006_")

    scenario_id: str = "006"
    api_prefix: str = "/api/scenario-006"
    # 本场景在平台清分里的代码（对应 platform_clearing.service_rate_card.scenario_code）
    scenario_code: str = "scenario-006"
    # 数据库通过环境注入；psycopg3 方言；本地 dev 库由 compose.dev.yml 提供。
    database_url: str = "postgresql+psycopg://dev:dev@localhost:5432/hospital"


settings = Settings()
