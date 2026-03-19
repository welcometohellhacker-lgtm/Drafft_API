class StatusService:
    def build_status_payload(self, job) -> dict:
        return {
            "job_id": job.id,
            "status": job.status,
            "current_step": job.current_step,
            "progress_percent": job.progress_percent,
            "failure_reason": job.failure_reason,
            "retryable": job.status == "failed",
            "timeline": [
                {"step": "created", "done": True},
                {"step": "uploaded", "done": job.progress_percent >= 5},
                {"step": "preprocessing", "done": job.progress_percent >= 10},
                {"step": "transcribing", "done": job.progress_percent >= 30},
                {"step": "analyzing", "done": job.progress_percent >= 55},
                {"step": "rendering", "done": job.progress_percent >= 80},
                {"step": "completed", "done": job.progress_percent >= 100},
            ],
        }
