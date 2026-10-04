from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import Base, SessionLocal, engine
from app.routes import artisans, bookings, jobs
from app.services.seed import seed_demo_artisans
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_artisans(db)
    yield


app = FastAPI(
    title="FixPune Prototype API",
    description="Local marketplace MVP with Gemini-assisted intake and simulated payments.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(artisans.router)
app.include_router(jobs.router)
app.include_router(bookings.router)


@app.get("/health")
def health():
    return {"status": "ok"}
