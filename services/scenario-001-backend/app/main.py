from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="场景001 · 在线随访")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "scenario": "001"}


app.include_router(router)
