from __future__ import annotations

import re
import subprocess
from pathlib import Path

from app.core.config import settings

# ffmpeg ASS colour: &HAABBGGRR  (AA=alpha, 00=opaque)
_CAPTION_STYLES: dict[str, dict] = {
    "kinetic_bold": {
        "FontSize": 26, "Bold": 1,
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000", "Outline": 3,
        "BackColour": "&HA0000000", "BorderStyle": 4,
        "MarginV": 200, "Alignment": 2,
    },
    "viral_pop": {
        "FontSize": 28, "Bold": 1,
        "PrimaryColour": "&H0000FFFF",   # yellow
        "OutlineColour": "&H00000000", "Outline": 3,
        "BackColour": "&H90000000", "BorderStyle": 4,
        "MarginV": 200, "Alignment": 2,
    },
    "strong_cta": {
        "FontSize": 24, "Bold": 1,
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H000A2540", "Outline": 3,
        "BackColour": "&H88000000", "BorderStyle": 4,
        "MarginV": 200, "Alignment": 2,
    },
    "finance_clean": {
        "FontSize": 22, "Bold": 0,
        "PrimaryColour": "&H00F8FAFC",
        "OutlineColour": "&H000A2540", "Outline": 2,
        "BackColour": "&H78000000", "BorderStyle": 4,
        "MarginV": 200, "Alignment": 2,
    },
    "premium_minimal": {
        "FontSize": 20, "Bold": 0,
        "PrimaryColour": "&H00F8FAFC",
        "OutlineColour": "&H00000000", "Outline": 1,
        "BackColour": "&H60000000", "BorderStyle": 4,
        "MarginV": 200, "Alignment": 2,
    },
}
_DEFAULT_STYLE = _CAPTION_STYLES["finance_clean"]


def _escape_drawtext(text: str) -> str:
    """Escape special characters for ffmpeg drawtext."""
    return re.sub(r"([\\':,])", r"\\\1", text)


class RenderService:
    def _format_srt_timestamp(self, seconds: float) -> str:
        if seconds < 0:
            seconds = 0.0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

    def _build_clip_srt(self, out_srt: Path, caption_groups: list[dict] | None, clip_start: float) -> bool:
        if not caption_groups:
            return False
        lines: list[str] = []
        idx = 1
        for g in caption_groups:
            text = (g.get("text") or "").strip()
            if not text:
                continue
            rel_start = max(0.0, float(g.get("start_time", 0.0)) - clip_start)
            rel_end = max(rel_start + 0.2, float(g.get("end_time", rel_start + 1.0)) - clip_start)
            lines += [str(idx), f"{self._format_srt_timestamp(rel_start)} --> {self._format_srt_timestamp(rel_end)}", text, ""]
            idx += 1
        if not lines:
            return False
        out_srt.write_text("\n".join(lines), encoding="utf-8")
        return True

    def _style_str(self, caption_style: str) -> str:
        s = _CAPTION_STYLES.get(caption_style, _DEFAULT_STYLE)
        return ",".join(f"{k}={v}" for k, v in s.items())

    def create_render_metadata(self, clip_id: str, aspect_ratio: str) -> dict:
        return {
            "clip_id": clip_id,
            "aspect_ratio": aspect_ratio,
            "engine": "ffmpeg_fallback" if settings.enable_mock_providers else "ffmpeg",
            "supports_remotion": True,
            "status": "queued",
        }

    def build_render_output(
        self,
        job_id: str,
        clip_id: str,
        aspect_ratio: str,
        caption_style: str,
        source_path: str | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
        caption_groups: list[dict] | None = None,
        clip_start_time: float | None = None,
        cta_text: str | None = None,
        brand_profile: dict | None = None,
    ) -> dict:
        if settings.enable_mock_providers or not source_path:
            return {
                "output_url": f"render://{job_id}/{clip_id}/{aspect_ratio.replace(':', 'x')}.mp4",
                "subtitle_url": f"subtitle://{job_id}.srt",
                "thumbnail_url": f"https://placehold.co/320x568/png?text={clip_id}",
                "metadata_json": {
                    "engine": "ffmpeg_fallback",
                    "caption_burned_in": False,
                    "aspect_ratio": aspect_ratio,
                    "caption_style": caption_style,
                    "export_format": "mp4",
                    "render_mode": "simple_vertical_mvp",
                },
            }

        storage_dir = Path(settings.local_storage_path) / job_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        out_mp4 = storage_dir / f"{clip_id}.mp4"
        out_thumb = storage_dir / f"{clip_id}_thumb.jpg"
        out_srt = storage_dir / f"{clip_id}.srt"

        clip_start = float(clip_start_time or start_time or 0.0)
        clip_dur = float((end_time or 0.0) - (start_time or 0.0))
        fade_out_start = max(0.0, clip_dur - 0.5)
        audio_fade_out_start = max(0.0, clip_dur - 0.35)
        captions_ok = self._build_clip_srt(out_srt, caption_groups, clip_start)

        # ── Base: scale + pad to 9:16 ──────────────────────────────────────
        vf_parts = [
            "scale=1080:1920:force_original_aspect_ratio=decrease",
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
        ]

        # ── Fade in / fade out ─────────────────────────────────────────────
        vf_parts.append(f"fade=t=in:st=0:d=0.4")
        if fade_out_start > 0:
            vf_parts.append(f"fade=t=out:st={fade_out_start:.2f}:d=0.4")
        # Visual vibe: slight punch + clarity without over-processing.
        vf_parts.append("eq=contrast=1.07:saturation=1.12:brightness=0.02")
        vf_parts.append("unsharp=5:5:0.7:5:5:0.0")

        # ── Captions burned-in ─────────────────────────────────────────────
        if captions_ok:
            # Escape path for ffmpeg (colons are special on Windows paths)
            srt_path = str(out_srt).replace("\\", "/").replace(":", "\\:")
            style = self._style_str(caption_style)
            vf_parts.append(f"subtitles={srt_path}:force_style='{style}'")

        # ── CTA drawtext overlay ───────────────────────────────────────────
        if cta_text and clip_dur > 4.0:
            cta_safe = _escape_drawtext(cta_text[:55])
            cta_start = max(0.0, clip_dur - 5.0)
            brand = (brand_profile or {}).get("brand_settings", {})
            # Use brand primary colour or default navy
            bg_hex = (brand.get("primary_color") or "#0A2540").lstrip("#")
            r, g, b = int(bg_hex[0:2], 16), int(bg_hex[2:4], 16), int(bg_hex[4:6], 16)
            box_color = f"0x{b:02x}{g:02x}{r:02x}@0.88"
            vf_parts.append(
                f"drawtext=text='{cta_safe}'"
                f":fontsize=26:fontcolor=white"
                f":x=(w-text_w)/2:y=h-110"
                f":box=1:boxcolor={box_color}:boxborderw=18"
                f":enable='between(t,{cta_start:.1f},{clip_dur:.1f})'"
            )

        vf_filter = ",".join(vf_parts)

        # ── FFmpeg encode ──────────────────────────────────────────────────
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        if start_time is not None:
            cmd += ["-ss", str(start_time)]
        cmd += ["-i", source_path]
        if end_time is not None and start_time is not None:
            cmd += ["-t", str(clip_dur)]
        cmd += [
            "-vf", vf_filter,
            "-af", f"afade=t=in:st=0:d=0.25,afade=t=out:st={audio_fade_out_start:.2f}:d=0.35",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(out_mp4),
        ]

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()[-800:]}")

        # ── Thumbnail at mid-clip ──────────────────────────────────────────
        mid = clip_dur / 2
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(out_mp4),
             "-ss", f"{mid:.1f}", "-vframes", "1", "-q:v", "2", str(out_thumb)],
            capture_output=True,
        )

        base_url = f"/files/{job_id}"
        return {
            "output_url": f"{base_url}/{clip_id}.mp4",
            "subtitle_url": f"{base_url}/{clip_id}.srt" if captions_ok else f"subtitle://{job_id}.srt",
            "thumbnail_url": f"{base_url}/{clip_id}_thumb.jpg",
            "metadata_json": {
                "engine": "ffmpeg",
                "caption_burned_in": captions_ok,
                "cta_burned_in": bool(cta_text and clip_dur > 4.0),
                "effects_applied": ["fade_in_out", "contrast_boost", "saturation_boost", "unsharp", "audio_fade_in_out"],
                "aspect_ratio": aspect_ratio,
                "caption_style": caption_style,
                "export_format": "mp4",
                "render_mode": "full_feature_vertical",
            },
        }
