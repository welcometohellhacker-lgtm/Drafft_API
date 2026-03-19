import shutil
import subprocess
from pathlib import Path


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

    def render(self, composition: str, props_path: str, output_path: str, thumb_path: str, timeout_seconds: int = 180) -> dict:
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
