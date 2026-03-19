class TranscriptIntelligenceService:
    HOOK_WORDS = {"mistake", "secret", "warning", "wrong", "before", "never", "avoid", "best", "biggest", "why"}
    CTA_WORDS = {"call", "book", "talk", "apply", "start", "contact", "schedule"}

    def _score_text(self, text: str, position_index: int) -> tuple[int, list[str]]:
        lowered = text.lower()
        reasons: list[str] = []
        score = 60

        hook_hits = sum(1 for word in self.HOOK_WORDS if word in lowered)
        if hook_hits:
            score += min(18, hook_hits * 4)
            reasons.append("contains strong hook language")

        cta_hits = sum(1 for word in self.CTA_WORDS if word in lowered)
        if cta_hits:
            score += min(8, cta_hits * 3)
            reasons.append("contains CTA or action-oriented phrasing")

        if "?" in text:
            score += 6
            reasons.append("uses curiosity/question framing")

        word_count = len(text.split())
        if 12 <= word_count <= 34:
            score += 8
            reasons.append("good short-form length")
        elif word_count < 8:
            score -= 10
            reasons.append("too short to stand alone well")
        else:
            score += 2

        if position_index == 0:
            score += 6
            reasons.append("appears early in the transcript")

        return max(0, min(100, score)), reasons

    def generate_candidates(self, job, transcript_segments: list[dict]) -> list[dict]:
        if not transcript_segments:
            return []

        candidates = []
        for idx, segment in enumerate(transcript_segments):
            text = segment["text"].strip()
            if not text:
                continue

            score, reasons = self._score_text(text, idx)
            title = text[:72].strip().rstrip('.') or f"Clip {idx + 1}"
            first_sentence = text.split('.')[0].strip()
            hook = (first_sentence or text)[:100]
            duration = max(0.1, segment["end_time"] - segment["start_time"])
            if duration < 4:
                score -= 6
                reasons.append("very short segment")
            if duration > 35:
                score -= 8
                reasons.append("longer than ideal short-form clip")

            candidates.append(
                {
                    "start_time": max(0.0, round(segment["start_time"], 3)),
                    "end_time": round(segment["end_time"], 3),
                    "title": title,
                    "hook": hook,
                    "score": max(0, min(100, score)),
                    "topic_label": "mortgage advice" if "mortgage" in text.lower() else "financial services",
                    "reasoning_json": reasons + ["derived from actual transcript segment", "starts on spoken boundary"],
                    "caption_style": job.style_preset,
                    "broll_prompts_json": [
                        f"cinematic b-roll matching: {hook}",
                        "professional finance office environment",
                        "close-up paperwork and phone consultation",
                    ],
                    "cta_text": "Talk to our team before making your next move",
                }
            )

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[: max(job.requested_clip_count, 1)]
