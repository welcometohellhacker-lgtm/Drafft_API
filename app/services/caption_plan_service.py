class CaptionPlanService:
    # Words per caption card by style
    _CHUNK_SIZES = {
        "kinetic_bold": 3,
        "viral_pop": 3,
        "strong_cta": 4,
        "finance_clean": 5,
        "premium_minimal": 6,
    }

    def build_caption_groups(self, transcript_segments: list[dict], caption_style: str) -> list[dict]:
        chunk_size = self._CHUNK_SIZES.get(caption_style, 4)
        groups: list[dict] = []

        for segment in transcript_segments:
            words = segment["text"].split()
            if not words:
                continue
            seg_duration = max(segment["end_time"] - segment["start_time"], 0.1)
            secs_per_word = seg_duration / len(words)

            for idx in range(0, len(words), chunk_size):
                chunk = words[idx : idx + chunk_size]
                word_start = idx * secs_per_word
                word_end = min((idx + len(chunk)) * secs_per_word, seg_duration)
                abs_start = round(segment["start_time"] + word_start, 3)
                abs_end = round(segment["start_time"] + word_end, 3)
                # Guarantee minimum display time
                if abs_end - abs_start < 0.3:
                    abs_end = abs_start + 0.3

                # Uppercase for impact styles
                text = " ".join(chunk)
                if caption_style in ("kinetic_bold", "viral_pop"):
                    text = text.upper()

                groups.append({
                    "text": text,
                    "start_time": abs_start,
                    "end_time": abs_end,
                    "style": caption_style,
                    "highlight": chunk[0] if chunk else None,
                })

        return groups
