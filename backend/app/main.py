from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api import scans, results, settings, health
from app.api import auth, admin
from app.core.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("DorkRaptor backend started")
    yield
    logger.info("DorkRaptor backend shutting down")


app = FastAPI(
    title="DorkRaptor API",
    description="OSINT & Google Dork Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(scans.router, prefix="/api/v1/scans", tags=["scans"])
app.include_router(results.router, prefix="/api/v1/results", tags=["results"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])


@app.get("/")
async def root():
    return {"name": "DorkRaptor", "version": "1.0.0", "status": "operational"}
