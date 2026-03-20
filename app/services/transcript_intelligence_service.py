from __future__ import annotations

import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TranscriptIntelligenceService:
    """Uses LLM to find the best viral clip moments from the full transcript."""

    def generate_candidates(self, job, transcript_segments: list[dict]) -> list[dict]:
        if not transcript_segments:
            return []

        n = max(job.requested_clip_count, 1)

        if settings.openrouter_api_key:
            try:
                return self._llm_candidates(job, transcript_segments, n)
            except Exception as exc:
                logger.warning("LLM clip selection failed (%s), falling back to heuristic", exc)

        return self._heuristic_candidates(job, transcript_segments, n)

    # ── LLM-based selection ───────────────────────────────────────────────────

    def _llm_candidates(self, job, segments: list[dict], n: int) -> list[dict]:
        # Build a compact transcript with timestamps
        transcript_lines = []
        for seg in segments:
            transcript_lines.append(f"[{seg['start_time']:.1f}s-{seg['end_time']:.1f}s] {seg['text']}")
        full_transcript = "\n".join(transcript_lines)

        video_duration = segments[-1]["end_time"] if segments else 60.0

        prompt = {
            "task": "Find the best viral short-form video clips from this transcript",
            "instructions": (
                f"You are a viral content strategist. The video is {video_duration:.0f} seconds long. "
                f"First identify the overall theme/topic of the video. "
                f"Then create exactly {n} viral short-form clips. "
                "Each clip MUST have a clear unifying THEME and can be composed of MULTIPLE non-contiguous "
                "segments from the video stitched together — this lets you combine the best moments "
                "around one theme into a cohesive clip. "
                "Each clip should total 60-120 seconds of content (sum of all its segments). "
                "Each segment within a clip should be a meaningful, continuous spoken moment. "
                "Spread clips across the full video — do not cluster them all at the start. "
                "Pick segments that together tell a complete story: hook → insight → CTA. "
                "Each clip needs: a strong opening hook, a clear theme, and a compelling CTA."
            ),
            "user_instructions": job.user_instructions or "",
            "style_preset": job.style_preset or "finance_clean",
            "full_transcript": full_transcript,
            "output_schema": {
                "video_theme": "overall theme of the full video in one sentence",
                "clips": [
                    {
                        "theme": "the single unifying theme of this clip",
                        "title": "catchy title under 72 chars",
                        "hook": "the strong opening hook line under 120 chars",
                        "cta_text": "compelling call to action under 80 chars",
                        "viral_score": "integer 0-100",
                        "reasoning": "why this clip will go viral",
                        "topic_label": "string",
                        "broll_prompts": ["3 visual b-roll prompt strings matching the theme"],
                        "segments": [
                            {
                                "start_time": "float seconds from transcript",
                                "end_time": "float seconds from transcript",
                                "note": "what this segment contributes to the theme",
                            }
                        ],
                    }
                ],
            },
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://docs.openclaw.ai",
                    "X-Title": "Drafft_API",
                },
                json={
                    "model": settings.openrouter_model or "openai/gpt-4o",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a viral video content strategist specializing in short-form social media. "
                                "Return only valid JSON matching the output_schema exactly."
                            ),
                        },
                        {"role": "user", "content": json.dumps(prompt)},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            parsed = json.loads(response.json()["choices"][0]["message"]["content"])

        clips_data = parsed.get("clips", [])
        if not clips_data:
            raise ValueError("LLM returned no clips")

        logger.info("Video theme: %s", parsed.get("video_theme", "unknown"))

        candidates = []
        for clip in clips_data[:n]:
            raw_segments = clip.get("segments", [])

            # Validate and clamp each segment
            clean_segments = []
            for s in raw_segments:
                seg_start = max(0.0, float(s.get("start_time", 0)))
                seg_end = min(video_duration, float(s.get("end_time", seg_start + 30)))
                if seg_end > seg_start + 1.0:
                    clean_segments.append({
                        "start_time": round(seg_start, 3),
                        "end_time": round(seg_end, 3),
                    })

            # Fallback to single segment if LLM didn't return segments
            if not clean_segments:
                seg_start = max(0.0, float(clip.get("start_time", 0)))
                seg_end = min(video_duration, float(clip.get("end_time", seg_start + 60)))
                clean_segments = [{"start_time": seg_start, "end_time": seg_end}]

            # Clip-level duration: sum of all segments
            total_duration = sum(s["end_time"] - s["start_time"] for s in clean_segments)
            # Clamp total to 60-120s
            if total_duration > 120.0 and len(clean_segments) > 1:
                # Trim last segment to stay within 120s
                excess = total_duration - 120.0
                last = clean_segments[-1]
                last["end_time"] = max(last["start_time"] + 1, last["end_time"] - excess)
                total_duration = 120.0

            # Collect words for captions (relative to clip start = 0)
            clip_words = []
            offset = 0.0
            for s in clean_segments:
                seg_words = self._extract_words_in_range(segments, s["start_time"], s["end_time"])
                for w in seg_words:
                    clip_words.append({
                        **w,
                        "start_time": round(w["start_time"] + offset, 3),
                        "end_time": round(w["end_time"] + offset, 3),
                    })
                offset += s["end_time"] - s["start_time"]

            candidates.append({
                "start_time": 0.0,
                "end_time": round(total_duration, 3),
                "title": (clip.get("title") or "")[:72].strip().rstrip(".") or f"Clip {len(candidates)+1}",
                "hook": (clip.get("hook") or "")[:120].strip(),
                "score": max(0, min(100, int(clip.get("viral_score", 75)))),
                "topic_label": clip.get("topic_label", "content"),
                "reasoning_json": [
                    clip.get("reasoning", "selected by LLM"),
                    f"theme: {clip.get('theme', '')}",
                    f"segments: {len(clean_segments)}",
                    "LLM-driven viral selection",
                ],
                "caption_style": job.style_preset or "finance_clean",
                "broll_prompts_json": clip.get("broll_prompts", [
                    f"cinematic b-roll: {clip.get('theme', '')[:60]}",
                    "professional environment shot",
                    "close-up detail shot",
                ]),
                "cta_text": clip.get("cta_text", "Follow for more"),
                "_words": clip_words,
                "_segments": clean_segments,
            })

        logger.info("LLM selected %d theme-based clips from transcript", len(candidates))
        return candidates

    def _extract_words_in_range(self, segments: list[dict], start: float, end: float) -> list[dict]:
        words = []
        for seg in segments:
            if seg["end_time"] < start or seg["start_time"] > end:
                continue
            for w in seg.get("words", []):
                ws = w.get("start_time", w.get("start", 0.0))
                we = w.get("end_time", w.get("end", 0.0))
                if ws >= start and we <= end:
                    words.append({
                        "text": w.get("word", w.get("text", "")),
                        "start_time": round(ws - start, 3),
                        "end_time": round(we - start, 3),
                        "confidence": w.get("confidence", 0.9),
                        "emphasis": w.get("emphasis", False),
                    })
        return words

    # ── Heuristic fallback ────────────────────────────────────────────────────

    HOOK_WORDS = {"mistake", "secret", "warning", "wrong", "before", "never", "avoid", "best", "biggest", "why"}
    CTA_WORDS = {"call", "book", "talk", "apply", "start", "contact", "schedule"}
    FILLER_WORDS = {"um", "uh", "like", "you know", "basically", "actually"}

    def _heuristic_candidates(self, job, segments: list[dict], n: int) -> list[dict]:
        candidates = []
        for idx, segment in enumerate(segments):
            text = segment["text"].strip()
            if not text:
                continue
            start, end, boundary_reasons = self._refine_window(segments, idx)
            window_text = self._window_text(segments, idx, start, end, segment)
            score, reasons = self._score_text(window_text, idx)
            duration = max(0.1, end - start)
            if 10 <= duration <= 24:
                score += 6
            elif duration < 6:
                score -= 10
            elif duration > 30:
                score -= 10

            candidates.append({
                "start_time": start,
                "end_time": end,
                "title": window_text[:72].strip().rstrip(".") or f"Clip {idx + 1}",
                "hook": window_text.split(".")[0].strip()[:100],
                "score": max(0, min(100, score)),
                "topic_label": "mortgage advice" if "mortgage" in window_text.lower() else "financial services",
                "reasoning_json": reasons + boundary_reasons + ["heuristic selection"],
                "caption_style": job.style_preset,
                "broll_prompts_json": [
                    f"cinematic b-roll matching: {window_text[:60]}",
                    "professional finance office environment",
                    "close-up paperwork and phone consultation",
                ],
                "cta_text": "Talk to our team before making your next move",
                "_words": self._extract_words_in_range(segments, start, end),
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:n]

    def _window_text(self, segments, idx, start, end, segment):
        parts = [segment["text"]]
        if start < segment["start_time"] and idx > 0:
            parts.insert(0, segments[idx - 1]["text"])
        if end > segment["end_time"] and idx + 1 < len(segments):
            parts.append(segments[idx + 1]["text"])
        return " ".join(parts).strip()

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
        else:
            score += 2
        if position_index == 0:
            score += 6
            reasons.append("appears early in transcript")
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
