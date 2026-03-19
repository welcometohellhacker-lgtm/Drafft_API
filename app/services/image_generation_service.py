class ImageGenerationService:
    def generate_for_broll(self, job_id: str, clip_id: str, broll_plan: dict, enabled: bool) -> list[dict]:
        if not enabled:
            return []
        assets: list[dict] = []
        for index, window in enumerate(broll_plan.get("windows", []), start=1):
            assets.append(
                {
                    "asset_type": "generated_image",
                    "provider": "mock_image_generation_provider",
                    "prompt": window["prompt"],
                    "url": f"image://{job_id}/{clip_id}/{index}.png",
                    "metadata_json": {
                        "clip_id": clip_id,
                        "start_time": window["start_time"],
                        "end_time": window["end_time"],
                        "motion": window["motion"],
                    },
                }
            )
        return assets
