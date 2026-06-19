from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCENARIO_019_")

    scenario_id: str = "019"
    api_prefix: str = "/api/scenario-019"
    # 本场景在平台里的代码（与 platform_clearing.service_rate_card.scenario_code 对应）
    scenario_code: str = "scenario-019"
    # 数据库/密钥等通过环境注入，绝不写死（见根 CLAUDE.md 合规条款）。
    # 用 postgresql+psycopg（psycopg3）方言；本地 dev 库由 compose.dev.yml 提供。
    database_url: str = "postgresql+psycopg://dev:dev@localhost:5432/hospital"


settings = Settings()
