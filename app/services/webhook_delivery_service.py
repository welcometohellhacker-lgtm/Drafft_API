class WebhookDeliveryService:
    def build_event(self, job_id: str, event_type: str, status: str) -> dict:
        return {
            "event_type": event_type,
            "job_id": job_id,
            "status": status,
            "delivery_status": "simulated",
        }
