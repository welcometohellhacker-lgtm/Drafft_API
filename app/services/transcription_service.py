from app.models.job import Job


class TranscriptionService:
    def transcribe(self, job: Job) -> list[dict]:
        base = job.user_instructions or "Most buyers focus on the wrong number before they understand total cost."
        return [
            {
                "speaker": "speaker_1",
                "start_time": 0.0,
                "end_time": 6.2,
                "text": f"{base}",
                "confidence": 0.96,
                "words": [
                    {"word": "Most", "start_time": 0.0, "end_time": 0.4, "confidence": 0.99},
                    {"word": "buyers", "start_time": 0.41, "end_time": 0.8, "confidence": 0.98},
                ],
            },
            {
                "speaker": "speaker_1",
                "start_time": 6.2,
                "end_time": 14.0,
                "text": "In mortgage and insurance content, the strongest clips usually start with a pain point and finish with a clear action.",
                "confidence": 0.95,
                "words": [],
            },
        ]
