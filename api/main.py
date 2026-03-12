from fastapi import FastAPI
from api.webhook import router

app = FastAPI(title="Code Review Agent")

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
