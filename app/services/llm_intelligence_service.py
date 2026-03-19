import json

import httpx

from app.core.config import settings


class LLMIntelligenceService:
    """GPT-driven creative planning with OpenAI Responses API and safe fallback."""

    MODEL_NAME = "gpt-5.4"

    def _fallback(self, transcript_segments: list[dict], project_brand: dict | None = None) -> dict:
        transcript_text = " ".join(segment.get("text", "") for segment in transcript_segments).lower()
        energetic = any(word in transcript_text for word in ["mistake", "warning", "secret", "don't", "wrong"])
        style = "viral_pop" if energetic else "finance_clean"
        palette = {
            "primary": (project_brand or {}).get("primary_color", "#0A2540"),
            "accent": "#00E5A8" if energetic else "#F4B400",
            "text": "#FFFFFF" if energetic else "#F8FAFC",
        }
        return {
            "llm_model": self.MODEL_NAME,
            "provider": "fallback",
            "caption_style": style,
            "font_family": (project_brand or {}).get("font_family", "Inter"),
            "color_palette": palette,
            "animation_pack": "high_energy_punch" if energetic else "clean_finance_flow",
            "transition_pack": "dynamic_cuts" if energetic else "smooth_fades",
            "cta_style": "strong_cta",
            "cto_score": 84 if energetic else 78,
            "reasoning": [
                "fallback style selected from transcript tone",
                "matched color palette to project brand",
                "chose animation intensity based on hook strength",
            ],
        }

    def choose_creative_direction(self, transcript_segments: list[dict], project_brand: dict | None = None) -> dict:
        fallback = self._fallback(transcript_segments, project_brand)
        if not settings.openai_api_key:
            return fallback

        prompt = {
            "task": "Choose creative direction for short-form video repurposing",
            "business_domain": "mortgage insurance finance",
            "project_brand": project_brand or {},
            "transcript_segments": transcript_segments,
            "allowed_caption_styles": ["kinetic_bold", "premium_minimal", "finance_clean", "viral_pop", "strong_cta"],
            "output_schema": {
                "caption_style": "string",
                "font_family": "string",
                "color_palette": {"primary": "hex", "accent": "hex", "text": "hex"},
                "animation_pack": "string",
                "transition_pack": "string",
                "cta_style": "string",
                "cto_score": "integer 0-100",
                "reasoning": ["string"]
            }
        }

        try:
            with httpx.Client(timeout=25.0) as client:
                response = client.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.MODEL_NAME,
                        "input": [
                            {
                                "role": "system",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": "You are a creative director for short-form B2B finance video repurposing. Return only valid JSON."
                                    }
                                ],
                            },
                            {
                                "role": "user",
                                "content": [{"type": "input_text", "text": json.dumps(prompt)}],
                            },
                        ],
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            fallback["reasoning"].append(f"openai fallback used: {exc.__class__.__name__}")
            return fallback

        text_output = None
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    text_output = content.get("text")
                    break
            if text_output:
                break

        if not text_output:
            fallback["reasoning"].append("openai fallback used: empty model output")
            return fallback

        try:
            parsed = json.loads(text_output)
        except json.JSONDecodeError:
            fallback["reasoning"].append("openai fallback used: invalid JSON output")
            return fallback

        return {
            "llm_model": self.MODEL_NAME,
            "provider": "openai",
            "caption_style": parsed.get("caption_style", fallback["caption_style"]),
            "font_family": parsed.get("font_family", fallback["font_family"]),
            "color_palette": parsed.get("color_palette", fallback["color_palette"]),
            "animation_pack": parsed.get("animation_pack", fallback["animation_pack"]),
            "transition_pack": parsed.get("transition_pack", fallback["transition_pack"]),
            "cta_style": parsed.get("cta_style", fallback["cta_style"]),
            "cto_score": parsed.get("cto_score", fallback["cto_score"]),
            "reasoning": parsed.get("reasoning", fallback["reasoning"]),
        }
