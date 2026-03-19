class CaptionPlanService:
    def build_caption_groups(self, transcript_segments: list[dict], caption_style: str) -> list[dict]:
        groups: list[dict] = []
        for segment in transcript_segments:
            words = segment["text"].split()
            chunk_size = 4 if caption_style in {"kinetic_bold", "viral_pop", "strong_cta"} else 6
            total_duration = max(segment["end_time"] - segment["start_time"], 0.1)
            step = total_duration / max((len(words) + chunk_size - 1) // chunk_size, 1)
            for index in range(0, len(words), chunk_size):
                chunk_words = words[index:index + chunk_size]
                start = segment["start_time"] + (index // chunk_size) * step
                end = min(segment["end_time"], start + step)
                groups.append(
                    {
                        "text": " ".join(chunk_words),
                        "start_time": round(start, 3),
                        "end_time": round(end, 3),
                        "style": caption_style,
                        "highlight": chunk_words[0] if chunk_words else None,
                    }
                )
        return groups
