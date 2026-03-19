class BrollService:
    def build_plan(self, clip_id: str, transcript_segments: list[dict], prompts: list[str]) -> dict:
        windows: list[dict] = []
        for index, prompt in enumerate(prompts):
            base_start = round(1.5 + (index * 2.5), 2)
            windows.append(
                {
                    "clip_id": clip_id,
                    "prompt": prompt,
                    "start_time": base_start,
                    "end_time": round(base_start + 1.8, 2),
                    "asset_mode": "ai_still",
                    "motion": "slow_zoom_in",
                    "priority": index + 1,
                }
            )
        context = [segment["text"] for segment in transcript_segments[:2]]
        return {
            "clip_id": clip_id,
            "context": context,
            "windows": windows,
        }
