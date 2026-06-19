from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLATFORM_AUTH_")

    # JWT 密钥：必须与 gateway 共享，由环境注入，绝不写死/不进仓库。
    # 这里的默认值仅供本地开发，生产必须覆盖。
    jwt_secret: str = "dev-only-secret-change-me"
    token_ttl_seconds: int = 8 * 3600        # 访问令牌 TTL
    refresh_ttl_seconds: int = 7 * 24 * 3600  # 刷新令牌 TTL
    api_prefix: str = "/api/platform-auth"
    # 身份库：对接 platform_identity（app_user/角色/数据权限/场景授权）。
    database_url: str = "postgresql+psycopg://dev:dev@localhost:5432/hospital"


settings = Settings()
