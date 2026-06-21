from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "platform-ai"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"

    model_config = {"env_prefix": "PLATFORM_AI_", "case_sensitive": False}


settings = Settings()
