from fastapi import APIRouter

from app.services.webhook_service import WebhookService

router = APIRouter()


@router.post("/test")
def test_webhook() -> dict:
    return WebhookService().build_test_payload()
