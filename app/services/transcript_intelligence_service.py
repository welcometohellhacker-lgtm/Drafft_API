class TranscriptIntelligenceService:
    HOOK_WORDS = {"mistake", "secret", "warning", "wrong", "before", "never", "avoid", "best", "biggest", "why"}
    CTA_WORDS = {"call", "book", "talk", "apply", "start", "contact", "schedule"}
    FILLER_WORDS = {"um", "uh", "like", "you know", "basically", "actually"}

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

        filler_hits = sum(1 for word in self.FILLER_WORDS if word in lowered)
        if filler_hits:
            score -= min(8, filler_hits * 2)
            reasons.append("contains filler language")

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

    def _refine_window(self, segments: list[dict], index: int) -> tuple[float, float, list[str]]:
        current = segments[index]
        start = current["start_time"]
        end = current["end_time"]
        reasons = ["starts on spoken boundary"]

        if index > 0:
            prev = segments[index - 1]
            gap = start - prev["end_time"]
            if gap < 0.8 and len(prev["text"].split()) < 8:
                start = prev["start_time"]
                reasons.append("pulled in previous short setup phrase")
            elif gap > 1.2:
                reasons.append("natural pause before clip start")

        if index + 1 < len(segments):
            nxt = segments[index + 1]
            if nxt["start_time"] - end < 0.8 and len(nxt["text"].split()) < 10:
                end = nxt["end_time"]
                reasons.append("extended to include complete payoff sentence")

        duration = end - start
        if duration < 8 and index + 1 < len(segments):
            end = max(end, segments[index + 1]["end_time"])
            reasons.append("extended to hit minimum short-form duration")
        if end - start > 28:
            end = start + 28
            reasons.append("trimmed to short-form max duration")

        return round(max(0.0, start), 3), round(end, 3), reasons

    def generate_candidates(self, job, transcript_segments: list[dict]) -> list[dict]:
        if not transcript_segments:
            return []

        candidates = []
        for idx, segment in enumerate(transcript_segments):
            text = segment["text"].strip()
            if not text:
                continue

            start_time, end_time, boundary_reasons = self._refine_window(transcript_segments, idx)
            window_parts = [segment["text"]]
            if start_time < segment["start_time"] and idx > 0:
                window_parts.insert(0, transcript_segments[idx - 1]["text"])
            if end_time > segment["end_time"] and idx + 1 < len(transcript_segments):
                window_parts.append(transcript_segments[idx + 1]["text"])
            window_text = " ".join(window_parts).strip()

            score, reasons = self._score_text(window_text, idx)
            title = window_text[:72].strip().rstrip('.') or f"Clip {idx + 1}"
            first_sentence = window_text.split('.')[0].strip()
            hook = (first_sentence or window_text)[:100]
            duration = max(0.1, end_time - start_time)
            if 10 <= duration <= 24:
                score += 6
                reasons.append("duration fits high-retention short-form range")
            elif duration < 6:
                score -= 10
                reasons.append("very short segment")
            elif duration > 30:
                score -= 10
                reasons.append("too long for strongest retention")

            candidates.append(
                {
                    'start_time': start_time,
                    'end_time': end_time,
                    'title': title,
                    'hook': hook,
                    'score': max(0, min(100, score)),
                    'topic_label': 'mortgage advice' if 'mortgage' in window_text.lower() else 'financial services',
                    'reasoning_json': reasons + boundary_reasons + ['derived from actual transcript segment'],
                    'caption_style': job.style_preset,
                    'broll_prompts_json': [
                        f'cinematic b-roll matching: {hook}',
                        'professional finance office environment',
                        'close-up paperwork and phone consultation',
                    ],
                    'cta_text': 'Talk to our team before making your next move',
                }
            )

        candidates.sort(key=lambda item: item['score'], reverse=True)
        return candidates[: max(job.requested_clip_count, 1)]
