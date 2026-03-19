class CaptionPlanService:
    def build_caption_plan(self, transcript_words: list[dict], caption_style: str) -> dict:
        if not transcript_words:
            return {"words": [], "groups": [], "style": caption_style}

        chunk_size = 3 if caption_style in {"kinetic_bold", "viral_pop", "strong_cta"} else 5
        words = [
            {
                "text": word["word"],
                "start_time": round(word["start_time"], 3),
                "end_time": round(word["end_time"], 3),
                "confidence": word.get("confidence"),
                "emphasis": len(word["word"]) > 6,
            }
            for word in transcript_words
        ]

        groups = []
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            groups.append(
                {
                    "text": " ".join(w["text"] for w in chunk),
                    "start_time": chunk[0]["start_time"],
                    "end_time": chunk[-1]["end_time"],
                    "style": caption_style,
                    "highlight": max(chunk, key=lambda w: len(w["text"]))["text"],
                    "animation_in": "pop" if caption_style in {"viral_pop", "kinetic_bold"} else "fade",
                    "animation_out": "fade",
                    "position": "lower_third",
                    "safe_margin": 80,
                    "words": chunk,
                }
            )

        return {"words": words, "groups": groups, "style": caption_style}
