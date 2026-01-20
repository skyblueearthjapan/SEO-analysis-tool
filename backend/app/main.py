"""
SEO Analysis API - FastAPI Application
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.models.schemas import HealthResponse
from app.routers import jobs_router, pages_router, results_router, sites_router
from app.routers.progress import router as progress_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


# Create FastAPI application
app = FastAPI(
    title="SEO Analysis API",
    description="SEO診断アプリケーションのバックエンドAPI",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    sites_router,
    prefix="/api/v1/sites",
    tags=["sites"]
)
app.include_router(
    pages_router,
    prefix="/api/v1/sites/{site_id}/pages",
    tags=["pages"]
)
app.include_router(
    jobs_router,
    prefix="/api/v1/sites/{site_id}/analysis-jobs",
    tags=["jobs"]
)
app.include_router(
    results_router,
    prefix="/api/v1/sites/{site_id}/analysis-results",
    tags=["results"]
)
app.include_router(
    progress_router,
    prefix="/api/v1/sites",
    tags=["progress"]
)


@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        time=datetime.utcnow()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
