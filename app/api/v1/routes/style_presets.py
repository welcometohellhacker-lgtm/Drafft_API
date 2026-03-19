from fastapi import APIRouter

from app.services.caption_service import CaptionService

router = APIRouter()


@router.get("")
def get_style_presets() -> dict:
    return CaptionService().list_presets()
