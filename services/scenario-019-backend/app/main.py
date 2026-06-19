from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.clinical import router as clinical_router
from app.api.mdt import router as mdt_router
from app.api.routes import router

app = FastAPI(title="场景019 · 转诊一件事")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "scenario": "019"}


app.include_router(router)
app.include_router(clinical_router)
app.include_router(mdt_router)
app.include_router(admin_router)
