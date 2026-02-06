"""
Routes package - API endpoints organized by domain

Exposes a single api_router that includes all route modules.
"""

from fastapi import APIRouter

from routes import auth, analysis, upload, pipeline, chat, health

# Main API router that aggregates all route modules
api_router = APIRouter()

# Register route modules
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
api_router.include_router(analysis.router, prefix="/api", tags=["Analysis"])
api_router.include_router(upload.router, prefix="/api", tags=["Upload"])
api_router.include_router(pipeline.router, prefix="/api", tags=["Pipeline"])
api_router.include_router(chat.router, prefix="/api", tags=["Chat"])
