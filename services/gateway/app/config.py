from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_")

    # 必须与 platform-auth 共享同一密钥（环境注入，绝不写死）。
    jwt_secret: str = "dev-only-secret-change-me"
    # 场景路由表（由脚手架 new:scenario 自动维护）。
    routes_file: str = str(Path(__file__).resolve().parent.parent / "routes.json")
    # 本地开发：上游用 localhost；生产/容器：用服务名（docker 网络）。
    use_localhost: bool = False
    request_timeout: float = 30.0
    # 可选：静态站点根目录。设置后，非 /api 路径由网关同源托管该目录（SPA 落到 index.html）。
    # 让前端页面与 API 同源，免跨域。生产一般由 nginx 托管前端，这里仅便于本地一体化演示。
    web_root: str = ""


settings = Settings()
