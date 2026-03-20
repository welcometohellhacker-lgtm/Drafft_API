import json
import shutil
import subprocess
from pathlib import Path

from app.core.config import settings


class RemotionCliService:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.renderer_root = project_root / 'remotion_renderer'

    def validate_runtime(self) -> dict:
        node_ok = shutil.which('node') is not None
        npm_ok = shutil.which('npm') is not None
        package_ok = (self.renderer_root / 'package.json').exists()
        render_script_ok = (self.renderer_root / 'render.mjs').exists()
        return {
            'node_available': node_ok,
            'npm_available': npm_ok,
            'package_json_present': package_ok,
            'render_script_present': render_script_ok,
            'ready': node_ok and package_ok and render_script_ok,
        }

    def _ffmpeg_placeholder_render(self, props_path: str, output_path: str, thumb_path: str) -> dict:
        """
        When ENABLE_MOCK_PROVIDERS=true, skip Node/Remotion entirely.

        This avoids failures in tests and local dev where:
        - No Node/npm/Chromium bundle is installed, or
        - Remotion would HTTP-fetch sourceVideoUrl from localhost:8000 while the
          FastAPI TestClient is not actually listening on that port.
        """
        ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
        props = json.loads(Path(props_path).read_text(encoding="utf-8"))
        comp = props.get("composition") or {}
        w = int(comp.get("width") or 1080)
        h = int(comp.get("height") or 1920)
        dur = float(props.get("clipDurationSec") or 5.0)
        dur = min(max(dur, 0.5), 60.0)

        out_mp4 = Path(output_path)
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        thumb = Path(thumb_path)
        thumb.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=#0A2540:s={w}x{h}:d={dur}",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r=48000:cl=stereo:d={dur}",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(out_mp4),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "ffmpeg mock render failed")[-2000:])

        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(out_mp4),
                "-ss",
                "0.5",
                "-vframes",
                "1",
                str(thumb),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        return {
            "stdout": json.dumps({"mock": True, "output": str(out_mp4), "thumbnail": str(thumb)}),
            "stderr": "",
            "output_path": str(out_mp4),
            "thumbnail_path": str(thumb),
            "runtime": {"mock": True, "engine": "ffmpeg_lavfi"},
        }

    def render(self, composition: str, props_path: str, output_path: str, thumb_path: str, timeout_seconds: int = 900) -> dict:
        if settings.enable_mock_providers:
            return self._ffmpeg_placeholder_render(props_path, output_path, thumb_path)

        runtime = self.validate_runtime()
        if not runtime['ready']:
            raise RuntimeError(f"Remotion runtime not ready: {runtime}")

        cmd = [
            'node',
            'render.mjs',
            '--composition', composition,
            '--props', props_path,
            '--out', output_path,
            '--thumb', thumb_path,
        ]
        proc = subprocess.run(
            cmd,
            cwd=self.renderer_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if proc.returncode != 0:
            stderr_tail = (proc.stderr or proc.stdout or 'Remotion render failed')[-2000:]
            raise RuntimeError(stderr_tail)
        return {
            'stdout': proc.stdout.strip(),
            'stderr': proc.stderr.strip(),
            'output_path': output_path,
            'thumbnail_path': thumb_path,
            'runtime': runtime,
        }
