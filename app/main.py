from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy import create_engine
import os

from app.routes.images import router as images_router

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/postgres"
)

engine = create_engine(DATABASE_URL)

app = FastAPI()

# register routes *after* app is created
app.include_router(images_router)

@app.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception:
        return {"status": "ok", "db": "down"}