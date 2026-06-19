from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="场景006 · 线上复诊")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "scenario": "006"}


app.include_router(router)
