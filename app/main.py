from fastapi import FastAPI
from app.routes.score import router as score_router

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(score_router)