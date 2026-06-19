from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="场景002 · 家庭病床")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "scenario": "002"}


app.include_router(router)
