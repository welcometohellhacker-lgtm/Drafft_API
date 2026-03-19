class TranscriptIntelligenceService:
    def generate_candidates(self, job, transcript_segments: list[dict]) -> list[dict]:
        if not transcript_segments:
            return []

        candidates = []
        for idx, segment in enumerate(transcript_segments[: max(job.requested_clip_count, 1)]):
            text = segment["text"].strip()
            title = text[:72].strip().rstrip('.') or f"Clip {idx + 1}"
            hook = text.split('.')[0][:90].strip() or title
            score = min(98, 78 + (12 if any(k in text.lower() for k in ["mistake", "secret", "warning", "wrong"]) else 6) + idx)
            candidates.append(
                {
                    "start_time": max(0.0, round(segment["start_time"], 3)),
                    "end_time": round(segment["end_time"], 3),
                    "title": title,
                    "hook": hook,
                    "score": score,
                    "topic_label": "mortgage advice" if "mortgage" in text.lower() else "financial services",
                    "reasoning_json": [
                        "derived from actual transcript segment",
                        "starts on spoken boundary",
                        "scores based on hook language and clarity",
                    ],
                    "caption_style": job.style_preset,
                    "broll_prompts_json": [
                        f"cinematic b-roll matching: {hook}",
                        "professional finance office environment",
                    ],
                    "cta_text": "Talk to our team before making your next move",
                }
            )
        return candidates
