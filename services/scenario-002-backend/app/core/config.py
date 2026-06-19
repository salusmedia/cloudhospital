from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCENARIO_002_")

    scenario_id: str = "002"
    api_prefix: str = "/api/scenario-002"
    scenario_code: str = "scenario-002"
    database_url: str = "postgresql+psycopg://dev:dev@localhost:5432/hospital"


settings = Settings()
