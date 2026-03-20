from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class VideoPreprocessingService:
    def __init__(self) -> None:
        self.storage = StorageService()
        self._ffmpeg = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
        self._ffprobe = shutil.which("ffprobe") or "/usr/bin/ffprobe"

    def probe(self, file_path: str) -> dict:
        """Real FFprobe metadata. Falls back to sensible defaults on error."""
        path = Path(file_path)
        fallback = {
            "duration_seconds": 60.0,
            "fps": 30,
            "width": 1080,
            "height": 1920,
            "is_landscape": False,
            "audio_presence": True,
            "file_size": path.stat().st_size if path.exists() else 0,
            "format": path.suffix.lstrip("."),
        }
        try:
            result = subprocess.run(
                [
                    self._ffprobe, "-v", "quiet",
                    "-print_format", "json",
                    "-show_streams", "-show_format",
                    str(file_path),
                ],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                logger.warning("ffprobe error: %s", result.stderr[-500:])
                return fallback
            data = json.loads(result.stdout)
            video = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                None,
            )
            if not video:
                return fallback
            width = int(video.get("width", 1080))
            height = int(video.get("height", 1920))
            fps_raw = video.get("r_frame_rate", "30/1")
            try:
                num, den = fps_raw.split("/")
                fps = max(1, int(round(int(num) / max(1, int(den)))))
            except Exception:
                fps = 30
            duration = float(data.get("format", {}).get("duration") or video.get("duration") or 60)
            has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
            return {
                "duration_seconds": round(duration, 3),
                "fps": fps,
                "width": width,
                "height": height,
                "is_landscape": width > height,
                "audio_presence": has_audio,
                "file_size": path.stat().st_size if path.exists() else 0,
                "format": path.suffix.lstrip("."),
            }
        except Exception as exc:
            logger.warning("probe failed (%s), using fallback", exc)
            return fallback

    def make_vertical(self, input_path: str, job_id: str) -> str | None:
        """
        Convert a landscape video to 9:16 portrait using a blur-background composite:
        - Background: scaled to fill 1080x1920, gaussian blurred
        - Foreground: scaled to fit within 1080x1920 (letterboxed, sharp)
        For already-vertical input, just scales to 1080x1920.
        Returns the absolute output path string, or None on failure.
        """
        output_path = self.storage.job_dir(job_id) / "processed_vertical.mp4"
        info = self.probe(input_path)
        is_landscape = info.get("is_landscape", False)
        has_audio = info.get("audio_presence", True)

        try:
            if is_landscape:
                # Blur-background composite: sharp fg centered over blurred bg
                filtergraph = (
                    "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                    "crop=1080:1920,gblur=sigma=30[bg];"
                    "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
                    "[bg][fg]overlay=(W-w)/2:(H-h)/2[out]"
                )
                vf_args = ["-filter_complex", filtergraph, "-map", "[out]"]
            else:
                # Already portrait: scale to fit, pad if needed
                filtergraph = (
                    "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
                    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black[out]"
                )
                vf_args = ["-filter_complex", filtergraph, "-map", "[out]"]

            audio_args = ["-map", "0:a", "-c:a", "aac", "-b:a", "192k"] if has_audio else ["-an"]

            cmd = [
                self._ffmpeg, "-y",
                "-i", str(input_path),
                *vf_args,
                *audio_args,
                "-c:v", "libx264", "-crf", "20", "-preset", "fast",
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if result.returncode != 0:
                logger.error("FFmpeg make_vertical failed: %s", result.stderr[-1500:])
                return None
            logger.info("Landscape → vertical (blur bg) done: %s", output_path)
            return str(output_path)
        except Exception as exc:
            logger.error("make_vertical exception: %s", exc)
            return None

    def merge_segments(
        self,
        source_path: str,
        job_id: str,
        clip_id: str,
        segments: list[dict],
    ) -> tuple[str | None, float]:
        """
        Concatenate multiple time segments from a vertical source video into a single clip.
        Uses a two-phase approach to avoid loading the full source into memory:
          1. Extract each segment individually via input-side seeking (low RAM footprint).
          2. Concatenate with the FFmpeg concat demuxer (-c copy, no re-encode).
        Returns (absolute output path, total_duration_seconds) or (None, 0).
        """
        if not segments:
            return None, 0.0

        clip_dir = self.storage.clip_dir(job_id, clip_id)
        output_path = clip_dir / "merged_source.mp4"
        info = self.probe(source_path)
        has_audio = info.get("audio_presence", True)

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                seg_files: list[Path] = []

                # Phase 1: extract each segment individually.
                # -ss before -i uses fast keyframe seek; -t limits output duration.
                # Re-encoding with ultrafast ensures proper keyframe boundaries for concat.
                audio_args = ["-c:a", "aac", "-b:a", "192k"] if has_audio else ["-an"]
                for i, seg in enumerate(segments):
                    start = max(0.0, float(seg.get("start_time", 0)))
                    end = float(seg.get("end_time", start + 30))
                    duration = max(0.1, end - start)
                    seg_out = tmp_path / f"seg_{i}.mp4"

                    cmd = [
                        self._ffmpeg, "-y",
                        "-ss", f"{start:.3f}",
                        "-i", str(source_path),
                        "-t", f"{duration:.3f}",
                        "-c:v", "libx264", "-crf", "20", "-preset", "ultrafast",
                        *audio_args,
                        "-avoid_negative_ts", "make_zero",
                        str(seg_out),
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    if result.returncode != 0:
                        logger.error("FFmpeg segment %d extraction failed: %s", i, result.stderr[-1000:])
                        return None, 0.0
                    seg_files.append(seg_out)

                # Phase 2: concatenate via concat demuxer (stream copy — no re-encode).
                concat_list = tmp_path / "concat_list.txt"
                concat_list.write_text("\n".join(f"file '{f}'" for f in seg_files))

                cmd = [
                    self._ffmpeg, "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", str(concat_list),
                    "-c", "copy",
                    str(output_path),
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    logger.error("FFmpeg concat failed: %s", result.stderr[-1000:])
                    return None, 0.0

            total_duration = sum(
                max(0.0, float(s.get("end_time", 0)) - max(0.0, float(s.get("start_time", 0))))
                for s in segments
            )
            logger.info("Merged %d segments → %s (%.1fs)", len(segments), output_path, total_duration)
            return str(output_path), round(total_duration, 3)
        except Exception as exc:
            logger.error("merge_segments exception: %s", exc)
            return None, 0.0

    def extract_highlights(
        self,
        input_path: str,
        job_id: str,
        is_landscape: bool,
        segments: list[dict],
    ) -> list[dict]:
        """
        Extract short (≤4s) B-roll clips from source video at interesting transcript moments.
        Uses blur-background for landscape sources.
        """
        if not segments:
            return []

        highlights_dir = self.storage.job_dir(job_id) / "highlights"
        highlights_dir.mkdir(exist_ok=True)

        if is_landscape:
            vf = (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,gblur=sigma=30[bg];"
                "[in]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2"
            )
            # For highlights just use simple approach (simpler filtergraph inside -ss/-t)
            crop_vf = (
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,gblur=sigma=25[bg];"
                "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[out]"
            )
            vf_args = ["-filter_complex", crop_vf, "-map", "[out]"]
        else:
            vf_args = [
                "-vf",
                "scale=1080:1920:force_original_aspect_ratio=decrease,"
                "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
            ]

        assets = []
        for idx, seg in enumerate(segments[:6]):
            start = max(0.0, float(seg.get("start_time", 0)))
            raw_end = float(seg.get("end_time", start + 2.5))
            duration = min(4.0, max(0.8, raw_end - start))
            out_path = highlights_dir / f"highlight_{idx}.mp4"
            cmd = [
                self._ffmpeg, "-y",
                "-ss", f"{start:.3f}",
                "-i", str(input_path),
                "-t", f"{duration:.3f}",
                *vf_args,
                "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
                "-an",
                str(out_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            if result.returncode == 0 and out_path.exists() and out_path.stat().st_size > 1000:
                assets.append({
                    "url": self.storage.public_url_for(out_path),
                    "start_time": start,
                    "end_time": start + duration,
                })
            else:
                logger.warning("highlight extraction failed for segment %d: %s", idx, result.stderr[-300:])

        return assets
