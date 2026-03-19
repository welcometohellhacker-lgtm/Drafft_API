from fastapi import APIRouter

from app.api.v1.routes import assets, health, jobs, projects, renders, style_presets, ultimate_clips, webhooks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(renders.router, prefix="/renders", tags=["renders"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(style_presets.router, prefix="/style-presets", tags=["style-presets"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

api_router.include_router(ultimate_clips.router, prefix="/ultimate-clips", tags=["ultimate-clips"])
