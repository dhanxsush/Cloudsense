"""
CloudSense API - Main Application Entry Point

App factory pattern with clean separation of concerns.
"""

import os
import logging
from contextlib import asynccontextmanager

# CRITICAL: Load environment variables BEFORE importing auth
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from core import init_db
from routes import api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Analysis directory for static file serving
ANALYSIS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
    "training"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize on startup, cleanup on shutdown."""
    # Startup
    init_db()
    logger.info("Database initialized")
    
    # Ensure analysis directory exists
    if not os.path.exists(ANALYSIS_DIR):
        os.makedirs(ANALYSIS_DIR)
    
    yield
    
    # Shutdown (if needed)
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """
    Application factory - creates and configures the FastAPI app.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="CloudSense API",
        description="TCC Detection and Tracking System API",
        version="2.0.0",
        lifespan=lifespan
    )
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include all API routes
    app.include_router(api_router)
    
    # Mount static files for analysis outputs
    if os.path.exists(ANALYSIS_DIR):
        app.mount("/static/analysis", StaticFiles(directory=ANALYSIS_DIR), name="analysis")
    
    logger.info("CloudSense API v2.0.0 initialized")
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
