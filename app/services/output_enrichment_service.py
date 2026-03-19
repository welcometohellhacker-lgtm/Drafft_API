from __future__ import annotations

import json

import httpx

from app.core.config import settings


class OutputEnrichmentService:
    def build_social_caption(self, clip_title: str, hook: str, cta_text: str | None) -> dict:
        if not settings.enable_mock_providers and settings.openrouter_api_key:
            try:
                return self._llm_caption(clip_title, hook, cta_text)
            except Exception:
                pass
        return self._fallback_caption(clip_title, hook, cta_text)

    def _llm_caption(self, clip_title: str, hook: str, cta_text: str | None) -> dict:
        prompt = {
            "task": "Write a high-converting social media caption for a short-form finance video clip",
            "clip_title": clip_title,
            "hook": hook,
            "cta": cta_text or "Follow for more",
            "platforms": ["TikTok", "Instagram Reels", "YouTube Shorts"],
            "output_schema": {
                "social_caption": "punchy 1-2 sentence caption with hook + CTA (max 150 chars)",
                "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
                "thumbnail_notes": ["note about thumbnail text or visual", "second note"],
                "cto_score": "integer 0-100 predicted click-through score",
            },
        }

        with httpx.Client(timeout=20.0) as client:
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
                                "You are a viral social media copywriter specialising in B2B finance content. "
                                "Write captions that stop the scroll and drive action. "
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
        return {
            "social_caption": parsed.get("social_caption", self._fallback_caption(clip_title, hook, cta_text)["social_caption"]),
            "hashtags": parsed.get("hashtags", ["#finance", "#shorts"]),
            "thumbnail_notes": parsed.get("thumbnail_notes", []),
            "cto_score": int(parsed.get("cto_score", 80)),
        }

    def _fallback_caption(self, clip_title: str, hook: str, cta_text: str | None) -> dict:
        caption = f"{hook} — {clip_title}."
        if cta_text:
            caption += f" {cta_text}."
        return {
            "social_caption": caption,
            "hashtags": ["#mortgage", "#finance", "#realestate", "#shorts", "#moneytips"],
            "thumbnail_notes": ["Bold hook text overlay", "High-contrast background"],
            "cto_score": 91 if "mistake" in hook.lower() else 83,
        }
