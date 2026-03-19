class WebhookService:
    def build_test_payload(self) -> dict:
        return {"event": "webhook.test", "status": "ok"}
