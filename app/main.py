from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routes import router as api_router
from app.tasks.scheduler import start_scheduler, stop_scheduler

from app.db.database import engine
from app.db.models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize scheduler, database connections, etc.
    print("Starting up Event Scraper backend...")

    # Initialize Database Schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Database schema initialized.")

    start_scheduler()
    yield
    # Shutdown: Clean up resources
    print("Shutting down Event Scraper backend...")
    stop_scheduler()

app = FastAPI(
    title="Event Scraper API",
    description="API for the long-running event aggregation platform in Berlin.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api-docs", # Mandatory HF Spaces documentation endpoint
    redoc_url=None,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Event Scraper API is running."}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
