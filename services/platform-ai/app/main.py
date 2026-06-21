"""平台 AI 能力服务：处方审方、AI 分诊。

无数据库依赖；鉴权由网关注入（X-User-* 头）。
配置 ANTHROPIC_API_KEY 后调用 Claude API，否则降级至规则引擎。
"""

from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="平台服务 · AI 能力")
app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "platform-ai"}
