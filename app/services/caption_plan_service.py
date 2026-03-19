class CaptionPlanService:
    def build_caption_plan(self, transcript_words: list[dict], caption_style: str) -> dict:
        if not transcript_words:
            return {"words": [], "groups": [], "style": caption_style}

        chunk_size = 3 if caption_style in {"kinetic_bold", "viral_pop", "strong_cta"} else 5
        words = []
        for word in transcript_words:
            token = word["word"]
            emphasis = (
                len(token) > 6
                or any(char.isdigit() for char in token)
                or token.lower() in {"best", "wrong", "never", "before", "biggest", "secret", "mistake"}
            )
            words.append(
                {
                    "text": token,
                    "start_time": round(word["start_time"], 3),
                    "end_time": round(word["end_time"], 3),
                    "confidence": word.get("confidence"),
                    "emphasis": emphasis,
                }
            )

        groups = []
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            highlight_word = next((w["text"] for w in chunk if w["emphasis"]), max(chunk, key=lambda w: len(w["text"]))["text"])
            groups.append(
                {
                    "text": " ".join(w["text"] for w in chunk),
                    "start_time": chunk[0]["start_time"],
                    "end_time": chunk[-1]["end_time"],
                    "style": caption_style,
                    "highlight": highlight_word,
                    "animation_in": "pop" if caption_style in {"viral_pop", "kinetic_bold"} else "fade",
                    "animation_out": "fade",
                    "position": "lower_third",
                    "safe_margin": 80,
                    "energy": "high" if caption_style in {"viral_pop", "kinetic_bold", "strong_cta"} else "medium",
                    "words": chunk,
                }
            )

        return {"words": words, "groups": groups, "style": caption_style}
