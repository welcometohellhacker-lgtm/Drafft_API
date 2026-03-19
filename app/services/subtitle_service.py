from app.models.job import Job


class SubtitleService:
    def _format_timestamp_srt(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

    def _format_timestamp_vtt(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"

    def build_srt(self, segments: list[dict]) -> str:
        blocks = []
        for index, segment in enumerate(segments, start=1):
            blocks.append(
                "\n".join(
                    [
                        str(index),
                        f"{self._format_timestamp_srt(segment['start_time'])} --> {self._format_timestamp_srt(segment['end_time'])}",
                        segment["text"],
                    ]
                )
            )
        return "\n\n".join(blocks)

    def build_vtt(self, segments: list[dict]) -> str:
        blocks = ["WEBVTT\n"]
        for segment in segments:
            blocks.append(
                "\n".join(
                    [
                        f"{self._format_timestamp_vtt(segment['start_time'])} --> {self._format_timestamp_vtt(segment['end_time'])}",
                        segment["text"],
                    ]
                )
            )
        return "\n\n".join(blocks)

    def build_assets(self, job: Job, segments: list[dict]) -> dict:
        return {
            "job_id": job.id,
            "srt": self.build_srt(segments),
            "vtt": self.build_vtt(segments),
        }
