from __future__ import annotations

import json

import httpx

from app.core.config import settings
from app.models.job import Job

_ALLOWED_STYLES = ["kinetic_bold", "premium_minimal", "finance_clean", "viral_pop", "strong_cta"]


class TranscriptIntelligenceService:
    def generate_candidates(self, job: Job, transcript_segments: list[dict]) -> list[dict]:
        duration = float(job.duration_seconds or 60)
        n = job.requested_clip_count or 3

        if not settings.enable_mock_providers and settings.openrouter_api_key:
            try:
                return self._llm_candidates(job, transcript_segments, duration, n)
            except Exception:
                pass

        return self._fallback_candidates(job, transcript_segments, duration, n)

    def _llm_candidates(self, job: Job, transcript_segments: list[dict], duration: float, n: int) -> list[dict]:
        frame_count = int((job.fps or 30) * duration)
        transcript_text = "\n".join(
            f"[{s['start_time']:.1f}s - {s['end_time']:.1f}s] {s['text']}"
            for s in transcript_segments
        )
        prompt = {
            "task": "Select the best short-form video clips from this transcript",
            "video_duration_seconds": duration,
            "video_fps": int(job.fps or 30),
            "total_frames": frame_count,
            "clip_count": n,
            "max_clip_duration_seconds": 60,
            "min_clip_duration_seconds": 15,
            "user_instructions": job.user_instructions or "Pick the most engaging moments",
            "transcript": transcript_text,
            "selection_guidance": [
                "Do not only rely on text. Consider visual pacing by frame span.",
                "Prefer segments with strong hook + fast motion context in first 2-3 seconds.",
                "Avoid near-duplicate windows.",
            ],
            "allowed_caption_styles": _ALLOWED_STYLES,
            "output_schema": {
                "clips": [
                    {
                        "start_time": "float (seconds, within video duration)",
                        "end_time": "float (seconds, within video duration)",
                        "title": "short punchy title (max 60 chars)",
                        "hook": "opening hook line (max 80 chars)",
                        "score": "integer 0-100 virality score",
                        "topic_label": "topic tag",
                        "reasoning": ["reason1", "reason2"],
                        "caption_style": "one of allowed_caption_styles",
                        "broll_prompts": ["visual prompt 1", "visual prompt 2"],
                        "cta_text": "call to action (max 50 chars)",
                        "motion_intensity": "integer 0-100",
                    }
                ]
            },
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://docs.openclaw.ai",
                    "X-Title": "Drafft_API",
                },
                json={
                    "model": settings.openrouter_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an expert short-form video editor for B2B finance content. "
                                "Identify the most viral, engaging 15-60 second clips. "
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
        raw_clips = parsed.get("clips", [])
        if not raw_clips:
            raise ValueError("empty clips from LLM")

        result = []
        for clip in raw_clips[:n]:
            start = float(clip.get("start_time", 0.0))
            end = float(clip.get("end_time", start + 30.0))
            end = min(end, duration)
            start = min(start, end - 5.0)
            style = clip.get("caption_style", "finance_clean")
            if style not in _ALLOWED_STYLES:
                style = "finance_clean"
            result.append({
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "title": clip.get("title", "Key Insight"),
                "hook": clip.get("hook", "Watch this"),
                "score": int(clip.get("score", 80)),
                "topic_label": clip.get("topic_label", "finance"),
                "reasoning_json": clip.get("reasoning", []) + [f"motion_intensity={int(clip.get('motion_intensity', 70))}"],
                "caption_style": style,
                "broll_prompts_json": clip.get("broll_prompts", [])[:3],
                "cta_text": clip.get("cta_text", "Learn more"),
            })
        return result

    def _fallback_candidates(self, job: Job, transcript_segments: list[dict], duration: float, n: int) -> list[dict]:
        """Frame-aware fallback: prioritizes dense/high-energy transcript windows."""
        styles = ["viral_pop", "strong_cta", "kinetic_bold", "finance_clean", "premium_minimal"]
        urgency = {"now", "must", "mistake", "warning", "secret", "don't", "never", "fast", "urgent", "risk"}
        windows: list[tuple[float, float, str, int, int]] = []

        for s in transcript_segments:
            start = float(s.get("start_time", 0.0))
            end = float(s.get("end_time", start + 3.0))
            text = (s.get("text") or "").strip()
            if end <= start:
                continue
            words = [w.strip(".,!?").lower() for w in text.split() if w.strip()]
            wpm_like = int(len(words) / max(end - start, 0.4) * 60)
            urgency_hits = sum(1 for w in words if w in urgency)
            frame_span = int((end - start) * (job.fps or 30))
            score = min(100, 50 + min(30, wpm_like // 8) + min(20, urgency_hits * 5))
            windows.append((start, end, text, frame_span, score))

        if not windows:
            clip_dur = min(30.0, duration / max(n, 1))
            windows = [(i * clip_dur, min((i + 1) * clip_dur, duration), "Key insight", int(clip_dur * (job.fps or 30)), 75) for i in range(n)]

        windows.sort(key=lambda x: x[4], reverse=True)
        picked = windows[:n]
        picked.sort(key=lambda x: x[0])

        candidates = []
        for i, (start, end, text, frame_span, score) in enumerate(picked):
            dur = max(12.0, min(35.0, end - start))
            clip_end = min(duration, start + dur)
            candidates.append({
                "start_time": round(start, 2),
                "end_time": round(clip_end, 2),
                "title": f"High-Impact Moment {i + 1}",
                "hook": (text[:80] or f"Insight #{i + 1}"),
                "score": int(score),
                "topic_label": "finance",
                "reasoning_json": [
                    f"frame_span={frame_span}",
                    "selected using transcript density + urgency + frame-span heuristics",
                ],
                "caption_style": styles[i % len(styles)],
                "broll_prompts_json": ["finance professional speaking to camera", "close-up of charts and key numbers"],
                "cta_text": (job.user_instructions or "Book a strategy call")[:55],
            })
        return candidates
