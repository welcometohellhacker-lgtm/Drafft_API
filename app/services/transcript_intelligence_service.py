from app.models.job import Job


class TranscriptIntelligenceService:
    def generate_candidates(self, job: Job, transcript_segments: list[dict]) -> list[dict]:
        transcript_text = " ".join(segment["text"] for segment in transcript_segments)
        return [
            {
                "start_time": 0.0,
                "end_time": 14.0,
                "title": "The biggest mistake homebuyers make first",
                "hook": "Most buyers focus on the wrong number",
                "score": 93,
                "topic_label": "mortgage advice",
                "reasoning_json": [
                    "strong hook in first 2 seconds",
                    "clear pain point",
                    "complete standalone thought",
                    "high educational shareability",
                ],
                "caption_style": job.style_preset,
                "broll_prompts_json": [
                    "young couple reviewing mortgage estimate at kitchen table",
                    "close-up of house keys and paperwork",
                ],
                "cta_text": "Talk to our team before locking your rate",
            },
            {
                "start_time": 6.2,
                "end_time": 14.0,
                "title": "Why financial videos need a clear CTA",
                "hook": transcript_text[:70],
                "score": 88,
                "topic_label": "financial services marketing",
                "reasoning_json": ["strong educational framing", "self-contained insight"],
                "caption_style": "strong_cta",
                "broll_prompts_json": ["financial advisor speaking to client across a desk"],
                "cta_text": "Book a strategy call",
            },
        ][: job.requested_clip_count]
