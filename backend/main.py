import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse

from backend.database import init_db
from backend.routes import (
    upload,
    cleaning,
    classification,
    sentiment,
    dashboard,
    chatbot,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database tables on startup."""
    init_db()
    yield


app = FastAPI(
    title="AlphaEV Intelligence Platform API",
    description="Explainable AI-Powered EV Review Intelligence Platform Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers (all routers define prefix="/api/v1")
app.include_router(upload.router)
app.include_router(cleaning.router)
app.include_router(classification.router)
app.include_router(sentiment.router)
app.include_router(dashboard.router)
app.include_router(chatbot.router)

# Mount static files if directory exists
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", tags=["health"])
def root():
    """Root endpoint providing platform status and API references."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)

    return {
        "platform": "AlphaEV - Explainable AI-Powered EV Review Intelligence",
        "version": "1.0.0",
        "status": "online",
        "documentation": "/docs",
        "api_prefix": "/api/v1",
    }


@app.get("/api/v1/health", tags=["health"])
@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "alphaev-backend",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
